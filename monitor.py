import os
import requests
from bs4 import BeautifulSoup

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
UNAVAILABLE_KEYWORD = "Sold Out"

# Function to check product availability
def is_available():
    try:
        response = requests.get(PRODUCT_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("Error:", e)
        return False
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True)
    return UNAVAILABLE_KEYWORD.lower() not in page_text.lower()

# Function to send Telegram notification
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
        # Retrieve your bot token and chat ID from environment variables
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if bot_token and chat_id:
            send_telegram_message("Product is now AVAILABLE!\n" + PRODUCT_URL, bot_token, chat_id)
        else:
            print("Telegram credentials not set.")
    else:
        print("Product is still sold out.")
