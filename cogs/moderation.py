"""
Sumair Tools Core - Enterprise Moderation & Fortress Commands Cog
================================================================
Comprehensive moderation suite replacing MEE6, Dyno, and Carl-bot.
Features native Discord timeouts, kick, ban, unban, persistent warnings,
selective purge filtering, slowmode, and channel lockdown.
"""

import re
import logging
from datetime import timedelta, datetime
from typing import Optional, Literal
import discord
from discord import app_commands
from discord.ext import commands
import config
from services.mod_db import ModerationDB

logger = logging.getLogger("SumairTools.ModerationCog")

def parse_duration(duration_str: str) -> Optional[timedelta]:
    """Parses strings like 30s, 10m, 2h, 7d into a timedelta object."""
    match = re.match(r"^(\d+)([smhd])$", duration_str.strip().lower())
    if not match:
        return None
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return timedelta(seconds=val)
    elif unit == "m":
        return timedelta(minutes=val)
    elif unit == "h":
        return timedelta(hours=val)
    elif unit == "d":
        return timedelta(days=val)
    return None

class ModerationCog(commands.Cog):
    """Fortress Moderation and Community Enforcement Suite."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.mod_db = ModerationDB()

    async def _send_audit_log(self, guild: discord.Guild, embed: discord.Embed):
        """Dispatches an audit embed to 📡・server-logs."""
        log_channel = discord.utils.get(guild.text_channels, name="📡・server-logs")
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Failed to write to audit log: {e}")

    def _can_moderate(self, mod: discord.Member, target: discord.Member, bot_member: discord.Member) -> tuple[bool, str]:
        """Validates role hierarchy to ensure action is permitted."""
        if target.id == mod.guild.owner_id:
            return False, "You cannot execute moderation actions on the Server Owner."
        if target.id == mod.id:
            return False, "You cannot moderate yourself."
        if target.id == bot_member.id:
            return False, "I cannot execute moderation actions on myself."

        if mod.id != mod.guild.owner_id and target.top_role >= mod.top_role:
            return False, f"Role Hierarchy Error: {target.mention}'s role is equal to or higher than yours."

        if target.top_role >= bot_member.top_role:
            return False, f"Role Hierarchy Error: My highest role is below {target.mention}'s role."

        return True, ""

    # ─── TIMEOUT / MUTE ───────────────────────────────────────
    @app_commands.command(name="timeout", description="Mute/timeout a member using Discord native timeout (e.g. 10m, 1h, 1d).")
    @app_commands.describe(
        member="Target member to timeout",
        duration="Duration format: 30s, 10m, 2h, 1d, 7d (Max: 28d)",
        reason="Reason for the timeout"
    )
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def timeout_cmd(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        duration: str,
        reason: Optional[str] = "No reason provided",
    ):
        guild = interaction.guild
        bot_member = guild.me
        mod = interaction.user

        can_mod, err = self._can_moderate(mod, member, bot_member)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        delta = parse_duration(duration)
        if not delta or delta.total_seconds() <= 0 or delta > timedelta(days=28):
            await interaction.response.send_message(
                "❌ **Invalid Duration**: Use formats like `30s`, `10m`, `2h`, `1d`, `7d` (Maximum is 28 days).",
                ephemeral=True
            )
            return

        until = discord.utils.utcnow() + delta
        try:
            try:
                dm_embed = discord.Embed(
                    title=f"⏳ TIMED OUT // {guild.name.upper()}",
                    description=f"You have been timed out for **{duration}**.\n**Reason**: {reason}",
                    color=config.COLOR_CRIMSON,
                )
                await member.send(embed=dm_embed)
            except Exception:
                pass

            await member.timeout(until, reason=f"[{mod.name}] {reason}")

            resp_embed = discord.Embed(
                title="⏳ MEMBER TIMED OUT",
                description=f"{member.mention} (`{member.id}`) was timed out for **{duration}**.\n**Reason**: {reason}",
                color=config.COLOR_CRIMSON,
            )
            resp_embed.set_footer(text=f"Moderator: {mod.name}")
            await interaction.response.send_message(embed=resp_embed)
            await self._send_audit_log(guild, resp_embed)

        except discord.Forbidden:
            await interaction.response.send_message("❌ Lacking permission to timeout this member.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error applying timeout: {e}", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a muted member.")
    @app_commands.describe(member="Member to lift timeout from", reason="Reason for lifting timeout")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def untimeout_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "Timeout revoked by staff"):
        guild = interaction.guild
        can_mod, err = self._can_moderate(interaction.user, member, guild.me)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        try:
            await member.timeout(None, reason=f"[{interaction.user.name}] {reason}")
            embed = discord.Embed(
                title="🟢 TIMEOUT LIFTED",
                description=f"Timeout removed from {member.mention}.\n**Reason**: {reason}",
                color=config.COLOR_SUCCESS,
            )
            embed.set_footer(text=f"Moderator: {interaction.user.name}")
            await interaction.response.send_message(embed=embed)
            await self._send_audit_log(guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error lifting timeout: {e}", ephemeral=True)

    # ─── KICK ─────────────────────────────────────────────────
    @app_commands.command(name="kick", description="Kick a member from the server.")
    @app_commands.describe(member="Target member to kick", reason="Reason for kick")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    async def kick_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "No reason provided"):
        guild = interaction.guild
        mod = interaction.user
        can_mod, err = self._can_moderate(mod, member, guild.me)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        try:
            try:
                dm_embed = discord.Embed(
                    title=f"👢 KICKED // {guild.name.upper()}",
                    description=f"You have been kicked from **{guild.name}**.\n**Reason**: {reason}",
                    color=config.COLOR_CRIMSON,
                )
                await member.send(embed=dm_embed)
            except Exception:
                pass

            await member.kick(reason=f"[{mod.name}] {reason}")
            embed = discord.Embed(
                title="👢 MEMBER KICKED",
                description=f"{member.mention} (`{member.id}`) was kicked.\n**Reason**: {reason}",
                color=config.COLOR_CRIMSON,
            )
            embed.set_footer(text=f"Moderator: {mod.name}")
            await interaction.response.send_message(embed=embed)
            await self._send_audit_log(guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to kick member: {e}", ephemeral=True)

    # ─── BAN & UNBAN ──────────────────────────────────────────
    @app_commands.command(name="ban", description="Permanently ban a member from the server.")
    @app_commands.describe(
        member="Target member to ban",
        delete_days="Days of message history to purge (0 to 7)",
        reason="Reason for ban"
    )
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def ban_cmd(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        delete_days: Optional[int] = 1,
        reason: Optional[str] = "No reason provided",
    ):
        guild = interaction.guild
        mod = interaction.user
        can_mod, err = self._can_moderate(mod, member, guild.me)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        delete_days = max(0, min(7, delete_days or 0))
        try:
            try:
                dm_embed = discord.Embed(
                    title=f"🔨 BANNED // {guild.name.upper()}",
                    description=f"You have been permanently banned from **{guild.name}**.\n**Reason**: {reason}",
                    color=config.COLOR_CRIMSON,
                )
                await member.send(embed=dm_embed)
            except Exception:
                pass

            await member.ban(delete_message_days=delete_days, reason=f"[{mod.name}] {reason}")
            embed = discord.Embed(
                title="🔨 MEMBER BANNED",
                description=f"**User**: {member.mention} (`{member.id}`)\n**Purge Window**: {delete_days} days\n**Reason**: {reason}",
                color=config.COLOR_CRIMSON,
            )
            embed.set_footer(text=f"Moderator: {mod.name}")
            await interaction.response.send_message(embed=embed)
            await self._send_audit_log(guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to ban member: {e}", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by their Discord user ID.")
    @app_commands.describe(user_id="Numeric Discord User ID to unban", reason="Reason for unban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    async def unban_cmd(self, interaction: discord.Interaction, user_id: str, reason: Optional[str] = "Pardoned by staff"):
        guild = interaction.guild
        try:
            target_id = int(user_id.strip())
            user = await self.bot.fetch_user(target_id)
            await guild.unban(user, reason=f"[{interaction.user.name}] {reason}")
            embed = discord.Embed(
                title="🟢 USER UNBANNED",
                description=f"Pardoned **{user.name}** (`{user.id}`).\n**Reason**: {reason}",
                color=config.COLOR_SUCCESS,
            )
            embed.set_footer(text=f"Moderator: {interaction.user.name}")
            await interaction.response.send_message(embed=embed)
            await self._send_audit_log(guild, embed)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID. Must be numeric.", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ User was not found in the server ban registry.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error unbanning: {e}", ephemeral=True)

    # ─── WARNINGS SYSTEM ──────────────────────────────────────
    @app_commands.command(name="warn", description="Issue a formal strike/warning to a member.")
    @app_commands.describe(member="Member to warn", reason="Rule violation details")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warn_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        guild = interaction.guild
        mod = interaction.user
        can_mod, err = self._can_moderate(mod, member, guild.me)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        warn_id = self.mod_db.add_warning(guild.id, member.id, mod.id, reason)
        all_warnings = self.mod_db.get_warnings(guild.id, member.id)

        try:
            dm_embed = discord.Embed(
                title=f"⚠️ OFFICIAL WARNING // {guild.name.upper()}",
                description=(
                    f"You have been issued a formal strike in **{guild.name}**.\n\n"
                    f"**Strike ID**: `#{warn_id}`\n"
                    f"**Total Strikes**: `{len(all_warnings)}`\n"
                    f"**Reason**: {reason}\n\n"
                    "Repeated violations will trigger automated timeouts or permanent removal."
                ),
                color=config.COLOR_CRIMSON,
            )
            await member.send(embed=dm_embed)
        except Exception:
            pass

        embed = discord.Embed(
            title="⚠️ FORMAL STRIKE ISSUED",
            description=(
                f"**Member**: {member.mention} (`{member.id}`)\n"
                f"**Strike ID**: `#{warn_id}`\n"
                f"**Total Strikes**: `{len(all_warnings)}`\n"
                f"**Reason**: {reason}"
            ),
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text=f"Moderator: {mod.name}")
        await interaction.response.send_message(embed=embed)
        await self._send_audit_log(guild, embed)

    @app_commands.command(name="warnings", description="View a member's disciplinary strike history.")
    @app_commands.describe(member="Member to inspect")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        guild = interaction.guild
        records = self.mod_db.get_warnings(guild.id, member.id)

        if not records:
            await interaction.response.send_message(f"✅ {member.mention} has a clean record (0 strikes).", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📋 DISCIPLINARY DOSSIER // {member.name}",
            description=f"Total strikes recorded on file: **`{len(records)}`**",
            color=config.COLOR_CRIMSON,
        )
        for r in records[-10:]:
            created = r['created_at'][:19].replace("T", " ")
            embed.add_field(
                name=f"Strike #{r['id']} • {created}",
                value=f"**Reason**: {r['reason']}\n**Mod ID**: <@{r['moderator_id']}>",
                inline=False,
            )
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clear-warnings", description="Reset and pardon all strikes for a member.")
    @app_commands.describe(member="Member to pardon")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def clear_warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        count = self.mod_db.clear_warnings(interaction.guild.id, member.id)
        embed = discord.Embed(
            title="🟢 STRIKES PARDONED",
            description=f"Cleared **{count}** warning(s) for {member.mention}.",
            color=config.COLOR_SUCCESS,
        )
        embed.set_footer(text=f"Authorized by: {interaction.user.name}")
        await interaction.response.send_message(embed=embed)
        await self._send_audit_log(interaction.guild, embed)

    # ─── BULK PURGE ───────────────────────────────────────────
    @app_commands.command(name="purge", description="Bulk delete messages with optional criteria.")
    @app_commands.describe(
        count="Number of messages to inspect & purge (1 to 100)",
        user="Only purge messages sent by this member",
        filter_type="Filter by type (all, bots_only, links_only, attachments_only)"
    )
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def purge_cmd(
        self,
        interaction: discord.Interaction,
        count: int,
        user: Optional[discord.Member] = None,
        filter_type: Optional[Literal["all", "bots_only", "links_only", "attachments_only"]] = "all"
    ):
        if count < 1 or count > 100:
            await interaction.response.send_message("❌ Purge count must be between 1 and 100.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        channel = interaction.channel

        def check(msg: discord.Message) -> bool:
            if user and msg.author.id != user.id:
                return False
            if filter_type == "bots_only" and not msg.author.bot:
                return False
            if filter_type == "links_only" and "http" not in msg.content:
                return False
            if filter_type == "attachments_only" and not msg.attachments:
                return False
            return True

        deleted = await channel.purge(limit=count, check=check)
        await interaction.followup.send(
            f"🧹 **Purge Complete**: Cleaned **{len(deleted)}** message(s) from {channel.mention}.",
            ephemeral=True
        )

        audit_embed = discord.Embed(
            title="🧹 BULK PURGE EXECUTED",
            description=(
                f"**Channel**: {channel.mention}\n"
                f"**Messages Purged**: `{len(deleted)}`\n"
                f"**Target Member**: {user.mention if user else '`Everyone`'}\n"
                f"**Filter Mode**: `{filter_type}`"
            ),
            color=config.COLOR_CRIMSON,
        )
        audit_embed.set_footer(text=f"Moderator: {interaction.user.name}")
        await self._send_audit_log(interaction.guild, audit_embed)

    # ─── SLOWMODE ─────────────────────────────────────────────
    @app_commands.command(name="slowmode", description="Set channel message cooldown rate limit.")
    @app_commands.describe(
        seconds="Cooldown in seconds (0 to 21600; 0 turns off)",
        channel="Channel to adjust (defaults to current)"
    )
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def slowmode_cmd(self, interaction: discord.Interaction, seconds: int, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        seconds = max(0, min(21600, seconds))
        await target.edit(slowmode_delay=seconds)

        if seconds == 0:
            msg = f"🟢 Slowmode disabled in {target.mention}."
        else:
            msg = f"⏳ Slowmode set to **{seconds} seconds** in {target.mention}."
        await interaction.response.send_message(msg, ephemeral=True)

    # ─── CHANNEL LOCK & UNLOCK ────────────────────────────────
    @app_commands.command(name="lock", description="Lock channel to prevent regular members from sending messages.")
    @app_commands.describe(channel="Channel to lock (defaults to current)", reason="Reason for channel lock")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def lock_cmd(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None, reason: Optional[str] = "Staff Channel Lockdown"):
        target = channel or interaction.channel
        guild = interaction.guild

        roles_to_restrict = [guild.default_role]
        verified_role = discord.utils.get(guild.roles, name=config.ROLE_VERIFIED_EDITOR)
        if verified_role:
            roles_to_restrict.append(verified_role)

        for role in roles_to_restrict:
            overwrite = target.overwrites_for(role)
            overwrite.send_messages = False
            overwrite.send_messages_in_threads = False
            overwrite.add_reactions = False
            await target.set_permissions(role, overwrite=overwrite, reason=f"[{interaction.user.name}] {reason}")

        embed = discord.Embed(
            title="🔒 SECTOR LOCKED",
            description=f"This channel has been locked by staff.\n**Reason**: {reason}",
            color=config.COLOR_CRIMSON,
        )
        await target.send(embed=embed)
        await interaction.response.send_message(f"🔒 Locked {target.mention}.", ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock a locked channel to restore normal messaging.")
    @app_commands.describe(channel="Channel to unlock (defaults to current)")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    async def unlock_cmd(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = channel or interaction.channel
        guild = interaction.guild

        roles_to_restore = [guild.default_role]
        verified_role = discord.utils.get(guild.roles, name=config.ROLE_VERIFIED_EDITOR)
        if verified_role:
            roles_to_restore.append(verified_role)

        for role in roles_to_restore:
            overwrite = target.overwrites_for(role)
            overwrite.send_messages = None
            overwrite.send_messages_in_threads = None
            overwrite.add_reactions = None
            await target.set_permissions(role, overwrite=overwrite, reason=f"[{interaction.user.name}] Unlocked channel")

        embed = discord.Embed(
            title="🔓 SECTOR UNLOCKED",
            description="Normal messaging permissions have been restored in this sector.",
            color=config.COLOR_SUCCESS,
        )
        await target.send(embed=embed)
        await interaction.response.send_message(f"🔓 Unlocked {target.mention}.", ephemeral=True)

    # ─── JAIL & QUARANTINE (Replaces 'JailBot') ───────────────
    @app_commands.command(name="jail", description="Quarantine and isolate a disruptive member in the server jail.")
    @app_commands.describe(member="Member to quarantine", reason="Infraction details")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def jail_cmd(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = "Disciplinary Quarantine"):
        guild = interaction.guild
        can_mod, err = self._can_moderate(interaction.user, member, guild.me)
        if not can_mod:
            await interaction.response.send_message(f"❌ {err}", ephemeral=True)
            return

        jail_role = discord.utils.get(guild.roles, name="🔒 Jailed")
        if not jail_role:
            try:
                jail_role = await guild.create_role(
                    name="🔒 Jailed",
                    color=discord.Color.dark_grey(),
                    reason="Auto-created jail quarantine role"
                )
            except Exception as e:
                await interaction.response.send_message(f"❌ Could not create jail role: {e}", ephemeral=True)
                return

        # Add jail role
        await member.add_roles(jail_role, reason=f"[{interaction.user.name}] {reason}")

        try:
            dm = discord.Embed(
                title=f"🔒 QUARANTINED // {guild.name.upper()}",
                description=f"You have been placed into server jail/quarantine.\n**Reason**: {reason}\nWait for staff instructions.",
                color=config.COLOR_CRIMSON,
            )
            await member.send(embed=dm)
        except Exception:
            pass

        embed = discord.Embed(
            title="🔒 MEMBER QUARANTINED (JAILED)",
            description=f"{member.mention} (`{member.id}`) has been sent to jail.\n**Reason**: {reason}",
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text=f"Moderator: {interaction.user.name}")
        await interaction.response.send_message(embed=embed)
        await self._send_audit_log(guild, embed)

    @app_commands.command(name="unjail", description="Release a member from server jail quarantine.")
    @app_commands.describe(member="Member to release")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    async def unjail_cmd(self, interaction: discord.Interaction, member: discord.Member):
        jail_role = discord.utils.get(interaction.guild.roles, name="🔒 Jailed")
        if not jail_role or jail_role not in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} is not currently jailed.", ephemeral=True)
            return

        await member.remove_roles(jail_role, reason=f"Released by [{interaction.user.name}]")
        embed = discord.Embed(
            title="🟢 QUARANTINE RELEASED",
            description=f"{member.mention} has been released from jail and pardoned.",
            color=config.COLOR_SUCCESS,
        )
        embed.set_footer(text=f"Authorized by: {interaction.user.name}")
        await interaction.response.send_message(embed=embed)
        await self._send_audit_log(interaction.guild, embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCog(bot))
