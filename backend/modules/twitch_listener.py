import asyncio
from typing import Callable, Dict, Any, Optional
from modules import logger
from twitchio.ext import commands
import twitchio
import os
import tempfile

def get_twitchio_major_version() -> int:
    """Get the major version of TwitchIO (1, 2, or 3)"""
    try:
        ver = getattr(twitchio, "__version__", "2.0.0")
        return int(str(ver).split(".")[0])
    except Exception:
        # Assume modern if unknown
        return 2


def prepare_twitchio_bot_kwargs(
    token: str,
    nick: str,
    user_id: Optional[str] = None,
    channels: Optional[list] = None,
    prefix: str = "!"
) -> Dict[str, Any]:
    """
    Prepare kwargs for TwitchIO Bot initialization that work across versions 1.x, 2.x, and 3.x.
    
    Args:
        token: OAuth token (with or without 'oauth:' prefix)
        nick: Bot username
        user_id: Twitch user ID (required for 3.x)
        channels: List of channels to join (default: empty list)
        prefix: Command prefix (default: "!")
    
    Returns:
        Dict of kwargs to pass to Bot.__init__()
    
    Raises:
        ValueError: If TwitchIO 3.x is detected but credentials are missing
    """
    # Handle both access-token and oauth: formats
    if token and not token.startswith("oauth:"):
        token = f"oauth:{token}"
    
    if channels is None:
        channels = []
    
    major_version = get_twitchio_major_version()
    
    # Build constructor kwargs compatible with 1.x, 2.x, and 3.x
    try:
        if major_version >= 3:
            # TwitchIO 3.x requires client_id, client_secret, and bot_id
            # Import here to avoid circular imports
            try:
                from modules.persistent_data import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
                client_id = TWITCH_CLIENT_ID or ""
                client_secret = TWITCH_CLIENT_SECRET or ""
            except ImportError:
                # Fallback for embedded builds with fixed client ID
                try:
                    import embedded_config
                    client_id = getattr(embedded_config, 'TWITCH_CLIENT_ID', '')
                    client_secret = getattr(embedded_config, 'TWITCH_CLIENT_SECRET', '')
                except ImportError:
                    client_id = ""
                    client_secret = ""
            
            # Validate that we have required credentials for TwitchIO 3.x
            if not client_id or not client_secret:
                raise ValueError(
                    f"TwitchIO 3.x requires TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET, "
                    f"but they are not configured. client_id={'present' if client_id else 'missing'}, "
                    f"client_secret={'present' if client_secret else 'missing'}"
                )
            
            # For TwitchIO 3.x, bot_id should be the user ID, not the username
            bot_id = user_id or nick
            
            return {
                "token": token,
                "client_id": client_id,
                "client_secret": client_secret,
                "bot_id": bot_id,
                "prefix": prefix,
                "initial_channels": channels
            }
        elif major_version >= 2:
            # TwitchIO 2.x
            return {
                "token": token,
                "prefix": prefix,
                "initial_channels": channels
            }
        else:
            # TwitchIO 1.x expects irc_token + nick
            return {
                "irc_token": token,
                "nick": nick,
                "prefix": prefix,
                "initial_channels": channels
            }
    except TypeError as e:
        # If we still get a TypeError, it might be version detection issue
        # Try the 3.x format as fallback
        if "client_id" in str(e) or "client_secret" in str(e) or "bot_id" in str(e):
            try:
                from modules.persistent_data import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
                client_id = TWITCH_CLIENT_ID or ""
                client_secret = TWITCH_CLIENT_SECRET or ""
            except ImportError:
                try:
                    import embedded_config
                    client_id = getattr(embedded_config, 'TWITCH_CLIENT_ID', '')
                    client_secret = getattr(embedded_config, 'TWITCH_CLIENT_SECRET', '')
                except ImportError:
                    client_id = ""
                    client_secret = ""
            
            # Validate that we have required credentials for TwitchIO 3.x
            if not client_id or not client_secret:
                raise ValueError(
                    f"TwitchIO 3.x requires TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET, "
                    f"but they are not configured. client_id={'present' if client_id else 'missing'}, "
                    f"client_secret={'present' if client_secret else 'missing'}"
                )
            
            # For TwitchIO 3.x, bot_id should be the user ID, not the username
            bot_id = user_id or nick
            
            return {
                "token": token,
                "client_id": client_id,
                "client_secret": client_secret,
                "bot_id": bot_id,
                "prefix": prefix,
                "initial_channels": channels
            }
        else:
            raise


