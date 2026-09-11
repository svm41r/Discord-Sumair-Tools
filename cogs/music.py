"""
Sumair Tools Core - Music & Audio Stream Cog
============================================
High-fidelity music playback commands for voice channels.
Replaces third-party music bots with native, low-latency streaming.
"""

import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import config
from services.music_player import MusicService

logger = logging.getLogger("SumairTools.MusicCog")

class MusicCog(commands.Cog):
    """Voice playback and queue management commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.music_service = MusicService(bot)

    async def _ensure_voice(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        """Connects bot to the caller's voice channel if not already connected."""
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return None

        user_voice = interaction.user.voice
        if not user_voice or not user_voice.channel:
            await interaction.response.send_message("❌ You must join a voice channel first.", ephemeral=True)
            return None

        target_channel = user_voice.channel
        vc = guild.voice_client

        if not vc:
            try:
                vc = await target_channel.connect(self_deaf=False)
            except Exception as e:
                await interaction.response.send_message(f"❌ Failed to connect to voice: {e}", ephemeral=True)
                return None
        elif vc.channel.id != target_channel.id:
            await vc.move_to(target_channel)

        return vc

    @app_commands.command(name="join", description="Connect bot to your current voice channel.")
    @app_commands.guild_only()
    async def join_cmd(self, interaction: discord.Interaction):
        vc = await self._ensure_voice(interaction)
        if vc:
            await interaction.response.send_message(f"🔊 Connected to **{vc.channel.name}**.", ephemeral=True)

    @app_commands.command(name="leave", description="Disconnect bot from voice and clear queue.")
    @app_commands.guild_only()
    async def leave_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        vc = guild.voice_client if guild else None
        if not vc or not vc.is_connected():
            await interaction.response.send_message("⚠️ Not connected to any voice channel.", ephemeral=True)
            return

        state = self.music_service.get_state(guild.id)
        state.queue.clear()
        state.current = None
        await vc.disconnect(force=True)
        await interaction.response.send_message("👋 Disconnected from voice. Playback queue cleared.")

    @app_commands.command(name="play", description="Play a track or search YouTube/SoundCloud.")
    @app_commands.describe(query="Song title, search terms, or direct URL")
    @app_commands.guild_only()
    async def play_cmd(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        vc = await self._ensure_voice(interaction)
        if not vc:
            return

        member: discord.Member = interaction.user
        song = await self.music_service.extract_song(query, member)
        if not song or not song.stream_url:
            await interaction.followup.send("❌ Could not extract audio from the provided query. Try another title or URL.")
            return

        state = self.music_service.get_state(interaction.guild_id)

        if vc.is_playing() or vc.is_paused():
            state.queue.append(song)
            embed = discord.Embed(
                title="🎵 ADDED TO QUEUE",
                description=f"[{song.title}]({song.url})\n\n**Duration**: `{song.formatted_duration}`\n**Position**: `#{len(state.queue)}`",
                color=config.COLOR_CRIMSON,
            )
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            embed.set_footer(text=f"Requested by {member.name}")
            await interaction.followup.send(embed=embed)
        else:
            state.queue.append(song)
            state.play_next()
            embed = discord.Embed(
                title="▶️ NOW PLAYING",
                description=f"[{song.title}]({song.url})\n\n**Duration**: `{song.formatted_duration}`",
                color=config.COLOR_CRIMSON,
            )
            if song.thumbnail:
                embed.set_thumbnail(url=song.thumbnail)
            embed.set_footer(text=f"Requested by {member.name}")
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Pause active audio playback.")
    @app_commands.guild_only()
    async def pause_cmd(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc or not vc.is_playing():
            await interaction.response.send_message("⚠️ No active playback to pause.", ephemeral=True)
            return

        vc.pause()
        await interaction.response.send_message("⏸️ Playback paused.")

    @app_commands.command(name="resume", description="Resume paused audio playback.")
    @app_commands.guild_only()
    async def resume_cmd(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc or not vc.is_paused():
            await interaction.response.send_message("⚠️ Playback is not paused.", ephemeral=True)
            return

        vc.resume()
        await interaction.response.send_message("▶️ Playback resumed.")

    @app_commands.command(name="skip", description="Skip to the next track in queue.")
    @app_commands.guild_only()
    async def skip_cmd(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        if not vc or not vc.is_connected():
            await interaction.response.send_message("⚠️ Not connected to voice.", ephemeral=True)
            return

        state = self.music_service.get_state(interaction.guild_id)
        current = state.current

        if vc.is_playing() or vc.is_paused():
            vc.stop()  # Triggers play_next via after callback
            title = current.title if current else "Current track"
            await interaction.response.send_message(f"⏭️ Skipped **{title}**.")
        else:
            await interaction.response.send_message("⚠️ Nothing currently playing to skip.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop playback and clear the queue.")
    @app_commands.guild_only()
    async def stop_cmd(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client if interaction.guild else None
        state = self.music_service.get_state(interaction.guild_id)
        state.queue.clear()
        state.current = None

        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()

        await interaction.response.send_message("⏹️ Playback stopped and queue cleared.")

    @app_commands.command(name="queue", description="Display songs currently waiting in queue.")
    @app_commands.guild_only()
    async def queue_cmd(self, interaction: discord.Interaction):
        state = self.music_service.get_state(interaction.guild_id)

        if not state.current and not state.queue:
            await interaction.response.send_message("📭 The audio queue is currently empty.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎶 AUDIO QUEUE // LIVE STREAM",
            color=config.COLOR_CRIMSON,
        )

        if state.current:
            embed.add_field(
                name="▶️ Currently Playing",
                value=f"[{state.current.title}]({state.current.url}) (`{state.current.formatted_duration}`)\n*Requested by {state.current.requester_name}*",
                inline=False,
            )

        if state.queue:
            q_list = []
            for i, s in enumerate(state.queue[:10]):
                q_list.append(f"`{i+1}.` [{s.title[:45]}]({s.url}) (`{s.formatted_duration}`) - *{s.requester_name}*")
            if len(state.queue) > 10:
                q_list.append(f"*...+{len(state.queue) - 10} more tracks*")
            embed.add_field(name=f"📋 Up Next ({len(state.queue)} tracks)", value="\n".join(q_list), inline=False)
        else:
            embed.add_field(name="📋 Up Next", value="*No further songs enqueued.*", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="now-playing", description="Show full info about the active track.")
    @app_commands.guild_only()
    async def now_playing_cmd(self, interaction: discord.Interaction):
        state = self.music_service.get_state(interaction.guild_id)
        if not state.current:
            await interaction.response.send_message("⚠️ No track is currently playing.", ephemeral=True)
            return

        s = state.current
        embed = discord.Embed(
            title="🎧 NOW PLAYING",
            description=f"**[{s.title}]({s.url})**\n\n**Duration**: `{s.formatted_duration}`\n**Requested by**: <@{s.requester_id}>\n**Volume**: `{int(state.volume * 100)}%`",
            color=config.COLOR_CRIMSON,
        )
        if s.thumbnail:
            embed.set_thumbnail(url=s.thumbnail)
        embed.set_footer(text="Sumair Tools Core • Voice Streamer")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Set audio playback volume (0 to 150%).")
    @app_commands.describe(level="Volume percentage from 0 to 150")
    @app_commands.guild_only()
    async def volume_cmd(self, interaction: discord.Interaction, level: int):
        level = max(0, min(150, level))
        state = self.music_service.get_state(interaction.guild_id)
        state.volume = level / 100.0

        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.source and hasattr(vc.source, "volume"):
            vc.source.volume = state.volume

        await interaction.response.send_message(f"🔊 Volume set to **{level}%**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(MusicCog(bot))
