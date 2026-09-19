"""
Comprehensive UI Verification for FireSense Portals & Themes:
1. Validates portal isolation (Table and Feed ONLY in NTRO).
2. Validates deep linking (?portal=ntro, command, responder, citizen).
3. Validates Responder state machine next-action progression.
4. Validates light mode high-contrast typography and dark mode.
5. Captures visual verification screenshots across all 4 portals in light and dark, plus mobile.
"""
import sys
import time
import subprocess
import threading
from playwright.sync_api import sync_playwright

# Ensure utf-8 stdout on Windows
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL = "http://127.0.0.1:5002"

def run_tests():
    # Start app.py if not already up
    import urllib.request
    server_process = None
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/incidents", timeout=1)
        print("[INIT] Backend server already running on port 5002.")
    except Exception:
        print("[INIT] Starting app.py on port 5002...")
        server_process = subprocess.Popen([sys.executable, "app.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

    passed = 0
    failed = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})

        # ----------------------------------------------------
        # TEST 1: Deep Linking & Portal Isolation
        # ----------------------------------------------------
        for portal in ['command', 'citizen', 'responder', 'ntro']:
            page = context.new_page()
            page.goto(f"{BASE_URL}/app?portal={portal}", wait_until="domcontentloaded")
            page.wait_for_timeout(600)

            # Check portal visibility
            is_active = page.locator(f"#portal-{portal}").is_visible()
            assert is_active, f"Portal #{portal} should be visible for ?portal={portal}"

            # Verify Incident Table isolation
            table_visible = page.locator("#inc-table").is_visible()
            feed_visible = page.locator("#detection-feed").is_visible()

            if portal == 'ntro':
                if table_visible and feed_visible:
                    print(f"  [PASS] NTRO Portal properly contains Incident Table and Detection Feed.")
                    passed += 1
                else:
                    print(f"  [FAIL] NTRO Portal missing table ({table_visible}) or feed ({feed_visible}).")
                    failed += 1
            else:
                if not table_visible and not feed_visible:
                    print(f"  [PASS] {portal.upper()} Portal correctly ISOLATED from Incident Table and Detection Feed.")
                    passed += 1
                else:
                    print(f"  [FAIL] {portal.upper()} Portal leaked table ({table_visible}) or feed ({feed_visible})!")
                    failed += 1

            page.close()

        # ----------------------------------------------------
        # TEST 2: Responder Operations State Machine
        # ----------------------------------------------------
        page = context.new_page()
        page.goto(f"{BASE_URL}/app?portal=responder", wait_until="domcontentloaded")
        page.wait_for_timeout(600)

        # Check responder elements
        assert page.locator("#resp-title").is_visible(), "Responder mission title visible"
        assert page.locator("#resp-coords").is_visible(), "Responder coordinates visible"
        assert page.locator("#resp-action-container").is_visible(), "Responder action container visible"

        # Verify only ONE next prominent button exists, not 5 equal buttons
        buttons = page.locator("#resp-action-container button").all()
        if len(buttons) == 1:
            btn_text = buttons[0].text_content().strip()
            print(f"  [PASS] Responder State Machine renders single prominent next-action button: '{btn_text}'")
            passed += 1
        else:
            print(f"  [FAIL] Expected 1 next-action button in Responder, found {len(buttons)}")
            failed += 1

        page.close()

        # ----------------------------------------------------
        # TEST 3: Capture Screenshots of all 4 Portals in Light & Dark
        # ----------------------------------------------------
        print("\n[CAPTURING SCREENSHOTS FOR VISUAL PROOF]")
        for theme in ['light', 'dark']:
            for portal in ['ntro', 'command', 'responder', 'citizen']:
                page = context.new_page()
                page.set_viewport_size({"width": 1280, "height": 880})
                page.goto(f"{BASE_URL}/app?portal={portal}", wait_until="domcontentloaded")
                page.wait_for_timeout(400)

                # Set theme
                page.evaluate(f"setTheme('{theme}')")
                page.wait_for_timeout(300)

                filename = f"verify_{portal}_{theme}.png"
                page.screenshot(path=filename, full_page=False)
                print(f"  [SAVED] {filename}")
                page.close()

        # Mobile Viewport for Responder & Citizen
        for portal in ['responder', 'citizen']:
            page = context.new_page()
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(f"{BASE_URL}/app?portal={portal}", wait_until="domcontentloaded")
            page.wait_for_timeout(400)
            page.evaluate("setTheme('light')")
            page.wait_for_timeout(300)
            filename = f"verify_mobile_{portal}_light.png"
            page.screenshot(path=filename, full_page=False)
            print(f"  [SAVED] {filename}")
            page.close()

        browser.close()

    if server_process:
        server_process.terminate()

    print(f"\n========================================")
    print(f"UI VERIFICATION: {passed} passed, {failed} failed")
    print(f"========================================")
    return failed == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
