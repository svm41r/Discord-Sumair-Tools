"""
Sumair Tools Core - License Activation Cog
==========================================
Validates customer purchases via asynchronous API client and
assigns the '💎 Pro License' role, unlocking the Pro & Beta Vault.
"""

import logging
import discord
from discord import app_commands
from discord.ext import commands
import config
from services.license import LicenseService

logger = logging.getLogger("SumairTools.LicensingCog")

class LicensingCog(commands.Cog):
    """Handles purchase validation and automated role assignment."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.license_service = LicenseService()

    @app_commands.command(
        name="activate",
        description="Verify your Sumair Tools purchase and claim your 💎 Pro License role.",
    )
    @app_commands.describe(
        license_key="Your Gumroad, Lemon Squeezy, or sumairtools.online license key"
    )
    @app_commands.guild_only()
    async def activate_license(self, interaction: discord.Interaction, license_key: str):
        """Asynchronously validates a customer license key and assigns the Pro License role."""
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Command must be run in-server.", ephemeral=True)
            return

        member: discord.Member = interaction.user
        await interaction.response.defer(ephemeral=True)

        pro_role = discord.utils.get(guild.roles, name=config.ROLE_PRO_LICENSE)
        if not pro_role:
            await interaction.followup.send(
                "⚠️ **Role Missing**: The `💎 Pro License` role does not exist on this server. Please notify an administrator.",
                ephemeral=True,
            )
            return

        if pro_role in member.roles:
            await interaction.followup.send(
                f"✨ **Already Active**: You already hold the {pro_role.mention} role. "
                "You have full clearance for <#💎・pro-lounge> and <#🧪・beta-builds>.",
                ephemeral=True,
            )
            return

        # Asynchronous validation
        validation = await self.license_service.validate_license(
            license_key=license_key,
            discord_user_id=member.id,
            discord_user_name=member.name,
        )

        if not validation.valid:
            error_embed = discord.Embed(
                title="❌ LICENSE AUTHENTICATION FAILED",
                description=(
                    f"**Reason**: {validation.message}\n\n"
                    "**Verification Steps:**\n"
                    "• Double-check the license key from your receipt.\n"
                    "• Ensure no accidental leading/trailing spaces.\n"
                    "• If recently purchased, allow 60 seconds for webhooks to sync.\n"
                    "• Need support? Open a private ticket in <#create-ticket>."
                ),
                color=config.COLOR_CRIMSON,
            )
            error_embed.set_footer(text="Sumair Tools Licensing Subsystem • Verification Engine")
            await interaction.followup.send(embed=error_embed, ephemeral=True)
            return

        # Grant role
        try:
            await member.add_roles(
                pro_role,
                reason=f"License activated: {validation.tier} ({validation.product_name})",
            )
            logger.info(f"Granted '{config.ROLE_PRO_LICENSE}' to {member.name} ({member.id}).")

            masked_key = (
                validation.license_key[:4] + "-" + "*" * 8 + "-" + validation.license_key[-4:]
                if len(validation.license_key) >= 12
                else "****-****-****"
            )

            success_embed = discord.Embed(
                title="💎 PRO CLEARANCE AUTHENTICATED",
                description=(
                    f"Congratulations {member.mention}! Your purchase has been authenticated.\n"
                    f"You have been attributed the **{pro_role.mention}** role."
                ),
                color=config.COLOR_CRIMSON,
            )
            success_embed.add_field(name="📦 Software", value=f"`{validation.product_name}`", inline=True)
            success_embed.add_field(name="🎖️ Tier", value=f"`{validation.tier}`", inline=True)
            success_embed.add_field(name="🔑 Reference", value=f"`{masked_key}`", inline=True)

            pro_lounge = discord.utils.get(guild.text_channels, name="💎・pro-lounge")
            beta_builds = discord.utils.get(guild.text_channels, name="🧪・beta-builds")
            dev_backlog = discord.utils.get(guild.text_channels, name="📋・dev-backlog")

            perks = []
            if pro_lounge:
                perks.append(f"• {pro_lounge.mention}: Private lounge for verified customers")
            if beta_builds:
                perks.append(f"• {beta_builds.mention}: Pre-release `.jsx` and `.zxp` extension builds")
            if dev_backlog:
                perks.append(f"• {dev_backlog.mention}: Direct feature voting and engineering roadmap")

            if perks:
                success_embed.add_field(name="🔓 Unlocked Sectors", value="\n".join(perks), inline=False)

            success_embed.set_thumbnail(url=member.display_avatar.url)
            success_embed.set_footer(
                text="Sumair Tools Ecosystem • https://sumairtools.online",
                icon_url=guild.icon.url if guild.icon else None,
            )

            await interaction.followup.send(embed=success_embed, ephemeral=True)

        except discord.Forbidden:
            logger.error(f"Cannot assign {pro_role.name} to {member.name}: Hierarchy error.")
            await interaction.followup.send(
                "❌ **Hierarchy Error**: The bot's role must be positioned above `💎 Pro License` in **Server Settings > Roles**.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            logger.error(f"HTTP error during role assignment: {e}")
            await interaction.followup.send("❌ Discord API error while assigning your role.", ephemeral=True)

    @app_commands.command(
        name="license-stats",
        description="View license database telemetry & activation counts (Staff Only).",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def license_stats_cmd(self, interaction: discord.Interaction):
        """Displays database counts for active, unactivated, and revoked keys."""
        stats = self.license_service.get_stats()
        embed = discord.Embed(
            title="📊 LICENSE DATABASE TELEMETRY",
            description="Real-time status of official Sumair Tools serial keys stored in the bot:",
            color=config.COLOR_CRIMSON,
        )
        embed.add_field(name="📦 Total Keys", value=f"`{stats['total']}`", inline=True)
        embed.add_field(name="⏳ Available (Unclaimed)", value=f"`{stats['unactivated']}`", inline=True)
        embed.add_field(name="💎 Redeemed (Active)", value=f"`{stats['active']}`", inline=True)
        embed.add_field(name="🚫 Revoked / Inactive", value=f"`{stats['revoked']}`", inline=True)
        embed.set_footer(text="Sumair Tools Fortress Core • Native SQLite Storage")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="license-lookup",
        description="Inspect details of a specific license key (Staff Only).",
    )
    @app_commands.describe(license_key="The exact license key to look up")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def license_lookup_cmd(self, interaction: discord.Interaction, license_key: str):
        """Looks up a specific license key in the database."""
        data = self.license_service.lookup_license(license_key)
        if not data:
            await interaction.response.send_message("❌ License key not found in the database.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔍 LICENSE AUDIT REPORT",
            color=config.COLOR_CRIMSON,
        )
        embed.add_field(name="🔑 License Key", value=f"`{data['license_key']}`", inline=False)
        embed.add_field(name="Status", value=f"`{data['status'].upper()}`", inline=True)
        embed.add_field(name="Active", value=f"`{bool(data['active'])}`", inline=True)

        claimed_id = data.get("claimed_user_id")
        user_val = f"<@{claimed_id}> (`{claimed_id}`)" if claimed_id else "`Unclaimed`"
        embed.add_field(name="Claimed User", value=user_val, inline=True)

        created = data.get("created_at") or "Unknown"
        activated = data.get("activated_at") or "Not yet activated"
        embed.add_field(name="Created At", value=f"`{created}`", inline=True)
        embed.add_field(name="Activated At", value=f"`{activated}`", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="license-revoke",
        description="Revoke an existing license key (Staff Only).",
    )
    @app_commands.describe(license_key="The exact license key to revoke")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def license_revoke_cmd(self, interaction: discord.Interaction, license_key: str):
        """Marks a license as revoked."""
        success = self.license_service.revoke_license(license_key)
        if success:
            await interaction.response.send_message(f"🚫 License key `{license_key}` has been marked as **REVOKED**.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ License key not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LicensingCog(bot))
