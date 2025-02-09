import os
import requests
import logging
from bs4 import BeautifulSoup

# Configure logging to output timestamp, log level, and message.
logging.basicConfig(
    level=logging.DEBUG, 
    format="%(asctime)s [%(levelname)s] %(message)s",
)

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"

def is_available():
    logging.info("Fetching product page: %s", PRODUCT_URL)
    try:
        response = requests.get(PRODUCT_URL, timeout=10)
        response.raise_for_status()
        logging.debug("Fetched page successfully. Response length: %d", len(response.text))
    except Exception as e:
        logging.error("Error fetching product page: %s", e)
        # If there’s an error, treat the product as unavailable.
        return False

    soup = BeautifulSoup(response.text, "html.parser")

    # --- Approach 1: Check near the product title ---
    title_container = soup.find(
        lambda tag: tag.name in ["h1", "h2", "h3"] and 
                    "amul high protein plain lassi" in tag.get_text(strip=True).lower()
    )
    if title_container and title_container.parent:
        parent_text = title_container.parent.get_text(separator=" ", strip=True).lower()
        logging.debug("Parent container text snippet: %s", parent_text[:200])
        if "sold out" in parent_text or "out of stock" in parent_text:
            logging.info("Detected unavailability keywords in the main product container.")
            return False

    # --- Approach 2: Look for a 'Notify Me' button ---
    notify_me = soup.find(
        lambda tag: tag.name in ["button", "a"] and 
                    "notify me" in tag.get_text(strip=True).lower()
    )
    if notify_me:
        logging.info("Detected 'Notify Me' button; product is unavailable.")
        return False

    logging.info("No unavailability indicators detected; product appears to be available.")
    return True

def send_telegram_message(message, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        response = requests.post(url, data=payload)
        logging.debug("Telegram response: %s - %s", response.status_code, response.text)
    except Exception as e:
        logging.error("Error sending Telegram message: %s", e)

if __name__ == "__main__":
    available = is_available()
    logging.info("Final availability status: %s", "AVAILABLE" if available else "SOLD OUT")
    
    if available:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            send_telegram_message("Product is now AVAILABLE!\n" + PRODUCT_URL, bot_token, chat_id)
        else:
            logging.error("Telegram credentials not set.")
    else:
        logging.info("Product is sold out or unavailable.")
