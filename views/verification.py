"""
Sumair Tools Core - Verification UI View
========================================
Persistent verification button component allowing unauthenticated members
to accept rules, receive the '🎨 Verified Editor' role, and drop '⏳ Unverified'.
"""

import logging
import discord
from discord import ui
import config

logger = logging.getLogger("SumairTools.Verification")

class VerificationView(ui.View):
    """
    Persistent View containing the [ ✅ Accept Rules & Enter ] button.
    timeout=None ensures this view remains active across bot restarts.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Accept Rules & Enter",
        style=discord.ButtonStyle.danger,  # Crimson Industrial Red
        emoji="✅",
        custom_id=config.VERIFY_BUTTON_ID,
    )
    async def verify_button_callback(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "❌ Verification must be completed within the Sumair Tools server.",
                ephemeral=True,
            )
            return

        member: discord.Member = interaction.user

        verified_role = discord.utils.get(guild.roles, name=config.ROLE_VERIFIED)
        unverified_role = discord.utils.get(guild.roles, name=config.ROLE_UNVERIFIED)

        if not verified_role:
            logger.error(f"Role '{config.ROLE_VERIFIED}' was not found in guild '{guild.name}'.")
            await interaction.response.send_message(
                "⚠️ **Configuration Error**: `Verified Editor` role missing. Please notify an administrator.",
                ephemeral=True,
            )
            return

        # Check if already authenticated
        if verified_role in member.roles:
            embed = discord.Embed(
                title="✨ ALREADY AUTHENTICATED",
                description=(
                    f"Welcome back, {member.mention}.\n\n"
                    "Your clearance is already active as a **Verified Editor**.\n"
                    "Access the community discussions in <#general-lounge> or test scripts in <#bot-sandbox>."
                ),
                color=config.COLOR_CRIMSON,
            )
            embed.set_footer(text="Sumair Tools Core • Security Clearance Level 1")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            # Grant verified role, strip unverified role
            roles_to_add = [verified_role]
            roles_to_remove = [unverified_role] if unverified_role and unverified_role in member.roles else []

            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="User authenticated via rules checkpoint")

            await member.add_roles(*roles_to_add, reason="User authenticated via rules checkpoint")

            logger.info(f"Verified user {member.name} ({member.id}) in guild '{guild.name}'.")

            embed = discord.Embed(
                title="🔓 CLEARANCE GRANTED // SECTOR UNLOCKED",
                description=(
                    f"Welcome to **Sumair Tools**, {member.mention}.\n\n"
                    "Your identity has been authenticated. You have been assigned the **🎨 Verified Editor** role.\n\n"
                    "**Next Directives:**\n"
                    "• 💬 Join discussions in `#general-lounge`\n"
                    "• 🎞️ Motion breakdowns in `#after-effects-motion`\n"
                    "• 💎 Own a license? Run `/activate <your-license-key>` in any channel\n"
                    "• 🎫 Need developer support? Head to `#create-ticket`\n"
                ),
                color=config.COLOR_CRIMSON,
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(
                text="Sumair Tools Ecosystem • Creative Automation Redefined",
                icon_url=guild.icon.url if guild.icon else None,
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            logger.error(f"Missing permissions to assign roles to {member.name} ({member.id}). Check role hierarchy.")
            await interaction.response.send_message(
                "❌ **Hierarchy Error**: The bot's role must be dragged above `Verified Editor` in "
                "**Server Settings > Roles**.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            logger.error(f"HTTP error during verification of {member.name}: {e}")
            await interaction.response.send_message(
                "❌ An unexpected Discord API error occurred. Please try again.",
                ephemeral=True,
            )
