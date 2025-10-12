"""Unit tests for database models (Setting, Voice, AvatarImage)"""
import json
import pytest
from datetime import datetime
from modules.models import Setting, Voice, AvatarImage


@pytest.mark.unit
@pytest.mark.models
class TestSetting:
    """Tests for the Setting model"""
    
    def test_create_setting(self, session):
        """Test creating a setting"""
        setting = Setting(key="test_key", value_json='{"value": "test"}')
        session.add(setting)
        session.commit()
        session.refresh(setting)
        
        assert setting.id is not None
        assert setting.key == "test_key"
        assert setting.value_json == '{"value": "test"}'
    
    def test_setting_json_storage(self, session):
        """Test storing complex JSON in settings"""
        complex_value = {
            "string": "test",
            "number": 42,
            "boolean": True,
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }
        
        setting = Setting(key="complex", value_json=json.dumps(complex_value))
        session.add(setting)
        session.commit()
        session.refresh(setting)
        
        # Verify we can parse it back
        parsed = json.loads(setting.value_json)
        assert parsed == complex_value
    
    def test_update_setting(self, session):
        """Test updating a setting value"""
        setting = Setting(key="update_test", value_json='{"value": "old"}')
        session.add(setting)
        session.commit()
        
        # Update the value
        setting.value_json = '{"value": "new"}'
        session.add(setting)
        session.commit()
        session.refresh(setting)
        
        assert json.loads(setting.value_json)["value"] == "new"


