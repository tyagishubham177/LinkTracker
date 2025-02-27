#!/usr/bin/env python
"""
monitor.py

Merged script to:
1) Launch the Amul product page
2) Enter pincode using improved approach (type pincode, click dropdown suggestion)
3) Take screenshots at key steps
4) Check product availability via multiple signals
5) Send a Telegram message if newly in stock
6) Write a "monitor_steps.txt" summary
"""

import time
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# URL of the product page to check
PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
# Pincode to enter
PINCODE = "201305"  # Example pincode
# Store the last known status to only send notifications on state change
last_status = False

def check_product_availability():
    """
    Loads the product page using Playwright, handles the pincode,
    checks product availability, and returns True if in stock, else False.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        steps_log = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps_log.append(f"[{current_time}] Launching browser & navigating to {PRODUCT_URL}")

        # 1) Navigate to product page
        page.goto(PRODUCT_URL, timeout=30000)
        page.screenshot(path="step1_launched_page.png", full_page=True)
        steps_log.append("Took screenshot: step1_launched_page.png")

        # 2) Enter pincode with improved approach
        #    Wait for the input, type pincode, wait for suggestions, click suggestion
        try:
            page.wait_for_selector("input#search", timeout=15000)
            page.fill("input#search", PINCODE)
            steps_log.append(f"Typed pincode '{PINCODE}' into input#search")

            page.screenshot(path="step2_pincode_typed.png", full_page=True)
            steps_log.append("Took screenshot: step2_pincode_typed.png")

            # Wait for suggestion
            page.wait_for_selector("#automatic .searchitem-name p.item-name", timeout=10000)
            # Click the matching suggestion
            suggestion_selector = f"#automatic .searchitem-name p.item-name:has-text('{PINCODE}')"
            page.click(suggestion_selector)
            steps_log.append(f"Clicked the pincode suggestion: {PINCODE}")

            # Wait for modal to close
            try:
                page.wait_for_selector("#locationWidgetModal", state="hidden", timeout=5000)
                steps_log.append("Modal closed automatically!")
            except:
                steps_log.append("Modal might still be open; continuing anyway...")

        except PlaywrightTimeoutError as e:
            steps_log.append(f"Timeout while handling pincode: {e}")
        except Exception as e:
            steps_log.append(f"Error handling pincode: {e}")

        # 3) After modal is presumably gone, final screenshot
        time.sleep(3)
        page.screenshot(path="step3_modal_closed.png", full_page=True)
        steps_log.append("Took screenshot: step3_modal_closed.png")

        # 4) Check product availability
        content = page.content()
        content_lower = content.lower()

        # 4a) Check schema.org link itemprop='availability'
        in_stock_schema = False
        schema_elem = page.query_selector("link[itemprop='availability']")
        if schema_elem:
            availability_href = schema_elem.get_attribute("href") or ""
            if "InStock".lower() in availability_href.lower():
                in_stock_schema = True

        # 4b) Check text signals
        add_to_cart = "add to cart" in content_lower
        out_of_stock = any(x in content_lower for x in ["sold out", "notify me", "out of stock"])

        if out_of_stock:
            is_available = False
        elif in_stock_schema or add_to_cart:
            is_available = True
        else:
            is_available = False  # default

        steps_log.append(f"Availability check => in_stock_schema={in_stock_schema}, add_to_cart={add_to_cart}, out_of_stock={out_of_stock}")
        steps_log.append(f"Final availability result: {is_available}")

        # Save final HTML for debugging
        with open("final_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        steps_log.append("Saved final HTML to final_page.html")

        # 5) Write out a small text file summarizing the steps
        with open("monitor_steps.txt", "w", encoding="utf-8") as stepfile:
            stepfile.write("\n".join(steps_log) + "\n")

        browser.close()
        return is_available

def send_telegram_message(message, bot_token, chat_id):
    """
    Sends a Telegram message via the Bot API.
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

    now = datetime.now()
    current_time = now.strftime("%Y-%m-%d %H:%M:%S")

    print(f"[{current_time}] Checking product availability...")
    available = check_product_availability()
    status = "AVAILABLE" if available else "SOLD OUT or UNAVAILABLE"
    print(f"[{current_time}] Product status: {status}")

    # Retrieve Telegram credentials from environment variables
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    # Only send a message if the product is newly in stock
    if available and (available != last_status):
        message = (f"🎉 <b>GOOD NEWS!</b> Product is now AVAILABLE!\n"
                   f"{PRODUCT_URL}\n"
                   f"Checked at: {current_time}")
        print("Sending availability notification...")

        if bot_token and chat_id:
            send_telegram_message(message, bot_token, chat_id)
        else:
            print("Telegram credentials not set. Skipping Telegram message.")

    # Update last_status
    last_status = available

if __name__ == "__main__":
    main()
