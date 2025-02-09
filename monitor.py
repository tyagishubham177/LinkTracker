#!/usr/bin/env python
"""
monitor.py

This script checks the availability of a product on Amul’s shop page.
It uses Playwright to load the page (executing its JavaScript) so that dynamic
content is rendered, and then inspects the full HTML for unavailability markers.
Regardless of whether the product is available or not, the script sends a Telegram
message with the product URL and the current status.
"""

import time
import os
import requests
from playwright.sync_api import sync_playwright

# URL of the product page to check
PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"

def is_product_available():
    """
    Loads the product page using Playwright (to render JavaScript)
    and checks the complete rendered HTML for unavailability markers.
    
    Returns:
        bool: True if the product appears available; False if markers indicate it is unavailable.
    """
    with sync_playwright() as p:
        # Launch Chromium in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Navigating to {PRODUCT_URL} ...")
        page.goto(PRODUCT_URL, timeout=30000)
        
        # Wait for network idle state (adjust timeout if needed)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print("Warning: network idle state not reached:", e)
        
        # Additional wait to ensure that dynamic content is fully rendered
        time.sleep(5)
        
        # Get the full rendered HTML content
        content = page.content()
        
        # Save HTML for debugging purposes (optional)
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            print("Saved full HTML to debug.html")
        
        browser.close()
        
        # Perform a case-insensitive check for unavailability markers
        content_lower = content.lower()
        if "sold out" in content_lower or "notify me" in content_lower:
            return False
        return True

def send_telegram_message(message, bot_token, chat_id):
    """
    Sends a Telegram message via the Bot API.
    
    Args:
        message (str): The message to send.
        bot_token (str): The Telegram bot token.
        chat_id (str): The target chat ID.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload, timeout=10)
        print("Telegram response:", response.status_code, response.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

def main():
    available = is_product_available()
    status = "AVAILABLE" if available else "SOLD OUT or UNAVAILABLE"
    message = f"Product status: {status}\n{PRODUCT_URL}"
    print(message)
    
    # Retrieve Telegram credentials from environment variables
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if bot_token and chat_id:
        send_telegram_message(message, bot_token, chat_id)
    else:
        print("Telegram credentials not set. Skipping Telegram message.")

if __name__ == "__main__":
    main()
