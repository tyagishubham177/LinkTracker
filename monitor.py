#!/usr/bin/env python
"""
monitor.py

This script checks the availability of a product on Amul's shop page.
It handles the pincode popup and verifies the pincode was successfully entered
before checking product availability status.
"""

import time
import os
import requests
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URL of the product page to check
PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
# Pincode to enter
PINCODE = "201305"  # Example: Noida

# Store the last known status to only send notifications on state change
last_status = False

def check_product_availability():
    """
    Loads the product page using Playwright, handles the pincode popup,
    verifies the pincode was entered correctly, and checks product availability.
    
    Returns:
        bool: True if the product is available; False otherwise.
    """
    with sync_playwright() as p:
        # Launch Chromium with a viewport large enough to see the entire page
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Navigating to {PRODUCT_URL} ...")
        page.goto(PRODUCT_URL, timeout=30000)
        
        # Take a screenshot before attempting pincode entry
        page.screenshot(path="before_pincode.png")
        
        # Check if pincode modal is visible and handle it
        pincode_entered = False
        try:
            # Check for the modal dialog
            if page.is_visible("#locationWidgetModal"):
                print("Found pincode modal popup")
                
                # Check for the pincode input field in the modal
                if page.is_visible("#locationWidgetModal input[placeholder='Enter Your Pincode']"):
                    # Fill in the pincode
                    page.fill("#locationWidgetModal input[placeholder='Enter Your Pincode']", PINCODE)
                    print(f"Entered pincode: {PINCODE} in modal popup")
                    
                    # Try to find and click an Apply/Check/Submit button
                    for button_selector in [
                        "#locationWidgetModal button:has-text('Apply')",
                        "#locationWidgetModal button:has-text('Check')",
                        "#locationWidgetModal button:has-text('Submit')",
                        "#locationWidgetModal button.btn-primary",
                        "#locationWidgetModal form button[type='submit']"
                    ]:
                        if page.is_visible(button_selector):
                            page.click(button_selector)
                            print(f"Clicked button using selector: {button_selector}")
                            pincode_entered = True
                            break
            
            # If modal approach didn't work, try the header pincode option
            if not pincode_entered:
                # Check if there's a pincode selector in the header
                if page.is_visible("text=Select Pincodes"):
                    page.click("text=Select Pincodes")
                    print("Clicked 'Select Pincodes' in header")
                    
                    # Wait for any popup to appear
                    page.wait_for_timeout(2000)
                    
                    # Look for pincode input field
                    pincode_selectors = [
                        "input[placeholder='Enter Your Pincode']",
                        "input[placeholder='Enter Pincode']",
                        "input#search.form-control"
                    ]
                    
                    for selector in pincode_selectors:
                        if page.is_visible(selector):
                            page.fill(selector, PINCODE)
                            print(f"Entered pincode: {PINCODE} using selector: {selector}")
                            
                            # Try to find and click an Apply/Check/Submit button
                            for button_selector in [
                                "button:has-text('Apply')",
                                "button:has-text('Check')",
                                "button:has-text('Submit')",
                                "button.btn-primary",
                                "form button[type='submit']"
                            ]:
                                if page.is_visible(button_selector):
                                    page.click(button_selector)
                                    print(f"Clicked button using selector: {button_selector}")
                                    pincode_entered = True
                                    break
                            
                            if pincode_entered:
                                break
        
            # Wait for any navigation or network activity to complete
            page.wait_for_load_state("networkidle", timeout=15000)
            
        except PlaywrightTimeoutError as e:
            print(f"Timeout while handling pincode: {e}")
        except Exception as e:
            print(f"Error handling pincode: {e}")
        
        # Take a screenshot after pincode entry attempt
        page.screenshot(path="after_pincode.png")
        
        # Additional wait to ensure dynamic content is loaded
        time.sleep(5)
        
        # Verify if pincode was successfully entered
        pincode_verification = verify_pincode_entered(page, PINCODE)
        print(f"Pincode verification result: {pincode_verification}")
        
        # Get the full rendered HTML content
        content = page.content()
        
        # Save HTML for debugging
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            print("Saved full HTML to debug.html")
        
        # Take one final screenshot of the complete page
        page.screenshot(path="final_product_page.png", full_page=True)
        
        browser.close()
        
        # Check for availability markers
        content_lower = content.lower()
        
        # Availability status
        is_available = False
        
        # Check for unavailability indicators
        if "sold out" in content_lower or "notify me" in content_lower or "out of stock" in content_lower:
            is_available = False
        # Check for availability indicators - "add to cart" usually indicates item is in stock
        elif "add to cart" in content_lower:
            is_available = True
            
        # Print verification details
        print(f"Pincode verification: {pincode_verification}")
        print(f"Product availability: {is_available}")
        
        return is_available

def verify_pincode_entered(page, pincode):
    """
    Verifies that the pincode was successfully entered by checking:
    1. If the pincode modal is no longer visible
    2. If the pincode appears in the header or elsewhere on the page
    
    Returns:
        dict: Verification results
    """
    verification = {
        "modal_closed": not page.is_visible("#locationWidgetModal"),
        "pincode_in_header": False,
        "pincode_displayed": False
    }
    
    # Check if pincode appears in the header
    header_text = page.text_content("header")
    if header_text and pincode in header_text:
        verification["pincode_in_header"] = True
    
    # Look for the pincode anywhere on the page
    page_content = page.content()
    if pincode in page_content:
        verification["pincode_displayed"] = True
    
    # Take additional screenshot of the header area
    header_box = page.locator("header").bounding_box()
    if header_box:
        page.screenshot(path="header.png", clip={
            "x": header_box["x"],
            "y": header_box["y"],
            "width": header_box["width"],
            "height": header_box["height"]
        })
    
    return verification

def send_telegram_message(message, bot_token, chat_id):
    """
    Sends a Telegram message via the Bot API.
    
    Args:
        message (str): The message to send.
        bot_token (str): The Telegram bot token.
        chat_id (str): The target chat ID.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
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
        message = f"🎉 <b>GOOD NEWS!</b> Product is now AVAILABLE!\n{PRODUCT_URL}\nChecked at: {current_time}"
        print("Sending availability notification")
        
        if bot_token and chat_id:
            send_telegram_message(message, bot_token, chat_id)
        else:
            print("Telegram credentials not set. Skipping Telegram message.")
    
    # Update the last status
    last_status = available

if __name__ == "__main__":
    main()
