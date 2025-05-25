import requests
from urllib.parse import quote_plus

def send_whatsapp_message(phone: str, api_key: str, message: str) -> bool:
    """
    Send a WhatsApp message using CallMeBot.
    """
    encoded_message = quote_plus(message)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={api_key}"

    print(f"[DEBUG] Request URL: {url}")

    try:
        response = requests.get(url)
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text}")

        if response.status_code == 200:
            print(f"[OK] Message sent to {phone}")
            return True
        else:
            print(f"[ERROR] Failed to send message: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"[EXCEPTION] Error during request: {e}")
        return False
