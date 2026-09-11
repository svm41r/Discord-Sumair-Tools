"""
Sumair Tools Core - Authoritative Role Architecture & Migration Engine
======================================================================
1. Migrates all 25 human members to '🎨 Verified Editor'.
2. Assigns '👑 Founder / Sumair' to the Server Owner.
3. Provisions the 15-tier Dark Industrial motion design hierarchy.
4. Safely purges ~90 obsolete junk roles.
5. Reorders the role hierarchy top-to-bottom.
"""

import sys
import os
import asyncio
import discord
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = config.GUILD_ID or 1461018926132498525

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print("=" * 65)
    print(f"Logged in as: {client.user.name} (ID: {client.user.id})")
    guild = client.get_guild(GUILD_ID)
    if not guild:
        print(f"ERROR: Guild {GUILD_ID} not found.")
        await client.close()
        return

    print(f"Server: {guild.name} | Total Roles currently: {len(guild.roles)}")
    print("=" * 65)

    # ──────────────────────────────────────────────────────────
    # STEP 1: Provision / Update Authoritative Roles
    # ──────────────────────────────────────────────────────────
    print(">>> STEP 1: Provisioning / Syncing Authoritative Role Suite...")
    authoritative_roles_map = {}

    for r_def in config.ROLE_HIERARCHY:
        existing = discord.utils.get(guild.roles, name=r_def.name)
        perms = discord.Permissions.all() if r_def.is_admin else discord.Permissions.none()

        if existing:
            try:
                await existing.edit(
                    color=discord.Color(r_def.color),
                    hoist=r_def.hoist,
                    mentionable=r_def.mentionable,
                    permissions=perms if r_def.is_admin else existing.permissions,
                    reason="Syncing authoritative role properties",
                )
                authoritative_roles_map[r_def.name] = existing
                print(f"  [SYNCED] {existing.name}")
            except Exception as e:
                print(f"  [ERROR EDITING] {r_def.name}: {e}")
                authoritative_roles_map[r_def.name] = existing
        else:
            try:
                new_role = await guild.create_role(
                    name=r_def.name,
                    color=discord.Color(r_def.color),
                    hoist=r_def.hoist,
                    mentionable=r_def.mentionable,
                    permissions=perms,
                    reason="Creating authoritative role",
                )
                authoritative_roles_map[r_def.name] = new_role
                print(f"  [CREATED] {new_role.name}")
                await asyncio.sleep(0.4)
            except Exception as e:
                print(f"  [ERROR CREATING] {r_def.name}: {e}")

    # ──────────────────────────────────────────────────────────
    # STEP 2: Member Migration & Founder Attribution
    # ──────────────────────────────────────────────────────────
    print("\n>>> STEP 2: Migrating Members & Attributing Founder...")
    verified_role = authoritative_roles_map.get(config.ROLE_VERIFIED)
    founder_role = authoritative_roles_map.get(config.ROLE_FOUNDER)

    # Migrate all humans to Verified Editor
    migrated_count = 0
    if verified_role:
        for m in guild.members:
            if not m.bot and verified_role not in m.roles:
                try:
                    await m.add_roles(verified_role, reason="Auto-migrated to Verified Editor")
                    migrated_count += 1
                except Exception as e:
                    print(f"  [MIGRATION ERROR] {m.name}: {e}")
        print(f"  Successfully ensured {migrated_count} human member(s) hold '{config.ROLE_VERIFIED}'.")

    # Grant Founder role to guild owner
    if founder_role and guild.owner:
        if founder_role not in guild.owner.roles:
            try:
                await guild.owner.add_roles(founder_role, reason="Attributed Founder role to server owner")
                print(f"  Attributed '{config.ROLE_FOUNDER}' to Server Owner ({guild.owner.name}).")
            except Exception as e:
                print(f"  [FOUNDER ATTRIBUTION ERROR]: {e}")
        else:
            print(f"  Server Owner ({guild.owner.name}) already holds '{config.ROLE_FOUNDER}'.")

    # ──────────────────────────────────────────────────────────
    # STEP 3: Purging Obsolete / Junk Roles
    # ──────────────────────────────────────────────────────────
    print("\n>>> STEP 3: Purging Obsolete Roles...")
    authoritative_names = set(r_def.name for r_def in config.ROLE_HIERARCHY)
    authoritative_names.add("Botsetup")  # Bot's operational role

    deleted_count = 0
    failed_count = 0

    # Fetch fresh roles
    for r in list(guild.roles):
        if r.name == "@everyone":
            continue
        if r.managed:  # Discord managed (e.g. Sumair Tools, Server Booster)
            continue
        if r.name in authoritative_names:
            continue

        print(f"  Deleting junk role: '{r.name}' (ID: {r.id})...", end=" ", flush=True)
        try:
            await r.delete(reason="Purged obsolete legacy role")
            print("✅ DELETED")
            deleted_count += 1
            await asyncio.sleep(0.4)
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed_count += 1

    print(f"\nRole Purge Summary: {deleted_count} deleted | {failed_count} failed")

    # ──────────────────────────────────────────────────────────
    # STEP 4: Synchronizing Exact Hierarchy Order
    # ──────────────────────────────────────────────────────────
    print("\n>>> STEP 4: Establishing Hierarchy Positions...")
    # Refresh roles
    bot_top_role = guild.me.top_role
    print(f"Bot top role: {bot_top_role.name} at position {bot_top_role.position}")

    # Build position map below bot's top role
    # Order: ROLE_HIERARCHY from index 0 down to bottom
    roles_in_order = []
    for r_def in config.ROLE_HIERARCHY:
        r_obj = discord.utils.get(guild.roles, name=r_def.name)
        if r_obj and r_obj < bot_top_role:
            roles_in_order.append(r_obj)

    # Assign positions: reverse so index 0 gets highest number
    positions_payload = {}
    base_pos = 1
    for r_obj in reversed(roles_in_order):
        positions_payload[r_obj] = base_pos
        base_pos += 1

    if positions_payload:
        try:
            await guild.edit_role_positions(positions_payload)
            print("  Successfully synchronized role hierarchy positions!")
        except Exception as e:
            print(f"  Note on positioning: {e}")

    # ──────────────────────────────────────────────────────────
    # STEP 5: Dispatch Audit Log
    # ──────────────────────────────────────────────────────────
    log_channel = discord.utils.get(guild.text_channels, name="📡・server-logs")
    if log_channel:
        embed = discord.Embed(
            title="🛡️ SERVER ROLE ARCHITECTURE RESTRUCTURING COMPLETE",
            description=(
                f"**Junk Roles Purged**: `{deleted_count}` obsolete roles\n"
                f"**Active Hierarchy**: `{len(config.ROLE_HIERARCHY)}` authoritative roles\n"
                f"**Members Migrated**: `{migrated_count}` members secured with **`{config.ROLE_VERIFIED}`**\n"
                f"**Server Owner**: Attributed **`{config.ROLE_FOUNDER}`**\n\n"
                "All legacy junk, pronoun, gaming, and city roles have been wiped. "
                "The server now operates on the official Dark Industrial motion design hierarchy."
            ),
            color=config.COLOR_CRIMSON,
        )
        embed.set_footer(text="Sumair Tools Core • Role Governance Engine")
        try:
            await log_channel.send(embed=embed)
            print("Dispatched audit log embed to 📡・server-logs.")
        except Exception as e:
            print(f"Error sending log embed: {e}")

    print("=" * 65)
    print("Role restructuring sequence successfully concluded.")
    await client.close()

if __name__ == "__main__":
    client.run(TOKEN)
