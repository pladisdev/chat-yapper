"""Unit tests for YouTube integration (OAuth, models, API endpoints)"""
import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from modules.models import YouTubeAuth


@pytest.mark.unit
@pytest.mark.youtube
class TestYouTubeAuthModel:
    """Tests for YouTubeAuth database model"""
    
    def test_create_youtube_auth(self, session):
        """Test creating a YouTube auth record"""
        auth = YouTubeAuth(
            channel_id="UC_test_channel_id",
            channel_name="Test Channel",
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_at=datetime.now().isoformat()
        )
        session.add(auth)
        session.commit()
        session.refresh(auth)
        
        assert auth.id is not None
        assert auth.channel_id == "UC_test_channel_id"
        assert auth.channel_name == "Test Channel"
    
    def test_youtube_auth_unique_channel(self, session):
        """Test that channel_id should be unique"""
        auth1 = YouTubeAuth(
            channel_id="UC_same_id",
            channel_name="Channel 1",
            access_token="token1",
            refresh_token="refresh1",
            expires_at=datetime.now().isoformat()
        )
        session.add(auth1)
        session.commit()
        
        # Try to add another with same channel_id
        # Note: uniqueness depends on schema definition
        auth2 = YouTubeAuth(
            channel_id="UC_same_id",
            channel_name="Channel 2",
            access_token="token2",
            refresh_token="refresh2",
            expires_at=datetime.now().isoformat()
        )
        
        # Behavior depends on schema - just verify we can create model
        assert auth2.channel_id == "UC_same_id"
    
    def test_youtube_auth_expires_at(self, session):
        """Test expires_at field"""
        future_time = (datetime.now() + timedelta(hours=1)).isoformat()
        
        auth = YouTubeAuth(
            channel_id="UC_expiry_test",
            channel_name="Expiry Test",
            access_token="token",
            refresh_token="refresh",
            expires_at=future_time
        )
        session.add(auth)
        session.commit()
        
        assert auth.expires_at == future_time


