#!/usr/bin/env python
"""
monitor.py

This script checks the availability of a product on Amul’s shop page.
Because the page loads its product details dynamically via JavaScript,
we use Playwright to render the page. After the dynamic content loads,
we inspect the full HTML to see if markers such as "Sold Out" or "Notify Me"
are present. If one of those markers is found, we assume the product is unavailable.
"""

import time
from playwright.sync_api import sync_playwright

# URL of the product page to check
PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"

def is_product_available():
    """
    Uses Playwright to load the product page fully (executing JavaScript)
    and then checks the rendered HTML for unavailability markers.

    Returns:
        True if the product appears available, False otherwise.
    """
    with sync_playwright() as p:
        # Launch a Chromium browser in headless mode
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"Navigating to {PRODUCT_URL} ...")
        page.goto(PRODUCT_URL, timeout=30000)
        
        # Wait for network idle to give dynamic content time to load.
        # (You may adjust the timeout and/or add specific waits for elements.)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception as e:
            print("Warning: network idle state not reached:", e)
        
        # Additional wait to ensure the dynamic content is rendered.
        time.sleep(5)
        
        # Retrieve the full rendered HTML content.
        content = page.content()
        
        # Save the HTML to a file for debugging purposes.
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            print("Saved full HTML to debug.html")
        
        browser.close()
        
        # Check if the content includes any unavailability markers.
        # We perform a case-insensitive check.
        content_lower = content.lower()
        if "sold out" in content_lower or "notify me" in content_lower:
            return False
        return True

def main():
    available = is_product_available()
    if available:
        print("Product is AVAILABLE!")
    else:
        print("Product is SOLD OUT or UNAVAILABLE!")

if __name__ == "__main__":
    main()
