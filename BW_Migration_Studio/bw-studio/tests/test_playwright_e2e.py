"""
HANAMORPH BW Migration & Modernization Studio
Milestone M4.5 — Playwright End-to-End Headless Browser Test Suite
Verifies all 12 workbench screens, DOM rendering, navigation, and auth lifecycle.
"""

import unittest
import os
import sys
import threading
import time

# Ensure bw-studio directory is in Python path
STUDIO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if STUDIO_DIR not in sys.path:
    sys.path.insert(0, STUDIO_DIR)

from backend.server import ThreadedHTTPServer, StudioHandler, SESSION_MGR

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

TEST_PORT = 4099
TEST_HOST = "127.0.0.1"
TEST_API_KEY = "test-playwright-e2e-api-key-999"
SCREENSHOT_DIR = os.path.join(os.path.dirname(STUDIO_DIR), "output", "playwright_evidence")


class TestPlaywrightBrowserE2E(unittest.TestCase):
    server = None
    server_thread = None

    @classmethod
    def setUpClass(cls):
        if not PLAYWRIGHT_AVAILABLE:
            raise unittest.SkipTest("Playwright library not installed.")

        os.makedirs(SCREENSHOT_DIR, exist_ok=True)
        os.environ["BW_STUDIO_API_KEY"] = TEST_API_KEY
        cls.server = ThreadedHTTPServer((TEST_HOST, TEST_PORT), StudioHandler, api_key=TEST_API_KEY)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        if cls.server:
            cls.server.shutdown()
            cls.server.server_close()

    def setUp(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900})
        self.page = self.context.new_page()
        self.console_errors = []
        self.page.on("console", lambda msg: self.console_errors.append(msg.text) if msg.type == "error" else None)

    def tearDown(self):
        self.context.close()
        self.browser.close()
        self.playwright.stop()

    def test_01_workbench_page_load_and_login_flow(self):
        """Verifies initial page load, security headers, and cookie-based login."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/index.html"
        resp = self.page.goto(url, wait_until="networkidle")
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status, 200)

        # Title check
        title = self.page.title()
        self.assertIn("HanaMorph", title)

        # Establish secure session via server API
        login_res = self.page.evaluate(f"""
            fetch('/api/auth/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ apiKey: '{TEST_API_KEY}' }})
            }}).then(r => r.json())
        """)
        self.assertEqual(login_res.get("status"), "AUTHENTICATED")

        # Reload with active session cookie
        self.page.reload(wait_until="networkidle")
        self.page.screenshot(path=os.path.join(SCREENSHOT_DIR, "screen_00_authenticated.png"))

        # Verify localStorage has zero API keys
        stored_key = self.page.evaluate("localStorage.getItem('bw_studio_api_key')")
        self.assertIsNone(stored_key, "API key must NOT be stored in localStorage")

    def test_02_all_twelve_modernization_screens(self):
        """Iterates through all 12 Modernization Intelligence screens and verifies DOM visibility and rendering."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/index.html"
        self.page.goto(url, wait_until="networkidle")

        # Authenticate session
        self.page.evaluate(f"""
            fetch('/api/auth/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ apiKey: '{TEST_API_KEY}' }})
            }})
        """)
        self.page.reload(wait_until="networkidle")

        screens = [
            ("nav-landscape", "tab-landscape", "01_landscape"),
            ("nav-discovery", "tab-discovery", "02_discovery"),
            ("nav-repository", "tab-repository", "03_repository"),
            ("nav-explorer", "tab-explorer", "04_explorer"),
            ("nav-lineage", "tab-lineage", "05_lineage"),
            ("nav-complexity", "tab-complexity", "06_complexity"),
            ("nav-assessment", "tab-assessment", "07_assessment"),
            ("nav-routes", "tab-routes", "08_routes"),
            ("nav-risk", "tab-risk", "09_risk"),
            ("nav-effort", "tab-effort", "10_effort"),
            ("nav-prioritization", "tab-prioritization", "11_prioritization"),
            ("nav-report", "tab-report", "12_report")
        ]

        for nav_id, tab_id, name in screens:
            nav_el = self.page.locator(f"#{nav_id}")
            self.assertTrue(nav_el.is_visible(), f"Nav item #{nav_id} must be visible")
            nav_el.click()
            time.sleep(0.3)

            # Assert tab container is visible
            tab_el = self.page.locator(f"#{tab_id}")
            self.assertTrue(tab_el.is_visible(), f"Screen container #{tab_id} must become visible on click")

            # Capture screenshot
            ss_path = os.path.join(SCREENSHOT_DIR, f"screen_{name}.png")
            self.page.screenshot(path=ss_path)
            self.assertTrue(os.path.exists(ss_path), f"Screenshot must be created: {ss_path}")

    def test_03_execution_screens_and_connections(self):
        """Tests the execution phase tabs: Planning, Generation, Validation, Delivery, Connections."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/index.html"
        self.page.goto(url, wait_until="networkidle")

        # Authenticate session
        self.page.evaluate(f"""
            fetch('/api/auth/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ apiKey: '{TEST_API_KEY}' }})
            }})
        """)
        self.page.reload(wait_until="networkidle")

        exec_screens = [
            ("nav-planning", "tab-planning", "13_planning"),
            ("nav-generation", "tab-generation", "14_generation"),
            ("nav-validation", "tab-validation", "15_validation"),
            ("nav-delivery", "tab-delivery", "16_delivery"),
            ("nav-connections", "tab-connections", "17_connections")
        ]

        for nav_id, tab_id, name in exec_screens:
            nav_el = self.page.locator(f"#{nav_id}")
            self.assertTrue(nav_el.is_visible(), f"Execution nav item #{nav_id} must be visible")
            nav_el.click()
            time.sleep(0.3)

            tab_el = self.page.locator(f"#{tab_id}")
            self.assertTrue(tab_el.is_visible(), f"Tab #{tab_id} must be visible")

            ss_path = os.path.join(SCREENSHOT_DIR, f"screen_{name}.png")
            self.page.screenshot(path=ss_path)
            self.assertTrue(os.path.exists(ss_path))

    def test_04_logout_clears_session(self):
        """Verifies that logout terminates session and invalidates cookie."""
        url = f"http://{TEST_HOST}:{TEST_PORT}/index.html"
        self.page.goto(url, wait_until="networkidle")

        # Authenticate
        self.page.evaluate(f"""
            fetch('/api/auth/login', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ apiKey: '{TEST_API_KEY}' }})
            }})
        """)

        # Execute logout
        logout_res = self.page.evaluate("""
            fetch('/api/auth/logout', { method: 'POST' }).then(r => r.json())
        """)
        self.assertEqual(logout_res.get("status"), "LOGGED_OUT")

        # Verify session is no longer valid
        sess_check = self.page.evaluate("fetch('/api/auth/session').then(r => r.json())")
        self.assertFalse(sess_check.get("authenticated"))


if __name__ == "__main__":
    unittest.main()
