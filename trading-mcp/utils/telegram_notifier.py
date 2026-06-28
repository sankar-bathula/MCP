import httpx
import os
from dotenv import load_dotenv
import requests

load_dotenv()

def send_telegram_notification(notification_data):
    """
    Sends a Telegram notification. 
    notification_data: can be a dict with 'text' (custom message) or 
    a dict with 'symbol', 'quantity', 'price', 'type' (structured trade).
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not configured in .env. Skipping notification.")
        return False

    # If 'text' is provided, use it directly as the message
    if isinstance(notification_data, dict) and "text" in notification_data:
        message = notification_data["text"]
    # Otherwise, assume it's a structured trade and format it
    elif isinstance(notification_data, dict) and "symbol" in notification_data:
        message = (
            f"🚀 *Trade Executed!*\n\n"
            f"📦 *Symbol:* {notification_data['symbol']}\n"
            f"↕️ *Type:* {notification_data['type']}\n"
            f"🔢 *Quantity:* {notification_data['quantity']}\n"
            f"💰 *Price:* {notification_data['price']}\n\n"
            f"🤖 _Sent by Trading MCP_"
        )
    else:
        print("Invalid notification data provided.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
        
        # Log success based on symbol or custom text
        identifier = notification_data.get('symbol', 'Custom Alert') if isinstance(notification_data, dict) else 'Alert'
        print(f"Telegram notification sent successfully for {identifier}.")
        return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False

