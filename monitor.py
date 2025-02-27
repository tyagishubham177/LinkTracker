#!/usr/bin/env python
"""
monitor.py

1) Launches the Amul product page using Playwright.
2) Enters pincode (type -> wait for suggestion -> click suggestion -> wait for modal to close).
3) Takes 3 screenshots at key steps.
4) Scopes "In Stock" checks to the main product container only:
   - Must have <link itemprop="availability" href="...InStock...">
   - Must contain "Add to Cart" text in the main product HTML snippet.
5) Sends a Telegram notification only if newly found in stock.
6) Writes a monitor_steps.txt summarizing the run.
"""

import time
import os
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
PINCODE = "201305"

# Keep track of last known status so we don't spam notifications
last_status = False


def check_product_availability():
    """
    Handles pincode entry, checks product availability within the main container,
    saves screenshots + logs steps, returns True if in stock, else False.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # We'll store each step in a list and write it out at the end
        steps_log = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps_log.append(
            f"[{current_time}] Launching browser & navigating to {PRODUCT_URL}"
        )

        # 1) Navigate to product page
        page.goto(PRODUCT_URL, timeout=30000)
        page.screenshot(path="step1_launched_page.png", full_page=True)
        steps_log.append("Took screenshot: step1_launched_page.png")

        # 2) Enter pincode using improved approach
        try:
            page.wait_for_selector("input#search", timeout=15000)
            page.fill("input#search", PINCODE)
            steps_log.append(f"Typed pincode '{PINCODE}' into input#search")

            page.screenshot(path="step2_pincode_typed.png", full_page=True)
            steps_log.append("Took screenshot: step2_pincode_typed.png")

            # Wait for suggestion
            page.wait_for_selector(
                "#automatic .searchitem-name p.item-name", timeout=10000
            )
            suggestion_selector = (
                f"#automatic .searchitem-name p.item-name:has-text('{PINCODE}')"
            )
            page.click(suggestion_selector)
            steps_log.append(f"Clicked the pincode suggestion: {PINCODE}")

            # Wait for modal to close
            try:
                page.wait_for_selector(
                    "#locationWidgetModal", state="hidden", timeout=5000
                )
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

        # 4) Scope availability checks to the main product container
        product_section = page.query_selector("div.col-12.col-md-6.product-details-col")
        if product_section:
            product_html = product_section.inner_html().lower()
        else:
            product_html = ""

        # 4a) Check schema.org link itemprop="availability" for "InStock"
        in_stock_schema = False
        if product_section:
            schema_elem = product_section.query_selector(
                "link[itemprop='availability']"
            )
            if schema_elem:
                availability_href = schema_elem.get_attribute("href") or ""
                if "instock" in availability_href.lower():
                    in_stock_schema = True

        # 4b) Check text for "Add to Cart" within that container
        has_add_to_cart = "add to cart" in product_html

        # 4c) Final availability
        is_available = in_stock_schema and has_add_to_cart
        steps_log.append(
            f"Availability check => in_stock_schema={in_stock_schema}, add_to_cart={has_add_to_cart}"
        )
        steps_log.append(f"Final availability result: {is_available}")

        # 5) Save final HTML + steps
        content = page.content()
        with open("final_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        steps_log.append("Saved final HTML to final_page.html")

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

    # Telegram credentials
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    # Send message only if newly in stock
    if available and (available != last_status):
        message = (
            f"🎉 <b>GOOD NEWS!</b> Product is now AVAILABLE!\n"
            f"{PRODUCT_URL}\n"
            f"Checked at: {current_time}"
        )
        print("Sending availability notification...")

        if bot_token and chat_id:
            send_telegram_message(message, bot_token, chat_id)
        else:
            print("Telegram credentials not set. Skipping Telegram message.")

    # Update last_status
    last_status = available


if __name__ == "__main__":
    main()
