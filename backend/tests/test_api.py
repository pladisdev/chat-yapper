"""Unit tests for FastAPI endpoints"""
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.mark.unit
@pytest.mark.api
class TestSettingsEndpoints:
    """Tests for settings-related API endpoints"""
    
    def test_get_settings(self, client, session, test_settings):
        """Test getting application settings"""
        # Add some test settings to database
        from models import Setting
        
        for key, value in test_settings.items():
            setting = Setting(key=key, value_json=json.dumps(value))
            session.add(setting)
        session.commit()
        
        response = client.get("/api/settings")
        
        assert response.status_code == 200
        data = response.json()
        assert "twitchChannel" in data
        assert data["twitchChannel"] == "test_channel"
    
    def test_update_settings(self, client, session):
        """Test updating application settings"""
        new_settings = {
            "twitchChannel": "updated_channel",
            "ttsProvider": "openai"
        }
        
        response = client.post(
            "/api/settings",
            json=new_settings
        )
        
        assert response.status_code == 200
        
        # Verify settings were saved
        from models import Setting
        saved_settings = {}
        for setting in session.query(Setting).all():
            saved_settings[setting.key] = json.loads(setting.value_json)
        
        assert saved_settings["twitchChannel"] == "updated_channel"


@pytest.mark.unit
@pytest.mark.api
class TestVoiceEndpoints:
    """Tests for voice-related API endpoints"""
    
    def test_get_voices_empty(self, client, session):
        """Test getting voices when database is empty"""
        response = client.get("/api/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_voices(self, client, session):
        """Test getting voices"""
        from models import Voice
        
        # Add test voices
        voices = [
            Voice(name="Voice 1", voice_id="voice1", provider="edge"),
            Voice(name="Voice 2", voice_id="voice2", provider="elevenlabs")
        ]
        for voice in voices:
            session.add(voice)
        session.commit()
        
        response = client.get("/api/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "Voice 1"
        assert data[1]["name"] == "Voice 2"
    
    def test_add_voice(self, client, session):
        """Test adding a new voice"""
        voice_data = {
            "name": "New Voice",
            "voice_id": "new-voice-id",
            "provider": "edge",
            "enabled": True,
            "avatar_mode": "single"
        }
        
        response = client.post("/api/voices", json=voice_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Voice"
        assert "id" in data
        
        # Verify in database
        from models import Voice
        voices = session.query(Voice).all()
        assert len(voices) == 1
        assert voices[0].name == "New Voice"
    
    def test_update_voice(self, client, session):
        """Test updating an existing voice"""
        from models import Voice
        
        # Create initial voice
        voice = Voice(
            name="Original Name",
            voice_id="test-id",
            provider="edge"
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        # Update the voice
        update_data = {
            "id": voice.id,
            "name": "Updated Name",
            "voice_id": "test-id",
            "provider": "edge",
            "enabled": False
        }
        
        response = client.put(f"/api/voices/{voice.id}", json=update_data)
        
        assert response.status_code == 200
        
        # Verify update
        session.refresh(voice)
        assert voice.name == "Updated Name"
        assert voice.enabled is False
    
    def test_delete_voice(self, client, session):
        """Test deleting a voice"""
        from models import Voice
        
        # Create voice to delete
        voice = Voice(name="Delete Me", voice_id="delete", provider="edge")
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        response = client.delete(f"/api/voices/{voice.id}")
        
        assert response.status_code == 200
        
        # Verify deletion
        voices = session.query(Voice).all()
        assert len(voices) == 0


@pytest.mark.unit
@pytest.mark.api
class TestAvatarEndpoints:
    """Tests for avatar-related API endpoints"""
    
    def test_get_avatars_empty(self, client, session):
        """Test getting avatars when database is empty"""
        response = client.get("/api/avatars")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_avatars(self, client, session):
        """Test getting avatar images"""
        from models import AvatarImage
        
        # Add test avatars
        avatars = [
            AvatarImage(
                name="Avatar 1",
                filename="avatar1.png",
                file_path="/path/avatar1.png"
            ),
            AvatarImage(
                name="Avatar 2",
                filename="avatar2.png",
                file_path="/path/avatar2.png"
            )
        ]
        for avatar in avatars:
            session.add(avatar)
        session.commit()
        
        response = client.get("/api/avatars")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    def test_delete_avatar(self, client, session):
        """Test deleting an avatar"""
        from models import AvatarImage
        
        # Create avatar to delete
        avatar = AvatarImage(
            name="Delete Me",
            filename="delete.png",
            file_path="/path/delete.png"
        )
        session.add(avatar)
        session.commit()
        session.refresh(avatar)
        
        response = client.delete(f"/api/avatars/{avatar.id}")
        
        assert response.status_code == 200
        
        # Verify deletion
        avatars = session.query(AvatarImage).all()
        assert len(avatars) == 0


@pytest.mark.unit
@pytest.mark.api
class TestTTSControlEndpoints:
    """Tests for TTS control endpoints"""
    
    @pytest.mark.asyncio
    async def test_stop_all_tts(self, client):
        """Test stopping all TTS"""
        response = client.post("/api/tts/stop-all")
        
        # Should succeed even if no TTS is playing
        assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_toggle_tts_enabled(self, client):
        """Test toggling TTS enabled state"""
        # Enable TTS
        response = client.post("/api/tts/toggle", json={"enabled": True})
        assert response.status_code == 200
        
        # Disable TTS
        response = client.post("/api/tts/toggle", json={"enabled": False})
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.api
class TestHealthEndpoint:
    """Tests for health check endpoint"""
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.integration
@pytest.mark.api
class TestWebSocketConnection:
    """Integration tests for WebSocket connections"""
    
    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    def test_websocket_connection(self, client):
        """Test establishing WebSocket connection"""
        with client.websocket_connect("/ws") as websocket:
            # Should connect successfully
            assert websocket is not None
    
    @pytest.mark.skip(reason="WebSocket testing requires additional setup")
    def test_websocket_receive_events(self, client):
        """Test receiving events over WebSocket"""
        with client.websocket_connect("/ws") as websocket:
            # Send a test event
            test_event = {
                "type": "test",
                "data": "test_data"
            }
            
            # In a real test, we'd verify the event was received
            pass


@pytest.mark.unit
@pytest.mark.api  
class TestMessageFilterEndpoint:
    """Tests for message filtering endpoint"""
    
    def test_message_filter_basic(self, client, session, test_settings):
        """Test basic message filtering"""
        # Set up test settings
        from models import Setting
        
        for key, value in test_settings.items():
            setting = Setting(key=key, value_json=json.dumps(value))
            session.add(setting)
        session.commit()
        
        # Test filtering a message
        test_data = {
            "message": "Hello world!",
            "username": "test_user"
        }
        
        response = client.post("/api/test-message-filter", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "should_process" in data
        assert "filtered_text" in data
    
    def test_message_filter_command(self, client, session):
        """Test filtering messages with command prefix"""
        from models import Setting
        
        # Enable command filtering
        settings = {
            "enableCommandFilter": True,
            "commandPrefixFilter": "!"
        }
        
        for key, value in settings.items():
            setting = Setting(key=key, value_json=json.dumps(value))
            session.add(setting)
        session.commit()
        
        # Test with command
        test_data = {
            "message": "!command test",
            "username": "test_user"
        }
        
        response = client.post("/api/test-message-filter", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        # Commands should be filtered
        assert data["should_process"] is False
    
    def test_message_filter_too_short(self, client, session):
        """Test filtering messages that are too short"""
        from models import Setting
        
        settings = {
            "minMessageLength": 5
        }
        
        for key, value in settings.items():
            setting = Setting(key=key, value_json=json.dumps(value))
            session.add(setting)
        session.commit()
        
        # Test with short message
        test_data = {
            "message": "Hi",
            "username": "test_user"
        }
        
        response = client.post("/api/test-message-filter", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        # Short messages should be filtered
        assert data["should_process"] is False
    
    def test_message_filter_too_long(self, client, session):
        """Test filtering messages that are too long"""
        from models import Setting
        
        settings = {
            "maxMessageLength": 10
        }
        
        for key, value in settings.items():
            setting = Setting(key=key, value_json=json.dumps(value))
            session.add(setting)
        session.commit()
        
        # Test with long message
        test_data = {
            "message": "This is a very long message that exceeds the limit",
            "username": "test_user"
        }
        
        response = client.post("/api/test-message-filter", json=test_data)
        
        assert response.status_code == 200
        data = response.json()
        # Long messages should be truncated but still processed
        assert data["should_process"] is True
        assert len(data["filtered_text"]) <= 10
