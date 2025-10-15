import asyncio
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timedelta
from modules import logger

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import YouTube dependencies: {e}")
    logger.info("Please install: pip install google-auth google-auth-oauthlib google-api-python-client")
    YOUTUBE_AVAILABLE = False


class YouTubeListener:
    """YouTube Live Chat listener using YouTube Data API v3"""
    
    def __init__(self, credentials: Credentials, video_id: Optional[str] = None):
        """
        Initialize YouTube listener
        
        Args:
            credentials: Google OAuth2 credentials
            video_id: Specific video/stream ID to monitor, or None to auto-detect active stream
        """
        if not YOUTUBE_AVAILABLE:
            raise ImportError("YouTube dependencies not available. Install google-auth, google-auth-oauthlib, google-api-python-client")
        
        self.credentials = credentials
        self.youtube = build('youtube', 'v3', credentials=credentials)
        self.video_id = video_id
        self.live_chat_id = None
        self.next_page_token = None
        self.running = False
        self.polling_interval = 5  # Default polling interval in seconds
        
        logger.info(f"YouTube listener initialized with video_id: {video_id or 'auto-detect'}")
    
    async def find_active_stream(self) -> bool:
        """Find the currently active live stream for the authenticated channel"""
        try:
            logger.info("Searching for active YouTube stream...")
            request = self.youtube.liveBroadcasts().list(
                part="snippet,contentDetails",
                broadcastStatus="active",
                mine=True,
                maxResults=1
            )
            response = request.execute()
            
            if response.get('items'):
                broadcast = response['items'][0]
                self.video_id = broadcast['id']
                # Get the live chat ID from the broadcast
                live_chat_id = broadcast['snippet'].get('liveChatId')
                if live_chat_id:
                    self.live_chat_id = live_chat_id
                    title = broadcast['snippet'].get('title', 'Unknown')
                    logger.info(f"✅ Found active stream: '{title}' (ID: {self.video_id})")
                    return True
                else:
                    logger.warning("Active stream found but no live chat ID available")
                    return False
            else:
                logger.warning("No active live stream found for this channel")
                return False
        except HttpError as e:
            logger.error(f"YouTube API error finding active stream: {e}")
            return False
        except Exception as e:
            logger.error(f"Error finding active stream: {e}", exc_info=True)
            return False
    
    async def get_live_chat_id(self) -> Optional[str]:
        """Get the live chat ID for a specific video"""
        if self.live_chat_id:
            return self.live_chat_id
        
        if not self.video_id:
            logger.error("No video ID available to get live chat")
            return None
        
        try:
            logger.info(f"Getting live chat ID for video: {self.video_id}")
            request = self.youtube.videos().list(
                part="liveStreamingDetails",
                id=self.video_id
            )
            response = request.execute()
            
            if response.get('items'):
                live_details = response['items'][0].get('liveStreamingDetails', {})
                self.live_chat_id = live_details.get('activeLiveChatId')
                if self.live_chat_id:
                    logger.info(f"✅ Got live chat ID: {self.live_chat_id}")
                    return self.live_chat_id
                else:
                    logger.error(f"Video {self.video_id} is not currently live or has no active chat")
                    return None
            else:
                logger.error(f"Video {self.video_id} not found")
                return None
        except HttpError as e:
            logger.error(f"YouTube API error getting live chat ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting live chat ID: {e}", exc_info=True)
            return None
    
    async def listen_to_chat(self, on_event: Callable[[Dict[str, Any]], None]):
        """
        Poll YouTube live chat for new messages
        
        Args:
            on_event: Callback function to handle chat events
        """
        self.running = True
        
        # If no video_id specified, find active stream
        if not self.video_id:
            if not await self.find_active_stream():
                logger.error("Cannot start YouTube listener: No active stream found")
                self.running = False
                return
        
        # Get live chat ID
        if not self.live_chat_id:
            if not await self.get_live_chat_id():
                logger.error("Cannot start YouTube listener: No live chat ID")
                self.running = False
                return
        
        logger.info(f"🎥 YouTube chat listener started for live chat: {self.live_chat_id}")
        
        # Track processed message IDs to avoid duplicates
        processed_messages = set()
        
        while self.running:
            try:
                # Build request with pagination token
                request_params = {
                    'liveChatId': self.live_chat_id,
                    'part': 'snippet,authorDetails'
                }
                if self.next_page_token:
                    request_params['pageToken'] = self.next_page_token
                
                request = self.youtube.liveChatMessages().list(**request_params)
                response = request.execute()
                
                # Process messages
                items = response.get('items', [])
                for item in items:
                    message_id = item['id']
                    
                    # Skip if we've already processed this message
                    if message_id in processed_messages:
                        continue
                    processed_messages.add(message_id)
                    
                    snippet = item['snippet']
                    author = item['authorDetails']
                    
                    # Extract message text
                    message_text = ""
                    if snippet.get('type') == 'textMessageEvent':
                        message_details = snippet.get('textMessageDetails', {})
                        message_text = message_details.get('messageText', '')
                    elif snippet.get('type') == 'superChatEvent':
                        # Super Chat messages
                        super_chat_details = snippet.get('superChatDetails', {})
                        message_text = super_chat_details.get('userComment', '[Super Chat]')
                    elif snippet.get('type') == 'membershipGiftingEvent':
                        # Membership gifting
                        message_text = '[Membership Gift]'
                    else:
                        # Other event types (new member, etc.)
                        message_text = f"[{snippet.get('type', 'unknown')}]"
                    
                    # Determine event type
                    event_type = self._determine_event_type(snippet, author)
                    
                    # Build message data
                    message_data = {
                        'type': 'chat',
                        'user': author.get('displayName', 'Unknown'),
                        'text': message_text,
                        'eventType': event_type,
                        'tags': {
                            'user_id': author.get('channelId', ''),
                            'channel_url': author.get('channelUrl', ''),
                            'is_moderator': author.get('isChatModerator', False),
                            'is_owner': author.get('isChatOwner', False),
                            'is_verified': author.get('isVerifiedUser', False),
                            'is_member': author.get('isChatSponsor', False),
                            'platform': 'youtube',
                            'timestamp': snippet.get('publishedAt', ''),
                            'message_id': message_id,
                            'has_display_content': snippet.get('hasDisplayContent', True),
                            'message_type': snippet.get('type', 'textMessageEvent')
                        }
                    }
                    
                    # Add Super Chat details if present
                    if snippet.get('type') == 'superChatEvent':
                        super_chat_details = snippet.get('superChatDetails', {})
                        message_data['tags']['super_chat'] = {
                            'amount': super_chat_details.get('amountMicros', 0) / 1000000,
                            'currency': super_chat_details.get('currency', 'USD'),
                            'tier': super_chat_details.get('tier', 0)
                        }
                    
                    # Call the event handler
                    try:
                        if asyncio.iscoroutinefunction(on_event):
                            await on_event(message_data)
                        else:
                            on_event(message_data)
                    except Exception as e:
                        logger.error(f"Error in YouTube event handler: {e}", exc_info=True)
                
                # Update next page token for polling
                self.next_page_token = response.get('nextPageToken')
                
                # Get polling interval from YouTube API (they tell us how often to poll)
                polling_interval_ms = response.get('pollingIntervalMillis', 5000)
                self.polling_interval = polling_interval_ms / 1000.0
                
                # Clean up old processed messages (keep last 1000)
                if len(processed_messages) > 1000:
                    processed_messages.clear()
                
                # Wait for the polling interval
                await asyncio.sleep(self.polling_interval)
                
            except HttpError as e:
                error_reason = getattr(e, 'reason', 'Unknown error')
                status_code = getattr(e, 'resp', {}).get('status', 0)
                
                if status_code == 403:
                    logger.error("YouTube API quota exceeded or access forbidden")
                    await asyncio.sleep(60)  # Wait longer on quota errors
                elif status_code == 404:
                    logger.error("Live chat not found - stream may have ended")
                    self.running = False
                else:
                    logger.error(f"YouTube API error: {error_reason}")
                    await asyncio.sleep(10)
                    
            except asyncio.CancelledError:
                logger.info("YouTube listener cancelled")
                self.running = False
                raise
                
            except Exception as e:
                logger.error(f"Error in YouTube listener: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info("🛑 YouTube chat listener stopped")
    
    def _determine_event_type(self, snippet: Dict[str, Any], author: Dict[str, Any]) -> str:
        """Determine the event type based on message details"""
        message_type = snippet.get('type', 'textMessageEvent')
        
        # Super Chat (donations)
        if message_type == 'superChatEvent':
            return 'bits'  # Similar to Twitch bits
        
        # New member
        if message_type == 'newSponsorEvent' or message_type == 'memberMilestoneChatEvent':
            return 'sub'  # Similar to Twitch subscription
        
        # Membership gifting
        if message_type == 'membershipGiftingEvent':
            return 'sub'
        
        # Owner message
        if author.get('isChatOwner'):
            return 'vip'  # Treat owner as VIP
        
        # Moderator message
        if author.get('isChatModerator'):
            return 'vip'  # Treat moderators as VIP
        
        # Channel member
        if author.get('isChatSponsor'):
            return 'vip'  # Treat members as VIP
        
        # Regular chat message
        return 'chat'
    
    def stop(self):
        """Stop listening to chat"""
        self.running = False
        logger.info("YouTube chat listener stop requested")


async def run_youtube_bot(credentials: Credentials, video_id: Optional[str] = None, 
                         on_event: Callable[[Dict[str, Any]], None] = None):
    """
    Main entry point for YouTube listener
    
    Args:
        credentials: Google OAuth2 credentials
        video_id: Specific video/stream ID to monitor, or None to auto-detect
        on_event: Callback function to handle chat events
    """
    if not YOUTUBE_AVAILABLE:
        logger.error("Cannot start YouTube bot: Required dependencies not installed")
        logger.info("Install with: pip install google-auth google-auth-oauthlib google-api-python-client")
        return
    
    bot_logger = logger
    listener = None
    
    try:
        bot_logger.info(f"Starting YouTube bot with video_id: {video_id or 'auto-detect'}")
        
        # Create listener instance
        listener = YouTubeListener(credentials, video_id)
        bot_logger.info("YouTube listener instance created, starting chat monitoring...")
        
        # Start listening to chat
        if on_event:
            await listener.listen_to_chat(on_event)
        else:
            bot_logger.warning("No event callback provided to YouTube bot")
            
    except asyncio.CancelledError:
        # Task was cancelled (e.g., server shutdown), clean up gracefully
        bot_logger.info("YouTube bot task cancelled")
        if listener:
            listener.stop()
        raise  # Re-raise CancelledError so the task properly terminates
        
    except Exception as e:
        bot_logger.error(f"YouTube bot failed: {e}", exc_info=True)
        if listener:
            listener.stop()
        raise
