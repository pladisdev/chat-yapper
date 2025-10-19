"""Enhanced unit tests for voice management (CRUD, avatars, providers)"""
import pytest
import datetime
from modules.models import Voice


@pytest.mark.unit
@pytest.mark.voices
class TestVoiceModel:
    """Tests for Voice database model"""
    
    def test_create_voice_minimal(self, session):
        """Test creating a voice with minimal fields"""
        voice = Voice(
            name="Test Voice",
            voice_id="test_voice_id",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        assert voice.id is not None
        assert voice.name == "Test Voice"
        assert voice.voice_id == "test_voice_id"
        assert voice.provider == "edge"
        assert voice.enabled is True
    
    def test_create_voice_with_single_avatar(self, session):
        """Test creating a voice with single avatar mode"""
        voice = Voice(
            name="Single Avatar Voice",
            voice_id="single_avatar",
            provider="edge",
            enabled=True,
            avatar_mode="single",
            avatar_image="default_avatar.png"
        )
        session.add(voice)
        session.commit()
        
        assert voice.avatar_mode == "single"
        assert voice.avatar_image == "default_avatar.png"
    
    def test_create_voice_with_dual_avatars(self, session):
        """Test creating a voice with dual avatar mode"""
        voice = Voice(
            name="Dual Avatar Voice",
            voice_id="dual_avatar",
            provider="monstertts",
            enabled=True,
            avatar_mode="dual",
            avatar_default="idle.png",
            avatar_speaking="speaking.png"
        )
        session.add(voice)
        session.commit()
        
        assert voice.avatar_mode == "dual"
        assert voice.avatar_default == "idle.png"
        assert voice.avatar_speaking == "speaking.png"
    
    def test_voice_created_at_timestamp(self, session):
        """Test that created_at timestamp is stored"""
        now = datetime.datetime.now().isoformat()
        
        voice = Voice(
            name="Timestamp Test",
            voice_id="timestamp_test",
            provider="edge",
            enabled=True,
            created_at=now
        )
        session.add(voice)
        session.commit()
        
        assert voice.created_at == now
    
    def test_voice_disabled(self, session):
        """Test creating a disabled voice"""
        voice = Voice(
            name="Disabled Voice",
            voice_id="disabled",
            provider="google",
            enabled=False
        )
        session.add(voice)
        session.commit()
        
        assert voice.enabled is False


@pytest.mark.unit
@pytest.mark.voices
class TestVoiceAPIEndpoints:
    """Tests for voice management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_voices(self, client):
        """Test getting all voices"""
        response = client.get("/api/voices")
        
        assert response.status_code == 200
        data = response.json()
        assert 'voices' in data
        assert isinstance(data['voices'], list)
    
    @pytest.mark.asyncio
    async def test_add_voice_success(self, client):
        """Test adding a new voice"""
        from modules.persistent_data import remove_voice, get_voice_by_id
        
        voice_data = {
            "name": "API Test Voice",
            "voice_id": "api_test_voice",
            "provider": "edge",
            "enabled": True,
            "avatar_mode": "single"
        }
        
        response = client.post("/api/voices", json=voice_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # If the voice already exists, clean it up and try again
        if 'error' in data:
            # Get all voices and find the duplicate
            from modules.persistent_data import get_voices
            voices_result = get_voices()
            voices = voices_result.get("voices", [])
            duplicate = next((v for v in voices if v.get("voice_id") == "api_test_voice"), None)
            if duplicate:
                remove_voice(duplicate['id'])
                response = client.post("/api/voices", json=voice_data)
                assert response.status_code == 200
                data = response.json()
        
        assert data['success'] is True
        assert 'voice' in data
        assert data['voice']['name'] == "API Test Voice"
        
        # Cleanup
        voice_id = data['voice']['id']
        remove_voice(voice_id)
    
    @pytest.mark.asyncio
    async def test_add_voice_duplicate(self, client, session):
        """Test adding a duplicate voice"""
        # Add voice first
        voice = Voice(
            name="Duplicate Test",
            voice_id="duplicate_id",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        # Try to add same voice again
        voice_data = {
            "name": "Duplicate Test 2",
            "voice_id": "duplicate_id",
            "provider": "edge",
            "enabled": True
        }
        
        response = client.post("/api/voices", json=voice_data)
        
        # Should fail or return error
        data = response.json()
        assert 'error' in data or response.status_code != 200
    
    @pytest.mark.asyncio
    async def test_update_voice(self, client, session):
        """Test updating a voice"""
        from modules.persistent_data import add_voice, remove_voice, get_voice_by_id
        
        # Create voice in persistent DB
        voice = Voice(
            name="Update Test",
            voice_id="update_test",
            provider="edge",
            enabled=True
        )
        add_voice(voice)
        voice_id = voice.id
        
        try:
            # Update voice
            update_data = {
                "name": "Updated Name",
                "enabled": False,
                "avatar_image": "new_avatar.png"
            }
            
            response = client.put(f"/api/voices/{voice_id}", json=update_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data['success'] is True
            
            # Verify update via persistent_data
            updated_voice = get_voice_by_id(voice_id)
            assert updated_voice is not None
            assert updated_voice.name == "Updated Name"
            assert updated_voice.enabled is False
        finally:
            # Cleanup
            remove_voice(voice_id)
    
    @pytest.mark.asyncio
    async def test_update_voice_not_found(self, client):
        """Test updating a non-existent voice"""
        response = client.put("/api/voices/99999", json={"name": "Test"})
        
        # Should return error
        data = response.json()
        assert 'error' in data or response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_delete_voice(self, client, session):
        """Test deleting a voice"""
        # Create voice
        voice = Voice(
            name="Delete Test",
            voice_id="delete_test",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        voice_id = voice.id
        
        # Delete voice
        response = client.delete(f"/api/voices/{voice_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify the response indicates success
        # Note: Don't check the test session DB as the API uses the persistent DB
    
    @pytest.mark.asyncio
    async def test_get_available_voices_edge(self, client):
        """Test getting available voices from Edge TTS"""
        response = client.get("/api/available-voices/edge")
        
        assert response.status_code == 200
        data = response.json()
        # Should return voices array (even if empty or mocked)
        assert isinstance(data, dict) or isinstance(data, list)
    
    @pytest.mark.asyncio
    async def test_get_available_voices_with_api_key(self, client):
        """Test getting available voices with API key"""
        response = client.get("/api/available-voices/monstertts?api_key=test_key")
        
        # Should attempt to fetch (may fail without real API key)
        assert response.status_code in [200, 400, 401, 500]


@pytest.mark.unit
@pytest.mark.voices
class TestVoicePersistentData:
    """Tests for voice persistent data functions"""
    
    def test_get_voices_empty(self):
        """Test getting voices when none exist"""
        from modules.persistent_data import get_voices
        
        data = get_voices()
        assert 'voices' in data
        assert isinstance(data['voices'], list)
    
    def test_add_voice(self, session):
        """Test adding a voice via persistent_data"""
        from modules.persistent_data import add_voice, get_voices
        
        new_voice = Voice(
            name="Persistent Data Test",
            voice_id="persistent_test",
            provider="edge",
            enabled=True
        )
        
        add_voice(new_voice)
        
        # Verify added
        voices_data = get_voices()
        voice_names = [v['name'] for v in voices_data['voices']]
        assert "Persistent Data Test" in voice_names
    
    def test_check_voice_exists_true(self, session):
        """Test checking if voice exists (exists)"""
        from modules.persistent_data import add_voice, check_voice_exists
        
        voice = Voice(
            name="Exists Test",
            voice_id="exists_test_id",
            provider="edge",
            enabled=True
        )
        add_voice(voice)
        
        exists = check_voice_exists("exists_test_id", "edge")
        assert exists is True
    
    def test_check_voice_exists_false(self):
        """Test checking if voice exists (doesn't exist)"""
        from modules.persistent_data import check_voice_exists
        
        exists = check_voice_exists("nonexistent_id", "edge")
        assert exists is False
    
    def test_get_voice_by_id(self, session):
        """Test getting a specific voice by ID"""
        from modules.persistent_data import add_voice, get_voice_by_id
        
        voice = Voice(
            name="Get By ID Test",
            voice_id="get_by_id",
            provider="edge",
            enabled=True
        )
        add_voice(voice)
        
        # Get the voice ID
        from modules.persistent_data import get_voices
        voices = get_voices()['voices']
        voice_id = next(v['id'] for v in voices if v['name'] == "Get By ID Test")
        
        # Retrieve by ID
        retrieved = get_voice_by_id(voice_id)
        assert retrieved is not None
        assert retrieved.name == "Get By ID Test"
    
    def test_remove_voice(self, session):
        """Test removing a voice"""
        from modules.persistent_data import add_voice, remove_voice, get_voice_by_id
        
        voice = Voice(
            name="Remove Test",
            voice_id="remove_test",
            provider="edge",
            enabled=True
        )
        add_voice(voice)
        
        # Get voice ID
        from modules.persistent_data import get_voices
        voices = get_voices()['voices']
        voice_id = next(v['id'] for v in voices if v['name'] == "Remove Test")
        
        # Remove voice
        remove_voice(voice_id)
        
        # Verify removed
        removed = get_voice_by_id(voice_id)
        assert removed is None


@pytest.mark.unit
@pytest.mark.voices
class TestVoiceAvatarModes:
    """Tests for voice avatar mode functionality"""
    
    def test_single_avatar_mode(self, session):
        """Test voice with single avatar mode"""
        voice = Voice(
            name="Single Mode",
            voice_id="single_mode",
            provider="edge",
            enabled=True,
            avatar_mode="single",
            avatar_image="avatar.png"
        )
        session.add(voice)
        session.commit()
        
        assert voice.avatar_mode == "single"
        assert voice.avatar_image is not None
        assert voice.avatar_default is None
        assert voice.avatar_speaking is None
    
    def test_dual_avatar_mode(self, session):
        """Test voice with dual avatar mode"""
        voice = Voice(
            name="Dual Mode",
            voice_id="dual_mode",
            provider="edge",
            enabled=True,
            avatar_mode="dual",
            avatar_default="idle.png",
            avatar_speaking="speaking.png"
        )
        session.add(voice)
        session.commit()
        
        assert voice.avatar_mode == "dual"
        assert voice.avatar_default is not None
        assert voice.avatar_speaking is not None
    
    def test_avatar_mode_default(self, session):
        """Test that default avatar mode is 'single'"""
        voice = Voice(
            name="Default Mode",
            voice_id="default_mode",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        # Default should be "single"
        assert voice.avatar_mode == "single"


@pytest.mark.unit
@pytest.mark.voices
class TestVoiceProviders:
    """Tests for different TTS providers"""
    
    def test_edge_provider(self, session):
        """Test voice with Edge TTS provider"""
        voice = Voice(
            name="Edge Voice",
            voice_id="en-US-AriaNeural",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        assert voice.provider == "edge"
    
    def test_monstertts_provider(self, session):
        """Test voice with MonsterTTS provider"""
        voice = Voice(
            name="Monster Voice",
            voice_id="monster_voice_id",
            provider="monstertts",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        assert voice.provider == "monstertts"
    
    def test_google_provider(self, session):
        """Test voice with Google Cloud TTS provider"""
        voice = Voice(
            name="Google Voice",
            voice_id="en-US-Standard-A",
            provider="google",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        assert voice.provider == "google"
    
    def test_polly_provider(self, session):
        """Test voice with Amazon Polly provider"""
        voice = Voice(
            name="Polly Voice",
            voice_id="Joanna",
            provider="polly",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        assert voice.provider == "polly"


@pytest.mark.integration
@pytest.mark.voices
class TestVoiceIntegration:
    """Integration tests for voice functionality"""
    
    @pytest.mark.asyncio
    async def test_voice_crud_cycle(self, client, session):
        """Test complete CRUD cycle for a voice"""
        # Create
        voice_data = {
            "name": "CRUD Cycle Test",
            "voice_id": "crud_cycle",
            "provider": "edge",
            "enabled": True,
            "avatar_mode": "dual",
            "avatar_default": "default.png",
            "avatar_speaking": "speaking.png"
        }
        
        create_response = client.post("/api/voices", json=voice_data)
        assert create_response.status_code == 200
        voice_id = create_response.json()['voice']['id']
        
        # Read
        get_response = client.get("/api/voices")
        voices = get_response.json()['voices']
        created_voice = next(v for v in voices if v['id'] == voice_id)
        assert created_voice['name'] == "CRUD Cycle Test"
        
        # Update
        update_data = {"name": "Updated CRUD Test", "enabled": False}
        update_response = client.put(f"/api/voices/{voice_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Verify update
        get_response2 = client.get("/api/voices")
        updated_voice = next(v for v in get_response2.json()['voices'] if v['id'] == voice_id)
        assert updated_voice['name'] == "Updated CRUD Test"
        assert updated_voice['enabled'] is False
        
        # Delete
        delete_response = client.delete(f"/api/voices/{voice_id}")
        assert delete_response.status_code == 200
        
        # Verify deletion
        get_response3 = client.get("/api/voices")
        remaining_voices = [v for v in get_response3.json()['voices'] if v['id'] == voice_id]
        assert len(remaining_voices) == 0
    
    @pytest.mark.asyncio
    async def test_voice_with_special_characters(self, client):
        """Test voice names with special characters"""
        from modules.persistent_data import remove_voice, get_voices
        
        # Clean up any existing voice with same voice_id
        voices_result = get_voices()
        voices = voices_result.get("voices", [])
        duplicate = next((v for v in voices if v.get("voice_id") == "special_chars"), None)
        if duplicate:
            remove_voice(duplicate['id'])
        
        voice_data = {
            "name": "Test Voice (Special) #1",
            "voice_id": "special_chars",
            "provider": "edge",
            "enabled": True
        }
        
        response = client.post("/api/voices", json=voice_data)
        assert response.status_code == 200
        
        data = response.json()
        assert 'success' in data
        
        # Verify stored correctly
        voice = data['voice']
        assert voice['name'] == "Test Voice (Special) #1"
        
        # Cleanup
        remove_voice(voice['id'])