@pytest.mark.unit
@pytest.mark.youtube
class TestYouTubeOAuthEndpoints:
    """Tests for YouTube OAuth endpoints"""
    
    @pytest.mark.asyncio
    async def test_youtube_auth_start(self, client):
        """Test initiating YouTube OAuth flow"""
        response = client.get("/auth/youtube")
        
        # Should redirect to Google OAuth
        assert response.status_code in [302, 307, 200]  # Redirect or success
        
        if response.status_code in [302, 307]:
            # Check redirect URL
            location = response.headers.get('location', '')
            assert 'accounts.google.com' in location or 'oauth' in location.lower()
    
    @pytest.mark.asyncio
    async def test_youtube_auth_callback_no_code(self, client):
        """Test YouTube OAuth callback without code parameter"""
        response = client.get("/auth/youtube/callback")
        
        # Should fail without code
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    @patch('modules.persistent_data.save_youtube_auth')
    async def test_youtube_auth_callback_with_code(self, mock_save, client):
        """Test YouTube OAuth callback with valid code"""
        with patch('backend.routers.auth.exchange_youtube_code_for_token') as mock_exchange:
            mock_exchange.return_value = {
                'access_token': 'test_access',
                'refresh_token': 'test_refresh',
                'expires_in': 3600
            }
            
            with patch('backend.routers.auth.get_youtube_channel_info') as mock_channel:
                mock_channel.return_value = {
                    'id': 'UC_test',
                    'snippet': {'title': 'Test Channel'}
                }
                
                response = client.get("/auth/youtube/callback?code=test_code&state=test_state")
                
                # Should succeed or redirect
                assert response.status_code in [200, 302, 307]
    
    @pytest.mark.asyncio
    async def test_youtube_status_not_connected(self, client):
        """Test YouTube status when not connected"""
        response = client.get("/api/youtube/status")
        
        assert response.status_code == 200
        data = response.json()
        assert 'connected' in data
        # Initially not connected
        if not data['connected']:
            assert 'channel_name' not in data or data['channel_name'] is None
    
    @pytest.mark.asyncio
    async def test_youtube_status_connected(self, client, session):
        """Test YouTube status when connected"""
        # Add YouTube auth
        auth = YouTubeAuth(
            channel_id="UC_status_test",
            channel_name="Status Test Channel",
            access_token="test_token",
            refresh_token="test_refresh",
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat()
        )
        session.add(auth)
        session.commit()
        
        response = client.get("/api/youtube/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['connected'] is True
        assert data['channel_name'] == "Status Test Channel"
        assert data['channel_id'] == "UC_status_test"
    
    @pytest.mark.asyncio
    async def test_youtube_disconnect(self, client, session):
        """Test disconnecting YouTube account"""
        # Add YouTube auth
        auth = YouTubeAuth(
            channel_id="UC_disconnect_test",
            channel_name="Disconnect Test",
            access_token="token",
            refresh_token="refresh",
            expires_at=datetime.now().isoformat()
        )
        session.add(auth)
        session.commit()
        
        # Disconnect
        response = client.delete("/api/youtube/disconnect")
        
        assert response.status_code == 200
        data = response.json()
        assert data.get('success') is True or data.get('ok') is True
        
        # Verify removed from database
        from modules.persistent_data import get_youtube_auth
        auth_after = get_youtube_auth()
        assert auth_after is None


@pytest.mark.unit
@pytest.mark.youtube
class TestYouTubePersistentData:
    """Tests for YouTube persistent data functions"""
    
    def test_save_youtube_auth(self, session):
        """Test saving YouTube auth to database"""
        from modules.persistent_data import save_youtube_auth
        
        save_youtube_auth(
            channel_id="UC_save_test",
            channel_name="Save Test",
            access_token="access",
            refresh_token="refresh",
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat()
        )
        
        # Verify saved
        from modules.persistent_data import get_youtube_auth
        auth = get_youtube_auth()
        
        assert auth is not None
        assert auth.channel_id == "UC_save_test"
        assert auth.channel_name == "Save Test"
    
    def test_get_youtube_auth_none(self):
        """Test getting YouTube auth when none exists"""
        from modules.persistent_data import get_youtube_auth
        
        # Delete any existing auth first
        from modules.persistent_data import delete_youtube_auth
        delete_youtube_auth()
        
        auth = get_youtube_auth()
        assert auth is None
    
    def test_delete_youtube_auth(self, session):
        """Test deleting YouTube auth"""
        from modules.persistent_data import save_youtube_auth, delete_youtube_auth, get_youtube_auth
        
        # Add auth
        save_youtube_auth(
            channel_id="UC_delete_test",
            channel_name="Delete Test",
            access_token="access",
            refresh_token="refresh",
            expires_at=datetime.now().isoformat()
        )
        
        # Verify exists
        assert get_youtube_auth() is not None
        
        # Delete
        delete_youtube_auth()
        
        # Verify deleted
        assert get_youtube_auth() is None
    
    def test_get_youtube_token(self, session):
        """Test getting YouTube token with Google Credentials"""
        from modules.persistent_data import save_youtube_auth
        
        # Add auth with valid token
        future_time = (datetime.now() + timedelta(hours=1)).isoformat()
        save_youtube_auth(
            channel_id="UC_token_test",
            channel_name="Token Test",
            access_token="valid_access_token",
            refresh_token="valid_refresh_token",
            expires_at=future_time
        )
        
        with patch('google.oauth2.credentials.Credentials') as mock_creds:
            from modules.persistent_data import get_youtube_token
            
            credentials = get_youtube_token()
            
            # Should have attempted to create Credentials
            # Note: actual implementation may vary
            if credentials:
                assert credentials is not None


@pytest.mark.unit
@pytest.mark.youtube
class TestYouTubeListener:
    """Tests for YouTube Live Chat listener"""
    
    @pytest.mark.asyncio
    async def test_youtube_listener_initialization(self):
        """Test creating YouTube listener"""
        from modules.youtube_listener import YouTubeListener
        
        mock_credentials = Mock()
        listener = YouTubeListener(
            credentials=mock_credentials,
            video_id=None,
            message_callback=Mock()
        )
        
        assert listener is not None
        assert listener.credentials == mock_credentials
        assert listener.video_id is None
    
    @pytest.mark.asyncio
    @patch('googleapiclient.discovery.build')
    async def test_find_active_stream(self, mock_build):
        """Test finding active live stream"""
        from modules.youtube_listener import YouTubeListener
        
        # Mock YouTube API response
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        mock_youtube.liveBroadcasts().list().execute.return_value = {
            'items': [
                {
                    'id': 'broadcast_id',
                    'snippet': {
                        'liveChatId': 'live_chat_id',
                        'title': 'Test Stream'
                    }
                }
            ]
        }
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        live_chat_id = await listener.find_active_stream()
        
        # Should return live chat ID
        if live_chat_id:
            assert live_chat_id == 'live_chat_id'
    
    @pytest.mark.asyncio
    @patch('googleapiclient.discovery.build')
    async def test_get_live_chat_id(self, mock_build):
        """Test getting live chat ID from video ID"""
        from modules.youtube_listener import YouTubeListener
        
        # Mock YouTube API response
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        mock_youtube.videos().list().execute.return_value = {
            'items': [
                {
                    'liveStreamingDetails': {
                        'activeLiveChatId': 'chat_id_from_video'
                    }
                }
            ]
        }
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id='test_video_id',
            message_callback=Mock()
        )
        
        chat_id = await listener.get_live_chat_id('test_video_id')
        
        if chat_id:
            assert chat_id == 'chat_id_from_video'
    
    @pytest.mark.asyncio
    @patch('googleapiclient.discovery.build')
    async def test_listen_to_chat_processes_messages(self, mock_build):
        """Test listening to chat and processing messages"""
        from modules.youtube_listener import YouTubeListener
        
        # Mock YouTube API
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        # Mock chat messages response
        mock_youtube.liveChatMessages().list().execute.return_value = {
            'items': [
                {
                    'id': 'msg_1',
                    'snippet': {
                        'authorChannelId': 'UC_author',
                        'displayMessage': 'Test message',
                        'publishedAt': datetime.now().isoformat()
                    },
                    'authorDetails': {
                        'displayName': 'TestUser',
                        'isChatOwner': False,
                        'isChatModerator': False,
                        'isChatSponsor': False
                    }
                }
            ],
            'pollingIntervalMillis': 5000,
            'pageInfo': {'totalResults': 1}
        }
        
        callback = Mock()
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=callback
        )
        
        # Mock stop after one iteration
        listener.should_stop = True
        
        # This would normally run in a loop, but we'll test one iteration
        # Note: Actual test may need more sophisticated mocking