async def test_twitch_connection(token_info: dict) -> bool:
    """
    Test Twitch connection without starting the full bot to detect auth issues early.
    
    Args:
        token_info: Dict with keys: token, username, user_id
    
    Returns:
        True if connection successful, False otherwise
    """
    logger.info("Testing Twitch connection...")
    
    # Save current directory and switch to a writable temp directory for TwitchIO token cache
    original_dir = os.getcwd()
    temp_dir = tempfile.gettempdir()
    
    try:
        # Change to temp directory to avoid permission issues with .tio.tokens.json
        os.chdir(temp_dir)
        
        # Create a minimal test bot that just connects and disconnects
        class TestBot(commands.Bot):
            def __init__(self, token, nick, user_id=None):
                # Store nick for logging
                self._nick = nick
                
                # Get shared initialization kwargs
                kwargs = prepare_twitchio_bot_kwargs(
                    token=token,
                    nick=nick,
                    user_id=user_id,
                    channels=[],  # Don't join any channels for testing
                    prefix="!"
                )
                
                super().__init__(**kwargs)
                self.connection_successful = False
                
            async def event_ready(self):
                logger.info(f"Twitch connection test successful for user: {self._nick}")
                self.connection_successful = True
                # Disconnect immediately after successful connection
                await self.close()
        
        # Create test bot instance using authenticated username and user ID for compatibility
        test_bot = TestBot(
            token=token_info["token"], 
            nick=token_info["username"],
            user_id=token_info.get("user_id")
        )
        
        # Run the test with a timeout
        try:
            await asyncio.wait_for(test_bot.start(), timeout=10.0)
            
            if test_bot.connection_successful:
                logger.info("Twitch connection test passed")
                return True
            else:
                logger.warning("Twitch connection test failed - no ready event received")
                return False
                
        except asyncio.TimeoutError:
            logger.warning("Twitch connection test timed out")
            await test_bot.close()
            return False
            
    except Exception as e:
        logger.error(f"Twitch connection test failed: {e}")
        logger.info(f"Connection test error type: {type(e).__name__}")
        
        # Check if this is a file permission error (TwitchIO 3.x token cache)
        if "Permission denied" in str(e) and ".tio.tokens.json" in str(e):
            logger.warning("TwitchIO token cache permission error - this is non-critical for testing")
            logger.info("Connection test will continue despite token cache error")
            # Don't treat this as a critical auth error since it's just a cache write issue
            return False
        
        # Check if this is a TwitchIO 3.x configuration error
        if "client_id" in str(e) or "client_secret" in str(e) or "bot_id" in str(e):
            logger.error("*** TwitchIO 3.x CONFIGURATION ERROR ***")
            logger.error("This error indicates TwitchIO 3.x is installed but TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET are not configured.")
            logger.error("This can happen when the application is built on a different PC without the proper .env file.")
            logger.error("To fix this, ensure TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET are properly configured in the build environment.")
        
        # Check if this is an authentication error
        error_str = str(e).lower()
        is_auth_error = (
            "authentication" in error_str or 
            "unauthorized" in error_str or 
            "invalid" in error_str or
            "access token" in error_str or
            e.__class__.__name__ == "AuthenticationError" or
            "client_id" in error_str or
            "client_secret" in error_str or
            "bot_id" in error_str
        )
        
        if is_auth_error:
            logger.warning("=== AUTHENTICATION ERROR DETECTED IN CONNECTION TEST ===")
            
            # Store and broadcast auth error immediately
            try:
                # Import here to avoid circular dependency
                from app import hub, twitch_auth_error
                
                # Update global error state
                import app
                app.twitch_auth_error = {
                    "type": "twitch_auth_error",
                    "message": "Twitch authentication failed. Please reconnect your account.",
                    "error": str(e)
                }
                
                # Broadcast the error to connected clients
                await hub.broadcast(app.twitch_auth_error)
                logger.info("Auth error broadcast completed (connection test)")
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast auth error during connection test: {broadcast_error}")
        
        return False
    
    finally:
        # Restore original directory
        try:
            os.chdir(original_dir)
        except Exception:
            pass  # Ignore errors when restoring directory

