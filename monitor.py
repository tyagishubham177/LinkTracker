#!/usr/bin/env python
"""
monitor.py

This script checks the availability of a product on Amul's shop page.
It handles the pincode popup and checks product availability status.
Messages are sent only when the product becomes available.
"""

import time
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URL of the product page to check
PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
# Pincode to enter (change this to your target delivery pincode)
PINCODE = "380015"  # Example: Ahmedabad pincode

# Store the last known status to only send notifications on state change
last_status = False

def check_product_availability():
    """
    Loads the product page using Playwright, handles the pincode popup,
    and checks the complete rendered HTML for availability.
    
    Returns:
        bool: True if the product is available; False otherwise.
    """
    with sync_playwright() as p:
        # Launch Chromium in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Navigating to {PRODUCT_URL} ...")
        page.goto(PRODUCT_URL, timeout=30000)
        
        # Handle pincode popup
        try:
            # Wait for pincode input to appear (adjust selector if needed)
            page.wait_for_selector('input[placeholder="Enter Pincode"]', timeout=10000)
            
            # Fill in the pincode
            page.fill('input[placeholder="Enter Pincode"]', PINCODE)
            
            # Click submit/check button (adjust selector if needed)
            page.click('button:has-text("Check")')
            
            print(f"Entered pincode: {PINCODE}")
            
            # Wait for page to update after pincode submission
            page.wait_for_load_state("networkidle", timeout=15000)
        except PlaywrightTimeoutError:
            print("Warning: Pincode popup not found or has changed. Continuing anyway...")
        except Exception as e:
            print(f"Error handling pincode popup: {e}")
        
        # Additional wait to ensure that all dynamic content is loaded
        time.sleep(5)
        
        # Get the full rendered HTML content
        content = page.content()
        
        # Take a screenshot for debugging
        page.screenshot(path="product_page.png")
        
        # Save HTML for debugging purposes
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            print("Saved full HTML to debug.html")
        
        browser.close()
        
        # Check for availability markers
        content_lower = content.lower()
        
        # Check for unavailability indicators
        if "sold out" in content_lower or "notify me" in content_lower or "out of stock" in content_lower:
            return False
            
        # Check for availability indicators - "add to cart" usually indicates item is in stock
        if "add to cart" in content_lower:
            return True
            
        # If no clear indicators found, default to unavailable
        return False

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
    global last_status
    
    # Get current time
    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"[{current_time}] Checking product availability...")
    available = check_product_availability()
    status = "AVAILABLE" if available else "SOLD OUT or UNAVAILABLE"
    
    print(f"[{current_time}] Product status: {status}")
    
    # Retrieve Telegram credentials from environment variables
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # Only send a message if the product is available and status has changed
    if available and available != last_status:
        message = f"🎉 GOOD NEWS! Product is now AVAILABLE!\n{PRODUCT_URL}\nChecked at: {current_time}"
        print("Sending availability notification")
        
        if bot_token and chat_id:
            send_telegram_message(message, bot_token, chat_id)
        else:
            print("Telegram credentials not set. Skipping Telegram message.")
    
    # Update the last status
    last_status = available

if __name__ == "__main__":
    main()
