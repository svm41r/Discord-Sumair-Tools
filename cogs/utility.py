"""
Sumair Tools Core - Utility & Community Suite Cog
=================================================
Essential server diagnostic, information, role allocation, announcement,
interactive poll, and latency utility commands.
"""

import time
import logging
from typing import Optional
import discord
from discord import app_commands, ui
from discord.ext import commands
import config

logger = logging.getLogger("SumairTools.UtilityCog")

class InteractivePollView(ui.View):
    """Button-driven interactive poll with live vote tallies and duplicate prevention."""

    def __init__(self, question: str, options: list[str], author_id: int):
        super().__init__(timeout=None)
        self.question = question
        self.options = options
        self.author_id = author_id
        self.votes: dict[int, int] = {}  # user_id -> option_index

        for idx, opt in enumerate(options):
            btn = ui.Button(
                label=opt[:80],
                style=discord.ButtonStyle.secondary,
                custom_id=f"poll_btn_{idx}",
                emoji=f"{idx+1}\u20e3"
            )
            btn.callback = self._create_callback(idx)
            self.add_item(btn)

    def _create_callback(self, opt_idx: int):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            if self.votes.get(user_id) == opt_idx:
                del self.votes[user_id]
                await interaction.response.send_message("🗳️ Your vote was withdrawn.", ephemeral=True)
            else:
                self.votes[user_id] = opt_idx
                await interaction.response.send_message(f"🗳️ You voted for **{self.options[opt_idx]}**!", ephemeral=True)

            embed = self.build_embed()
            await interaction.message.edit(embed=embed)

        return callback

    def build_embed(self) -> discord.Embed:
        counts = [0] * len(self.options)
        for val in self.votes.values():
            if 0 <= val < len(counts):
                counts[val] += 1
        total_votes = len(self.votes)

        embed = discord.Embed(
            title=f"📊 COMMUNITY POLL // {self.question}",
            color=config.COLOR_CRIMSON,
            description="Click the buttons below to cast or toggle your vote:\n",
        )

        for i, opt in enumerate(self.options):
            cnt = counts[i]
            pct = (cnt / total_votes * 100) if total_votes > 0 else 0
            bar_len = int(pct / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            embed.add_field(
                name=f"{i+1}\u20e3 {opt}",
                value=f"`{bar}` **{cnt}** ({pct:.1f}%)",
                inline=False,
            )

        embed.set_footer(text=f"Total Votes: {total_votes} • Sumair Tools Community Polls")
        return embed


class UtilityCog(commands.Cog):
    """Community tools, server telemetry, and role utilities."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ─── SERVER INFO ──────────────────────────────────────────
    @app_commands.command(name="server-info", description="Display comprehensive server infrastructure telemetry.")
    @app_commands.guild_only()
    async def server_info_cmd(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild:
            return

        total_members = guild.member_count or 0
        bots = sum(1 for m in guild.members if m.bot)
        humans = total_members - bots

        text_chs = len(guild.text_channels)
        voice_chs = len(guild.voice_channels)
        stage_chs = len(guild.stage_channels)
        forum_chs = len(guild.forums) if hasattr(guild, "forums") else 0
        categories = len(guild.categories)

        created_str = guild.created_at.strftime("%Y-%m-%d %H:%M UTC")
        owner = guild.owner or await self.bot.fetch_user(guild.owner_id)

        embed = discord.Embed(
            title=f"🏢 SERVER TELEMETRY // {guild.name.upper()}",
            color=config.COLOR_CRIMSON,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Owner", value=f"{owner.mention}\n`{owner.name}`", inline=True)
        embed.add_field(name="🆔 Guild ID", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="📅 Commissioned", value=f"`{created_str}`", inline=True)

        embed.add_field(
            name="👥 Population",
            value=f"• Total: `{total_members}`\n• Humans: `{humans}`\n• Automation: `{bots}`",
            inline=True,
        )
        embed.add_field(
            name="📁 Sectors & Layout",
            value=f"• Categories: `{categories}`\n• Text: `{text_chs}` | Voice: `{voice_chs}`\n• Forums: `{forum_chs}` | Stage: `{stage_chs}`",
            inline=True,
        )
        embed.add_field(
            name="💎 Boost & Security",
            value=f"• Tier: `{guild.premium_tier}` ({guild.premium_subscription_count} Boosts)\n• Fortress Engine: `ACTIVE`\n• 2FA Required: `{bool(guild.mfa_level)}`",
            inline=True,
        )

        embed.set_footer(text="Sumair Tools Core Subsystem • Infrastructure Diagnostic")
        await interaction.response.send_message(embed=embed)

    # ─── USER INFO ────────────────────────────────────────────
    @app_commands.command(name="user-info", description="Inspect detailed profile and permission data for a user.")
    @app_commands.describe(member="Member to inspect (defaults to yourself)")
    @app_commands.guild_only()
    async def user_info_cmd(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        if not isinstance(target, discord.Member):
            target = await interaction.guild.fetch_member(target.id)

        created = target.created_at.strftime("%Y-%m-%d %H:%M UTC")
        joined = target.joined_at.strftime("%Y-%m-%d %H:%M UTC") if target.joined_at else "Unknown"

        roles = [r.mention for r in reversed(target.roles) if r.name != "@everyone"]
        roles_str = ", ".join(roles[:12]) if roles else "No roles"
        if len(roles) > 12:
            roles_str += f" *(+{len(roles) - 12} more)*"

        embed = discord.Embed(
            title=f"👤 IDENTITY DOSSIER // {target.name}",
            color=target.color if target.color.value != 0 else config.COLOR_CRIMSON,
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="Mention", value=target.mention, inline=True)
        embed.add_field(name="User ID", value=f"`{target.id}`", inline=True)
        embed.add_field(name="Bot Account", value="`Yes`" if target.bot else "`No`", inline=True)

        embed.add_field(name="Account Created", value=f"`{created}`", inline=True)
        embed.add_field(name="Joined Server", value=f"`{joined}`", inline=True)
        embed.add_field(name="Highest Role", value=target.top_role.mention, inline=True)

        embed.add_field(name=f"Assigned Roles ({len(roles)})", value=roles_str, inline=False)
        embed.set_footer(text="Sumair Tools Fortress Core • Profile Intelligence")
        await interaction.response.send_message(embed=embed)

    # ─── AVATAR ───────────────────────────────────────────────
    @app_commands.command(name="avatar", description="View and download a user's avatar in high resolution.")
    @app_commands.describe(member="Member to inspect")
    @app_commands.guild_only()
    async def avatar_cmd(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        target = member or interaction.user
        avatar = target.display_avatar

        embed = discord.Embed(
            title=f"🖼️ AVATAR // {target.name}",
            description=f"[Open High-Res]({avatar.url})",
            color=config.COLOR_CRIMSON,
        )
        embed.set_image(url=avatar.url)
        embed.set_footer(text="Sumair Tools Core")
        await interaction.response.send_message(embed=embed)

    # ─── ROLE MANAGEMENT ──────────────────────────────────────
    @app_commands.command(name="role-give", description="Assign a role to a member.")
    @app_commands.describe(member="Target member", role="Role to assign")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def role_give_cmd(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        mod = interaction.user
        bot_member = interaction.guild.me

        if role >= bot_member.top_role:
            await interaction.response.send_message("❌ Cannot assign this role: It is positioned higher than my role.", ephemeral=True)
            return
        if mod.id != interaction.guild.owner_id and role >= mod.top_role:
            await interaction.response.send_message("❌ Cannot assign this role: It is equal to or higher than your highest role.", ephemeral=True)
            return

        if role in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} already holds {role.mention}.", ephemeral=True)
            return

        await member.add_roles(role, reason=f"Assigned by [{mod.name}] via /role-give")
        await interaction.response.send_message(f"✅ Granted {role.mention} to {member.mention}.", ephemeral=True)

    @app_commands.command(name="role-remove", description="Remove a role from a member.")
    @app_commands.describe(member="Target member", role="Role to remove")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def role_remove_cmd(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        mod = interaction.user
        bot_member = interaction.guild.me

        if role >= bot_member.top_role:
            await interaction.response.send_message("❌ Cannot modify this role: It is positioned higher than my role.", ephemeral=True)
            return
        if mod.id != interaction.guild.owner_id and role >= mod.top_role:
            await interaction.response.send_message("❌ Cannot modify this role: It is equal to or higher than your highest role.", ephemeral=True)
            return

        if role not in member.roles:
            await interaction.response.send_message(f"⚠️ {member.mention} does not hold {role.mention}.", ephemeral=True)
            return

        await member.remove_roles(role, reason=f"Removed by [{mod.name}] via /role-remove")
        await interaction.response.send_message(f"✅ Stripped {role.mention} from {member.mention}.", ephemeral=True)

    # ─── ANNOUNCE ─────────────────────────────────────────────
    @app_commands.command(name="announce", description="Broadcast a styled announcement into a specific channel.")
    @app_commands.describe(
        channel="Destination channel",
        title="Announcement title",
        message="Full broadcast text",
        ping_role="Optional role to ping"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def announce_cmd(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        message: str,
        ping_role: Optional[discord.Role] = None
    ):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title=f"📢 {title.upper()}",
            description=message.replace("\\n", "\n"),
            color=config.COLOR_CRIMSON,
        )
        embed.set_author(name=interaction.guild.name, icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        embed.set_footer(text=f"Dispatched by {interaction.user.name} • Sumair Tools Ecosystem")

        content = ping_role.mention if ping_role else None
        await channel.send(content=content, embed=embed)
        await interaction.followup.send(f"✅ Announcement successfully dispatched to {channel.mention}!", ephemeral=True)

    # ─── INTERACTIVE POLL ─────────────────────────────────────
    @app_commands.command(name="poll", description="Create an interactive button poll with live tallies.")
    @app_commands.describe(
        question="Poll subject",
        option1="Option 1",
        option2="Option 2",
        option3="Optional Option 3",
        option4="Optional Option 4"
    )
    @app_commands.guild_only()
    async def poll_cmd(
        self,
        interaction: discord.Interaction,
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None
    ):
        options = [opt for opt in [option1, option2, option3, option4] if opt and opt.strip()]
        if len(options) < 2:
            await interaction.response.send_message("❌ A poll requires at least two options.", ephemeral=True)
            return

        view = InteractivePollView(question=question, options=options, author_id=interaction.user.id)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view)

    # ─── PING & LATENCY ───────────────────────────────────────
    @app_commands.command(name="ping", description="Check bot latency and gateway heartbeat.")
    async def ping_cmd(self, interaction: discord.Interaction):
        t0 = time.perf_counter()
        await interaction.response.send_message("📡 Contacting Gateway Subsystem...", ephemeral=True)
        t1 = time.perf_counter()

        rest_latency = round((t1 - t0) * 1000)
        ws_latency = round(self.bot.latency * 1000)

        embed = discord.Embed(
            title="⚡ TELEMETRY DIAGNOSTICS",
            color=config.COLOR_CRIMSON,
        )
        embed.add_field(name="🌐 Gateway WebSocket", value=f"`{ws_latency} ms`", inline=True)
        embed.add_field(name="🔄 REST API Roundtrip", value=f"`{rest_latency} ms`", inline=True)
        embed.set_footer(text="Sumair Tools Fortress Core • Network Health")
        await interaction.edit_original_response(content=None, embed=embed)

    # ─── QUOTE GENERATOR (Replaces 'Make it a Quote') ─────────
    @app_commands.command(name="quote", description="Generate a quote card from a message ID or text.")
    @app_commands.describe(
        message_id="Numeric ID of the message to quote",
        channel="Channel where message was posted (defaults to current)"
    )
    @app_commands.guild_only()
    async def quote_cmd(
        self,
        interaction: discord.Interaction,
        message_id: str,
        channel: Optional[discord.TextChannel] = None
    ):
        target_ch = channel or interaction.channel
        try:
            mid = int(message_id.strip())
            msg = await target_ch.fetch_message(mid)
        except ValueError:
            await interaction.response.send_message("❌ Message ID must be a numeric integer.", ephemeral=True)
            return
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found in the designated channel.", ephemeral=True)
            return
        except Exception as e:
            await interaction.response.send_message(f"❌ Error fetching message: {e}", ephemeral=True)
            return

        embed = discord.Embed(
            description=f"“{msg.content}”" if msg.content else "*[No text content / Media only]*",
            color=msg.author.color if msg.author.color.value != 0 else config.COLOR_CRIMSON,
            timestamp=msg.created_at,
        )
        embed.set_author(name=msg.author.display_name, icon_url=msg.author.display_avatar.url)
        if msg.attachments:
            embed.set_image(url=msg.attachments[0].url)
        embed.set_footer(text=f"Quoted by {interaction.user.display_name} • Jump to message: {msg.jump_url}")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
