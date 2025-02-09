import requests
from bs4 import BeautifulSoup

PRODUCT_URL = "https://shop.amul.com/en/product/amul-high-protein-plain-lassi-200-ml-or-pack-of-30"
UNAVAILABLE_KEYWORD = "Sold Out"

def is_available():
    try:
        response = requests.get(PRODUCT_URL, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print("Error:", e)
        return False
    soup = BeautifulSoup(response.text, "html.parser")
    page_text = soup.get_text(separator=" ", strip=True)
    # If the page DOES NOT contain the unavailable keyword, assume it's available.
    return UNAVAILABLE_KEYWORD.lower() not in page_text.lower()

if __name__ == "__main__":
    if is_available():
        # Call the IFTTT webhook to send an alert.
        # The IFTTT URL will be stored in an environment variable (see below).
        ifttt_url = os.environ.get("IFTTT_WEBHOOK_URL")
        if ifttt_url:
            payload = {"value1": "Product is now AVAILABLE!", "value2": PRODUCT_URL}
            r = requests.post(ifttt_url, json=payload)
            print("Alert sent, status code:", r.status_code)
        else:
            print("IFTTT_WEBHOOK_URL not set")
    else:
        print("Product still sold out")
