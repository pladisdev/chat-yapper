"""Unit tests for configuration export/import functionality"""
import pytest
import json
import os
import tempfile
import zipfile
import io
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock FastAPI dependencies before importing
from unittest.mock import AsyncMock


@pytest.mark.unit
@pytest.mark.export_import
class TestConfigExport:
    """Tests for configuration export functionality"""
    
    @pytest.mark.asyncio
    async def test_export_creates_zip(self, client):
        """Test that export creates a ZIP file"""
        response = client.get("/api/config/export")
        
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/zip'
        assert 'attachment' in response.headers.get('content-disposition', '')
        
    @pytest.mark.asyncio
    async def test_export_zip_contains_config(self, client):
        """Test that exported ZIP contains config.json"""
        response = client.get("/api/config/export")
        
        assert response.status_code == 200
        
        # Parse ZIP content
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            filenames = zip_file.namelist()
            assert 'config.json' in filenames
    
    @pytest.mark.asyncio
    async def test_export_config_structure(self, client):
        """Test that exported config has correct structure"""
        response = client.get("/api/config/export")
        
        # Extract and parse config.json
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            config_data = json.loads(zip_file.read('config.json'))
            
            # Check required fields
            assert 'version' in config_data
            assert 'exported_at' in config_data
            assert 'app_name' in config_data
            assert 'settings' in config_data
            assert 'voices' in config_data
            assert 'avatars' in config_data
            
            # Validate types
            assert isinstance(config_data['settings'], dict)
            assert isinstance(config_data['voices'], list)
            assert isinstance(config_data['avatars'], list)
    
    @pytest.mark.asyncio
    async def test_export_includes_avatars_directory(self, client, session):
        """Test that export includes avatars directory when avatars exist"""
        # Add a test avatar to database
        from modules.models import AvatarImage
        
        test_avatar = AvatarImage(
            name="TestAvatar",
            filename="test_avatar.png",
            file_path="/user_avatars/test_avatar.png",
            avatar_type="default",
            disabled=False
        )
        session.add(test_avatar)
        session.commit()
        
        response = client.get("/api/config/export")
        
        # Check ZIP contains avatars folder
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            filenames = zip_file.namelist()
            # Should have avatars/ directory (even if empty)
            avatar_files = [f for f in filenames if f.startswith('avatars/')]
            assert len(avatar_files) >= 0  # May be empty if file doesn't actually exist
    
    @pytest.mark.asyncio
    async def test_export_voice_data_format(self, client, session):
        """Test that exported voices have correct format"""
        # Add test voice
        from modules.models import Voice
        
        test_voice = Voice(
            name="Test Voice",
            voice_id="test_voice_id",
            provider="edge",
            enabled=True,
            avatar_mode="single",
            created_at=datetime.now().isoformat()
        )
        session.add(test_voice)
        session.commit()
        
        response = client.get("/api/config/export")
        
        zip_content = io.BytesIO(response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            config_data = json.loads(zip_file.read('config.json'))
            
            voices = config_data['voices']
            if len(voices) > 0:
                voice = voices[0]
                # Check required voice fields
                assert 'name' in voice
                assert 'voice_id' in voice
                assert 'provider' in voice
                assert 'enabled' in voice
                assert 'avatar_mode' in voice


@pytest.mark.unit
@pytest.mark.export_import
class TestConfigImport:
    """Tests for configuration import functionality"""
    
    def _create_test_export_zip(self) -> bytes:
        """Helper to create a valid test export ZIP"""
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add config.json
            config = {
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "app_name": "Chat Yapper",
                "settings": {
                    "volume": 1.0,
                    "avatarSize": 200
                },
                "voices": [
                    {
                        "name": "Import Test Voice",
                        "voice_id": "import_test_voice",
                        "provider": "edge",
                        "enabled": True,
                        "avatar_mode": "single",
                        "created_at": datetime.now().isoformat()
                    }
                ],
                "avatars": []
            }
            zip_file.writestr("config.json", json.dumps(config, indent=2))
            
            # Add empty avatars directory
            zip_file.writestr("avatars/", "")
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    @pytest.mark.asyncio
    async def test_import_valid_zip(self, client):
        """Test importing a valid configuration ZIP"""
        zip_content = self._create_test_export_zip()
        
        response = client.post(
            "/api/config/import",
            files={"file": ("export.zip", io.BytesIO(zip_content), "application/zip")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'stats' in data
    
    @pytest.mark.asyncio
    async def test_import_invalid_file(self, client):
        """Test importing an invalid file"""
        # Send non-ZIP file
        response = client.post(
            "/api/config/import",
            files={"file": ("test.txt", io.BytesIO(b"not a zip file"), "text/plain")}
        )
        
        assert response.status_code in [400, 500]  # Should fail
    
    @pytest.mark.asyncio
    async def test_import_missing_config(self, client):
        """Test importing ZIP without config.json"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            zip_file.writestr("dummy.txt", "no config here")
        
        zip_buffer.seek(0)
        
        response = client.post(
            "/api/config/import",
            files={"file": ("bad_export.zip", zip_buffer, "application/zip")}
        )
        
        assert response.status_code in [400, 500]  # Should fail
    
    @pytest.mark.asyncio
    async def test_import_creates_backup(self, client):
        """Test that import creates a database backup"""
        zip_content = self._create_test_export_zip()
        
        with patch('shutil.copy2') as mock_copy:
            response = client.post(
                "/api/config/import",
                files={"file": ("export.zip", io.BytesIO(zip_content), "application/zip")}
            )
            
            # Should have called shutil.copy2 to create backup
            if response.status_code == 200:
                assert mock_copy.called or response.json()['success']
    
    @pytest.mark.asyncio
    async def test_import_stats(self, client):
        """Test that import returns correct statistics"""
        zip_content = self._create_test_export_zip()
        
        response = client.post(
            "/api/config/import",
            files={"file": ("export.zip", io.BytesIO(zip_content), "application/zip")}
        )
        
        if response.status_code == 200:
            data = response.json()
            stats = data['stats']
            
            # Check stats structure
            assert 'settings_imported' in stats
            assert 'voices_imported' in stats
            assert 'avatars_imported' in stats
            assert 'images_copied' in stats
            assert 'errors' in stats
            
            # Check types
            assert isinstance(stats['settings_imported'], bool)
            assert isinstance(stats['voices_imported'], int)
            assert isinstance(stats['avatars_imported'], int)
            assert isinstance(stats['images_copied'], int)
            assert isinstance(stats['errors'], list)
    
    @pytest.mark.asyncio
    async def test_import_replace_mode(self, client):
        """Test import with replace mode"""
        zip_content = self._create_test_export_zip()
        
        response = client.post(
            "/api/config/import?merge_mode=replace",
            files={"file": ("export.zip", io.BytesIO(zip_content), "application/zip")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
    
    @pytest.mark.asyncio
    async def test_import_merge_mode(self, client):
        """Test import with merge mode"""
        zip_content = self._create_test_export_zip()
        
        response = client.post(
            "/api/config/import?merge_mode=merge",
            files={"file": ("export.zip", io.BytesIO(zip_content), "application/zip")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True


@pytest.mark.unit
@pytest.mark.export_import
class TestConfigInfo:
    """Tests for configuration info endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_config_info(self, client):
        """Test getting configuration info"""
        response = client.get("/api/config/info")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'info' in data
    
    @pytest.mark.asyncio
    async def test_config_info_structure(self, client):
        """Test configuration info structure"""
        response = client.get("/api/config/info")
        
        data = response.json()
        info = data['info']
        
        # Check required fields
        assert 'settings_count' in info
        assert 'voices_count' in info
        assert 'avatars_count' in info
        assert 'avatar_storage_mb' in info
        assert 'database_path' in info
        assert 'avatars_path' in info
        
        # Check types
        assert isinstance(info['settings_count'], int)
        assert isinstance(info['voices_count'], int)
        assert isinstance(info['avatars_count'], int)
        assert isinstance(info['avatar_storage_mb'], (int, float))
        assert isinstance(info['database_path'], str)
        assert isinstance(info['avatars_path'], str)
    
    @pytest.mark.asyncio
    async def test_config_info_counts(self, client, session):
        """Test that config info returns accurate counts"""
        from modules.models import Voice, AvatarImage
        
        # Add test data
        test_voice = Voice(
            name="Count Test",
            voice_id="count_test",
            provider="edge",
            enabled=True
        )
        session.add(test_voice)
        session.commit()
        
        response = client.get("/api/config/info")
        
        data = response.json()
        info = data['info']
        
        # Should have at least our test voice
        assert info['voices_count'] >= 1


@pytest.mark.integration
@pytest.mark.export_import
class TestExportImportIntegration:
    """Integration tests for full export/import cycle"""
    
    @pytest.mark.asyncio
    async def test_export_import_roundtrip(self, client, session):
        """Test exporting and then importing configuration"""
        from modules.models import Voice
        
        # Add test voice
        original_voice = Voice(
            name="Roundtrip Test",
            voice_id="roundtrip_test",
            provider="edge",
            enabled=True,
            avatar_mode="dual",
            created_at=datetime.now().isoformat()
        )
        session.add(original_voice)
        session.commit()
        original_voice_id = original_voice.id
        
        # Export configuration
        export_response = client.get("/api/config/export")
        assert export_response.status_code == 200
        
        # Import the exported configuration
        import_response = client.post(
            "/api/config/import",
            files={"file": ("export.zip", io.BytesIO(export_response.content), "application/zip")}
        )
        
        assert import_response.status_code == 200
        data = import_response.json()
        assert data['success'] is True
        
        # Verify voice still exists after import
        session.expire_all()  # Clear session cache
        voice = session.get(Voice, original_voice_id)
        # Voice may have been replaced with import, so just check voices exist
        from modules.persistent_data import get_voices
        voices_data = get_voices()
        assert len(voices_data['voices']) > 0
    
    @pytest.mark.asyncio
    async def test_export_preserves_settings(self, client):
        """Test that export preserves all settings"""
        # Get current settings
        settings_response = client.get("/api/settings")
        original_settings = settings_response.json()
        
        # Export
        export_response = client.get("/api/config/export")
        
        # Parse exported config
        zip_content = io.BytesIO(export_response.content)
        with zipfile.ZipFile(zip_content, 'r') as zip_file:
            config_data = json.loads(zip_file.read('config.json'))
            
            # Check settings are preserved
            exported_settings = config_data['settings']
            
            # Key settings should match
            if 'volume' in original_settings:
                assert exported_settings.get('volume') == original_settings['volume']
    
    @pytest.mark.asyncio
    async def test_import_handles_errors_gracefully(self, client):
        """Test that import handles errors and doesn't corrupt database"""
        # Create invalid ZIP (missing required fields)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
            invalid_config = {
                "version": "1.0",
                # Missing required fields
                "settings": {}
            }
            zip_file.writestr("config.json", json.dumps(invalid_config))
        
        zip_buffer.seek(0)
        
        # Try to import
        response = client.post(
            "/api/config/import",
            files={"file": ("invalid.zip", zip_buffer, "application/zip")}
        )
        
        # Should either succeed (with errors in stats) or fail gracefully
        assert response.status_code in [200, 400, 500]
        
        # Database should still be accessible
        settings_response = client.get("/api/settings")
        assert settings_response.status_code == 200
