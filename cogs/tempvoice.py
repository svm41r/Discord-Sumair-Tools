"""
Sumair Tools Core - Dynamic Temp Voice Subsystem
================================================
Replaces VoiceMaster and TempVoice with a native, zero-latency
"Join-to-Create" dynamic voice channel generator.
Auto-spawns custom rooms for creators and auto-destroys when empty.
"""

import logging
from typing import Optional, Dict
import discord
from discord import app_commands
from discord.ext import commands
import config

logger = logging.getLogger("SumairTools.TempVoice")

class TempVoiceCog(commands.Cog):
    """Dynamic voice channel management and creator controls."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Maps temp_channel_id -> creator_user_id
        self.temp_channels: Dict[int, int] = {}

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Monitors voice moves to generate or clean up temporary voice rooms."""
        # 1. User Joined a Generator Channel
        if after.channel and after.channel != before.channel:
            ch_name = after.channel.name.lower()
            is_generator = "create" in ch_name or "➕" in ch_name or "generator" in ch_name

            if is_generator:
                guild = member.guild
                category = after.channel.category

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(connect=True, speak=True),
                    member: discord.PermissionOverwrite(
                        connect=True,
                        speak=True,
                        manage_channels=True,
                        move_members=True,
                        mute_members=True,
                    ),
                    guild.me: discord.PermissionOverwrite(
                        connect=True,
                        speak=True,
                        manage_channels=True,
                        move_members=True,
                    ),
                }

                try:
                    new_ch = await guild.create_voice_channel(
                        name=f"🔊・{member.name}'s Lounge",
                        category=category,
                        overwrites=overwrites,
                        reason=f"Temp voice created for {member.name}",
                    )
                    self.temp_channels[new_ch.id] = member.id
                    await member.move_to(new_ch)
                    logger.info(f"Created temp voice channel {new_ch.name} for {member.name}")
                except Exception as e:
                    logger.error(f"Failed to create temp voice channel: {e}")

        # 2. User Left a Temporary Channel
        if before.channel and before.channel != after.channel:
            ch_id = before.channel.id
            if ch_id in self.temp_channels:
                if len(before.channel.members) == 0:
                    try:
                        await before.channel.delete(reason="Temp voice channel empty")
                        del self.temp_channels[ch_id]
                        logger.info(f"Cleaned up empty temp voice channel {before.channel.name}")
                    except Exception as e:
                        logger.error(f"Failed to delete empty temp voice channel: {e}")

    def _get_caller_temp_channel(self, interaction: discord.Interaction) -> Optional[discord.VoiceChannel]:
        """Returns the temp voice channel if caller is inside it and is owner or admin."""
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice:
            return None

        vc = interaction.user.voice.channel
        if not vc or vc.id not in self.temp_channels:
            return None

        creator_id = self.temp_channels.get(vc.id)
        if interaction.user.id != creator_id and not interaction.user.guild_permissions.administrator:
            return None

        return vc

    @app_commands.command(name="voice-lock", description="Lock your temporary voice room to prevent others from joining.")
    @app_commands.guild_only()
    async def voice_lock_cmd(self, interaction: discord.Interaction):
        vc = self._get_caller_temp_channel(interaction)
        if not vc:
            await interaction.response.send_message("❌ You must be the owner of your active temporary voice room.", ephemeral=True)
            return

        overwrites = vc.overwrites_for(interaction.guild.default_role)
        overwrites.connect = False
        await vc.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.response.send_message("🔒 **Voice Room Locked**: New members cannot join.", ephemeral=True)

    @app_commands.command(name="voice-unlock", description="Unlock your temporary voice room to allow members in.")
    @app_commands.guild_only()
    async def voice_unlock_cmd(self, interaction: discord.Interaction):
        vc = self._get_caller_temp_channel(interaction)
        if not vc:
            await interaction.response.send_message("❌ You must be the owner of your active temporary voice room.", ephemeral=True)
            return

        overwrites = vc.overwrites_for(interaction.guild.default_role)
        overwrites.connect = True
        await vc.set_permissions(interaction.guild.default_role, overwrite=overwrites)
        await interaction.response.send_message("🔓 **Voice Room Unlocked**: Open to all verified members.", ephemeral=True)

    @app_commands.command(name="voice-limit", description="Set user capacity limit for your temporary voice room.")
    @app_commands.describe(limit="Maximum member limit (0 for unlimited, up to 99)")
    @app_commands.guild_only()
    async def voice_limit_cmd(self, interaction: discord.Interaction, limit: int):
        vc = self._get_caller_temp_channel(interaction)
        if not vc:
            await interaction.response.send_message("❌ You must be the owner of your active temporary voice room.", ephemeral=True)
            return

        limit = max(0, min(99, limit))
        await vc.edit(user_limit=limit)
        limit_str = f"**{limit} members**" if limit > 0 else "**Unlimited**"
        await interaction.response.send_message(f"👥 Voice room limit updated to {limit_str}.", ephemeral=True)

    @app_commands.command(name="voice-rename", description="Rename your temporary voice room.")
    @app_commands.describe(name="New voice room title")
    @app_commands.guild_only()
    async def voice_rename_cmd(self, interaction: discord.Interaction, name: str):
        vc = self._get_caller_temp_channel(interaction)
        if not vc:
            await interaction.response.send_message("❌ You must be the owner of your active temporary voice room.", ephemeral=True)
            return

        new_name = f"🔊・{name.strip()}"[:32]
        await vc.edit(name=new_name)
        await interaction.response.send_message(f"🏷️ Voice room renamed to **{new_name}**.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(TempVoiceCog(bot))
