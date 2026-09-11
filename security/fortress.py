"""
Sumair Tools Core - Fortress Security Engine
============================================
Autonomous anti-MEE6 / anti-Dyno / anti-Carl security daemon:
1. Rapid-Fire Anti-Spam: >5 msgs in 3s -> Immediate Purge + 10m Timeout.
2. Anti-Raid / Mass-Join: >8 joins in 10s -> Automatic Lockdown + Emergency Ping.
3. Link Guard / Anti-Scam: Deletes unapproved Discord invites & scam links from unverified users.
"""

import re
import time
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import discord
import config

logger = logging.getLogger("SumairTools.Fortress")

class FortressSecurityEngine:
    """Enterprise-grade security gatekeeper and intrusion detection system."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        # Maps user_id -> List of message epoch timestamps
        self.user_message_timestamps: Dict[int, List[float]] = defaultdict(list)
        # Maps user_id -> List of recent discord.Message objects for purge
        self.user_recent_messages: Dict[int, List[discord.Message]] = defaultdict(list)
        # Guild join timestamps for raid detection
        self.guild_join_timestamps: List[float] = []
        # Lockdown state
        self.lockdown_active: bool = False

        # Compiled Regex patterns
        self.invite_pattern = re.compile(config.INVITE_REGEX, re.IGNORECASE)
        self.scam_pattern = re.compile(config.SUSPICIOUS_LINKS_REGEX, re.IGNORECASE)

    async def log_security_event(self, guild: discord.Guild, embed: discord.Embed):
        """Dispatches formatted telemetry into 📡・server-logs."""
        log_channel = discord.utils.get(guild.text_channels, name="📡・server-logs") or discord.utils.get(guild.text_channels, name="server-logs")
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.HTTPException as e:
                logger.error(f"Failed to post to security log: {e}")

    async def alert_owner_terminal(self, guild: discord.Guild, message_text: str, embed: Optional[discord.Embed] = None):
        """Pings the Founder / Sumair in 🔒・owner-terminal during critical incidents."""
        terminal_channel = discord.utils.get(guild.text_channels, name="🔒・owner-terminal") or discord.utils.get(guild.text_channels, name="owner-terminal")
        founder_role = discord.utils.get(guild.roles, name=config.ROLE_FOUNDER)
        ping = f"{founder_role.mention} " if founder_role else "@everyone "

        if terminal_channel:
            try:
                await terminal_channel.send(content=f"🚨 {ping}\n{message_text}", embed=embed)
            except discord.HTTPException as e:
                logger.error(f"Failed to alert owner terminal: {e}")

    async def process_message(self, message: discord.Message) -> bool:
        """
        Scans inbound messages for spam floods and unauthorized invite/scam links.
        Returns True if message violated security policy and was mitigated.
        """
        if not message.guild or message.author.bot:
            return False

        author = message.author
        if not isinstance(author, discord.Member):
            return False

        # Staff exemption: Founder and Admin are exempt from spam and link checks
        author_role_names = {r.name for r in author.roles}
        is_staff = author.guild_permissions.administrator or bool(
            author_role_names.intersection({config.ROLE_FOUNDER, config.ROLE_ADMIN})
        )

        now = time.time()

        # -------------------------------------------------------------
        # 1. RAPID-FIRE ANTI-SPAM ENGINE (>5 msgs in 3s)
        # -------------------------------------------------------------
        if not is_staff:
            timestamps = self.user_message_timestamps[author.id]
            recent_msgs = self.user_recent_messages[author.id]

            # Prune messages older than window
            cutoff = now - config.SPAM_WINDOW_SECONDS
            valid_indices = [i for i, t in enumerate(timestamps) if t >= cutoff]
            self.user_message_timestamps[author.id] = [timestamps[i] for i in valid_indices]
            self.user_recent_messages[author.id] = [recent_msgs[i] for i in valid_indices]

            # Record this message
            self.user_message_timestamps[author.id].append(now)
            self.user_recent_messages[author.id].append(message)

            if len(self.user_message_timestamps[author.id]) > config.SPAM_MSG_LIMIT:
                logger.warning(f"Spam flood detected by {author.name}#{author.discriminator} ({author.id})")

                # Purge messages
                msgs_to_delete = list(self.user_recent_messages[author.id])
                self.user_message_timestamps[author.id].clear()
                self.user_recent_messages[author.id].clear()

                for msg in msgs_to_delete:
                    try:
                        await msg.delete()
                    except (discord.NotFound, discord.Forbidden):
                        pass

                # Apply 10 minute timeout
                timeout_until = discord.utils.utcnow() + timedelta(minutes=config.SPAM_TIMEOUT_MINUTES)
                try:
                    await author.timeout(
                        timeout_until,
                        reason="Fortress Security Engine: Rapid-fire message flood detected",
                    )
                except discord.Forbidden:
                    logger.error(f"Cannot timeout user {author.name}; check role hierarchy.")

                # Notify user
                warn_embed = discord.Embed(
                    title="🛑 FORTRESS SECURITY INTERVENTION",
                    description=(
                        f"{author.mention}, you have been timed out for **{config.SPAM_TIMEOUT_MINUTES} minutes**.\n\n"
                        "**Violation**: Rapid-fire message flood (`>5 messages in 3 seconds`).\n"
                        "All messages were automatically purged. Continued disruption may result in an automated ban."
                    ),
                    color=config.COLOR_CRIMSON,
                )
                warn_embed.set_footer(text="Sumair Tools Fortress Security • Incident #SPAM-AUTO")
                try:
                    await message.channel.send(embed=warn_embed, delete_after=12)
                except discord.HTTPException:
                    pass

                # Log incident to 📡・server-logs
                log_embed = discord.Embed(
                    title="⚠️ SECURITY INCIDENT: SPAM FLOOD MITIGATED",
                    description=(
                        f"**Target Member**: {author.mention} (`{author.id}`)\n"
                        f"**Channel**: {message.channel.mention}\n"
                        f"**Action Taken**: Purged `{len(msgs_to_delete)}` messages + **10m Timeout**\n"
                        f"**Detection**: Rate exceeded `{config.SPAM_MSG_LIMIT} messages / {config.SPAM_WINDOW_SECONDS}s`\n"
                        f"**Timestamp**: <t:{int(now)}:F>"
                    ),
                    color=config.COLOR_CRIMSON,
                )
                log_embed.set_thumbnail(url=author.display_avatar.url)
                await self.log_security_event(message.guild, log_embed)
                return True

        # -------------------------------------------------------------
        # 2. ANTI-SCAM & LINK GUARD ENGINE
        # -------------------------------------------------------------
        # Members with Verified Editor or higher are trusted to share links
        trusted_roles = {
            config.ROLE_FOUNDER,
            config.ROLE_ADMIN,
            config.ROLE_SUPPORT_LEAD,
            config.ROLE_PRO_LICENSE,
            config.ROLE_VIP,
            config.ROLE_BETA,
            config.ROLE_VERIFIED,
        }
        has_trusted_role = bool(author_role_names.intersection(trusted_roles))

        if not has_trusted_role:
            content = message.content
            has_invite = bool(self.invite_pattern.search(content))
            has_scam = bool(self.scam_pattern.search(content))

            if has_invite or has_scam:
                try:
                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass

                violation_type = "Discord Invite Link" if has_invite else "Suspicious Phishing / Scam Pattern"
                logger.warning(f"Link Guard blocked {violation_type} from unverified user {author.name} ({author.id})")

                # Warning
                warn_embed = discord.Embed(
                    title="🛡️ LINK GUARD BLOCKED MESSAGE",
                    description=(
                        f"{author.mention}, unverified members are prohibited from posting links.\n"
                        f"**Reason**: {violation_type}.\n"
                        "Please complete verification in <#rules-and-safety> before sharing content."
                    ),
                    color=config.COLOR_CRIMSON,
                )
                try:
                    await message.channel.send(embed=warn_embed, delete_after=8)
                except discord.HTTPException:
                    pass

                # Incident Telemetry
                log_embed = discord.Embed(
                    title="🚨 LINK GUARD INTERCEPTION",
                    description=(
                        f"**User**: {author.mention} (`{author.id}`)\n"
                        f"**Channel**: {message.channel.mention}\n"
                        f"**Intercepted Content**: `{content[:100]}`\n"
                        f"**Reason**: `{violation_type}` (User lacks `Verified Editor` role)\n"
                        f"**Timestamp**: <t:{int(now)}:R>"
                    ),
                    color=config.COLOR_CRIMSON,
                )
                await self.log_security_event(message.guild, log_embed)
                return True

        return False

    async def process_member_join(self, member: discord.Member):
        """
        Scans member joins for mass-join raids (>8 joins in 10s).
        Engages automatic lockdown if threshold is exceeded.
        """
        guild = member.guild
        now = time.time()

        # Prune join timestamps older than window
        cutoff = now - config.RAID_WINDOW_SECONDS
        self.guild_join_timestamps = [t for t in self.guild_join_timestamps if t >= cutoff]
        self.guild_join_timestamps.append(now)

        join_count = len(self.guild_join_timestamps)

        if join_count > config.RAID_JOIN_LIMIT and not self.lockdown_active:
            self.lockdown_active = True
            logger.critical(f"MASS-JOIN RAID DETECTED in {guild.name}! ({join_count} joins in {config.RAID_WINDOW_SECONDS}s)")

            # Lock down @everyone send permissions
            try:
                default_role = guild.default_role
                current_perms = default_role.permissions
                current_perms.update(send_messages=False, send_messages_in_threads=False, add_reactions=False)
                await default_role.edit(permissions=current_perms, reason="Fortress Security Engine: Anti-Raid Automated Lockdown")
                logger.info("Successfully revoked send_messages on @everyone")
            except discord.Forbidden:
                logger.error("Failed to revoke @everyone permissions; bot lacks Manage Roles / Administrator.")

            # Build Lockdown Alert Embed
            lockdown_embed = discord.Embed(
                title="🚨 FORTRESS AUTOMATED LOCKDOWN ENGAGED",
                description=(
                    f"**MASS-JOIN INTRUSION DETECTED**\n\n"
                    f"• **Rate**: `{join_count} members / {config.RAID_WINDOW_SECONDS}s`\n"
                    f"• **Trigger Member**: {member.mention} (`{member.id}`)\n"
                    f"• **Countermeasure**: `@everyone` send and reaction permissions have been **REVOKED** server-wide.\n"
                    "• **Action Required**: Review recent joiners in the audit log. Run `/lockdown-release` to lift."
                ),
                color=config.COLOR_CRIMSON,
                timestamp=datetime.utcnow(),
            )
            lockdown_embed.set_footer(text="Sumair Tools Fortress Security Subsystem")

            # Alert Owner Terminal
            await self.alert_owner_terminal(
                guild,
                message_text="**EMERGENCY: MASS-JOIN RAID IN PROGRESS. LOCKDOWN HAS BEEN AUTONOMOUSLY ENGAGED.**",
                embed=lockdown_embed,
            )

            # Log to Server Logs
            await self.log_security_event(guild, lockdown_embed)
