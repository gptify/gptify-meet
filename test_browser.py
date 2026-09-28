"""
GPTify Meet - Playwright Browser Automation Test
Validates end-to-end frontend interaction, API communication, and UI components.
"""
import sys
import threading
import time
import uvicorn
from playwright.sync_api import sync_playwright
from server import app

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8877, log_level="warning")

def test_frontend_flow():
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(1.5)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 1. Open app
        page.goto("http://127.0.0.1:8877/")
        page.wait_for_selector("#meetings-list-container")
        print("Page loaded successfully")

        # 2. Check meeting item is rendered
        meeting_item = page.locator(".g-meeting-item").first
        assert meeting_item.is_visible()
        title_text = meeting_item.locator("strong").text_content()
        print("First meeting in list:", title_text)
        assert len(title_text) > 0

        # 3. Check tabs switching
        page.click("#tab-btn-transcript")
        assert page.locator("#panel-transcript").is_visible()
        print("Transkripsiya tab opened")

        page.click("#tab-btn-tasks")
        assert page.locator("#panel-tasks").is_visible()
        print("Vazifalar tab opened")

        # 4. Check Telegram share modal
        page.click("button:has-text('Telegramga ulashish')")
        page.wait_for_selector("#telegram-modal", state="visible")
        preview_text = page.locator("#telegram-preview-text").input_value()
        print("Telegram preview text snippet:", preview_text[:80])
        assert "Qisqacha xulosa" in preview_text or "qarorlar" in preview_text or "Hamkorlik" in preview_text

        # Close modal
        page.click("#telegram-modal button:has-text('Bekor qilish')")
        page.wait_for_selector("#telegram-modal", state="hidden")
        print("Telegram modal closed")

        # 5. Check Landing view switcher
        page.click("#btn-view-landing")
        assert page.locator("#view-landing").is_visible()
        assert page.locator("#view-app").is_hidden()
        print("Switched to Landing view")

        # 6. Check Pricing switch
        page.click("#bill-year")
        price_text = page.locator("#price-display").text_content()
        assert "1 900 000" in price_text
        print("Pricing updated to yearly:", price_text.strip())

        browser.close()
        print("ALL BROWSER TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_frontend_flow()
