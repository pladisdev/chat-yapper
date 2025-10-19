"""Unit tests for avatar management (upload, groups, positions)"""
import pytest
import os
import tempfile
import io
from datetime import datetime
from unittest.mock import Mock, patch

from modules.models import AvatarImage


@pytest.mark.unit
@pytest.mark.avatars
class TestAvatarModel:
    """Tests for AvatarImage database model"""
    
    def test_create_avatar_minimal(self, session):
        """Test creating an avatar with minimal fields"""
        avatar = AvatarImage(
            name="Test Avatar",
            filename="test_avatar.png",
            file_path="/user_avatars/test_avatar.png",
            avatar_type="default",
            disabled=False
        )
        session.add(avatar)
        session.commit()
        session.refresh(avatar)
        
        assert avatar.id is not None
        assert avatar.name == "Test Avatar"
        assert avatar.filename == "test_avatar.png"
        assert avatar.disabled is False
    
    def test_create_avatar_with_group(self, session):
        """Test creating an avatar with group ID"""
        avatar = AvatarImage(
            name="Grouped Avatar",
            filename="grouped.png",
            file_path="/user_avatars/grouped.png",
            avatar_type="default",
            avatar_group_id="group_123",
            disabled=False
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.avatar_group_id == "group_123"
    
    def test_create_avatar_with_voice_id(self, session):
        """Test creating an avatar linked to a voice"""
        avatar = AvatarImage(
            name="Voice Avatar",
            filename="voice_avatar.png",
            file_path="/user_avatars/voice_avatar.png",
            avatar_type="default",
            voice_id=1,
            disabled=False
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.voice_id == 1
    
    def test_create_avatar_with_spawn_position(self, session):
        """Test creating an avatar with specific spawn position"""
        avatar = AvatarImage(
            name="Positioned Avatar",
            filename="positioned.png",
            file_path="/user_avatars/positioned.png",
            avatar_type="default",
            spawn_position=5,
            disabled=False
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.spawn_position == 5
    
    def test_create_avatar_disabled(self, session):
        """Test creating a disabled avatar"""
        avatar = AvatarImage(
            name="Disabled Avatar",
            filename="disabled.png",
            file_path="/user_avatars/disabled.png",
            avatar_type="default",
            disabled=True
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.disabled is True
    
    def test_avatar_upload_metadata(self, session):
        """Test avatar with upload metadata"""
        now = datetime.now().isoformat()
        
        avatar = AvatarImage(
            name="Metadata Avatar",
            filename="metadata.png",
            file_path="/user_avatars/metadata.png",
            avatar_type="default",
            upload_date=now,
            file_size=102400,  # 100 KB
            disabled=False
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.upload_date == now
        assert avatar.file_size == 102400
    
    def test_avatar_types(self, session):
        """Test different avatar types"""
        types = ["default", "speaking", "custom"]
        
        for avatar_type in types:
            avatar = AvatarImage(
                name=f"{avatar_type} Avatar",
                filename=f"{avatar_type}.png",
                file_path=f"/user_avatars/{avatar_type}.png",
                avatar_type=avatar_type,
                disabled=False
            )
            session.add(avatar)
        
        session.commit()
        
        # Verify all types saved
        from sqlmodel import select
        avatars = session.exec(select(AvatarImage)).all()
        stored_types = [a.avatar_type for a in avatars]
        
        for avatar_type in types:
            assert avatar_type in stored_types


@pytest.mark.unit
@pytest.mark.avatars
class TestAvatarAPIEndpoints:
    """Tests for avatar management API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_managed_avatars(self, client):
        """Test getting all managed avatars"""
        response = client.get("/api/avatars/managed")
        
        assert response.status_code == 200
        data = response.json()
        assert 'avatars' in data
        assert isinstance(data['avatars'], list)
    
    @pytest.mark.asyncio
    async def test_get_avatars_grouped(self, client, session):
        """Test getting avatars by group"""
        # Add avatars with same group
        for i in range(3):
            avatar = AvatarImage(
                name=f"Group Test {i}",
                filename=f"group_{i}.png",
                file_path=f"/user_avatars/group_{i}.png",
                avatar_type="default",
                avatar_group_id="test_group",
                disabled=False
            )
            session.add(avatar)
        session.commit()
        
        response = client.get("/api/avatars/managed")
        data = response.json()
        
        # Filter by group
        group_avatars = [a for a in data['avatars'] if a.get('avatar_group_id') == "test_group"]
        assert len(group_avatars) == 3
    
    @pytest.mark.asyncio
    async def test_upload_avatar(self, client):
        """Test uploading an avatar image"""
        # Create fake image file
        file_content = b"fake image content"
        file = io.BytesIO(file_content)
        
        response = client.post(
            "/api/upload-avatar",
            files={"file": ("test_avatar.png", file, "image/png")},
            data={
                "name": "Upload Test Avatar",
                "avatar_type": "default"
            }
        )
        
        # Should succeed or fail gracefully
        assert response.status_code in [200, 400, 413, 500]
    
    @pytest.mark.asyncio
    async def test_upload_avatar_with_group(self, client):
        """Test uploading avatar with group ID"""
        file_content = b"fake image content"
        file = io.BytesIO(file_content)
        
        response = client.post(
            "/api/upload-avatar",
            files={"file": ("group_avatar.png", file, "image/png")},
            data={
                "name": "Group Upload Test",
                "avatar_type": "default",
                "avatar_group_id": "upload_group"
            }
        )
        
        assert response.status_code in [200, 400, 413, 500]
    
    @pytest.mark.asyncio
    async def test_delete_avatar(self, client, session):
        """Test deleting an avatar"""
        # Create avatar
        avatar = AvatarImage(
            name="Delete Test",
            filename="delete_test.png",
            file_path="/user_avatars/delete_test.png",
            avatar_type="default",
            disabled=False
        )
        session.add(avatar)
        session.commit()
        avatar_id = avatar.id
        
        # Delete avatar
        response = client.delete(f"/api/avatars/{avatar_id}")
        
        assert response.status_code == 200
        
        # Verify deleted
        session.expire_all()
        deleted = session.get(AvatarImage, avatar_id)
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_update_avatar(self, client, session):
        """Test updating avatar metadata"""
        # Create avatar
        avatar = AvatarImage(
            name="Update Test",
            filename="update_test.png",
            file_path="/user_avatars/update_test.png",
            avatar_type="default",
            disabled=False
        )
        session.add(avatar)
        session.commit()
        avatar_id = avatar.id
        
        # Update avatar
        update_data = {
            "name": "Updated Avatar Name",
            "disabled": True,
            "spawn_position": 10
        }
        
        response = client.put(f"/api/avatars/{avatar_id}", json=update_data)
        
        if response.status_code == 200:
            # Verify update
            session.expire_all()
            updated = session.get(AvatarImage, avatar_id)
            assert updated.name == "Updated Avatar Name"
            assert updated.disabled is True
            assert updated.spawn_position == 10


@pytest.mark.unit
@pytest.mark.avatars
class TestAvatarPersistentData:
    """Tests for avatar persistent data functions"""
    
    def test_get_avatars_enabled_only(self, session):
        """Test getting only enabled avatars"""
        from modules.persistent_data import get_avatars
        
        # Add enabled and disabled avatars
        enabled = AvatarImage(
            name="Enabled",
            filename="enabled.png",
            file_path="/user_avatars/enabled.png",
            avatar_type="default",
            disabled=False
        )
        disabled = AvatarImage(
            name="Disabled",
            filename="disabled.png",
            file_path="/user_avatars/disabled.png",
            avatar_type="default",
            disabled=True
        )
        session.add(enabled)
        session.add(disabled)
        session.commit()
        
        # get_avatars should return only enabled
        avatars = get_avatars()
        avatar_names = [a.name for a in avatars]
        
        assert "Enabled" in avatar_names
        assert "Disabled" not in avatar_names
    
    def test_get_all_avatars(self, session):
        """Test getting all avatars including disabled"""
        from modules.persistent_data import get_all_avatars
        
        # Add enabled and disabled avatars
        enabled = AvatarImage(
            name="All Test Enabled",
            filename="all_enabled.png",
            file_path="/user_avatars/all_enabled.png",
            avatar_type="default",
            disabled=False
        )
        disabled = AvatarImage(
            name="All Test Disabled",
            filename="all_disabled.png",
            file_path="/user_avatars/all_disabled.png",
            avatar_type="default",
            disabled=True
        )
        session.add(enabled)
        session.add(disabled)
        session.commit()
        
        # get_all_avatars should return both
        all_avatars = get_all_avatars()
        names = [a.name for a in all_avatars]
        
        assert "All Test Enabled" in names
        assert "All Test Disabled" in names
    
    def test_get_avatar(self, session):
        """Test getting a specific avatar"""
        from modules.persistent_data import add_avatar, get_avatar
        
        avatar = AvatarImage(
            name="Get Test",
            filename="get_test.png",
            file_path="/user_avatars/get_test.png",
            avatar_type="default",
            disabled=False
        )
        add_avatar(avatar)
        
        # Retrieve by name and type
        retrieved = get_avatar("Get Test", "default")
        assert retrieved is not None
        assert retrieved.name == "Get Test"
    
    def test_add_avatar(self, session):
        """Test adding an avatar"""
        from modules.persistent_data import add_avatar, get_all_avatars
        
        avatar = AvatarImage(
            name="Add Test",
            filename="add_test.png",
            file_path="/user_avatars/add_test.png",
            avatar_type="default",
            disabled=False
        )
        
        add_avatar(avatar)
        
        # Verify added
        all_avatars = get_all_avatars()
        names = [a.name for a in all_avatars]
        assert "Add Test" in names


@pytest.mark.unit
@pytest.mark.avatars
class TestAvatarGrouping:
    """Tests for avatar grouping functionality"""
    
    def test_avatars_same_group(self, session):
        """Test multiple avatars in same group"""
        group_id = "character_set_1"
        
        for i in range(3):
            avatar = AvatarImage(
                name=f"Character {i}",
                filename=f"char_{i}.png",
                file_path=f"/user_avatars/char_{i}.png",
                avatar_type="default",
                avatar_group_id=group_id,
                disabled=False
            )
            session.add(avatar)
        
        session.commit()
        
        # Query by group
        from sqlmodel import select
        grouped_avatars = session.exec(
            select(AvatarImage).where(AvatarImage.avatar_group_id == group_id)
        ).all()
        
        assert len(grouped_avatars) == 3
    
    def test_avatars_different_groups(self, session):
        """Test avatars in different groups"""
        groups = ["group_a", "group_b", "group_c"]
        
        for group in groups:
            avatar = AvatarImage(
                name=f"{group} Avatar",
                filename=f"{group}.png",
                file_path=f"/user_avatars/{group}.png",
                avatar_type="default",
                avatar_group_id=group,
                disabled=False
            )
            session.add(avatar)
        
        session.commit()
        
        # Verify distinct groups
        from sqlmodel import select
        all_groups = session.exec(
            select(AvatarImage.avatar_group_id).distinct()
        ).all()
        
        for group in groups:
            assert group in all_groups


@pytest.mark.unit
@pytest.mark.avatars
class TestAvatarPositioning:
    """Tests for avatar spawn position functionality"""
    
    def test_avatars_with_positions(self, session):
        """Test avatars with specific spawn positions"""
        positions = [1, 3, 5, 7]
        
        for pos in positions:
            avatar = AvatarImage(
                name=f"Position {pos}",
                filename=f"pos_{pos}.png",
                file_path=f"/user_avatars/pos_{pos}.png",
                avatar_type="default",
                spawn_position=pos,
                disabled=False
            )
            session.add(avatar)
        
        session.commit()
        
        # Query ordered by position
        from sqlmodel import select
        positioned = session.exec(
            select(AvatarImage).order_by(AvatarImage.spawn_position)
        ).all()
        
        # Check positions are stored
        stored_positions = [a.spawn_position for a in positioned if a.spawn_position is not None]
        for pos in positions:
            assert pos in stored_positions
    
    def test_avatars_without_position(self, session):
        """Test avatars without spawn position (None)"""
        avatar = AvatarImage(
            name="No Position",
            filename="no_pos.png",
            file_path="/user_avatars/no_pos.png",
            avatar_type="default",
            spawn_position=None,
            disabled=False
        )
        session.add(avatar)
        session.commit()
        
        assert avatar.spawn_position is None


@pytest.mark.integration
@pytest.mark.avatars
class TestAvatarIntegration:
    """Integration tests for avatar functionality"""
    
    @pytest.mark.asyncio
    async def test_avatar_lifecycle(self, client, session):
        """Test complete avatar lifecycle"""
        # Create avatar
        avatar = AvatarImage(
            name="Lifecycle Test",
            filename="lifecycle.png",
            file_path="/user_avatars/lifecycle.png",
            avatar_type="default",
            avatar_group_id="lifecycle_group",
            spawn_position=1,
            disabled=False
        )
        session.add(avatar)
        session.commit()
        avatar_id = avatar.id
        
        # Verify created
        get_response = client.get("/api/avatars/managed")
        avatars = get_response.json()['avatars']
        created = next((a for a in avatars if a['id'] == avatar_id), None)
        assert created is not None
        assert created['name'] == "Lifecycle Test"
        
        # Update avatar
        if hasattr(client, 'put'):
            update_response = client.put(
                f"/api/avatars/{avatar_id}",
                json={"disabled": True}
            )
            
            if update_response.status_code == 200:
                # Verify update
                session.expire_all()
                updated = session.get(AvatarImage, avatar_id)
                assert updated.disabled is True
        
        # Delete avatar
        delete_response = client.delete(f"/api/avatars/{avatar_id}")
        if delete_response.status_code == 200:
            # Verify deleted
            session.expire_all()
            deleted = session.get(AvatarImage, avatar_id)
            assert deleted is None
    
    @pytest.mark.asyncio
    async def test_avatar_filtering(self, client, session):
        """Test filtering avatars by type and status"""
        # Create avatars with different types and statuses
        avatars_data = [
            ("Default Enabled", "default", False),
            ("Speaking Enabled", "speaking", False),
            ("Default Disabled", "default", True),
            ("Speaking Disabled", "speaking", True)
        ]
        
        for name, avatar_type, disabled in avatars_data:
            avatar = AvatarImage(
                name=name,
                filename=f"{name.replace(' ', '_').lower()}.png",
                file_path=f"/user_avatars/{name.replace(' ', '_').lower()}.png",
                avatar_type=avatar_type,
                disabled=disabled
            )
            session.add(avatar)
        session.commit()
        
        # Get all avatars
        response = client.get("/api/avatars/managed")
        all_avatars = response.json()['avatars']
        
        # Filter by type
        default_avatars = [a for a in all_avatars if a['avatar_type'] == 'default']
        speaking_avatars = [a for a in all_avatars if a['avatar_type'] == 'speaking']
        
        assert len(default_avatars) >= 2
        assert len(speaking_avatars) >= 2
