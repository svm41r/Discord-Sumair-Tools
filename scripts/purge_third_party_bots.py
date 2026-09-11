"""
Sumair Tools Core - Autonomous Third-Party Bot Purge Engine
===========================================================
Kicks all 29 legacy third-party bots from Guild 1461018926132498525
with rate-limit handling and audit logging, preserving only
Sumair Tools (ID: 1547976148435206164).
"""

import sys
import asyncio
import logging
import discord
import os
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1461018926132498525
SUMAIR_TOOLS_BOT_ID = 1547976148435206164

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("=" * 65)
    print(f"Logged in as: {client.user.name} ({client.user.id})")
    guild = client.get_guild(GUILD_ID)
    if not guild:
        print(f"ERROR: Guild {GUILD_ID} not found.")
        await client.close()
        return

    print(f"Target Guild: {guild.name} (Total Members: {guild.member_count})")
    bots_to_kick = [
        m for m in guild.members
        if m.bot and m.id != SUMAIR_TOOLS_BOT_ID
    ]

    print(f"Found {len(bots_to_kick)} third-party bots to purge.")
    print("=" * 65)

    kicked_count = 0
    failed_count = 0

    log_channel = discord.utils.get(guild.text_channels, name="📡・server-logs")

    for idx, b in enumerate(bots_to_kick, 1):
        print(f"[{idx}/{len(bots_to_kick)}] Kicking {b.name} (ID: {b.id})...", end=" ", flush=True)
        try:
            await guild.kick(
                b,
                reason="All functionality consolidated into native Sumair Tools Core suite"
            )
            print("✅ KICKED")
            kicked_count += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed_count += 1

        await asyncio.sleep(1.0)  # Gentle rate limit throttle

    print("=" * 65)
    print(f"Purge Complete! Successfully kicked: {kicked_count} | Failed: {failed_count}")

    if log_channel:
        embed = discord.Embed(
            title="🧹 THIRD-PARTY BOT PURGE COMPLETE",
            description=(
                f"**Total Purged**: `{kicked_count}` third-party bots\n"
                f"**Failed**: `{failed_count}`\n"
                f"**Sovereign System**: <@{SUMAIR_TOOLS_BOT_ID}> is now the sole active bot.\n\n"
                "All legacy moderation, music, tickets, quotes, temp voice, and invite tracking "
                "have been consolidated into the native **Sumair Tools Core**."
            ),
            color=0xFF0033,
        )
        embed.set_footer(text="Sumair Tools Fortress Core • Ecosystem Lockdown")
        try:
            await log_channel.send(embed=embed)
            print("Dispatched audit report embed to 📡・server-logs.")
        except Exception as e:
            print(f"Failed sending audit log: {e}")

    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
