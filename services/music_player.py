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

import shutil
import glob

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    logger.info("Initialized static_ffmpeg paths.")
except Exception as e:
    logger.warning(f"static_ffmpeg initialization skipped/failed: {e}")

# Ensure system and nix bin paths are present in os.environ["PATH"]
for extra_path in (
    "/root/.nix-profile/bin",
    "/nix/var/nix/profiles/default/bin",
    "/home/railway/.nix-profile/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
):
    current_path = os.environ.get("PATH", "")
    if extra_path not in current_path and os.path.exists(extra_path):
        os.environ["PATH"] = f"{extra_path}:{current_path}"

# Locate local FFmpeg binary
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_FFMPEG = os.path.join(BASE_DIR, "Sumair Tools Extension", "bin", "ffmpeg.exe")

def get_ffmpeg_binary() -> str:
    """Robust binary resolver across Windows, Debian, and Nixpacks environments."""
    if os.path.exists(LOCAL_FFMPEG):
        return LOCAL_FFMPEG

    found = shutil.which("ffmpeg")
    if found:
        return found

    candidates = [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/root/.nix-profile/bin/ffmpeg",
        "/nix/var/nix/profiles/default/bin/ffmpeg",
        "/home/railway/.nix-profile/bin/ffmpeg",
        "/bin/ffmpeg",
    ]
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            logger.info(f"Resolved FFmpeg at absolute path: {c}")
            return c

    nix_matches = glob.glob("/nix/store/*ffmpeg*/bin/ffmpeg")
    if nix_matches:
        for m in nix_matches:
            if os.path.isfile(m) and os.access(m, os.X_OK):
                logger.info(f"Resolved FFmpeg in nix store: {m}")
                return m

    return "ffmpeg"

COOKIE_FILE = os.path.join(BASE_DIR, "cookies.txt")
env_cookies = os.getenv("YOUTUBE_COOKIES")
if env_cookies:
    try:
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(env_cookies.strip())
        logger.info("Saved YOUTUBE_COOKIES from environment variable to cookies.txt")
    except Exception as e:
        logger.warning(f"Could not save YOUTUBE_COOKIES: {e}")

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch1",
    "js_runtimes": {"node": {}},
}

if os.path.exists(COOKIE_FILE):
    YTDL_OPTIONS["cookiefile"] = COOKIE_FILE
    logger.info(f"Loaded YouTube cookies from {COOKIE_FILE}")

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
        self.text_channel: Optional[Any] = None
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

    def get_voice_client(self) -> Optional[discord.VoiceClient]:
        guild = self.bot.get_guild(self.guild_id)
        if guild and guild.voice_client and isinstance(guild.voice_client, discord.VoiceClient):
            return guild.voice_client
        return None

    def play_next(self, error=None):
        if error:
            logger.error(f"Playback error in guild {self.guild_id}: {error}")
            if self.text_channel:
                asyncio.run_coroutine_threadsafe(
                    self.text_channel.send(f"⚠️ Audio playback stopped: `{error}`"),
                    self.loop
                )

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
            user_agent = next_song.http_headers.get("User-Agent", "")
            before_opts = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            if user_agent:
                before_opts += f' -user_agent "{user_agent}"'

            ffmpeg_bin = get_ffmpeg_binary()
            logger.info(f"Invoking FFmpeg executable: {ffmpeg_bin}")
            raw_source = discord.FFmpegPCMAudio(
                next_song.stream_url,
                executable=ffmpeg_bin,
                before_options=before_opts,
                options="-vn",
            )
            source = discord.PCMVolumeTransformer(raw_source, volume=self.volume)
            vc.play(source, after=lambda e: self.loop.call_soon_threadsafe(self.play_next, e))
            logger.info(f"Now transmitting audio in guild {self.guild_id}: {next_song.title}")
        except Exception as e:
            logger.exception(f"Error starting track '{next_song.title}': {e}")
            if self.text_channel:
                asyncio.run_coroutine_threadsafe(
                    self.text_channel.send(f"❌ Failed to stream audio for **{next_song.title}**: `{e}`"),
                    self.loop
                )
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
            info = None

            if is_url:
                try:
                    info = self.ytdl.extract_info(query, download=False)
                except Exception as e:
                    logger.warning(f"Direct URL extraction failed for '{query}': {e}")
                    raise e
            else:
                # 1. Primary search: YouTube
                try:
                    info = self.ytdl.extract_info(f"ytsearch1:{query}", download=False)
                    if not info or not info.get("entries"):
                        info = None
                except Exception as yt_err:
                    logger.warning(f"YouTube search blocked/failed ({yt_err}). Attempting SoundCloud fallback...")
                    info = None

                # 2. Resilient fallback search: SoundCloud (never blocked by YouTube bot checks)
                if not info:
                    try:
                        info = self.ytdl.extract_info(f"scsearch1:{query}", download=False)
                        if info and info.get("entries"):
                            logger.info(f"Successfully resolved '{query}' via SoundCloud fallback.")
                    except Exception as sc_err:
                        logger.error(f"SoundCloud fallback also failed: {sc_err}")
                        return None

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
