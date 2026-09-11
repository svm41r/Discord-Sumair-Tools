"""
Sumair Tools Core - Fortress Architecture & Configuration
=========================================================
Authoritative 8-tier role matrix, 10-category industrial layout,
Crimson aesthetic constants (0xFF0033 / 0x990000), security thresholds,
and persistent lock definitions for https://sumairtools.online.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

# --- Discord & Environment Config ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
GUILD_ID = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") and os.getenv("GUILD_ID").isdigit() else None
LICENSE_API_KEY = os.getenv("LICENSE_API_KEY", "")
LICENSE_API_URL = os.getenv("LICENSE_API_URL", "https://sumairtools.online/api/v1/licenses/verify")
ENABLE_MOCK_LICENSES = os.getenv("ENABLE_MOCK_LICENSES", "true").lower() in ("true", "1", "yes")

# --- Persistent Setup Lockfile ---
SETUP_LOCK_FILE = os.path.join(os.path.dirname(__file__), ".setup_lock")

# --- Brand & Ecosystem URLs ---
SUMAIR_WEBSITE_URL = "https://sumairtools.online"
SUMAIR_DOCS_URL = "https://sumairtools.online/docs"
SUMAIR_STORE_GUMROAD = "https://sumairtools.gumroad.com"
SUMAIR_STORE_LEMON = "https://sumairtools.lemonsqueezy.com"

# --- Persistent Custom IDs ---
VERIFY_BUTTON_ID = "sumair_fortress:btn_verify_v2"
TICKET_LAUNCH_BUTTON_ID = "sumair_fortress:btn_ticket_launch_v2"
TICKET_CLOSE_BUTTON_ID = "sumair_fortress:btn_ticket_close_v2"
TICKET_TRANSCRIPT_BUTTON_ID = "sumair_fortress:btn_ticket_transcript_v2"

# --- Crimson Industrial Aesthetic Colors ---
COLOR_FOUNDER = 0xFF0033       # #FF0033 Vivid Crimson
COLOR_ADMIN = 0xB30000         # #B30000 Deep Crimson Overseer
COLOR_SUPPORT_LEAD = 0x800000  # #800000 Maroon Support
COLOR_PRO_LICENSE = 0xFF4D4D   # #FF4D4D Bright Red Pro
COLOR_VIP = 0xE63946           # #E63946 Electric Red
COLOR_BETA = 0x990000          # #990000 Dark Crimson
COLOR_VERIFIED = 0xCCCCCC      # #CCCCCC Industrial Silver
COLOR_UNVERIFIED = 0x555555    # #555555 Matte Gunmetal

COLOR_CRIMSON = 0xFF0033
COLOR_DARK_CRIMSON = 0x990000
COLOR_SUCCESS = 0x00FF66
COLOR_ERROR = 0xFF0033

# --- Role Names (Authoritative) ---
ROLE_FOUNDER = "👑 Founder / Sumair"
ROLE_ADMIN = "🛡️ Admin / Overseer"
ROLE_SUPPORT_LEAD = "🛠️ Support Lead"
ROLE_PRO_LICENSE = "💎 Pro License"
ROLE_BETA = "🧪 Beta Tester"
ROLE_VIP = "⚡ VIP / Contributor"
ROLE_MOTION_DESIGNER = "🎬 Motion Designer"
ROLE_VIDEO_EDITOR = "✂️ Video Editor"
ROLE_TOOL_DEV = "💻 Tool / JSX Developer"
ROLE_3D_VFX = "🎨 3D / VFX Artist"
ROLE_VERIFIED = "🎨 Verified Editor"
ROLE_ANNOUNCE_PING = "📢 Announcement Ping"
ROLE_RELEASE_PING = "⚡ Release & Patch Ping"
ROLE_JAILED = "🔒 Jailed"
ROLE_UNVERIFIED = "⏳ Unverified"

# Colors for Specializations & Pings
COLOR_MOTION_DESIGNER = 0x3498DB
COLOR_VIDEO_EDITOR = 0x9B59B6
COLOR_TOOL_DEV = 0x2ECC71
COLOR_3D_VFX = 0xE67E22
COLOR_ANNOUNCE_PING = 0x00FFFF
COLOR_RELEASE_PING = 0xFF0033
COLOR_JAILED = 0x333333

# --- Fortress Security Engine Thresholds ---
SPAM_MSG_LIMIT = 5            # >5 messages
SPAM_WINDOW_SECONDS = 3.0     # in 3 seconds
SPAM_TIMEOUT_MINUTES = 10     # 10 minute timeout

RAID_JOIN_LIMIT = 8           # >8 member joins
RAID_WINDOW_SECONDS = 10.0    # in 10 seconds

# Disallowed Invite & Scam RegEx Patterns
INVITE_REGEX = r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discord(?:app)?\.com/invite)/[a-zA-Z0-9]+"
SUSPICIOUS_LINKS_REGEX = r"(?:nitro|steamcommunity-free|gift-discord|airdrop-eth|claim-gift|free-nitro)"

@dataclass
class RoleDefinition:
    name: str
    color: int
    hoist: bool
    mentionable: bool
    is_admin: bool = False
    permissions_summary: str = ""

# Strict Authoritative Role Hierarchy
ROLE_HIERARCHY: List[RoleDefinition] = [
    RoleDefinition(
        name=ROLE_FOUNDER,
        color=COLOR_FOUNDER,
        hoist=True,
        mentionable=True,
        is_admin=True,
        permissions_summary="Full Administrator & Owner Terminal access",
    ),
    RoleDefinition(
        name=ROLE_ADMIN,
        color=COLOR_ADMIN,
        hoist=True,
        mentionable=True,
        is_admin=True,
        permissions_summary="Kick, ban, manage messages, audit log, server logs",
    ),
    RoleDefinition(
        name=ROLE_SUPPORT_LEAD,
        color=COLOR_SUPPORT_LEAD,
        hoist=True,
        mentionable=True,
        permissions_summary="Manage threads, triage support tickets",
    ),
    RoleDefinition(
        name=ROLE_PRO_LICENSE,
        color=COLOR_PRO_LICENSE,
        hoist=True,
        mentionable=False,
        permissions_summary="Unlocked via /activate, Pro & Beta Vault",
    ),
    RoleDefinition(
        name=ROLE_BETA,
        color=COLOR_BETA,
        hoist=True,
        mentionable=False,
        permissions_summary="Access to pre-release scripts & beta builds",
    ),
    RoleDefinition(
        name=ROLE_VIP,
        color=COLOR_VIP,
        hoist=True,
        mentionable=False,
        permissions_summary="Early adopter tier & community champions",
    ),
    RoleDefinition(
        name=ROLE_MOTION_DESIGNER,
        color=COLOR_MOTION_DESIGNER,
        hoist=True,
        mentionable=False,
        permissions_summary="After Effects Motion Designers",
    ),
    RoleDefinition(
        name=ROLE_VIDEO_EDITOR,
        color=COLOR_VIDEO_EDITOR,
        hoist=True,
        mentionable=False,
        permissions_summary="Premiere Pro & Timeline Video Editors",
    ),
    RoleDefinition(
        name=ROLE_TOOL_DEV,
        color=COLOR_TOOL_DEV,
        hoist=True,
        mentionable=False,
        permissions_summary="ExtendScript, CEP & Automation Developers",
    ),
    RoleDefinition(
        name=ROLE_3D_VFX,
        color=COLOR_3D_VFX,
        hoist=True,
        mentionable=False,
        permissions_summary="Blender, Cinema4D, and VFX Compositors",
    ),
    RoleDefinition(
        name=ROLE_VERIFIED,
        color=COLOR_VERIFIED,
        hoist=False,
        mentionable=False,
        permissions_summary="Base authenticated member for editor sector",
    ),
    RoleDefinition(
        name=ROLE_ANNOUNCE_PING,
        color=COLOR_ANNOUNCE_PING,
        hoist=False,
        mentionable=True,
        permissions_summary="Notification role for official server announcements",
    ),
    RoleDefinition(
        name=ROLE_RELEASE_PING,
        color=COLOR_RELEASE_PING,
        hoist=False,
        mentionable=True,
        permissions_summary="Notification role for software updates & patch releases",
    ),
    RoleDefinition(
        name=ROLE_JAILED,
        color=COLOR_JAILED,
        hoist=False,
        mentionable=False,
        permissions_summary="Quarantine role for disciplinary isolation",
    ),
    RoleDefinition(
        name=ROLE_UNVERIFIED,
        color=COLOR_UNVERIFIED,
        hoist=False,
        mentionable=False,
        permissions_summary="Default join state, restricted to onboarding",
    ),
]

# --- Category & Channel Specifications ---
@dataclass
class ChannelDefinition:
    name: str
    channel_type: str = "text"  # "text", "voice", "forum", "stage"
    topic: Optional[str] = None
    forum_tags: List[str] = field(default_factory=list)
    bitrate: Optional[int] = None
    slowmode_delay: int = 0
    is_hidden: bool = False

@dataclass
class CategoryDefinition:
    name: str
    channels: List[ChannelDefinition]
    permission_mode: str  # "onboarding", "ecosystem", "verified_only", "pro_vault", "founder_terminal", "voice_collab"
    description: str = ""

CATEGORY_STRUCTURE: List[CategoryDefinition] = [
    CategoryDefinition(
        name="🛑 ︱ ONBOARDING & SYSTEM",
        permission_mode="onboarding",
        description="Public entry corridor: read-only for @everyone, hidden audit logs.",
        channels=[
            ChannelDefinition(name="🚩・welcome-hub", topic="Orientation roadmap and brand manifesto."),
            ChannelDefinition(name="📜・rules-and-safety", topic="Server code of conduct & verification gateway."),
            ChannelDefinition(name="🔗・official-links", topic="Verified Sumair Tools domains & download portals."),
            ChannelDefinition(name="📢・announcements", topic="Critical ecosystem releases and notices."),
            ChannelDefinition(name="📡・server-logs", topic="Fortress Security Engine audit and moderation telemetry.", is_hidden=True),
        ],
    ),
    CategoryDefinition(
        name="🚀 ︱ SVM41R TOOLS HUB",
        permission_mode="ecosystem",
        description="Public read-only developer repository & tool documentation.",
        channels=[
            ChannelDefinition(name="⚡・updates-changelog", topic="Live patch notes & version drops."),
            ChannelDefinition(name="🧭・roadmap-previews", topic="Upcoming After Effects & Premiere tool previews."),
            ChannelDefinition(name="📚・documentation", topic="Installation walkthroughs & JSX syntax cheat-sheets."),
            ChannelDefinition(name="❓・faq-knowledgebase", topic="Troubleshooting common render and script errors."),
        ],
    ),
    CategoryDefinition(
        name="💬 ︱ EDITORS SECTOR",
        permission_mode="verified_only",
        description="Restricted discussion sector for Verified Editors.",
        channels=[
            ChannelDefinition(name="💬・general-lounge", topic="Central discussion for motion designers and creators."),
            ChannelDefinition(name="🎞️・after-effects-motion", topic="After Effects, JSX expressions, and rendering pipelines."),
            ChannelDefinition(name="✂️・premiere-video-editing", topic="Premiere Pro, timeline pacing, and client feedback."),
            ChannelDefinition(name="🖥️・rigs-and-workstations", topic="Hardware setups, GPU benchmarks, and render nodes."),
            ChannelDefinition(name="🤖・bot-sandbox", topic="Bot commands, license verification, and sandbox testing."),
        ],
    ),
    CategoryDefinition(
        name="🏆 ︱ SHOWCASE & REEL",
        permission_mode="verified_only",
        description="Portfolios, peer reviews, and live production highlights.",
        channels=[
            ChannelDefinition(name="🎬・client-showcase", topic="Polished client reels, commercial motion, and YouTube edits."),
            ChannelDefinition(name="🔍・review-and-critique", topic="Works-in-progress seeking technical or aesthetic feedback."),
            ChannelDefinition(name="🔥・tools-in-action", topic="Live workflow recordings featuring Sumair Tools."),
        ],
    ),
    CategoryDefinition(
        name="🎒 ︱ ASSET VAULT",
        permission_mode="verified_only",
        description="Community resources, presets, and audio beds.",
        channels=[
            ChannelDefinition(name="💾・presets-and-scripts", topic="Community JSX snippets, AE presets, and automation utilities."),
            ChannelDefinition(name="🔊・sound-effects-sfx", topic="Curated SFX packs, risers, hits, and audio mastering."),
            ChannelDefinition(name="🎞️・textures-and-overlays", topic="Film grains, light leaks, and UI motion overlays."),
            ChannelDefinition(name="🧠・ai-motion-prompts", topic="Generative prompts, storyboard concepts, and AI animation."),
        ],
    ),
    CategoryDefinition(
        name="💼 ︱ FREELANCE & AGENCY",
        permission_mode="verified_only",
        description="Paid opportunities and agency negotiations.",
        channels=[
            ChannelDefinition(name="📌・job-board", topic="Paid editing and motion design bookings only. Include budget.", slowmode_delay=120),
            ChannelDefinition(name="📁・editor-portfolios", topic="Member showreels, CV links, and booking availability.", slowmode_delay=300),
            ChannelDefinition(name="💰・contracts-and-pricing", topic="Retainer advice, invoicing standards, and rate calculation."),
        ],
    ),
    CategoryDefinition(
        name="🧰 ︱ SUPPORT DESK",
        permission_mode="verified_only",
        description="Interactive ticket triage and issue trackers.",
        channels=[
            ChannelDefinition(name="🎫・create-ticket", topic="Spawn an encrypted, private support ticket channel."),
            ChannelDefinition(
                name="🐛・bug-tracker",
                channel_type="forum",
                topic="Report software defects with system specs and reproduction steps.",
                forum_tags=["Investigating", "Confirmed", "Fixed", "User Error"],
            ),
            ChannelDefinition(
                name="💡・feature-requests",
                channel_type="forum",
                topic="Submit workflow requests and tool enhancement proposals.",
                forum_tags=["Under Review", "Planned", "Shipped"],
            ),
        ],
    ),
    CategoryDefinition(
        name="💎 ︱ PRO & BETA VAULT",
        permission_mode="pro_vault",
        description="Strictly restricted to Pro License holders, Beta Testers, and Founder.",
        channels=[
            ChannelDefinition(name="💎・pro-lounge", topic="Exclusive lounge for verified Sumair Tools license owners."),
            ChannelDefinition(name="🧪・beta-builds", topic="Pre-release .zxp extensions and experimental JSX builds."),
            ChannelDefinition(name="📋・dev-backlog", topic="Direct developer updates, feature voting, and core roadmap."),
        ],
    ),
    CategoryDefinition(
        name="👑 ︱ FOUNDER TERMINAL",
        permission_mode="founder_terminal",
        description="Encrypted operations center locked strictly to Founder / Owner.",
        channels=[
            ChannelDefinition(name="🔒・owner-terminal", topic="Direct command center and raid alert broadcast.", is_hidden=True),
            ChannelDefinition(name="📊・analytics-revenue", topic="License analytics, sales metrics, and growth tracking.", is_hidden=True),
            ChannelDefinition(name="⚙️・bot-control", topic="Core bot operations, diagnostics, and lockdown control.", is_hidden=True),
        ],
    ),
    CategoryDefinition(
        name="🔊 ︱ VOICE PROTOCOLS",
        permission_mode="voice_collab",
        description="High-fidelity voice, editing sessions, and staff sync.",
        channels=[
            ChannelDefinition(name="🔊 General Lounge", channel_type="voice", bitrate=96000),
            ChannelDefinition(name="🔊 Co-Working", channel_type="voice", bitrate=384000),
            ChannelDefinition(name="🔊 Dev Stage", channel_type="stage"),
            ChannelDefinition(name="🔒 Staff Sync", channel_type="voice", is_hidden=True),
        ],
    ),
]
