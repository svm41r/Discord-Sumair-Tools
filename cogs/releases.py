"""
Sumair Tools Core - Releases & Changelog Cog
============================================
Staff-only command /changelog to publish professional, formatted release
notes directly into ⚡・updates-changelog.
"""

import logging
from datetime import datetime
import discord
from discord import app_commands, ui
from discord.ext import commands
import config

logger = logging.getLogger("SumairTools.ReleasesCog")

class ChangelogLinkView(ui.View):
    """Action buttons attached to changelog announcements."""

    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(
            ui.Button(
                label="Download / Update",
                style=discord.ButtonStyle.link,
                url=config.SUMAIR_WEBSITE_URL,
                emoji="🚀",
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

class ReleasesCog(commands.Cog):
    """Publishes formatted ecosystem changelogs and software updates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="changelog",
        description="Publish formatted tool patch notes to ⚡・updates-changelog (Staff Only).",
    )
    @app_commands.describe(
        tool_name="Name of the tool or script (e.g., SpeedJSX, MotionFlow, Sumair Suite)",
        version="Semantic version number (e.g., v2.4.0)",
        notes="Change breakdown & bug fixes (use \\n or standard newlines)",
    )
    @app_commands.guild_only()
    async def changelog_cmd(
        self,
        interaction: discord.Interaction,
        tool_name: str,
        version: str,
        notes: str,
    ):
        """Dispatches an official tool update embed to ⚡・updates-changelog."""
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Command can only be run in a server.", ephemeral=True)
            return

        member: discord.Member = interaction.user

        # Staff Verification Check
        user_roles = [r.name for r in member.roles]
        is_staff = (
            member.guild_permissions.administrator
            or config.ROLE_FOUNDER in user_roles
            or config.ROLE_ADMIN in user_roles
        )

        if not is_staff:
            await interaction.response.send_message(
                "❌ **Access Denied**: Only Founders and Administrators can broadcast changelogs.",
                ephemeral=True,
            )
            return

        # Target channel: ⚡・updates-changelog
        changelog_channel = (
            discord.utils.get(guild.text_channels, name="⚡・updates-changelog")
            or discord.utils.get(guild.text_channels, name="updates-changelog")
        )

        if not changelog_channel:
            await interaction.response.send_message(
                "⚠️ **Target Channel Missing**: `⚡・updates-changelog` was not found. Please run `/setup-server`.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        clean_version = version if version.startswith("v") else f"v{version}"
        formatted_notes = notes.replace("\\n", "\n")

        embed = discord.Embed(
            title=f"📦 {tool_name.upper()} // RELEASE {clean_version}",
            description=(
                f"An official update has been deployed for **{tool_name}**.\n"
                "All licensed users can obtain the updated build immediately via the portal.\n\n"
                f"### 📋 PATCH NOTES ({clean_version}):\n"
                f"{formatted_notes}\n"
            ),
            color=config.COLOR_CRIMSON,
            timestamp=datetime.utcnow(),
        )

        embed.add_field(name="🛠️ Tool", value=f"`{tool_name}`", inline=True)
        embed.add_field(name="🏷️ Version Tag", value=f"`{clean_version}`", inline=True)
        embed.add_field(name="👤 Deployed By", value=member.mention, inline=True)

        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(
            text="Sumair Tools Ecosystem • Production Release",
            icon_url=member.display_avatar.url,
        )

        view = ChangelogLinkView()
        sent_msg = await changelog_channel.send(
            content=f"📢 **NEW RELEASE**: `{clean_version}` is now live for **{tool_name}**.",
            embed=embed,
            view=view,
        )

        if changelog_channel.is_news():
            try:
                await sent_msg.publish()
            except Exception as e:
                logger.debug(f"Could not crosspost changelog: {e}")

        await interaction.followup.send(
            f"✅ **Changelog Published!** View it here: {sent_msg.jump_url}",
            ephemeral=True,
        )
        logger.info(f"Published changelog for '{tool_name} {clean_version}' to #{changelog_channel.name} by {member.name}.")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReleasesCog(bot))
