"""
Sumair Tools Core - Welcome and Onboarding Cog
==============================================
Automated, high-fidelity welcome messages for new members.
Configurable per-guild via slash commands with custom embeds,
placeholders, and database persistence. Includes zero-touch
auto-discovery for channels like `join-hub` or `welcome-hub`.
"""

import os
import sqlite3
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import discord
from discord import app_commands
from discord.ext import commands
import config

logger = logging.getLogger("SumairTools.WelcomeCog")

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "welcome.db")

DEFAULT_BANNER_URL = "https://raw.githubusercontent.com/svm41r/Discord-Sumair-Tools/main/assets/welcome_banner.jpg"


class WelcomeDB:
    """Persistent SQLite database storing welcome channel configurations per guild."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS welcome_settings (
                    guild_id TEXT PRIMARY KEY,
                    channel_id TEXT NOT NULL,
                    custom_message TEXT,
                    banner_url TEXT,
                    enabled INTEGER DEFAULT 1,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def set_welcome(self, guild_id: int, channel_id: int, custom_message: Optional[str] = None, banner_url: Optional[str] = None) -> None:
        now = discord.utils.utcnow().isoformat()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO welcome_settings (guild_id, channel_id, custom_message, banner_url, enabled, updated_at)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    channel_id = excluded.channel_id,
                    custom_message = excluded.custom_message,
                    banner_url = excluded.banner_url,
                    enabled = 1,
                    updated_at = excluded.updated_at
            """, (str(guild_id), str(channel_id), custom_message, banner_url, now))
            conn.commit()

    def get_welcome(self, guild_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM welcome_settings WHERE guild_id = ?", (str(guild_id),))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def disable_welcome(self, guild_id: int) -> bool:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE welcome_settings SET enabled = 0 WHERE guild_id = ?", (str(guild_id),))
            conn.commit()
            return cursor.rowcount > 0


