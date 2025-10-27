import asyncio
from typing import Callable, Dict, Any, Optional, TYPE_CHECKING
from modules import logger

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials

try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    YOUTUBE_AVAILABLE = True
except ImportError as e:
    logger.error(f"Failed to import YouTube dependencies: {e}")
    logger.info("Please install: pip install google-auth google-auth-oauthlib google-api-python-client")
    YOUTUBE_AVAILABLE = False
    Credentials = None  # type: ignore
    HttpError = Exception


class YouTubeListener:
    """YouTube Live Chat listener using YouTube Data API v3"""
    
    def __init__(self, credentials: Any, video_id: Optional[str] = None, settings: Optional[Dict[str, Any]] = None):
        """
        Initialize YouTube listener
        
        Args:
            credentials: Google OAuth2 credentials
            video_id: Specific video/stream ID to monitor, or None to auto-detect active stream
            settings: Optional settings dict to configure polling behavior
        """
        if not YOUTUBE_AVAILABLE:
            raise ImportError("YouTube dependencies not available. Install google-auth, google-auth-oauthlib, google-api-python-client")
        
        self.credentials = credentials
        self.youtube = build('youtube', 'v3', credentials=credentials)
        self.video_id = video_id
        self.live_chat_id = None
        self.next_page_token = None
        self.running = False
        
        # Get YouTube settings with defaults
        youtube_settings = settings.get('youtube', {}) if settings else {}
        
        # Adaptive polling: start slower and adjust based on API response
        self.polling_interval = 20  # Start with 10 seconds (more conservative)
        self.min_polling_interval = youtube_settings.get('minPollingInterval', 15)  # YouTube's minimum recommended
        self.max_polling_interval = youtube_settings.get('maxPollingInterval', 30)  # Maximum when chat is slow
        self.polling_strategy = youtube_settings.get('pollingStrategy', 'adaptive')  # 'adaptive' or 'fixed'
        self.consecutive_empty_polls = 0  # Track empty responses
        
        logger.info(f"YouTube listener initialized with video_id: {video_id or 'auto-detect'}")
        logger.info(f"Polling strategy: {self.polling_strategy} (min: {self.min_polling_interval}s, max: {self.max_polling_interval}s)")
        logger.info("💡 Tip: Adaptive polling reduces API quota usage by slowing down when chat is quiet")
    
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
                    logger.info(f"Found active stream: '{title}' (ID: {self.video_id})")
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
                    logger.info(f"Got live chat ID: {self.live_chat_id}")
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
                new_messages_count = 0
                
                for item in items:
                    message_id = item['id']
                    
                    # Skip if we've already processed this message
                    if message_id in processed_messages:
                        continue
                    processed_messages.add(message_id)
                    new_messages_count += 1
                    
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
                
                # Adaptive polling interval management
                # YouTube API provides pollingIntervalMillis - always respect it as minimum
                api_suggested_interval = response.get('pollingIntervalMillis', 6000) / 1000.0
                
                # Ensure we don't poll faster than YouTube recommends
                base_interval = max(api_suggested_interval, self.min_polling_interval)
                
                # Apply polling strategy
                if self.polling_strategy == 'adaptive':
                    # Adaptive strategy: slow down when chat is inactive to save quota
                    if new_messages_count == 0:
                        self.consecutive_empty_polls += 1
                        # Gradually increase interval up to max when chat is quiet
                        # After 3 empty polls, start backing off
                        if self.consecutive_empty_polls > 3:
                            backoff_multiplier = min(1 + (self.consecutive_empty_polls - 3) * 0.5, 3)
                            self.polling_interval = min(base_interval * backoff_multiplier, self.max_polling_interval)
                            if self.consecutive_empty_polls == 4:  # Log once when backing off
                                logger.info(f"💤 Chat quiet, reducing poll frequency to save quota (interval: {self.polling_interval:.1f}s)")
                        else:
                            self.polling_interval = base_interval
                    else:
                        # Active chat - use API suggested interval
                        if self.consecutive_empty_polls > 3:  # Log when resuming normal polling
                            logger.info(f"💬 Chat active, resuming normal poll frequency (interval: {base_interval:.1f}s)")
                        self.consecutive_empty_polls = 0
                        self.polling_interval = base_interval
                else:
                    # Fixed strategy: always use API suggested interval
                    self.polling_interval = base_interval
                
                # Log quota-saving info periodically
                if new_messages_count > 0:
                    logger.debug(f"Processed {new_messages_count} new message(s), next poll in {self.polling_interval:.1f}s")
                
                # Clean up old processed messages (keep last 1000)
                if len(processed_messages) > 1000:
                    processed_messages.clear()
                
                # Wait for the polling interval
                await asyncio.sleep(self.polling_interval)
                
            except HttpError as e:
                error_reason = getattr(e, 'reason', 'Unknown error')
                status_code = getattr(e, 'resp', {}).get('status', 0)
                
                if status_code == 403:
                    logger.error("⚠️  YouTube API quota exceeded or access forbidden")
                    logger.error("   The YouTube Data API has strict quota limits:")
                    logger.error("   - Default quota: 10,000 units/day")
                    logger.error("   - Each chat poll costs ~5 units")
                    logger.error("   - This allows ~2,000 polls/day (~83/hour or ~1.4/minute)")
                    logger.error("   Pausing for 5 minutes to avoid further quota usage...")
                    await asyncio.sleep(300)  # Wait 5 minutes on quota errors
                    # After quota error, slow down significantly
                    self.polling_interval = self.max_polling_interval
                    self.consecutive_empty_polls = 10  # Force slow polling
                elif status_code == 404:
                    logger.error("Live chat not found - stream may have ended")
                    self.running = False
                else:
                    logger.error(f"YouTube API error ({status_code}): {error_reason}")
                    await asyncio.sleep(15)  # Longer wait for other errors
                    
            except asyncio.CancelledError:
                logger.info("YouTube listener cancelled")
                self.running = False
                raise
                
            except Exception as e:
                logger.error(f"Error in YouTube listener: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying
        
        logger.info("YouTube chat listener stopped")
    
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


async def run_youtube_bot(credentials: Any, video_id: Optional[str] = None, 
                         on_event: Callable[[Dict[str, Any]], None] = None,
                         settings: Optional[Dict[str, Any]] = None):
    """
    Main entry point for YouTube listener
    
    Args:
        credentials: Google OAuth2 credentials
        video_id: Specific video/stream ID to monitor, or None to auto-detect
        on_event: Callback function to handle chat events
        settings: Optional settings dict to configure polling behavior
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
        listener = YouTubeListener(credentials, video_id, settings)
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