@pytest.mark.unit
@pytest.mark.models
class TestVoice:
    """Tests for the Voice model"""
    
    def test_create_voice_minimal(self, session):
        """Test creating a voice with minimal fields"""
        voice = Voice(
            name="Test Voice",
            voice_id="en-US-TestVoice",
            provider="edge"
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        assert voice.id is not None
        assert voice.name == "Test Voice"
        assert voice.voice_id == "en-US-TestVoice"
        assert voice.provider == "edge"
        assert voice.enabled is True  # Default value
        assert voice.avatar_mode == "single"  # Default value
    
    def test_create_voice_full(self, session):
        """Test creating a voice with all fields"""
        voice = Voice(
            name="Full Voice",
            voice_id="en-US-FullVoice",
            provider="elevenlabs",
            enabled=False,
            avatar_image="avatar.png",
            avatar_default="default.png",
            avatar_speaking="speaking.png",
            avatar_mode="dual",
            created_at="2025-10-08T12:00:00"
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        assert voice.id is not None
        assert voice.name == "Full Voice"
        assert voice.enabled is False
        assert voice.avatar_mode == "dual"
        assert voice.avatar_default == "default.png"
        assert voice.avatar_speaking == "speaking.png"
    
    def test_voice_providers(self, session):
        """Test creating voices with different providers"""
        providers = ["edge", "elevenlabs", "openai", "azure", "aws"]
        
        for provider in providers:
            voice = Voice(
                name=f"{provider} Voice",
                voice_id=f"test-{provider}",
                provider=provider
            )
            session.add(voice)
        
        session.commit()
        
        # Verify all were created
        voices = session.query(Voice).all()
        assert len(voices) == len(providers)
        assert set(v.provider for v in voices) == set(providers)
    
    def test_voice_avatar_modes(self, session):
        """Test voice with different avatar modes"""
        single_mode = Voice(
            name="Single Mode",
            voice_id="single",
            provider="edge",
            avatar_mode="single",
            avatar_image="single.png"
        )
        
        dual_mode = Voice(
            name="Dual Mode",
            voice_id="dual",
            provider="edge",
            avatar_mode="dual",
            avatar_default="default.png",
            avatar_speaking="speaking.png"
        )
        
        session.add(single_mode)
        session.add(dual_mode)
        session.commit()
        
        voices = session.query(Voice).all()
        assert len(voices) == 2
        assert any(v.avatar_mode == "single" for v in voices)
        assert any(v.avatar_mode == "dual" for v in voices)
    
    def test_disable_voice(self, session):
        """Test disabling a voice"""
        voice = Voice(
            name="Disable Test",
            voice_id="test",
            provider="edge",
            enabled=True
        )
        session.add(voice)
        session.commit()
        
        # Disable the voice
        voice.enabled = False
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        assert voice.enabled is False


@pytest.mark.unit
@pytest.mark.models
class TestAvatarImage:
    """Tests for the AvatarImage model"""
    
    def test_create_avatar_image_minimal(self, session):
        """Test creating an avatar image with minimal fields"""
        avatar = AvatarImage(
            name="Test Avatar",
            filename="test.png",
            file_path="/path/to/test.png"
        )
        session.add(avatar)
        session.commit()
        session.refresh(avatar)
        
        assert avatar.id is not None
        assert avatar.name == "Test Avatar"
        assert avatar.filename == "test.png"
        assert avatar.file_path == "/path/to/test.png"
        assert avatar.avatar_type == "default"  # Default value
    
    def test_create_avatar_image_full(self, session):
        """Test creating an avatar image with all fields"""
        avatar = AvatarImage(
            name="Full Avatar",
            filename="full.png",
            file_path="/path/to/full.png",
            upload_date="2025-10-08T12:00:00",
            file_size=2048,
            avatar_type="speaking",
            avatar_group_id="group-123",
            voice_id=1,
            spawn_position=3
        )
        session.add(avatar)
        session.commit()
        session.refresh(avatar)
        
        assert avatar.id is not None
        assert avatar.name == "Full Avatar"
        assert avatar.file_size == 2048
        assert avatar.avatar_type == "speaking"
        assert avatar.avatar_group_id == "group-123"
        assert avatar.voice_id == 1
        assert avatar.spawn_position == 3
    
    def test_avatar_types(self, session):
        """Test creating avatars with different types"""
        default_avatar = AvatarImage(
            name="Default",
            filename="default.png",
            file_path="/path/default.png",
            avatar_type="default"
        )
        
        speaking_avatar = AvatarImage(
            name="Speaking",
            filename="speaking.png",
            file_path="/path/speaking.png",
            avatar_type="speaking"
        )
        
        session.add(default_avatar)
        session.add(speaking_avatar)
        session.commit()
        
        avatars = session.query(AvatarImage).all()
        assert len(avatars) == 2
        assert any(a.avatar_type == "default" for a in avatars)
        assert any(a.avatar_type == "speaking" for a in avatars)
    
    def test_avatar_with_voice_assignment(self, session):
        """Test avatar assigned to a specific voice"""
        voice = Voice(
            name="Test Voice",
            voice_id="test",
            provider="edge"
        )
        session.add(voice)
        session.commit()
        session.refresh(voice)
        
        avatar = AvatarImage(
            name="Voice Avatar",
            filename="voice_avatar.png",
            file_path="/path/voice_avatar.png",
            voice_id=voice.id
        )
        session.add(avatar)
        session.commit()
        session.refresh(avatar)
        
        assert avatar.voice_id == voice.id
    
    def test_avatar_spawn_positions(self, session):
        """Test avatars with specific spawn positions"""
        for position in range(1, 7):
            avatar = AvatarImage(
                name=f"Avatar {position}",
                filename=f"avatar{position}.png",
                file_path=f"/path/avatar{position}.png",
                spawn_position=position
            )
            session.add(avatar)
        
        session.commit()
        
        avatars = session.query(AvatarImage).all()
        assert len(avatars) == 6
        positions = {a.spawn_position for a in avatars}
        assert positions == {1, 2, 3, 4, 5, 6}
    
    def test_avatar_group(self, session):
        """Test avatars in the same group (dual mode)"""
        group_id = "group-abc-123"
        
        default_avatar = AvatarImage(
            name="Default Avatar",
            filename="default.png",
            file_path="/path/default.png",
            avatar_type="default",
            avatar_group_id=group_id
        )
        
        speaking_avatar = AvatarImage(
            name="Speaking Avatar",
            filename="speaking.png",
            file_path="/path/speaking.png",
            avatar_type="speaking",
            avatar_group_id=group_id
        )
        
        session.add(default_avatar)
        session.add(speaking_avatar)
        session.commit()
        
        # Query avatars in the same group
        group_avatars = session.query(AvatarImage).filter(
            AvatarImage.avatar_group_id == group_id
        ).all()
        
        assert len(group_avatars) == 2
        assert any(a.avatar_type == "default" for a in group_avatars)
        assert any(a.avatar_type == "speaking" for a in group_avatars)
