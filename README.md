# Sumair Tools Core — Production Discord Infrastructure Bot

![Discord.py Version](https://img.shields.io/badge/discord.py-v2.x-5865F2?logo=discord&logoColor=white)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/production-ready-57F287)
![Platform](https://img.shields.io/badge/platform-Sumair%20Tools-FF4B4B)

A custom, enterprise-grade Discord bot designed for **Sumair Tools** (https://sumairtools.online). Built using `discord.py` (v2.x), featuring Slash Commands (`app_commands`), persistent interactive UI components (`discord.ui.View`), native server structure provisioning, self-verification, ticket triage, and automated license validation.

---

## ⚡ Core Capabilities

1. **Autonomous Server Provisioning (`/setup-server`)**:
   - Wipes legacy channels/categories with a double-confirmation safety prompt.
   - Reconstructs a 9-tier role matrix with exact brand colors and hoisting.
   - Deploys 9 structured categories, explicit permission overwrites, high-bitrate voice channels, stage channel, and forum channels with custom workflow tags (`[Investigating]`, `[Confirmed]`, `[Fixed]`, etc.).
   - Drops starter manifestos and documentation links immediately.

2. **Native Verification System (`/post-verification`)**:
   - Persistent `[ ✅ Verify & Enter ]` button embedded into `#rules-and-safety`.
   - Adds `👥 Verified Member`, removes `⏳ Unverified`.
   - Never expires (`timeout=None`, registered in `setup_hook`).

3. **Help Desk & Support Triage (`/post-support`)**:
   - Persistent `[ 📩 Open Support Ticket ]` button in `#tool-support`.
   - Creates private ticket channels with user and staff-only overwrites.
   - Includes persistent `[ 🔒 Close Ticket ]` and `[ 📜 Save Transcript ]` actions with transcript generation.

4. **Automated License Validation (`/activate`)**:
   - Asynchronous `aiohttp` client hitting the https://sumairtools.online verification API (with support for Gumroad, Lemon Squeezy, or sandbox mock mode).
   - Automatically assigns `💎 Lifetime / Pro License` and unlocks `#pro-lounge`, `#beta-builds`, and `#dev-backlog`.

5. **Ecosystem Changelog Publisher (`/changelog`)**:
   - Staff-only slash command to format and post tool release notes directly into `#changelog-releases`.

---

## 🛠️ Discord Developer Portal Setup Guide

Follow these steps carefully to ensure the bot functions with full capabilities.

### 1. Create Application & Bot
1. Navigate to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name it `Sumair Tools Core`, and confirm.
3. Click the **Bot** tab on the left navigation sidebar.
4. Click **Add Bot** (or **Reset Token**) and copy your Bot Token. Save this in your `.env` file as `DISCORD_TOKEN`.

### 2. Enable Privileged Gateway Intents (CRITICAL)
Under the **Bot** tab, scroll down to the **Privileged Gateway Intents** section and toggle **ON** the following:
- ✅ **Server Members Intent** (Required for assigning `Verified Member`, `Unverified`, and `Pro License` roles).
- ✅ **Message Content Intent** (Required for compiling ticket transcripts).

Click **Save Changes**.

### 3. Generate Bot Invite URL & Permissions Integer
1. Go to **OAuth2 > URL Generator** in the Developer Portal.
2. Under **Scopes**, select:
   - `bot`
   - `applications.commands`
3. Under **Bot Permissions**, select:
   - `Administrator` (Permission Integer: `8`)
   *Alternatively, if not using Administrator, grant: Manage Roles, Manage Channels, Kick Members, Ban Members, Read Messages/View Channels, Send Messages, Manage Messages, Embed Links, Attach Files, Read Message History, Connect, Speak, Move Members, Manage Threads, Use External Emojis.*
4. Copy the generated URL at the bottom and open it in your browser to invite the bot to your server.

### 4. Enable Community in Your Server (For Forum & Stage Channels)
Discord Forum Channels (`🐛-bug-reports`, `💡-feature-requests`) and Stage Channels (`🔊 Dev Stage`) require the **Community** feature:
1. In your Discord server, open **Server Settings**.
2. Under **Community**, click **Enable Community**.
3. Follow the quick setup wizard (requires verified email and explicit content filter).
*(Note: If Community is not enabled, the bot automatically falls back to standard text and voice channels so provisioning never breaks).*

### 5. Role Hierarchy Golden Rule (CRITICAL)
In Discord, a bot **cannot manage or assign any role positioned above its own highest role**:
1. Open **Server Settings > Roles**.
2. Find the role named after your bot (`Sumair Tools Core`).
3. **Drag the bot's role to the top of the list**, positioned *above* `👑 Founder / Dev (Sumair)`, `💎 Lifetime / Pro License`, and `👥 Verified Member`.

---

## 📦 Project Structure

```
Discord Sumair Tools/
├── bot.py                  # Bot entry point, setup_hook, event listeners & error handling
├── config.py               # Authoritative role hierarchy, category layout, colors & constants
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── README.md               # Documentation & setup walkthrough
│
├── views/                  # Persistent Discord UI views (timeout=None)
│   ├── __init__.py
│   ├── verification.py     # Persistent [ Verify & Enter ] button view
│   └── tickets.py          # Persistent [ Open Ticket ], [ Close ], [ Transcript ] views
│
├── services/               # Core business logic & integrations
│   ├── __init__.py
│   ├── license.py          # Async aiohttp validation client (with mock testing support)
│   └── provisioner.py      # Automated server wiper, channel builder & permission linker
│
└── cogs/                   # Slash command extensions
    ├── __init__.py
    ├── admin.py            # /setup-server, /post-verification, /post-support
    ├── licensing.py        # /activate <license_key>
    └── releases.py         # /changelog <tool_name> <version> <changes>
```

---

## 🚀 Installation & Local Deployment

### 1. Clone or Open Workspace
```powershell
cd "c:\Users\votor\OneDrive\Desktop\Discord Sumair Tools"
```

### 2. Install Dependencies
Ensure Python 3.10+ is installed:
```powershell
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Edit `.env` with your values:
```env
# Your Discord Bot Token from Developer Portal
DISCORD_TOKEN=MTE...your_token_here

# Your Discord Server ID (enables instant slash command sync)
GUILD_ID=123456789012345678

# Sumair Tools API Key
LICENSE_API_KEY=your_license_api_key_here
LICENSE_API_URL=https://sumairtools.online/api/v1/licenses/verify

# Enable test keys (e.g. SUMAIR-PRO-TEST-1234) for local testing without live API
ENABLE_MOCK_LICENSES=true
```

### 4. Start the Bot
```powershell
python bot.py
```

Console output upon successful connection:
```
2026-09-11 19:20:00 | INFO     | SumairTools.Core         | Initializing Sumair Tools Core setup hook...
2026-09-11 19:20:00 | INFO     | SumairTools.Core         | Registered persistent views: VerificationView, SupportTicketView, TicketControlView
2026-09-11 19:20:01 | INFO     | SumairTools.Core         | Loaded extension: cogs.admin
2026-09-11 19:20:01 | INFO     | SumairTools.Core         | Loaded extension: cogs.licensing
2026-09-11 19:20:01 | INFO     | SumairTools.Core         | Loaded extension: cogs.releases
2026-09-11 19:20:02 | INFO     | SumairTools.Core         | Synchronized 5 guild-specific slash commands for guild ...
============================================================
Logged in as: Sumair Tools Core#0000 (ID: ...)
discord.py version: 2.7.1
Connected Guilds: 1
============================================================
```

---

## 📋 Slash Command Reference

| Command | Permission | Description |
| :--- | :--- | :--- |
| `/setup-server` | Administrator | Wipes legacy channels and provisions the full role hierarchy, 9 categories, forums, and panels. |
| `/post-verification` | Administrator | Drops the rules manifesto and persistent `[ Verify & Enter ]` button into `#rules-and-safety`. |
| `/post-support` | Administrator | Drops the support desk embed and persistent `[ Open Support Ticket ]` button into `#tool-support`. |
| `/activate <key>` | Everyone (Ephemeral) | Validates license key asynchronously and grants `💎 Lifetime / Pro License`. |
| `/changelog <tool> <ver> <notes>` | Staff Only | Publishes a formatted software release embed directly to `#changelog-releases`. |

---

## 🧪 Testing License Activation

When `ENABLE_MOCK_LICENSES=true`, you can test `/activate` immediately in Discord using sandbox test keys:
- `SUMAIR-PRO-TEST-0001`
- `SUMAIR-LIFETIME-MOTION-2024`
- `TEST-ACCESS-GRANTED`

Any key starting with `SUMAIR-PRO`, `SUMAIR-LIFETIME`, or `TEST-` will instantly validate and grant the role without requiring live HTTP server endpoints.

For production, point `LICENSE_API_URL` to your production validation endpoint (`https://sumairtools.online/api/v1/licenses/verify`) and set `ENABLE_MOCK_LICENSES=false`.

---

## 🔒 Production Hosting Recommendations

For 24/7 uptime on Linux/VPS (Ubuntu/Debian):

### Using `systemd` Service:
1. Create service file `/etc/systemd/system/sumairbot.service`:
```ini
[Unit]
Description=Sumair Tools Core Discord Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/sumair-tools-bot
ExecStart=/opt/sumair-tools-bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now sumairbot
```
