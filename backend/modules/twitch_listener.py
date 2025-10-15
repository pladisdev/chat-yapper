import asyncio
from typing import Callable, Dict, Any
from modules import logger
from twitchio.ext import commands
import twitchio

def _ti_major() -> int:
    try:
        ver = getattr(twitchio, "__version__", "2.0.0")
        return int(str(ver).split(".")[0])
    except Exception:
        # Assume modern if unknown
        return 2

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
    def __init__(self, token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None]):
        # Handle both access-token and oauth: formats
        if token and not token.startswith("oauth:"):
            token = f"oauth:{token}"

        self._major = _ti_major()
        self.on_event_cb = on_event
        self.channel_name = channel
        self._nick = nick  # keep our own record for logs

        # Build constructor kwargs compatible with 1.x and 2.x
        if self._major >= 2:
            super().__init__(token=token, prefix="!", initial_channels=[channel])
        else:
            # TwitchIO 1.x expects irc_token + nick
            super().__init__(irc_token=token, nick=nick, prefix="!", initial_channels=[channel])

    # ---------- Lifecycle ----------

    async def event_ready(self):
        # self.nick is available in both, but keep fallback to provided nick
        who = getattr(self, "nick", None) or self._nick or "unknown"
        try:
            logger.info(f"Twitch bot ready as {who}, listening to {self.channel_name}")
        except Exception:
            pass

    async def event_error(self, error, data=None):
        try:
            logger.error(f"Twitch bot error: {error}", exc_info=True)
        except Exception:
            pass

    # ---------- Messages ----------

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

        # If you also use commands, keep TwitchIO's command handling alive:
        try:
            await self.handle_commands(message)  # no-op if no commands defined
        except Exception:
            pass

    # ---------- Notices (subs, raids, etc.) ----------

    def _emit_usernotice(self, channel, tags_in):
        tags = _normalize_tags(tags_in)
        msgid = (tags.get("msg-id") or "").lower()
        user = tags.get("display-name") or tags.get("login") or "unknown"
        text = tags.get("system-msg") or ""

        etype = {
            "sub": "sub",
            "resub": "sub",
            "subgift": "sub",
            "anonsubgift": "sub",
            "submysterygift": "sub",
            "raid": "raid",
            "bitsbadgetier": "bits",
        }.get(msgid, "chat")

        self.on_event_cb({
            "type": "notice",
            "user": user,
            "text": text,
            "eventType": etype,
            "tags": tags,
        })

    # TwitchIO 2.x
    async def event_raw_usernotice(self, channel, tags):
        self._emit_usernotice(channel, tags)

    # TwitchIO 1.x sometimes uses event_usernotice
    async def event_usernotice(self, channel, tags):
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

    # TwitchIO 2.x
    async def event_raw_clearchat(self, channel, tags):
        self._emit_clearchat(channel, tags)

    # TwitchIO 1.x fallback
    async def event_clearchat(self, channel, tags):
        self._emit_clearchat(channel, tags)


async def run_twitch_bot(token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None]):
    bot_logger = None
    bot = None
    try:
        import logging
        bot_logger = logging.getLogger("ChatYapper.Twitch")
        bot_logger.info(f"Starting Twitch bot: nick={nick}, channel={channel}")
    except Exception:
        pass

    try:
        bot = TwitchBot(token, nick, channel, on_event)
        if bot_logger:
            bot_logger.info("Twitch bot instance created, connecting...")

        # Start compatibly across versions
        # Prefer async start() if present (2.x), else connect() (1.x),
        # else last-resort run() via a thread to avoid blocking an async caller.
        started = False

        start_coro = getattr(bot, "start", None)
        if start_coro and asyncio.iscoroutinefunction(start_coro):
            await bot.start()
            started = True

        if not started:
            connect_coro = getattr(bot, "connect", None)
            if connect_coro and asyncio.iscoroutinefunction(connect_coro):
                await bot.connect()
                started = True

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
            except Exception as close_err:
                # Ignore cleanup errors during cancellation
                if bot_logger:
                    bot_logger.debug(f"Error during bot cleanup: {close_err}")
        raise  # Re-raise CancelledError so the task properly terminates
    except Exception as e:
        try:
            if bot_logger:
                bot_logger.error(f"Twitch bot startup failed: {e}", exc_info=True)
        except Exception:
            pass
        raise
