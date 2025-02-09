import os
import requests
from bs4 import BeautifulSoup

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"

def is_available():
    try:
        response = requests.get(PRODUCT_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("Error fetching product page:", e)
        # If there’s a problem fetching the page, assume product is unavailable.
        return False

    soup = BeautifulSoup(response.text, "html.parser")
    
    # --- Approach 1: Check the product section near the title ---
    # Find the product title container (assuming it’s in a header tag)
    title_container = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3"] and 
                    "amul high protein plain lassi" in tag.get_text(strip=True).lower()
    )
    if title_container and title_container.parent:
        # Check the parent container's text for unavailability keywords
        parent_text = title_container.parent.get_text(separator=" ", strip=True).lower()
        if "sold out" in parent_text or "out of stock" in parent_text:
            print("Detected 'sold out' or 'out of stock' in the main product container.")
            return False

    # --- Approach 2: Look for a 'Notify Me' button ---
    # On this website, when the product is unavailable, a "Notify Me" button is shown.
    notify_me = soup.find(
        lambda tag: tag.name in ["button", "a"] and 
                    "notify me" in tag.get_text(strip=True).lower()
    )
    if notify_me:
        print("Detected 'Notify Me' button; product is unavailable.")
        return False

    # If neither indicator is found, assume the product is available.
    print("No unavailability indicators detected; product appears to be available.")
    return True

def send_telegram_message(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        print("Telegram response:", response.status_code, response.text)
    except Exception as e:
        print("Error sending Telegram message:", e)

if __name__ == "__main__":
    if is_available():
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            send_telegram_message("Product is now AVAILABLE!\n" + PRODUCT_URL, bot_token, chat_id)
        else:
            print("Telegram credentials not set.")
    else:
        print("Product is sold out or unavailable.")
