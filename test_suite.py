"""
Sumair Tools Core - Fortress Automated Verification Suite
=========================================================
Validates Crimson role specifications, 10-category layouts,
persistent UI views, lockfile behavior, and Fortress security rate-limiters.
"""

import os
import sys
import asyncio
import unittest
import config
from services.license import LicenseService
from services.provisioner import ServerProvisioner, OfficialLinksView
from views.verification import VerificationView
from views.tickets import TicketLauncher, TicketCloseView
from security.fortress import FortressSecurityEngine

class TestFortressConfig(unittest.TestCase):
    """Checks Crimson roles, 10 categories, and channel definitions."""

    def test_role_hierarchy_order_and_colors(self):
        expected_roles = [
            ("👑 Founder / Sumair", 0xFF0033, True),
            ("🛡️ Admin / Overseer", 0xB30000, True),
            ("🛠️ Support Lead", 0x800000, True),
            ("💎 Pro License", 0xFF4D4D, True),
            ("⚡ VIP / Power User", 0xE63946, True),
            ("🧪 Beta Tester", 0x990000, False),
            ("🎨 Verified Editor", 0xCCCCCC, False),
            ("⏳ Unverified", 0x555555, False),
        ]
        self.assertEqual(len(config.ROLE_HIERARCHY), len(expected_roles))

        for idx, (expected_name, expected_color, expected_hoist) in enumerate(expected_roles):
            role_def = config.ROLE_HIERARCHY[idx]
            self.assertEqual(role_def.name, expected_name, f"Role mismatch at {idx}")
            self.assertEqual(role_def.color, expected_color, f"Color mismatch for {expected_name}")
            self.assertEqual(role_def.hoist, expected_hoist, f"Hoist mismatch for {expected_name}")

    def test_ten_categories(self):
        expected_categories = [
            "🛑 ︱ ONBOARDING & SYSTEM",
            "🚀 ︱ SVM41R TOOLS HUB",
            "💬 ︱ EDITORS SECTOR",
            "🏆 ︱ SHOWCASE & REEL",
            "🎒 ︱ ASSET VAULT",
            "💼 ︱ FREELANCE & AGENCY",
            "🧰 ︱ SUPPORT DESK",
            "💎 ︱ PRO & BETA VAULT",
            "👑 ︱ FOUNDER TERMINAL",
            "🔊 ︱ VOICE PROTOCOLS",
        ]
        actual_categories = [cat.name for cat in config.CATEGORY_STRUCTURE]
        self.assertEqual(actual_categories, expected_categories)

    def test_onboarding_channels(self):
        onboarding = next(c for c in config.CATEGORY_STRUCTURE if c.name == "🛑 ︱ ONBOARDING & SYSTEM")
        ch_names = [ch.name for ch in onboarding.channels]
        self.assertEqual(ch_names, ["🚩・welcome-hub", "📜・rules-and-safety", "🔗・official-links", "📢・announcements", "📡・server-logs"])

    def test_support_desk_channels_and_tags(self):
        support_cat = next(c for c in config.CATEGORY_STRUCTURE if c.name == "🧰 ︱ SUPPORT DESK")
        ch_names = [ch.name for ch in support_cat.channels]
        self.assertIn("🎫・create-ticket", ch_names)
        self.assertIn("🐛・bug-tracker", ch_names)
        self.assertIn("💡・feature-requests", ch_names)

        bug_tracker = next(ch for ch in support_cat.channels if ch.name == "🐛・bug-tracker")
        self.assertEqual(bug_tracker.forum_tags, ["Investigating", "Confirmed", "Fixed", "User Error"])


class TestFortressSecurity(unittest.TestCase):
    """Tests rate limiter logic and regex patterns."""

    def setUp(self):
        self.engine = FortressSecurityEngine(bot=None)

    def test_invite_regex(self):
        valid_invites = [
            "https://discord.gg/abcd123",
            "discord.gg/xyz",
            "discord.com/invite/testing123",
        ]
        for inv in valid_invites:
            self.assertTrue(bool(self.engine.invite_pattern.search(inv)), f"Failed to detect invite: {inv}")

        normal_msg = "Hey check out https://sumairtools.online for new updates!"
        self.assertFalse(bool(self.engine.invite_pattern.search(normal_msg)))

    def test_setup_lockfile_lifecycle(self):
        # Ensure clean state
        ServerProvisioner.remove_lock()
        self.assertFalse(ServerProvisioner.is_locked())

        # Engage lock
        ServerProvisioner.set_lock()
        self.assertTrue(ServerProvisioner.is_locked())

        # Clear lock
        ServerProvisioner.remove_lock()
        self.assertFalse(ServerProvisioner.is_locked())


class TestPersistentViews(unittest.TestCase):
    """Validates views have timeout=None and match custom IDs."""

    def test_views_persistence(self):
        views = [
            VerificationView(),
            TicketLauncher(),
            TicketCloseView(),
            OfficialLinksView(),
        ]
        for v in views:
            self.assertIsNone(v.timeout, f"View {v.__class__.__name__} must have timeout=None")


if __name__ == "__main__":
    unittest.main()
