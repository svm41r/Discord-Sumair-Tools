"""
Sumair Tools Core - Documentation Dispatcher & Tutorial Publisher Cog
=====================================================================
Automates ingestion and multi-embed broadcasting of the official
Sumair Tools v6.5 Master Tutorial directly into #documentation or
#tutorials-documentation.
Supports direct file attachment uploads or defaults to the v6.5 manual.
"""

import os
import re
import asyncio
import logging
from typing import Optional, List
import discord
from discord import app_commands
from discord.ext import commands
import config

logger = logging.getLogger("SumairTools.DocsCog")

# Paths to tutorial sources
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TUTORIAL_65_PATH = os.path.join(BASE_DIR, "SUMAIR_TOOLS_6.5_DISCORD_TUTORIAL.txt")
DOCS_DEFAULT_PATH = os.path.join(BASE_DIR, "data", "docs", "svm41r_master_tutorials.md")


def chunk_text(title: str, text: str, max_len: int = 3800) -> List[discord.Embed]:
    """Chunks text into Discord embeds ensuring neither title nor description overflows."""
    embeds = []
    lines = text.strip().split("\n")
    current_chunk = []
    current_len = 0
    part = 1

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_len:
            desc = "\n".join(current_chunk)
            embed_title = title if part == 1 else f"{title} (Part {part})"
            embed = discord.Embed(
                title=embed_title[:256],
                description=desc,
                color=config.COLOR_CRIMSON,
            )
            embed.set_footer(text="Sumair Tools v6.5 Official Manual • https://sumairtools.online/")
            embeds.append(embed)
            part += 1
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        desc = "\n".join(current_chunk)
        embed_title = title if part == 1 else f"{title} (Part {part})"
        embed = discord.Embed(
            title=embed_title[:256],
            description=desc,
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text="Sumair Tools v6.5 Official Manual • https://sumairtools.online/")
        embeds.append(embed)

    return embeds


