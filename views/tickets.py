"""
Sumair Tools Core - Support Ticket UI Views
===========================================
Persistent views handling ticket creation (TicketLauncher),
channel provisioning, transcript archiving, and closure (TicketCloseView).
"""

import io
import asyncio
import logging
from datetime import datetime
import discord
from discord import ui
import config

logger = logging.getLogger("SumairTools.Tickets")

class TicketCloseConfirmView(ui.View):
    """Safety confirmation before archiving and purging ticket channel."""

    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id

    @ui.button(label="Confirm Close & Archive", style=discord.ButtonStyle.danger, emoji="🔒")
    async def confirm_close(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Cannot perform action outside text channels.", ephemeral=True)
            return

        # Check permissions: ticket opener or staff
        user_roles = [r.name for r in interaction.user.roles] if isinstance(interaction.user, discord.Member) else []
        is_staff = any(r in user_roles for r in [config.ROLE_FOUNDER, config.ROLE_ADMIN, config.ROLE_SUPPORT_LEAD])
        is_owner = str(interaction.user.id) in (channel.topic or "")

        if not (is_staff or is_owner or interaction.user.guild_permissions.administrator):
            await interaction.response.send_message(
                "❌ Unauthorized: Only the ticket author or support staff can close this ticket.",
                ephemeral=True,
            )
            return

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        closing_embed = discord.Embed(
            title="🔒 TICKET ARCHIVING INITIATED",
            description=(
                f"Archived by {interaction.user.mention}.\n"
                "Compiling security transcript. Channel will self-destruct in **5 seconds**."
            ),
            color=config.COLOR_CRIMSON,
        )
        await channel.send(embed=closing_embed)

        # Generate Transcript
        transcript_text = f"=== SUMAIR TOOLS SUPPORT AUDIT TRANSCRIPT ===\n"
        transcript_text += f"Channel: #{channel.name} (ID: {channel.id})\n"
        transcript_text += f"Archived By: {interaction.user.name} ({interaction.user.id})\n"
        transcript_text += f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        transcript_text += f"{'='*50}\n\n"

        async for message in channel.history(limit=500, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator != "0" else message.author.name
            transcript_text += f"[{timestamp}] {author}: {message.content}\n"
            for attachment in message.attachments:
                transcript_text += f"    [Attachment: {attachment.filename} ({attachment.url})]\n"

        # Attempt to DM transcript to ticket creator
        try:
            creator_id = None
            if channel.topic and "UserID:" in channel.topic:
                for part in channel.topic.split("|"):
                    if "UserID:" in part:
                        creator_id = int(part.replace("UserID:", "").strip())
                        break
            if creator_id:
                creator = interaction.guild.get_member(creator_id)
                if creator:
                    file_data = io.BytesIO(transcript_text.encode("utf-8"))
                    discord_file = discord.File(file_data, filename=f"transcript-{channel.name}.txt")
                    dm_embed = discord.Embed(
                        title="📜 SUPPORT TRANSCRIPT ARCHIVED",
                        description=(
                            f"Your ticket `#{channel.name}` in **Sumair Tools** has been resolved and closed.\n"
                            "Your audit transcript is attached below for your records."
                        ),
                        color=config.COLOR_CRIMSON,
                    )
                    dm_embed.set_footer(text="Sumair Tools Ecosystem • https://sumairtools.online")
                    await creator.send(embed=dm_embed, file=discord_file)
        except Exception as dm_err:
            logger.warning(f"Could not send DM transcript: {dm_err}")

        await asyncio.sleep(5)
        try:
            await channel.delete(reason=f"Ticket closed by {interaction.user.name}")
        except discord.HTTPException as e:
            logger.error(f"Failed to delete channel #{channel.name}: {e}")

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="✖️")
    async def cancel_close(self, interaction: discord.Interaction, button: ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Ticket closure cancelled.", embed=None, view=None)


class TicketCloseView(ui.View):
    """
    Persistent control view inside each ticket channel with [ 🔒 Close & Archive ]
    and [ 📜 Transcript ] buttons.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Close & Archive",
        style=discord.ButtonStyle.danger,
        emoji="🔒",
        custom_id=config.TICKET_CLOSE_BUTTON_ID,
    )
    async def close_ticket_callback(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Action invalid outside text channels.", ephemeral=True)
            return

        confirm_view = TicketCloseConfirmView(author_id=interaction.user.id)
        await interaction.response.send_message(
            "⚠️ **Confirm Ticket Closure**: Do you want to generate a transcript and close this channel?",
            view=confirm_view,
            ephemeral=True,
        )

    @ui.button(
        label="Transcript",
        style=discord.ButtonStyle.secondary,
        emoji="📜",
        custom_id=config.TICKET_TRANSCRIPT_BUTTON_ID,
    )
    async def transcript_ticket_callback(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Action invalid outside text channels.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript_text = f"=== SUMAIR TOOLS SUPPORT AUDIT TRANSCRIPT ===\n"
        transcript_text += f"Channel: #{channel.name} (ID: {channel.id})\n"
        transcript_text += f"Generated By: {interaction.user.name} ({interaction.user.id})\n"
        transcript_text += f"Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        transcript_text += f"{'='*50}\n\n"

        async for message in channel.history(limit=500, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            author = f"{message.author.name}#{message.author.discriminator}" if message.author.discriminator != "0" else message.author.name
            transcript_text += f"[{timestamp}] {author}: {message.content}\n"
            for attachment in message.attachments:
                transcript_text += f"    [Attachment: {attachment.filename} ({attachment.url})]\n"

        file_data = io.BytesIO(transcript_text.encode("utf-8"))
        discord_file = discord.File(file_data, filename=f"transcript-{channel.name}.txt")

        await interaction.followup.send(
            content="📄 **Compiled Support Transcript:**",
            file=discord_file,
            ephemeral=True,
        )


class TicketLauncher(ui.View):
    """
    Persistent View stationed in 🎫・create-ticket.
    Spawns private channels named ticket-{username} visible only to opener, Support Lead, and Founder.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(
        label="Open Support Ticket",
        style=discord.ButtonStyle.danger,  # Crimson Red
        emoji="🎫",
        custom_id=config.TICKET_LAUNCH_BUTTON_ID,
    )
    async def open_ticket_button(
        self, interaction: discord.Interaction, button: ui.Button
    ):
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Command must be executed in-server.", ephemeral=True)
            return

        member: discord.Member = interaction.user

        # Anti-Spam: Check if ticket already exists
        user_id_tag = f"UserID: {member.id}"
        for existing_ch in guild.text_channels:
            if existing_ch.topic and user_id_tag in existing_ch.topic:
                await interaction.response.send_message(
                    f"⚠️ You already have an active ticket open in {existing_ch.mention}.\n"
                    "Please resolve that inquiry before opening another ticket.",
                    ephemeral=True,
                )
                return

        await interaction.response.defer(ephemeral=True)

        # Locate ticket category
        target_category = None
        for cat in guild.categories:
            if "SUPPORT" in cat.name.upper() or "HELP" in cat.name.upper():
                target_category = cat
                break

        # Roles for overwrites: opener, Support Lead, Founder
        founder_role = discord.utils.get(guild.roles, name=config.ROLE_FOUNDER)
        support_lead_role = discord.utils.get(guild.roles, name=config.ROLE_SUPPORT_LEAD)

        # Overwrite: Visible ONLY to opener, Support Lead, Founder, and Bot
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True,
            ),
        }

        if support_lead_role:
            overwrites[support_lead_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True,
            )
        if founder_role:
            overwrites[founder_role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                attach_files=True,
                embed_links=True,
            )

        # Format: ticket-{username}
        safe_username = "".join(c for c in member.name.lower() if c.isalnum() or c in ("-", "_"))[:20]
        channel_name = f"ticket-{safe_username}"

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=target_category,
                overwrites=overwrites,
                topic=f"Owner: {member.name} | UserID: {member.id} | Sumair Tools Support Desk",
                reason=f"Support ticket opened by {member.name} ({member.id})",
            )

            welcome_embed = discord.Embed(
                title="🛠️ SUMAIR TOOLS SUPPORT DESK",
                description=(
                    f"Welcome {member.mention}. A secure support channel has been provisioned.\n\n"
                    "Only **Support Lead**, **Founder**, and you have access to this sector.\n\n"
                    "```yaml\n"
                    "Tool / Script:   [e.g., SpeedJSX / Motion Engine]\n"
                    "Host Application: [e.g., After Effects 2024 / Premiere Pro 2024]\n"
                    "Operating System: [Windows 11 / macOS Sonoma]\n"
                    "License Key:     [If applicable]\n"
                    "Issue Overview:  [Provide full description + exact error logs]\n"
                    "```\n"
                    "📸 *Screenshots and reproduction videos significantly accelerate resolution.*"
                ),
                color=config.COLOR_CRIMSON,
            )
            welcome_embed.set_thumbnail(url=member.display_avatar.url)
            welcome_embed.set_footer(
                text="Sumair Tools Fortress Triage • Press [Close & Archive] when resolved",
                icon_url=guild.icon.url if guild.icon else None,
            )

            pings = [member.mention]
            if support_lead_role:
                pings.append(support_lead_role.mention)
            if founder_role:
                pings.append(founder_role.mention)

            await ticket_channel.send(
                content=" ".join(pings),
                embed=welcome_embed,
                view=TicketCloseView(),
            )

            await interaction.followup.send(
                f"✅ **Ticket Created:** {ticket_channel.mention}",
                ephemeral=True,
            )
            logger.info(f"Provisioned ticket channel #{ticket_channel.name} for {member.name} ({member.id}).")

        except discord.Forbidden:
            logger.error("Forbidden: Bot lacks permissions to create channel or apply overwrites.")
            await interaction.followup.send(
                "❌ **Bot Permission Error**: The bot lacks `Administrator` or `Manage Channels` permissions.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            logger.error(f"HTTP error creating ticket channel: {e}")
            await interaction.followup.send(
                f"❌ Failed to create support channel: `{e.text}`",
                ephemeral=True,
            )
