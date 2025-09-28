import asyncio
from typing import Callable, Dict, Any

from twitchio.ext import commands

class TwitchBot(commands.Bot):
    def __init__(self, token: str, nick: str, channel: str, on_event: Callable[[Dict[str, Any]], None]):
        super().__init__(token=token, prefix="!", initial_channels=[channel])
        self.on_event_cb = on_event
        self.channel_name = channel

    async def event_ready(self):
        print(f"Twitch bot ready as {self.nick}")

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
    bot = TwitchBot(token, nick, channel, on_event)
    await bot.start()