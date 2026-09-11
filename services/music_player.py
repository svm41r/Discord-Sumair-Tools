"""
Sumair Tools Core - Audio Streaming & Music Player Service
==========================================================
Low-latency asynchronous audio streaming engine powered by yt-dlp,
discord.py VoiceClient (DAVE + PyNaCl), and local FFmpeg 7.1.
Hardened against YouTube 403 Forbidden via Android client emulation
and HTTP header propagation.
"""

import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import discord
import yt_dlp

logger = logging.getLogger("SumairTools.MusicService")

# Locate local FFmpeg binary
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_FFMPEG = os.path.join(BASE_DIR, "Sumair Tools Extension", "bin", "ffmpeg.exe")
FFMPEG_EXECUTABLE = LOCAL_FFMPEG if os.path.exists(LOCAL_FFMPEG) else "ffmpeg"

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "source_address": "0.0.0.0",
    "extractor_args": {
        "youtube": {
            "player_client": ["android", "web"]
        }
    },
}

@dataclass
class Song:
    title: str
    url: str
    stream_url: str
    duration: int
    thumbnail: Optional[str]
    requester_name: str
    requester_id: int
    http_headers: Dict[str, str] = field(default_factory=dict)

    @property
    def formatted_duration(self) -> str:
        if not self.duration:
            return "Live Stream / Unknown"
        mins, secs = divmod(self.duration, 60)
        hours, mins = divmod(mins, 60)
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"


class GuildMusicState:
    """Maintains state, playback queue, and volume per Discord Guild."""

    def __init__(self, guild_id: int, bot: discord.Client):
        self.guild_id = guild_id
        self.bot = bot
        self.queue: List[Song] = []
        self.current: Optional[Song] = None
        self.volume: float = 1.0  # 100% volume by default
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    def get_voice_client(self) -> Optional[discord.VoiceClient]:
        guild = self.bot.get_guild(self.guild_id)
        if guild and guild.voice_client and isinstance(guild.voice_client, discord.VoiceClient):
            return guild.voice_client
        return None

    def play_next(self, error=None):
        if error:
            logger.error(f"Playback error in guild {self.guild_id}: {error}")

        vc = self.get_voice_client()
        if not vc or not vc.is_connected():
            self.current = None
            return

        if not self.queue:
            self.current = None
            return

        next_song = self.queue.pop(0)
        self.current = next_song

        try:
            # Build headers argument to avoid YouTube 403 Forbidden
            header_str = "".join(f"{k}: {v}\r\n" for k, v in next_song.http_headers.items())
            if header_str:
                before_opts = f'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -headers "{header_str}"'
            else:
                before_opts = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

            raw_source = discord.FFmpegPCMAudio(
                next_song.stream_url,
                executable=FFMPEG_EXECUTABLE,
                before_options=before_opts,
                options="-vn",
            )
            source = discord.PCMVolumeTransformer(raw_source, volume=self.volume)
            vc.play(source, after=lambda e: self.loop.call_soon_threadsafe(self.play_next, e))
            logger.info(f"Now transmitting audio in guild {self.guild_id}: {next_song.title}")
        except Exception as e:
            logger.error(f"Error starting track '{next_song.title}': {e}")
            self.play_next()


class MusicService:
    """Manages audio queries and guild states."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.states: Dict[int, GuildMusicState] = {}
        self.ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

    def get_state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState(guild_id, self.bot)
        return self.states[guild_id]

    async def extract_song(self, query: str, requester: discord.Member) -> Optional[Song]:
        """Extracts audio metadata and streaming URL without blocking async loop."""
        loop = asyncio.get_event_loop()

        # Check if local file exists (e.g. sumair.mp3)
        if os.path.isfile(query):
            return Song(
                title=os.path.basename(query),
                url=query,
                stream_url=os.path.abspath(query),
                duration=0,
                thumbnail=None,
                requester_name=requester.name,
                requester_id=requester.id,
                http_headers={},
            )

        def _fetch():
            is_url = query.startswith("http://") or query.startswith("https://")
            target = query if is_url else f"ytsearch1:{query}"
            info = self.ytdl.extract_info(target, download=False)
            if not info:
                return None
            if "entries" in info:
                if not info["entries"]:
                    return None
                info = info["entries"][0]

            headers = info.get("http_headers", {})
            return Song(
                title=info.get("title", "Unknown Track"),
                url=info.get("webpage_url", query),
                stream_url=info.get("url", ""),
                duration=info.get("duration", 0),
                thumbnail=info.get("thumbnail"),
                requester_name=requester.name,
                requester_id=requester.id,
                http_headers=headers,
            )

        try:
            return await loop.run_in_executor(None, _fetch)
        except Exception as e:
            logger.error(f"Error extracting song for query '{query}': {e}")
            return None