class WelcomeCog(commands.Cog):
    """Automated member greeting and onboarding system."""

    DEFAULT_BANNER = DEFAULT_BANNER_URL

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = WelcomeDB()

    def resolve_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Resolves the designated welcome channel from DB or auto-discovers join-hub / welcome-hub."""
        # 1. Stored DB configuration
        settings = self.db.get_welcome(guild.id)
        if settings and settings.get("enabled"):
            try:
                ch = guild.get_channel(int(settings["channel_id"]))
                if ch and isinstance(ch, discord.TextChannel):
                    return ch
            except (ValueError, TypeError):
                pass

        # 2. Zero-touch auto-discovery: look for join-hub, welcome-hub, join, or welcome
        ranked_candidates: List[tuple] = []
        for ch in guild.text_channels:
            name_clean = ch.name.lower().replace("・", "-").replace("·", "-").replace(" ", "-")
            if "join-hub" in name_clean:
                ranked_candidates.append((1, ch))
            elif "welcome-hub" in name_clean:
                ranked_candidates.append((2, ch))
            elif "join" in name_clean:
                ranked_candidates.append((3, ch))
            elif "welcome" in name_clean:
                ranked_candidates.append((4, ch))

        if ranked_candidates:
            ranked_candidates.sort(key=lambda x: x[0])
            matched_channel: discord.TextChannel = ranked_candidates[0][1]
            # Automatically persist into database
            self.db.set_welcome(
                guild_id=guild.id,
                channel_id=matched_channel.id,
                custom_message=None,
                banner_url=self.DEFAULT_BANNER
            )
            logger.info(f"Auto-configured welcome channel #{matched_channel.name} ({matched_channel.id}) for guild '{guild.name}'")
            return matched_channel

        # 3. System channel fallback
        if guild.system_channel and isinstance(guild.system_channel, discord.TextChannel):
            return guild.system_channel

        return None

    @commands.Cog.listener()
    async def on_ready(self):
        """Auto-discovers and sets up welcome channels on startup for all guilds."""
        for guild in self.bot.guilds:
            try:
                ch = self.resolve_welcome_channel(guild)
                if ch:
                    logger.info(f"Welcome channel ready for guild '{guild.name}': #{ch.name}")
            except Exception as e:
                logger.error(f"Error resolving welcome channel for {guild.name}: {e}")

    def build_welcome_embed(self, member: discord.Member, custom_msg: Optional[str] = None, banner_url: Optional[str] = None) -> discord.Embed:
        guild = member.guild
        embed = discord.Embed(
            title=f"👋 WELCOME TO {guild.name.upper()}",
            color=config.COLOR_CRIMSON,
            timestamp=discord.utils.utcnow()
        )

        if custom_msg:
            formatted = custom_msg.replace("{user}", member.mention) \
                                  .replace("{username}", member.name) \
                                  .replace("{server}", guild.name) \
                                  .replace("{count}", str(guild.member_count))
            embed.description = formatted
        else:
            embed.description = (
                f"Welcome {member.mention} to **{guild.name}**!\n\n"
                f"We are excited to have you here. Please make sure to review the server rules "
                f"and introduce yourself to the community!"
            )

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="👥 Member Count", value=f"#{guild.member_count}", inline=True)

        effective_banner = banner_url or self.DEFAULT_BANNER
        if effective_banner:
            embed.set_image(url=effective_banner)

        embed.set_footer(text=f"User ID: {member.id} • Fortress Onboarding Engine")
        return embed

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Listens for new members and sends the welcome embed to the designated channel."""
        if member.bot:
            return

        channel = self.resolve_welcome_channel(member.guild)
        if not channel:
            return

        permissions = channel.permissions_for(member.guild.me)
        if not permissions.send_messages or not permissions.embed_links:
            logger.warning(f"Missing send_messages or embed_links permissions in welcome channel #{channel.name} ({member.guild.name}).")
            return

        settings = self.db.get_welcome(member.guild.id)
        custom_msg = settings.get("custom_message") if settings else None
        banner_url = (settings.get("banner_url") if settings else None) or self.DEFAULT_BANNER

        try:
            embed = self.build_welcome_embed(
                member,
                custom_msg=custom_msg,
                banner_url=banner_url
            )
            await channel.send(content=f"👋 Welcome {member.mention} to **{member.guild.name}**!", embed=embed)
            logger.info(f"Dispatched welcome greeting for {member.name} in {member.guild.name} -> #{channel.name}")
        except Exception as e:
            logger.error(f"Failed sending welcome message for {member.name} in {member.guild.name}: {e}")

    @app_commands.command(name="setwelcome", description="Configure the automatic welcome channel and greeting.")
    @app_commands.describe(
        channel="The text channel where welcome messages should be posted",
        message="Optional custom greeting text (supports {user}, {username}, {server}, {count})",
        banner_url="Optional direct image/GIF URL for the embed banner"
    )
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def set_welcome_cmd(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: Optional[str] = None,
        banner_url: Optional[str] = None
    ):
        """Sets up or updates the welcome system for this server."""
        perms = channel.permissions_for(interaction.guild.me)
        if not perms.send_messages or not perms.embed_links:
            await interaction.response.send_message(
                f"❌ I need Send Messages and Embed Links permissions in {channel.mention} to post welcome cards.",
                ephemeral=True
            )
            return

        effective_banner = banner_url or self.DEFAULT_BANNER

        self.db.set_welcome(
            guild_id=interaction.guild_id,
            channel_id=channel.id,
            custom_message=message,
            banner_url=effective_banner
        )

        preview_embed = self.build_welcome_embed(
            interaction.user,
            custom_msg=message,
            banner_url=effective_banner
        )

        response_embed = discord.Embed(
            title="🛡️ WELCOME SYSTEM CONFIGURED",
            description=(
                f"Automatic member greetings are now **ACTIVE**!\n\n"
                f"📌 **Channel**: {channel.mention}\n"
                f"💬 **Custom Message**: {f'`{message}`' if message else '*Default Greeting*'}\n"
                f"🖼️ **Banner**: [View Banner]({effective_banner})\n\n"
                f"*(Below is a live preview of how new members will be greeted)*"
            ),
            color=config.COLOR_SUCCESS
        )

        await interaction.response.send_message(embeds=[response_embed, preview_embed], ephemeral=True)

    @app_commands.command(name="testwelcome", description="Send a test welcome message to your configured welcome channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def test_welcome_cmd(self, interaction: discord.Interaction):
        """Simulates a welcome greeting in the configured channel."""
        channel = self.resolve_welcome_channel(interaction.guild)
        if not channel:
            await interaction.response.send_message(
                "❌ No welcome channel could be resolved or auto-detected. Use `/setwelcome` to select a channel.",
                ephemeral=True
            )
            return

        settings = self.db.get_welcome(interaction.guild_id)
        custom_msg = settings.get("custom_message") if settings else None
        banner_url = (settings.get("banner_url") if settings else None) or self.DEFAULT_BANNER

        embed = self.build_welcome_embed(
            interaction.user,
            custom_msg=custom_msg,
            banner_url=banner_url
        )
        await channel.send(content=f"🧪 *(Test Greeting)* 👋 Welcome {interaction.user.mention}!", embed=embed)
        await interaction.response.send_message(f"✅ Test welcome message dispatched to {channel.mention}!", ephemeral=True)

    @app_commands.command(name="removewelcome", description="Disable automatic welcome messages for this server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def remove_welcome_cmd(self, interaction: discord.Interaction):
        """Disables the welcome system for the guild."""
        success = self.db.disable_welcome(interaction.guild_id)
        if success:
            await interaction.response.send_message("✅ Welcome greeting system has been **disabled** for this server.", ephemeral=True)
        else:
            await interaction.response.send_message("ℹ️ Welcome system was not active on this server.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