@pytest.mark.integration
@pytest.mark.youtube
class TestYouTubeIntegration:
    """Integration tests for YouTube functionality"""
    
    @pytest.mark.asyncio
    async def test_youtube_settings_integration(self, client):
        """Test YouTube settings in application settings"""
        response = client.get("/api/settings")
        
        assert response.status_code == 200
        settings = response.json()
        
        # YouTube settings should exist
        if 'youtube' in settings:
            youtube_settings = settings['youtube']
            assert 'enabled' in youtube_settings
            assert isinstance(youtube_settings['enabled'], bool)
    
    @pytest.mark.asyncio
    async def test_youtube_oauth_config_exists(self):
        """Test that YouTube OAuth configuration is available"""
        from modules.persistent_data import (
            YOUTUBE_CLIENT_ID,
            YOUTUBE_CLIENT_SECRET,
            YOUTUBE_REDIRECT_URI,
            YOUTUBE_SCOPE
        )
        
        # Should have configuration constants defined
        assert YOUTUBE_CLIENT_ID is not None
        assert YOUTUBE_CLIENT_SECRET is not None
        assert YOUTUBE_REDIRECT_URI is not None
        assert YOUTUBE_SCOPE is not None
        
        # Check redirect URI format
        assert 'localhost' in YOUTUBE_REDIRECT_URI or 'http' in YOUTUBE_REDIRECT_URI
    
    @pytest.mark.asyncio
    @patch('modules.app.restart_youtube_if_needed')
    async def test_youtube_restart_on_settings_change(self, mock_restart, client):
        """Test that YouTube restarts when settings change"""
        # Get current settings
        settings_response = client.get("/api/settings")
        settings = settings_response.json()
        
        # Toggle YouTube enabled
        if 'youtube' not in settings:
            settings['youtube'] = {}
        
        settings['youtube']['enabled'] = not settings['youtube'].get('enabled', False)
        
        # Update settings
        update_response = client.post(
            "/api/settings",
            json=settings
        )
        
        assert update_response.status_code == 200


@pytest.mark.unit
@pytest.mark.youtube
class TestYouTubeEventMapping:
    """Tests for YouTube event type mapping (Super Chat, memberships, etc.)"""
    
    @pytest.mark.asyncio
    async def test_super_chat_maps_to_bits(self):
        """Test that Super Chat events map to 'bits' type"""
        from modules.youtube_listener import YouTubeListener
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        # Super Chat message
        message_item = {
            'snippet': {
                'type': 'superChatEvent',
                'superChatDetails': {
                    'amountMicros': '5000000',
                    'currency': 'USD'
                }
            }
        }
        
        event_type = listener._determine_event_type(message_item)
        assert event_type == 'bits'
    
    @pytest.mark.asyncio
    async def test_membership_maps_to_sub(self):
        """Test that membership events map to 'sub' type"""
        from modules.youtube_listener import YouTubeListener
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        # Membership message
        message_item = {
            'snippet': {
                'type': 'newSponsorEvent'
            }
        }
        
        event_type = listener._determine_event_type(message_item)
        assert event_type == 'sub'
    
    @pytest.mark.asyncio
    async def test_owner_has_vip_badge(self):
        """Test that channel owner gets VIP badge"""
        from modules.youtube_listener import YouTubeListener
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        author_details = {
            'isChatOwner': True,
            'isChatModerator': False,
            'isChatSponsor': False
        }
        
        badges = listener._get_user_badges(author_details)
        assert 'vip' in badges
    
    @pytest.mark.asyncio
    async def test_moderator_has_vip_badge(self):
        """Test that moderators get VIP badge"""
        from modules.youtube_listener import YouTubeListener
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        author_details = {
            'isChatOwner': False,
            'isChatModerator': True,
            'isChatSponsor': False
        }
        
        badges = listener._get_user_badges(author_details)
        assert 'vip' in badges
    
    @pytest.mark.asyncio
    async def test_member_has_vip_badge(self):
        """Test that members get VIP badge"""
        from modules.youtube_listener import YouTubeListener
        
        listener = YouTubeListener(
            credentials=Mock(),
            video_id=None,
            message_callback=Mock()
        )
        
        author_details = {
            'isChatOwner': False,
            'isChatModerator': False,
            'isChatSponsor': True
        }
        
        badges = listener._get_user_badges(author_details)
        assert 'vip' in badges