def _ti_major() -> int:
    """Legacy compatibility wrapper - use get_twitchio_major_version() instead"""
    return get_twitchio_major_version()

def _normalize_tags(tags_obj) -> Dict[str, Any]:
    """
    TwitchIO 2.x gives a dict-like tags mapping.
    Some 1.x builds may provide a list of dict pairs or a custom object.
    This normalizes into a plain dict[str, Any].
    """
    if tags_obj is None:
        return {}
    if isinstance(tags_obj, dict):
        return tags_obj
    # List[dict] -> dict
    if isinstance(tags_obj, (list, tuple)):
        flat: Dict[str, Any] = {}
        for part in tags_obj:
            if isinstance(part, dict):
                flat.update(part)
        return flat
    # Fallback: try to read .items()
    try:
        return dict(tags_obj.items())
    except Exception:
        return {}

def _is_vip_from(message, tags: Dict[str, Any]) -> bool:
    # Prefer attribute if it exists (2.x)
    try:
        if getattr(message.author, "is_vip", None):
            return True
    except Exception:
        pass
    # Derive from badges string (works across versions)
    badges = str(tags.get("badges", "") or "")
    # badges looks like "vip/1,subscriber/12" etc.
    return "vip/" in badges or badges == "vip"

class TwitchBot(commands.Bot):
    def __init__(self, token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None], user_id: str = None):
        self._major = get_twitchio_major_version()
        self.on_event_cb = on_event
        self.channel_name = channel
        self._nick = nick  # keep our own record for logs

        # Get shared initialization kwargs for TwitchIO compatibility
        kwargs = prepare_twitchio_bot_kwargs(
            token=token,
            nick=nick,
            user_id=user_id,
            channels=[channel],
            prefix="!"
        )
        
        super().__init__(**kwargs)

    async def event_ready(self):
        who = getattr(self, "nick", None) or self._nick or "unknown"
        try:
            logger.info(f"Twitch bot ready as {who}, listening to {self.channel_name}")
            # Join the channel to start receiving messages (required in TwitchIO 3.x)
            await self.join_channels([self.channel_name])
            logger.info(f"Joined channel: {self.channel_name}")
        except Exception as e:
            logger.error(f"Error in event_ready: {e}", exc_info=True)

    async def event_error(self, error, data=None):
        try:
            logger.error(f"Twitch bot error: {error}", exc_info=True)
        except Exception:
            pass

    async def event_message(self, message):
        # 2.x provides echo; 1.x sometimes not—guard it.
        if getattr(message, "echo", False):
            return

        tags = _normalize_tags(getattr(message, "tags", None))
        user = "unknown"
        try:
            if getattr(message, "author", None) and getattr(message.author, "name", None):
                user = message.author.name
            else:
                # Fall back to login/display-name from tags
                user = tags.get("login") or tags.get("display-name") or "unknown"
        except Exception:
            pass

        # VIP / highlight detection that works across versions
        is_vip = _is_vip_from(message, tags)
        msg_id = (tags.get("msg-id") or "").lower()
        event_type = "vip" if is_vip else ("highlight" if msg_id == "highlighted-message" else "chat")

        payload = {
            "type": "chat",
            "user": user,
            "text": getattr(message, "content", "") or "",
            "eventType": event_type,
            "tags": tags,
        }
        self.on_event_cb(payload)

    def _emit_usernotice(self, channel, tags_in):
        tags = _normalize_tags(tags_in)
        msgid = (tags.get("msg-id") or "").lower()
        user = tags.get("display-name") or tags.get("login") or "unknown"
        
        etype = {
            "sub": "skip",
            "resub": "skip",
            "subgift": "skip",
            "anonsubgift": "skip",
            "submysterygift": "skip",
            "raid": "skip",
            "bitsbadgetier": "skip",
            "viewcount" : "skip",
            "watchstreak" : "skip"
        }.get(msgid, "chat")
        
        #For now, skip these messages. Deal with them later
        if etype == "skip":
            return
        else:
            text = tags.get("system-msg") or ""

        self.on_event_cb({
            "type": "notice",
            "user": user,
            "text": text,
            "eventType": etype,
            "tags": tags,
        })

    # TwitchIO 2.x+ uses raw events, 1.x uses non-raw
    # Only implement the raw version for 2.x+, let 1.x fall through to non-raw
    async def event_raw_usernotice(self, channel, tags):
        # Only handle if we're on 2.x+ (which supports raw events)
        if self._major >= 2:
            self._emit_usernotice(channel, tags)

    # TwitchIO 1.x fallback - only fires on 1.x
    async def event_usernotice(self, channel, tags):
        # Only handle if we're on 1.x (which doesn't have raw events)
        if self._major < 2:
            self._emit_usernotice(channel, tags)

    # ---------- Moderation Events (Bans/Timeouts) ----------
    # Handles CLEARCHAT IRC events which are sent when:
    # - A user is banned (no ban-duration tag)
    # - A user is timed out (has ban-duration tag with seconds)
    # - Chat is cleared by a moderator (no target-user-id tag)
    
    def _emit_clearchat(self, channel, tags_in):
        """Handle CLEARCHAT events (bans, timeouts, chat clears)"""
        tags = _normalize_tags(tags_in)
        # For CLEARCHAT, the target username is usually in "target-user-id" but we need the actual username
        # Try multiple fields to get the username, prioritizing login name over display name
        target_user = tags.get("login") or tags.get("display-name") or tags.get("target-user-id")
        ban_duration = tags.get("ban-duration")  # Present for timeouts, absent for bans
        
        # Debug: log all available tags for troubleshooting
        logger.info(f"CLEARCHAT tags: {tags}")
        if target_user:
            logger.info(f"Extracted target user: '{target_user}' from tags")
        
        if target_user:
            # This is a user-specific action (ban or timeout)
            event_type = "timeout" if ban_duration else "ban"
            duration = int(ban_duration) if ban_duration else None
            
            logger.info(f"Twitch moderation: {event_type} for user {target_user}" + (f" ({duration}s)" if duration else ""))
            
            self.on_event_cb({
                "type": "moderation",
                "eventType": event_type,
                "target_user": target_user,
                "duration": duration,
                "tags": tags,
            })
        else:
            # This is a general chat clear
            logger.info("Twitch chat cleared by moderator")
            self.on_event_cb({
                "type": "moderation",
                "eventType": "clear_chat",
                "tags": tags,
            })

    # TwitchIO 2.x+ uses raw events, 1.x uses non-raw
    # Only implement the raw version for 2.x+, let 1.x fall through to non-raw
    async def event_raw_clearchat(self, channel, tags):
        # Only handle if we're on 2.x+ (which supports raw events)
        if self._major >= 2:
            self._emit_clearchat(channel, tags)

    # TwitchIO 1.x fallback - only fires on 1.x
    async def event_clearchat(self, channel, tags):
        # Only handle if we're on 1.x (which doesn't have raw events)
        if self._major < 2:
            self._emit_clearchat(channel, tags)


