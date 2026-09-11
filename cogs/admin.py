"""
Sumair Tools Core - Administrative Commands Cog
===============================================
Includes /setup-server (with self-destructing .setup_lock guard),
/setup-unlock (emergency owner unlock), /post-verification, /post-support,
and /lockdown-release (anti-raid recovery).
"""

import logging
import discord
from discord import app_commands, ui
from discord.ext import commands
import config
from services.provisioner import ServerProvisioner
from views.verification import VerificationView
from views.tickets import TicketLauncher

logger = logging.getLogger("SumairTools.AdminCog")

class SetupConfirmView(ui.View):
    """Safety confirmation before executing destructive nuke and rebuild."""

    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.confirmed = False

    @ui.button(
        label="Confirm Nuke & Provision Server",
        style=discord.ButtonStyle.danger,
        emoji="💣",
    )
    async def confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Unauthorized: Only the initiating administrator can confirm.", ephemeral=True)
            return

        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="🚀 **Provisioning sequence confirmed!** Initiating purge and 10-category deployment...",
            view=self,
        )
        self.stop()

    @ui.button(label="Abort", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Unauthorized action.", ephemeral=True)
            return

        self.confirmed = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="🛑 **Operation aborted.** No server structures were altered.", view=self)
        self.stop()


class AdminCog(commands.Cog):
    """Administrative command suite for Sumair Tools."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="setup-server",
        description="Nuke legacy channels and provision the Crimson Fortress server architecture (Locked after run).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_server_cmd(self, interaction: discord.Interaction):
        """Wipes legacy channels and constructs the full 10-category Sumair Tools server layout."""
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Command must be executed within a Discord server.", ephemeral=True)
            return

        # 1. Check Persistent Setup Lock
        if ServerProvisioner.is_locked():
            lock_embed = discord.Embed(
                title="🛑 SETUP LOCKED // SAFETY ENGAGED",
                description=(
                    "The `/setup-server` command is **permanently locked** on this instance to prevent accidental server wipes.\n\n"
                    "If you are the Server Owner and need to re-provision from scratch, run `/setup-unlock` first."
                ),
                color=config.COLOR_CRIMSON,
            )
            lock_embed.set_footer(text="Sumair Tools Fortress Core • Self-Destructing Lock Protection")
            await interaction.response.send_message(embed=lock_embed, ephemeral=True)
            return

        # 2. Permission checks: Server Owner or Administrator
        if not interaction.user.guild_permissions.administrator and interaction.user.id != guild.owner_id:
            await interaction.response.send_message("❌ You must have Administrator permissions to run server provisioning.", ephemeral=True)
            return

        if not guild.me.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ **Missing Bot Permission**: The bot requires **Administrator** permissions to construct categories and configure overwrites.",
                ephemeral=True,
            )
            return

        # 3. Confirmation Dialog
        confirm_embed = discord.Embed(
            title="⚠️ CRITICAL NOTICE // ARCHITECTURE DEPLOYMENT",
            description=(
                f"You are about to rebuild **{guild.name}** into the Sumair Tools Fortress layout.\n\n"
                "**Action Plan:**\n"
                "1. **Legacy Purge**: All current channels & categories will be **deleted**.\n"
                "2. **Role Hierarchy**: 8 Crimson roles synchronized (`Founder` down to `Unverified`).\n"
                "3. **Category Tree**: 10 categories, forums with tags, high-bitrate voice, and stage.\n"
                "4. **Auto-Population**: Rules, official links, and ticket launcher embeds deployed.\n"
                "5. **Persistent Lock**: `.setup_lock` will be engaged upon completion.\n\n"
                "**Do you confirm this action?**"
            ),
            color=config.COLOR_CRIMSON,
        )
        confirm_embed.set_footer(text="This action is irreversible. Sumair Tools Core.")

        view = SetupConfirmView(author_id=interaction.user.id)
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=False)

        await view.wait()
        if not view.confirmed:
            return

        # 4. Provisioning Process
        status_msg = await interaction.channel.send("⏳ **Phase 1/4**: Purging legacy channels...")

        async def update_status(text: str):
            try:
                await status_msg.edit(content=f"⚙️ **Deployment in progress:**\n> {text}")
            except Exception:
                pass

        provisioner = ServerProvisioner(guild)

        try:
            # Step 1: Wipe legacy
            nuked_count = await provisioner.nuke_legacy_structure(progress_callback=update_status)

            # Step 2: Roles
            await update_status("Synchronizing 8-tier Crimson Role Hierarchy...")
            roles_map = await provisioner.provision_roles(progress_callback=update_status)

            # Step 3: Categories & Channels
            await update_status("Building 10 Categories, Forum Channels, and Audio Protocols...")
            await provisioner.provision_channels_and_categories(progress_callback=update_status)

            # Step 4: Auto-populate rules, links, tickets
            await update_status("Auto-populating rules, official directories, and ticket desk...")
            await provisioner.auto_populate_sectors()

            # Step 5: Lock setup
            ServerProvisioner.set_lock()
            logger.info("Engaged .setup_lock flag.")

            try:
                await status_msg.edit(content="✅ **Fortress Deployment Complete!** Setup lockfile has been engaged.")
            except Exception:
                pass

        except Exception as e:
            logger.exception(f"Error during server provisioning: {e}")
            try:
                await status_msg.edit(content=f"❌ **Provisioning Error**: `{str(e)}`")
            except Exception:
                pass

    @app_commands.command(
        name="setup-unlock",
        description="Emergency unlock for /setup-server (Server Owner Only).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setup_unlock_cmd(self, interaction: discord.Interaction):
        """Allows server owner to remove .setup_lock and enable re-provisioning."""
        if interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ **Restricted**: Only the Server Owner can remove the setup lock.",
                ephemeral=True,
            )
            return

        ServerProvisioner.remove_lock()
        await interaction.response.send_message(
            "🔓 **Setup Unlocked**: The `.setup_lock` flag has been removed. `/setup-server` is now callable.",
            ephemeral=True,
        )

    @app_commands.command(
        name="post-verification",
        description="Deploy the rules and [ Accept Rules & Enter ] button into 📜・rules-and-safety.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def post_verification_cmd(self, interaction: discord.Interaction):
        """Manually drops the rules manifesto and persistent verification button."""
        channel = discord.utils.get(interaction.guild.text_channels, name="📜・rules-and-safety") or interaction.channel
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🛡️ SERVER RULES // FORTRESS ACCESS PROTOCOL",
            description=(
                "Welcome to **Sumair Tools** — high-performance workflow automation, After Effects JSX scripting, "
                "and professional motion design architecture.\n\n"
                "### 📋 OPERATIONAL DIRECTIVES\n"
                "**1. ZERO TOLERANCE PIRACY**\n"
                "Sharing, requesting, or distributing cracked `.jsx`, `.zxp`, or unauthorized serials results in an immediate permanent ban.\n\n"
                "**2. PROFESSIONAL CONDUCT**\n"
                "Maintain professional discourse. Harassment, hate speech, or spam will trigger automated security mutes.\n\n"
                "**3. SECTOR DISCIPLINE**\n"
                "Keep After Effects, Premiere Pro, and hardware discussions constrained to their designated sectors.\n\n"
                "### 🔓 AUTHENTICATION GATEWAY\n"
                "Click **Accept Rules & Enter** below to accept the server terms, receive the **🎨 Verified Editor** role, "
                "and gain immediate access to the community sectors."
            ),
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text="Sumair Tools Fortress Core • Automated Gatekeeper")
        await channel.send(embed=embed, view=VerificationView())
        await interaction.followup.send(f"✅ Verification panel deployed to {channel.mention}!", ephemeral=True)

    @app_commands.command(
        name="post-support",
        description="Deploy the ticket launcher into 🎫・create-ticket.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def post_support_cmd(self, interaction: discord.Interaction):
        """Manually drops the support desk panel and persistent ticket launcher."""
        channel = discord.utils.get(interaction.guild.text_channels, name="🎫・create-ticket") or interaction.channel
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🎫 SUMAIR TOOLS SUPPORT DESK // TRIAGE DISPATCH",
            description=(
                "Need assistance with tool installation, license activation, or bug triage?\n\n"
                "Click the button below to spawn a private, encrypted ticket channel. "
                "Access will be restricted strictly to you, **Support Lead**, and **Founder**."
            ),
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text="Sumair Tools Help Desk • Response SLA: Within 24h")
        await channel.send(embed=embed, view=TicketLauncher())
        await interaction.followup.send(f"✅ Support panel deployed to {channel.mention}!", ephemeral=True)

    @app_commands.command(
        name="lockdown-release",
        description="Release Fortress anti-raid lockdown and restore @everyone send permissions (Staff Only).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def lockdown_release_cmd(self, interaction: discord.Interaction):
        """Lifts server lockdown imposed by the Fortress Security Engine."""
        guild = interaction.guild
        default_role = guild.default_role

        try:
            perms = default_role.permissions
            perms.update(send_messages=True, send_messages_in_threads=True, add_reactions=True)
            await default_role.edit(permissions=perms, reason="Staff manually lifted Fortress Lockdown")

            embed = discord.Embed(
                title="🟢 FORTRESS LOCKDOWN LIFTED",
                description=f"Server lockdown released by {interaction.user.mention}. Standard messaging restored for `@everyone`.",
                color=config.COLOR_SUCCESS,
            )
            await interaction.response.send_message(embed=embed)

            # Telemetry to server logs
            log_channel = discord.utils.get(guild.text_channels, name="📡・server-logs")
            if log_channel:
                await log_channel.send(embed=embed)

        except discord.Forbidden:
            await interaction.response.send_message("❌ Lacking permission to edit `@everyone` role.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
