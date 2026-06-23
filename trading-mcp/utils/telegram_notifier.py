import httpx
import os
from dotenv import load_dotenv

load_dotenv()

def send_telegram_notification(trade_details):
    """
    Sends a Telegram notification when a trade is executed.
    trade_details: dict containing symbol, quantity, price, and type.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("Telegram credentials not configured in .env. Skipping notification.")
        return False

    message = (
        f"🚀 *Trade Executed!*

"
        f"📦 *Symbol:* {trade_details['symbol']}
"
        f"↕️ *Type:* {trade_details['type']}
"
        f"🔢 *Quantity:* {trade_details['quantity']}
"
        f"💰 *Price:* {trade_details['price']}

"
        f"🤖 _Sent by Trading MCP_"
    )

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
        print(f"Telegram notification sent successfully for {trade_details['symbol']}.")
        return True
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
        return False