class DocsCog(commands.Cog):
    """Documentation publishing and tutorials broadcaster."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _parse_tutorial_text(self, text: str) -> List[discord.Embed]:
        """Parses ASCII box divided files like SUMAIR_TOOLS_6.5_DISCORD_TUTORIAL.txt."""
        embeds: List[discord.Embed] = []
        pattern = re.compile(r"={30,}\s*\n\s*(.*?)\s*\n={30,}\s*\n(.*?)(?=(?:={30,}|$))", re.DOTALL)
        matches = pattern.findall(text)

        if not matches:
            # Fallback if text doesn't use === boxes: try standard markdown (# or ##)
            return self._parse_markdown_document(text)

        for i, (title, raw_body) in enumerate(matches):
            clean_title = title.strip()
            body = raw_body.strip()
            if not body:
                continue

            # Strip large ASCII lines and convert [Headers] to bold markdown subheads
            body = re.sub(r"-{20,}", "", body)
            body = re.sub(r"(?m)^\[(.*?)\]", r"### 🔹 \1", body)

            # Highlight table of contents nicely if this is the header embed
            if "TABLE OF CONTENTS" in body:
                body = body.replace("TABLE OF CONTENTS:", "**📑 TABLE OF CONTENTS:**\n")

            sub_embeds = chunk_text(clean_title, body)
            embeds.extend(sub_embeds)

        return embeds

    def _parse_markdown_document(self, text: str) -> List[discord.Embed]:
        """Parses standard markdown document with ## headers."""
        embeds: List[discord.Embed] = []
        sections = re.split(r"(?m)^(?=##\s+)", text)

        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue

            header_match = re.match(r"^#\s+(.+?)(?:\r?\n|$)", sec)
            if header_match:
                doc_title = header_match.group(1).strip()
                body = sec[header_match.end():].strip()
                if body.startswith("---"):
                    body = body[3:].strip()

                embed = discord.Embed(
                    title=f"📚 {doc_title}"[:256],
                    description=body[:3900],
                    color=config.COLOR_CRIMSON,
                )
                embed.set_footer(text="Sumair Tools Master Knowledge Base • https://sumairtools.online/")
                embeds.append(embed)
                continue

            sub_match = re.match(r"^##\s+(.+?)(?:\r?\n|$)", sec)
            if sub_match:
                section_title = sub_match.group(1).strip()
                section_body = sec[sub_match.end():].strip()
                if section_body.startswith("---"):
                    section_body = section_body[3:].strip()
                embeds.extend(chunk_text(section_title, section_body))
            else:
                embeds.extend(chunk_text("Technical Overview", sec))

        return embeds

    def _resolve_target_channel(self, guild: discord.Guild, channel: Optional[discord.TextChannel]) -> Optional[discord.TextChannel]:
        """Finds the most appropriate documentation channel in the server."""
        if channel:
            return channel

        # Priority search order
        candidates = [
            "📚・documentation",
            "documentation",
            "📚・tutorials-documentation",
            "tutorials-documentation",
            "tutorials",
            "docs",
        ]
        for name in candidates:
            ch = discord.utils.get(guild.text_channels, name=name)
            if ch:
                return ch

        # Fuzzy match
        for ch in guild.text_channels:
            if "doc" in ch.name.lower() or "tut" in ch.name.lower():
                return ch

        return None

    @app_commands.command(
        name="post-tutorials",
        description="Deploy the official Sumair Tools v6.5 Master Tutorial into #documentation.",
    )
    @app_commands.describe(
        file="Optional custom tutorial file (.txt or .md) to publish instead of v6.5 default",
        channel="Destination channel (defaults to #documentation)",
        clear_first="Wipe previous tutorial messages before posting (default: True)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def post_tutorials_cmd(
        self,
        interaction: discord.Interaction,
        file: Optional[discord.Attachment] = None,
        channel: Optional[discord.TextChannel] = None,
        clear_first: Optional[bool] = True,
    ):
        """Broadcasts Sumair Tools tutorials into the documentation channel."""
        guild = interaction.guild
        if not guild:
            return

        target_channel = self._resolve_target_channel(guild, channel) or interaction.channel
        await interaction.response.defer(ephemeral=True)

        doc_content = ""
        source_name = "SUMAIR_TOOLS_6.5_DISCORD_TUTORIAL.txt"

        if file:
            if not (file.filename.endswith(".txt") or file.filename.endswith(".md")):
                await interaction.followup.send("❌ Attached file must be a `.txt` or `.md` file.", ephemeral=True)
                return
            try:
                raw_bytes = await file.read()
                doc_content = raw_bytes.decode("utf-8", errors="replace")
                source_name = file.filename
            except Exception as e:
                await interaction.followup.send(f"❌ Failed reading uploaded file: {e}", ephemeral=True)
                return
        else:
            # Check for local v6.5 tutorial file
            if os.path.exists(TUTORIAL_65_PATH):
                with open(TUTORIAL_65_PATH, "r", encoding="utf-8") as f:
                    doc_content = f.read()
            elif os.path.exists(DOCS_DEFAULT_PATH):
                with open(DOCS_DEFAULT_PATH, "r", encoding="utf-8") as f:
                    doc_content = f.read()
                source_name = "svm41r_master_tutorials.md"
            else:
                await interaction.followup.send(f"❌ No tutorial file found on disk.", ephemeral=True)
                return

        # Parse file into embeds
        embeds = self._parse_tutorial_text(doc_content)
        if not embeds:
            await interaction.followup.send("❌ Could not parse any sections from the tutorial file.", ephemeral=True)
            return

        # Optional wipe
        if clear_first and target_channel.permissions_for(guild.me).manage_messages:
            try:
                await target_channel.purge(limit=100)
                await asyncio.sleep(1)
            except Exception as e:
                logger.warning(f"Could not purge channel {target_channel.name}: {e}")

        # Send intro header banner
        banner = discord.Embed(
            title="🛡️ SUMAIR TOOLS ARCHITECTURE // OFFICIAL MASTER KNOWLEDGEBASE",
            description=(
                f"**Release Build**: `v6.5 (Zero-Config Groq Cloud AI)`\n"
                f"**Engineered by**: `Sumair Ali Siddiqui`\n"
                f"**Official Portal**: [https://sumairtools.online/](https://sumairtools.online/)\n"
                f"**Total Modules**: `{len(embeds)} Documentation Sections`\n\n"
                "Review the breakdown below for complete installation steps, Groq AI automation, "
                "Hormozi subtitle workflows, Auto Cut parameters, and After Effects keyboard shortcuts."
            ),
            color=config.COLOR_CRIMSON,
        )
        banner.set_image(url="https://sumairtools.online/images/logo_icon.png") if hasattr(config, "LOGO_URL") else None
        banner.set_footer(text="Sumair Tools Ecosystem • Fortress Documentation System")
        await target_channel.send(embed=banner)
        await asyncio.sleep(0.8)

        # Broadcast each section with rate limit prevention
        sent_count = 0
        for emb in embeds:
            await target_channel.send(embed=emb)
            sent_count += 1
            await asyncio.sleep(0.8)

        await interaction.followup.send(
            f"✅ **Tutorials Published!** Dispatched **{sent_count}** formatted embeds into {target_channel.mention} from `{source_name}`.",
            ephemeral=True,
        )

    @app_commands.command(
        name="post-docs",
        description="Alias for /post-tutorials (Deploys v6.5 manual into #documentation).",
    )
    @app_commands.describe(
        file="Optional custom tutorial file (.txt or .md)",
        channel="Destination channel",
        clear_first="Wipe previous messages before posting (default: True)"
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def post_docs_cmd(
        self,
        interaction: discord.Interaction,
        file: Optional[discord.Attachment] = None,
        channel: Optional[discord.TextChannel] = None,
        clear_first: Optional[bool] = True,
    ):
        """Direct alias forwarding to post_tutorials_cmd."""
        await self.post_tutorials_cmd(interaction, file=file, channel=channel, clear_first=clear_first)

    @app_commands.command(
        name="clear-docs",
        description="Purge messages in the documentation channel before re-publishing (Admin Only).",
    )
    @app_commands.describe(channel="Documentation channel to clear (defaults to #documentation)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def clear_docs_cmd(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        target = self._resolve_target_channel(interaction.guild, channel) or interaction.channel
        await interaction.response.defer(ephemeral=True)

        try:
            deleted = await target.purge(limit=100)
            await interaction.followup.send(f"🧹 Cleared **{len(deleted)}** message(s) from {target.mention}.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error clearing channel: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DocsCog(bot))
