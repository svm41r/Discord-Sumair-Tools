"""
Sumair Tools Core - Production Discord Bot & Fortress Engine
============================================================
Hardened enterprise Discord bot built with discord.py (v2.x),
featuring Slash Commands, persistent UI views (timeout=None),
native API integration for https://sumairtools.online, and
the native Fortress Security Engine (eliminating MEE6, Dyno, Carl-bot).

Theme: Minimalist Dark Industrial with Crimson Red accents (0xFF0033).
Author: Principal Systems Engineer & Cybersecurity Lead
"""

import os
import sys
import logging
import asyncio
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands
import config
from security.fortress import FortressSecurityEngine
from views.verification import VerificationView
from views.tickets import TicketLauncher, TicketCloseView
from services.provisioner import OfficialLinksView

# Force UTF-8 stream handling on Windows to prevent Unicode charmap encode errors
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# --- High-Visibility Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-24s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("SumairTools.Core")

class SumairToolsBot(commands.Bot):
    """Fortress-Hardened Core Bot for Sumair Tools."""

    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True          # Required for role swaps & raid monitoring
        intents.message_content = True  # Required for rapid anti-spam & transcript audits

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        # Initialize Fortress Security Engine
        self.security = FortressSecurityEngine(self)

    async def setup_hook(self) -> None:
        """
        Runs before gateway connection:
        1. Registers persistent UI views across restarts (timeout=None).
        2. Loads modular extension cogs.
        3. Synchronizes slash commands.
        """
        logger.info("Initializing Fortress Core setup hook...")

        # 1. Register Persistent UI Views
        self.add_view(VerificationView())
        self.add_view(TicketLauncher())
        self.add_view(TicketCloseView())
        self.add_view(OfficialLinksView())
        logger.info("Registered persistent views: VerificationView, TicketLauncher, TicketCloseView, OfficialLinksView")

        # 2. Load Modular Cogs
        cogs = [
            "cogs.admin",
            "cogs.licensing",
            "cogs.releases",
            "cogs.docs",
            "cogs.moderation",
            "cogs.utility",
            "cogs.music",
            "cogs.tempvoice",
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded extension: {cog}")
            except Exception as e:
                logger.exception(f"Failed to load extension {cog}: {e}")

        # 3. Synchronize Slash Commands
        if config.GUILD_ID:
            guild_obj = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            try:
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Synchronized {len(synced)} guild slash commands for {config.GUILD_ID}")
            except Exception as e:
                logger.error(f"Guild command sync deferred: {e}")
        else:
            try:
                synced = await self.tree.sync()
                logger.info(f"Synchronized {len(synced)} global application commands.")
            except Exception as e:
                logger.error(f"Global command sync error: {e}")

        # 4. Optional Cloud Healthcheck Server (For Render.com Web Services)
        import os
        port = os.getenv("PORT")
        if port:
            try:
                from aiohttp import web

                async def handle_health(request):
                    return web.Response(text="Sumair Tools Core: Healthy", status=200)

                app = web.Application()
                app.router.add_get("/", handle_health)
                app.router.add_get("/health", handle_health)
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, "0.0.0.0", int(port))
                await site.start()
                logger.info(f"Started cloud health check web listener on 0.0.0.0:{port}")
            except Exception as e:
                logger.warning(f"Could not start cloud web listener: {e}")

    async def on_ready(self) -> None:
        """Fires when the bot gateway connects and cache is fully populated."""
        logger.info("=" * 65)
        logger.info(f"Logged in as: {self.user.name}#{self.user.discriminator} (ID: {self.user.id})")
        logger.info(f"discord.py version: {discord.__version__}")
        logger.info(f"Connected Guilds: {len(self.guilds)}")
        for guild in self.guilds:
            logger.info(f"  • {guild.name} (ID: {guild.id}) - Members: {guild.member_count}")
        logger.info("Fortress Security Engine: ONLINE & ACTIVE")
        logger.info("=" * 65)

        # Set rich presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="sumairtools.online | 🛡️ Fortress Active",
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

        # Ensure guild-specific commands are synced if target guild is present
        if config.GUILD_ID:
            target_guild = self.get_guild(config.GUILD_ID)
            if target_guild:
                guild_obj = discord.Object(id=config.GUILD_ID)
                self.tree.copy_global_to(guild=guild_obj)
                try:
                    synced = await self.tree.sync(guild=guild_obj)
                    logger.info(f"Verified & synced {len(synced)} slash commands for {target_guild.name}")
                except Exception as e:
                    logger.error(f"Error syncing in on_ready: {e}")

    async def on_guild_join(self, guild: discord.Guild) -> None:
        """Automatically syncs slash commands when bot is invited to a new server."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        guild_obj = discord.Object(id=guild.id)
        self.tree.copy_global_to(guild=guild_obj)
        try:
            synced = await self.tree.sync(guild=guild_obj)
            logger.info(f"Automatically synced {len(synced)} slash commands for {guild.name}")
        except Exception as e:
            logger.error(f"Sync failed on guild join: {e}")

    async def on_message(self, message: discord.Message) -> None:
        """Intercepts messages for Fortress anti-spam and link inspection."""
        if message.author.bot or not message.guild:
            return

        # Scan with Fortress Security Engine
        is_mitigated = await self.security.process_message(message)
        if is_mitigated:
            return

        await self.process_commands(message)

    async def on_member_join(self, member: discord.Member) -> None:
        """
        Fires when a new user joins:
        1. Fortress Anti-Raid detection (>8 joins in 10s -> Lockdown).
        2. Assigns '⏳ Unverified' role to restrict user to Onboarding sector.
        """
        # 1. Anti-Raid evaluation
        await self.security.process_member_join(member)

        # 2. Gatekeeper role assignment
        guild = member.guild
        unverified_role = discord.utils.get(guild.roles, name=config.ROLE_UNVERIFIED)

        if unverified_role:
            try:
                await member.add_roles(unverified_role, reason="Auto-assigned Unverified role on server join")
                logger.info(f"Assigned '{config.ROLE_UNVERIFIED}' to {member.name} ({member.id})")
            except discord.Forbidden:
                logger.warning(f"Lacking permission to assign {unverified_role.name} to {member.name}.")
            except discord.HTTPException as e:
                logger.error(f"Failed to assign unverified role on join: {e}")


def register_error_handlers(bot: SumairToolsBot):
    """Registers global error telemetry for application slash commands."""

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Command on cooldown. Retry in `{error.retry_after:.1f}s`.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.MissingPermissions):
            missing_perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await interaction.response.send_message(
                f"❌ **Permission Denied**: You require {missing_perms} clearance.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            missing_perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await interaction.response.send_message(
                f"❌ **Bot Permission Error**: Missing {missing_perms}.",
                ephemeral=True,
            )
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("❌ Command can only be executed in-server.", ephemeral=True)
        else:
            cmd_name = interaction.command.name if interaction.command else "unknown"
            logger.exception(f"Unhandled slash command error in /{cmd_name}: {error}")
            msg = "❌ An unexpected error occurred while executing this command."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)


def init_opus() -> bool:
    """Ensure libopus is loaded for Discord voice on Linux containers & Windows."""
    import discord.opus
    if discord.opus.is_loaded():
        logger.info("Opus audio engine is already loaded.")
        return True

    # 1. First priority: Bundled library in repository lib/ directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_dir = os.path.join(base_dir, "lib")
    if os.path.isdir(bundled_dir):
        if bundled_dir not in os.environ.get("LD_LIBRARY_PATH", ""):
            os.environ["LD_LIBRARY_PATH"] = f"{bundled_dir}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        for bundled_name in ("libopus.so.0", "libopus.so"):
            bundled_path = os.path.join(bundled_dir, bundled_name)
            if os.path.isfile(bundled_path):
                try:
                    discord.opus.load_opus(bundled_path)
                    if discord.opus.is_loaded():
                        logger.info(f"Loaded bundled Opus library from: {bundled_path}")
                        return True
                except Exception as be:
                    logger.warning(f"Could not load bundled Opus at {bundled_path}: {be}")

    # 2. Try default loader
    try:
        if discord.opus._load_default():
            logger.info("Default Opus library loaded successfully.")
            return True
    except Exception:
        pass

    import glob
    opus_libs = [
        "libopus.so.0",
        "libopus.so",
        "opus",
        "/usr/lib/x86_64-linux-gnu/libopus.so.0",
        "/usr/lib/x86_64-linux-gnu/libopus.so",
        "/usr/lib/aarch64-linux-gnu/libopus.so.0",
        "/usr/lib/libopus.so.0",
        "/usr/local/lib/libopus.so",
        "/root/.nix-profile/lib/libopus.so",
        "/root/.nix-profile/lib/libopus.so.0",
        "/nix/var/nix/profiles/default/lib/libopus.so",
    ]
    opus_libs.extend(glob.glob("/nix/store/*libopus*/lib/libopus.so*"))
    opus_libs.extend(glob.glob("/nix/store/*opus*/lib/libopus.so*"))
    opus_libs.extend(glob.glob("/usr/lib/**/libopus.so*", recursive=True))

    for lib in opus_libs:
        try:
            discord.opus.load_opus(lib)
            if discord.opus.is_loaded():
                logger.info(f"Loaded Opus library from: {lib}")
                return True
        except Exception:
            continue

    logger.critical("Opus library could not be loaded; voice audio might fail to encode.")
    return False


def main():
    """Bot startup and token validation."""
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN == "your_bot_token_here":
        logger.critical("DISCORD_TOKEN is missing or empty! Please configure .env.")
        sys.exit(1)

    init_opus()

    bot = SumairToolsBot()
    register_error_handlers(bot)

    logger.info("Deploying Sumair Tools Core Fortress daemon...")
    bot.run(config.DISCORD_TOKEN)


if __name__ == "__main__":
    main()
