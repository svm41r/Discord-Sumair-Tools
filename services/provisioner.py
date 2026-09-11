"""
Sumair Tools Core - Server Provisioning Engine
==============================================
Hardened architecture deployment:
- Enforces .setup_lock self-destructing protection
- Purges legacy channels
- Synchronizes 8-tier Crimson Role Matrix (0xFF0033)
- Builds 10 Categories with exact overwrites
- Auto-populates rules, official links with action buttons, and ticket desk
"""

import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
import discord
from discord import ForumTag, ui
import config
from views.verification import VerificationView
from views.tickets import TicketLauncher

logger = logging.getLogger("SumairTools.Provisioner")

class OfficialLinksView(ui.View):
    """Persistent action buttons linking to verified official portals."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            ui.Button(
                label="Official Website",
                style=discord.ButtonStyle.link,
                url=config.SUMAIR_WEBSITE_URL,
                emoji="🌐",
            )
        )
        self.add_item(
            ui.Button(
                label="Documentation",
                style=discord.ButtonStyle.link,
                url=config.SUMAIR_DOCS_URL,
                emoji="📚",
            )
        )
        self.add_item(
            ui.Button(
                label="Gumroad Store",
                style=discord.ButtonStyle.link,
                url=config.SUMAIR_STORE_GUMROAD,
                emoji="🛍️",
            )
        )
        self.add_item(
            ui.Button(
                label="Lemon Squeezy Store",
                style=discord.ButtonStyle.link,
                url=config.SUMAIR_STORE_LEMON,
                emoji="🍋",
            )
        )

class ServerProvisioner:
    """Production provisioning engine for Sumair Tools Discord server."""

    def __init__(self, guild: discord.Guild):
        self.guild = guild
        self.roles_map: Dict[str, discord.Role] = {}

    @staticmethod
    def is_locked() -> bool:
        """Returns True if the setup lockfile exists on disk."""
        return os.path.exists(config.SETUP_LOCK_FILE)

    @staticmethod
    def set_lock():
        """Writes the setup lockfile to prevent subsequent destructive resets."""
        try:
            with open(config.SETUP_LOCK_FILE, "w", encoding="utf-8") as f:
                f.write(f"LOCKED_AT={datetime.utcnow().isoformat()}\n")
            logger.info(f"Written setup lockfile to {config.SETUP_LOCK_FILE}")
        except Exception as e:
            logger.error(f"Failed to write setup lock: {e}")

    @staticmethod
    def remove_lock():
        """Manually unlocks setup in case of an emergency override."""
        if os.path.exists(config.SETUP_LOCK_FILE):
            try:
                os.remove(config.SETUP_LOCK_FILE)
                logger.warning("Setup lockfile has been manually cleared.")
            except Exception as e:
                logger.error(f"Failed to clear lockfile: {e}")

    async def nuke_legacy_structure(self, progress_callback=None) -> int:
        """Nukes existing channels, categories, and threads (excluding Discord system channels)."""
        deleted_count = 0
        logger.warning(f"Purging legacy channels for guild '{self.guild.name}' ({self.guild.id})")

        all_channels = list(self.guild.channels)
        for channel in all_channels:
            try:
                if channel == self.guild.rules_channel or channel == self.guild.public_updates_channel:
                    logger.info(f"Skipping Discord-reserved system channel: #{channel.name}")
                    continue

                await channel.delete(reason="Sumair Tools Core: Full Infrastructure Reset")
                deleted_count += 1
                if progress_callback:
                    await progress_callback(f"Deleted #{channel.name} ({deleted_count}/{len(all_channels)})")
                await asyncio.sleep(0.3)
            except (discord.Forbidden, discord.HTTPException) as e:
                logger.warning(f"Could not delete channel #{channel.name}: {e}")

        logger.info(f"Purged {deleted_count} obsolete channels/categories.")
        return deleted_count

    async def provision_roles(self, progress_callback=None) -> Dict[str, discord.Role]:
        """Provisions and synchronizes the 8-tier Crimson Role Matrix."""
        logger.info("Synchronizing 8-tier Crimson Role Matrix...")
        existing_roles = {role.name: role for role in self.guild.roles}
        created_or_updated: Dict[str, discord.Role] = {}

        bot_member = self.guild.me
        bot_top_role = bot_member.top_role

        for role_def in config.ROLE_HIERARCHY:
            permissions = discord.Permissions.none()
            if role_def.is_admin:
                permissions = discord.Permissions(administrator=True)
            elif role_def.name == config.ROLE_ADMIN:
                permissions = discord.Permissions(
                    manage_guild=True,
                    manage_roles=True,
                    manage_channels=True,
                    kick_members=True,
                    ban_members=True,
                    manage_messages=True,
                    view_audit_log=True,
                    moderate_members=True,
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    mention_everyone=True,
                )
            elif role_def.name == config.ROLE_SUPPORT_LEAD:
                permissions = discord.Permissions(
                    manage_threads=True,
                    manage_messages=True,
                    read_messages=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                )
            elif role_def.name in (config.ROLE_PRO_LICENSE, config.ROLE_VIP, config.ROLE_BETA, config.ROLE_VERIFIED):
                permissions = discord.Permissions(
                    read_messages=True,
                    send_messages=True,
                    read_message_history=True,
                    embed_links=True,
                    attach_files=True,
                    add_reactions=True,
                    use_external_emojis=True,
                    connect=True,
                    speak=True,
                )

            color = discord.Color(role_def.color)

            if role_def.name in existing_roles:
                target_role = existing_roles[role_def.name]
                try:
                    if target_role < bot_top_role:
                        await target_role.edit(
                            color=color,
                            hoist=role_def.hoist,
                            mentionable=role_def.mentionable,
                            permissions=permissions if role_def.is_admin or role_def.name in (config.ROLE_ADMIN, config.ROLE_SUPPORT_LEAD) else target_role.permissions,
                            reason="Sumair Tools Core: Synced Crimson role specs",
                        )
                        logger.info(f"Updated role: {role_def.name}")
                    else:
                        logger.warning(f"Role '{role_def.name}' is above bot role '{bot_top_role.name}', skipping edit.")
                except discord.HTTPException as e:
                    logger.error(f"Failed to edit role '{role_def.name}': {e}")
                created_or_updated[role_def.name] = target_role
            else:
                try:
                    new_role = await self.guild.create_role(
                        name=role_def.name,
                        color=color,
                        hoist=role_def.hoist,
                        mentionable=role_def.mentionable,
                        permissions=permissions,
                        reason="Sumair Tools Core: Provisioned Crimson role matrix",
                    )
                    logger.info(f"Created role: {role_def.name}")
                    created_or_updated[role_def.name] = new_role
                    await asyncio.sleep(0.3)
                except discord.HTTPException as e:
                    logger.error(f"Failed to create role '{role_def.name}': {e}")

            if progress_callback:
                await progress_callback(f"Synced role: {role_def.name}")

        self.roles_map = created_or_updated
        return created_or_updated

    def _build_overwrites(self, permission_mode: str) -> Dict[discord.abc.Snowflake, discord.PermissionOverwrite]:
        """Constructs explicit category-level permission overwrites based on operational mode."""
        everyone = self.guild.default_role
        verified = self.roles_map.get(config.ROLE_VERIFIED)
        unverified = self.roles_map.get(config.ROLE_UNVERIFIED)
        pro_license = self.roles_map.get(config.ROLE_PRO_LICENSE)
        beta_tester = self.roles_map.get(config.ROLE_BETA)
        founder = self.roles_map.get(config.ROLE_FOUNDER)
        admin = self.roles_map.get(config.ROLE_ADMIN)
        bot_member = self.guild.me

        overwrites: Dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}

        # Bot always retains management permissions
        overwrites[bot_member] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
        )

        if permission_mode == "onboarding":
            # Public read-only
            overwrites[everyone] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False,
                add_reactions=True,
                read_message_history=True,
            )
            if founder:
                overwrites[founder] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        elif permission_mode == "ecosystem":
            # Public read-only
            overwrites[everyone] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                add_reactions=True,
            )
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    read_message_history=True,
                    add_reactions=True,
                )
            if founder:
                overwrites[founder] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        elif permission_mode == "verified_only":
            # Locked to unverified and @everyone, unlocked for Verified Editor
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False, send_messages=False)
            if unverified:
                overwrites[unverified] = discord.PermissionOverwrite(view_channel=False, send_messages=False)
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    send_messages_in_threads=True,
                    create_public_threads=True,
                    embed_links=True,
                    attach_files=True,
                    read_message_history=True,
                    add_reactions=True,
                    connect=True,
                    speak=True,
                )

        elif permission_mode == "pro_vault":
            # Locked strictly to Pro License, Beta Tester, Founder, Admin
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
            if unverified:
                overwrites[unverified] = discord.PermissionOverwrite(view_channel=False)
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(view_channel=False)
            if pro_license:
                overwrites[pro_license] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )
            if beta_tester:
                overwrites[beta_tester] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )
            if founder:
                overwrites[founder] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        elif permission_mode == "founder_terminal":
            # Locked strictly to Founder / Owner
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
            if unverified:
                overwrites[unverified] = discord.PermissionOverwrite(view_channel=False)
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(view_channel=False)
            if admin:
                overwrites[admin] = discord.PermissionOverwrite(view_channel=False)
            if founder:
                overwrites[founder] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    attach_files=True,
                    embed_links=True,
                )

        elif permission_mode == "voice_collab":
            # Audio protocols open to Verified Editor
            overwrites[everyone] = discord.PermissionOverwrite(view_channel=False)
            if unverified:
                overwrites[unverified] = discord.PermissionOverwrite(view_channel=False)
            if verified:
                overwrites[verified] = discord.PermissionOverwrite(
                    view_channel=True,
                    connect=True,
                    speak=True,
                    use_voice_activation=True,
                    read_message_history=True,
                )

        return overwrites

    async def provision_channels_and_categories(self, progress_callback=None):
        """Constructs all 10 categories and channels with exact overwrites."""
        has_community = "COMMUNITY" in self.guild.features
        bitrate_limit = self.guild.bitrate_limit

        for cat_def in config.CATEGORY_STRUCTURE:
            overwrites = self._build_overwrites(cat_def.permission_mode)

            category = await self.guild.create_category(
                name=cat_def.name,
                overwrites=overwrites,
                reason="Sumair Tools Core: Fortress Architecture Category Provisioning",
            )
            logger.info(f"Created category: {cat_def.name}")
            if progress_callback:
                await progress_callback(f"Created Category: **{cat_def.name}**")

            await asyncio.sleep(0.3)

            for ch_def in cat_def.channels:
                try:
                    ch_overwrites = None
                    # Custom overwrites for hidden audit channels
                    if ch_def.is_hidden:
                        ch_overwrites = dict(overwrites)
                        ch_overwrites[self.guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                        verified_role = self.roles_map.get(config.ROLE_VERIFIED)
                        if verified_role:
                            ch_overwrites[verified_role] = discord.PermissionOverwrite(view_channel=False)

                        admin_role = self.roles_map.get(config.ROLE_ADMIN)
                        founder_role = self.roles_map.get(config.ROLE_FOUNDER)
                        if admin_role and cat_def.permission_mode != "founder_terminal":
                            ch_overwrites[admin_role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True, read_message_history=True
                            )
                        if founder_role:
                            ch_overwrites[founder_role] = discord.PermissionOverwrite(
                                view_channel=True, send_messages=True, read_message_history=True
                            )

                    if ch_def.channel_type == "text":
                        kwargs = {
                            "name": ch_def.name,
                            "category": category,
                            "topic": ch_def.topic,
                            "slowmode_delay": ch_def.slowmode_delay,
                            "reason": "Sumair Tools Core: Text channel creation",
                        }
                        if ch_overwrites is not None:
                            kwargs["overwrites"] = ch_overwrites
                        channel = await self.guild.create_text_channel(**kwargs)
                        logger.info(f"Created text channel: #{ch_def.name}")

                    elif ch_def.channel_type == "voice":
                        target_bitrate = min(ch_def.bitrate or 96000, bitrate_limit)
                        kwargs = {
                            "name": ch_def.name,
                            "category": category,
                            "bitrate": target_bitrate,
                            "reason": "Sumair Tools Core: Voice channel creation",
                        }
                        if ch_overwrites is not None:
                            kwargs["overwrites"] = ch_overwrites
                        channel = await self.guild.create_voice_channel(**kwargs)
                        logger.info(f"Created voice channel: {ch_def.name}")

                    elif ch_def.channel_type == "forum":
                        if has_community:
                            tags = [ForumTag(name=t, moderated=False) for t in ch_def.forum_tags]
                            kwargs = {
                                "name": ch_def.name,
                                "category": category,
                                "topic": ch_def.topic,
                                "available_tags": tags,
                                "reason": "Sumair Tools Core: Forum channel creation",
                            }
                            if ch_overwrites is not None:
                                kwargs["overwrites"] = ch_overwrites
                            channel = await self.guild.create_forum_channel(**kwargs)
                            logger.info(f"Created forum channel: {ch_def.name}")
                        else:
                            kwargs = {
                                "name": ch_def.name,
                                "category": category,
                                "topic": f"{ch_def.topic} (Enable Server Community for Forum)",
                                "reason": "Sumair Tools Core: Fallback text channel",
                            }
                            if ch_overwrites is not None:
                                kwargs["overwrites"] = ch_overwrites
                            channel = await self.guild.create_text_channel(**kwargs)

                    elif ch_def.channel_type == "stage":
                        if has_community:
                            try:
                                kwargs = {
                                    "name": ch_def.name,
                                    "category": category,
                                    "reason": "Sumair Tools Core: Stage channel creation",
                                }
                                if ch_overwrites is not None:
                                    kwargs["overwrites"] = ch_overwrites
                                channel = await self.guild.create_stage_channel(**kwargs)
                                logger.info(f"Created stage channel: {ch_def.name}")
                            except Exception as stage_err:
                                logger.warning(f"Could not create stage channel: {stage_err}, fallback to voice.")
                                kwargs = {
                                    "name": ch_def.name,
                                    "category": category,
                                    "reason": "Sumair Tools Core: Stage fallback voice",
                                }
                                if ch_overwrites is not None:
                                    kwargs["overwrites"] = ch_overwrites
                                channel = await self.guild.create_voice_channel(**kwargs)
                        else:
                            kwargs = {
                                "name": ch_def.name,
                                "category": category,
                                "reason": "Sumair Tools Core: Stage fallback voice",
                            }
                            if ch_overwrites is not None:
                                kwargs["overwrites"] = ch_overwrites
                            channel = await self.guild.create_voice_channel(**kwargs)

                    if progress_callback:
                        await progress_callback(f"  ↳ `{ch_def.name}`")
                    await asyncio.sleep(0.3)

                except Exception as ch_err:
                    logger.error(f"Failed to create channel {ch_def.name}: {ch_err}")

    async def auto_populate_sectors(self):
        """
        Auto-populates rules-and-safety, official-links, create-ticket,
        and orientation channels with rich crimson embeds (color=0xFF0033).
        """
        rules_channel = discord.utils.get(self.guild.text_channels, name="📜・rules-and-safety")
        links_channel = discord.utils.get(self.guild.text_channels, name="🔗・official-links")
        ticket_channel = discord.utils.get(self.guild.text_channels, name="🎫・create-ticket")
        welcome_channel = discord.utils.get(self.guild.text_channels, name="🚩・welcome-hub")
        announcements_channel = discord.utils.get(self.guild.text_channels, name="📢・announcements")
        faq_channel = discord.utils.get(self.guild.text_channels, name="❓・faq-knowledgebase")

        # 1. 📜・rules-and-safety (Rules + Verification View)
        if rules_channel:
            rules_embed = discord.Embed(
                title="🛡️ SERVER RULES // FORTRESS ACCESS PROTOCOL",
                description=(
                    "Welcome to **Sumair Tools** — high-performance workflow automation, After Effects JSX scripting, "
                    "and professional motion design architecture.\n\n"
                    "### 📋 OPERATIONAL DIRECTIVES\n"
                    "**1. ZERO TOLERANCE PIRACY**\n"
                    "Sharing, requesting, or distributing cracked `.jsx`, `.zxp`, or unauthorized serials results in an immediate permanent ban without appeal.\n\n"
                    "**2. PROFESSIONAL CONDUCT**\n"
                    "Maintain professional discourse. Harassment, hate speech, or unsolicited advertising will trigger automated security mutes.\n\n"
                    "**3. SECTOR DISCIPLINE**\n"
                    "Keep After Effects, Premiere Pro, and hardware discussions constrained to their designated sectors.\n\n"
                    "**4. ASSET INTEGRITY**\n"
                    "All presets and scripts shared in `#presets-and-scripts` must be vetted and free of malicious payloads.\n\n"
                    "### 🔓 AUTHENTICATION GATEWAY\n"
                    "Click **Accept Rules & Enter** below to accept the server terms, receive the **🎨 Verified Editor** role, "
                    "and gain immediate access to the community sectors."
                ),
                color=config.COLOR_CRIMSON,
            )
            rules_embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else None)
            rules_embed.set_footer(text="Sumair Tools Fortress Core • Automated Gatekeeper")
            await rules_channel.send(embed=rules_embed, view=VerificationView())

        # 2. 🔗・official-links (Official links + interactive link buttons)
        if links_channel:
            links_embed = discord.Embed(
                title="🔗 VERIFIED DIRECTORY // OFFICIAL SUMAIR TOOLS DOMAINS",
                description=(
                    "Always ensure you are accessing official Sumair Tools portals. "
                    "Never trust third-party mirrors or unauthorized Discord distributors.\n\n"
                    "• **Domain**: `https://sumairtools.online`\n"
                    "• **Documentation**: `https://sumairtools.online/docs`\n"
                    "• **Official Stores**: Gumroad & Lemon Squeezy\n\n"
                    "Use the verified portal buttons below to launch official destinations directly:"
                ),
                color=config.COLOR_CRIMSON,
            )
            links_embed.set_footer(text="Sumair Tools Ecosystem • Verified Distribution")
            await links_channel.send(embed=links_embed, view=OfficialLinksView())

        # 3. 🎫・create-ticket (Support desk launcher)
        if ticket_channel:
            ticket_embed = discord.Embed(
                title="🎫 SUMAIR TOOLS SUPPORT DESK // TRIAGE DISPATCH",
                description=(
                    "Encountering unexpected JSX errors, license activation failures, or rendering issues?\n\n"
                    "### 🛠️ PRE-FLIGHT CHECKLIST:\n"
                    "• Verify *'Allow Scripts to Write Files and Access Network'* is checked in After Effects Preferences.\n"
                    "• Consult <#faq-knowledgebase> for known JSX compatibility solutions.\n"
                    "• Check <#documentation> for installation steps.\n\n"
                    "### 📩 PRIVATE SUPPORT SECTOR:\n"
                    "Click the button below to provision an encrypted, private support ticket channel. "
                    "Access will be restricted strictly to you, **Support Lead**, and **Founder**."
                ),
                color=config.COLOR_CRIMSON,
            )
            ticket_embed.set_thumbnail(url=self.guild.icon.url if self.guild.icon else None)
            ticket_embed.set_footer(text="Sumair Tools Help Desk • Response SLA: Within 24h")
            await ticket_channel.send(embed=ticket_embed, view=TicketLauncher())

        # 4. 🚩・welcome-hub
        if welcome_channel:
            welcome_embed = discord.Embed(
                title="🚩 WELCOME // SUMAIR TOOLS ARCHITECTURE HUB",
                description=(
                    "**Sumair Tools** engineers industrial-grade automation tools and extensions for motion designers.\n\n"
                    "### 🧭 SYSTEM ORIENTATION\n"
                    "1. **Authenticate**: Read terms and click verify in <#rules-and-safety>.\n"
                    "2. **Official Portals**: Access vetted repositories in <#official-links>.\n"
                    "3. **Claim Pro License**: Run `/activate <license_key>` in any channel to unlock **💎・pro-lounge**.\n"
                    "4. **Developer Triage**: Report defects in <#create-ticket>.\n\n"
                    "Engineered for speed. Built for motion mastery."
                ),
                color=config.COLOR_CRIMSON,
            )
            welcome_embed.set_footer(text="https://sumairtools.online")
            await welcome_channel.send(embed=welcome_embed)

        # 5. 📢・announcements
        if announcements_channel:
            ann_embed = discord.Embed(
                title="📢 FORTRESS INFRASTRUCTURE ONLINE",
                description=(
                    f"**Sumair Tools Core Fortress** is fully deployed on **{self.guild.name}**.\n\n"
                    "• **Security Engine**: Active (Anti-Spam, Anti-Raid Lockdown, Link Guard)\n"
                    "• **Authentication Gateway**: Operational\n"
                    "• **Support Desk**: Standing By\n\n"
                    "Begin your onboarding in <#rules-and-safety>."
                ),
                color=config.COLOR_CRIMSON,
            )
            await announcements_channel.send(embed=ann_embed)

        # 6. ❓・faq-knowledgebase
        if faq_channel:
            faq_embed = discord.Embed(
                title="❓ KNOWLEDGEBASE // FREQUENTLY ASKED QUESTIONS",
                description=(
                    "**Q: Where do I install .jsx and .jsxbin files?**\n"
                    "A: Place them in `After Effects/Scripts/ScriptUI Panels/` and restart After Effects.\n\n"
                    "**Q: How do I activate my Pro role?**\n"
                    "A: Use the `/activate <license_key>` slash command.\n\n"
                    "**Q: What do I do if After Effects displays 'Unable to execute script at line ...'?**\n"
                    "A: Ensure a comp is open and selected before executing scripts, and verify your host version."
                ),
                color=config.COLOR_CRIMSON,
            )
            await faq_channel.send(embed=faq_embed)
