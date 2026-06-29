from SmartApi import SmartConnect
import os
from dotenv import load_dotenv

load_dotenv()

def inspect_smartconnect():
    api_key = os.getenv("ANGEL_API_KEY")
    client_id = os.getenv("ANGEL_CLIENT_CODE")
    password = os.getenv("ANGEL_PASSWORD")
    totp_secret = os.getenv("ANGEL_TOTP_SECRET")
    
    if not all([api_key, client_id, password, totp_secret]):
        print("Missing credentials in .env")
        return

    smart_api = SmartConnect(api_key=api_key)
    # We don't actually need to login to inspect methods, but let's see if we can.
    # However, for just inspection, dir() is enough.
    
    print("Methods in SmartConnect:")
    for method in dir(smart_api):
        if not method.startswith("_"):
            print(method)

if __name__ == "__main__":
    inspect_smartconnect()
