from SmartApi import SmartConnect
import os
from dotenv import load_dotenv
import inspect

load_dotenv()

def inspect_get_candle_data():
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_CODE")
    password = os.getenv("ANGEL_PASSWORD")
    totp_secret = os.getenv("ANGEL_TOTP_SECRET")
    
    if not all([api_key, client_id, password, totp_secret]):
        print("Missing credentials in .env")
        return

    smart_api = SmartConnect(api_key=api_key)
    
    if hasattr(smart_api, 'getCandleData'):
        print("getCandleData found.")
        sig = inspect.signature(smart_api.getCandleData)
        print(f"Signature: {sig}")
    else:
        print("getCandleData NOT found.")

if __name__ == "__main__":
    inspect_get_candle_data()
