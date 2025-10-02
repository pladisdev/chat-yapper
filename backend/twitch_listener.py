import asyncio
from typing import Callable, Dict, Any

from twitchio.ext import commands

class TwitchBot(commands.Bot):
    def __init__(self, token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None]):
        # Handle both access token and oauth: formats
        if token and not token.startswith('oauth:'):
            token = f'oauth:{token}'
        
        super().__init__(token=token, prefix="!", initial_channels=[channel])
        self.on_event_cb = on_event
        self.channel_name = channel

    async def event_ready(self):
        print(f"Twitch bot connected successfully as {self.nick}")
        print(f"Listening to channel: {self.channel_name}")
        # Also log to help debug executable issues
        try:
            import logging
            logger = logging.getLogger('ChatYapper.Twitch')
            logger.info(f"Twitch bot ready as {self.nick}, listening to {self.channel_name}")
        except:
            pass

    async def event_message(self, message):
        if message.echo:
            return
        tags = message.tags or {}
        user = message.author.name if message.author else "unknown"
        is_vip = bool(getattr(message.author, 'is_vip', False))
        payload = {
            "type": "chat",
            "user": user,
            "text": message.content,
            "eventType": "vip" if is_vip else ("highlight" if tags.get('msg-id') == 'highlighted-message' else "chat"),
            "tags": tags,
        }
        self.on_event_cb(payload)

    @commands.Cog.event()
    async def event_raw_usernotice(self, channel, tags):
        # Covers subs, raids, etc.
        msgid = tags.get('msg-id')
        user = tags.get('display-name') or tags.get('login') or 'unknown'
        text = tags.get('system-msg') or ''
        etype = {
            'sub': 'sub', 'resub': 'sub', 'subgift': 'sub', 'anonsubgift': 'sub',
            'raid': 'raid', 'submysterygift': 'sub', 'bitsbadgetier': 'bits'
        }.get(msgid, 'chat')
        self.on_event_cb({
            "type": "notice",
            "user": user,
            "text": text,
            "eventType": etype,
            "tags": tags,
        })

async def run_twitch_bot(token: str, nick: str, channel: str, on_event):
    print(f"Starting Twitch bot for channel: {channel}")
    try:
        import logging
        logger = logging.getLogger('ChatYapper.Twitch')
        logger.info(f"Starting Twitch bot: nick={nick}, channel={channel}")
    except:
        pass
    
    try:
        bot = TwitchBot(token, nick, channel, on_event)
        print(f"Twitch bot instance created, connecting...")
        await bot.start()
    except Exception as e:
        print(f"Twitch bot failed to start: {e}")
        try:
            logger = logging.getLogger('ChatYapper.Twitch')
            logger.error(f"Twitch bot startup failed: {e}", exc_info=True)
        except:
            pass
        raise