async def run_twitch_bot(token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None], user_id: str = None):
    bot_logger = None
    bot = None
    
    # Save current directory and switch to a writable temp directory for TwitchIO token cache
    import os
    import tempfile
    original_dir = os.getcwd()
    temp_dir = tempfile.gettempdir()
    
    # Early logging to confirm function is called
    print(f"[TWITCH DEBUG] run_twitch_bot called: nick={nick}, channel={channel}, user_id={user_id}")
    
    try:
        # Change to temp directory to avoid permission issues with .tio.tokens.json
        os.chdir(temp_dir)
        
        import logging
        bot_logger = logging.getLogger("ChatYapper.Twitch")
        bot_logger.info(f"Starting Twitch bot: nick={nick}, channel={channel}, user_id={user_id}")
        
        # Log TwitchIO version for debugging
        try:
            import twitchio
            version = getattr(twitchio, "__version__", "unknown")
            bot_logger.info(f"TwitchIO version: {version}")
        except Exception:
            pass
    except Exception as log_err:
        print(f"[TWITCH DEBUG] Logging setup failed: {log_err}")
        pass

    try:
        bot_logger.info(f"Creating TwitchBot instance with user_id={user_id}...")
        bot = TwitchBot(token, nick, channel, on_event, user_id)
        if bot_logger:
            bot_logger.info("Twitch bot instance created, connecting...")

        # Start compatibly across versions
        # Prefer async start() if present (2.x/3.x), else connect() (1.x),
        # else last-resort run() via a thread to avoid blocking an async caller.
        started = False

        try:
            start_coro = getattr(bot, "start", None)
            if start_coro and asyncio.iscoroutinefunction(start_coro):
                await bot.start()
                started = True
        except AttributeError as attr_err:
            # Handle twitchio internal errors during startup
            if bot_logger:
                bot_logger.warning(f"Twitchio startup error (may be due to cancellation): {attr_err}")
            raise asyncio.CancelledError() from attr_err

        if not started:
            try:
                connect_coro = getattr(bot, "connect", None)
                if connect_coro and asyncio.iscoroutinefunction(connect_coro):
                    await bot.connect()
                    started = True
            except AttributeError as attr_err:
                if bot_logger:
                    bot_logger.warning(f"Twitchio connect error (may be due to cancellation): {attr_err}")
                raise asyncio.CancelledError() from attr_err

        if not started:
            # Blocking fallback (older 1.x) — run in executor so our async
            # function doesn't block the event loop.
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, getattr(bot, "run"))

    except asyncio.CancelledError:
        # Task was cancelled (e.g., server shutdown), clean up gracefully
        if bot_logger:
            bot_logger.info("Twitch bot task cancelled during startup")
        # Try to close the bot connection if it exists
        if bot:
            try:
                close_method = getattr(bot, "close", None)
                if close_method:
                    if asyncio.iscoroutinefunction(close_method):
                        await close_method()
                    else:
                        close_method()
            except AttributeError as attr_err:
                # Twitchio internal cleanup error (e.g., NoneType has no attribute 'cancel')
                if bot_logger:
                    bot_logger.debug(f"Twitchio internal cleanup error (safe to ignore): {attr_err}")
            except Exception as close_err:
                # Ignore other cleanup errors during cancellation
                if bot_logger:
                    bot_logger.debug(f"Error during bot cleanup: {close_err}")
        # Restore original directory
        try:
            os.chdir(original_dir)
        except Exception:
            pass
        raise  # Re-raise CancelledError so the task properly terminates
    except Exception as e:
        try:
            if bot_logger:
                bot_logger.error(f"Twitch bot startup failed: {e}", exc_info=True)
        except Exception:
            pass
        
        # Restore original directory before re-raising
        try:
            os.chdir(original_dir)
        except Exception:
            pass
        
        # Check if this is an authentication error
        error_str = str(e).lower()
        if "authentication" in error_str or "unauthorized" in error_str or "invalid" in error_str:
            # Re-raise with a more specific error type that we can catch
            from twitchio.errors import AuthenticationError
            if isinstance(e, AuthenticationError) or "access token" in error_str:
                raise AuthenticationError("Invalid or unauthorized Access Token") from e
        
        raise
