import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv()

def send_trade_notification(trade_details):
    """
    Sends an email notification when a trade is executed.
    trade_details: dict containing symbol, quantity, price, and type.
    """
    sender_email = os.getenv("EMAIL_SENDER")
    sender_password = os.getenv("EMAIL_PASSWORD")
    receiver_email = os.getenv("EMAIL_RECEIVER")
    smtp_server = os.getenv("EMAIL_SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_SMTP_PORT", "587"))

    if not sender_email or not sender_password or not receiver_email:
        print("Email credentials not configured in .env. Skipping notification.")
        return False

    subject = f"Trade Executed: {trade_details['symbol']} {trade_details['type']}"
    
    # Create a professional HTML email body
    body = f"""
    <html>
      <body style='font-family: Arial, sans-serif;'>
        <h2 style='color: #2c3e50;'>Trade Execution Notification</h2>
        <p>A new trade has been executed by the Trading MCP agent.</p>
        <table style='border-collapse: collapse; width: 300px;'>
          <tr>
            <td style='padding: 8px; border: 1px solid #ddd;'><b>Symbol:</b></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>{trade_details['symbol']}</td>
          </tr>
          <tr>
            <td style='padding: 8px; border: 1px solid #ddd;'><b>Type:</b></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>{trade_details['type']}</td>
          </tr>
          <tr>
            <td style='padding: 8px; border: 1px solid #ddd;'><b>Quantity:</b></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>{trade_details['quantity']}</td>
          </tr>
          <tr>
            <td style='padding: 8px; border: 1px solid #ddd;'><b>Price:</b></td>
            <td style='padding: 8px; border: 1px solid #ddd;'>{trade_details['price']}</td>
          </tr>
        </table>
        <p style='margin-top: 20px;'>This is an automated message from your Trading MCP.</p>
      </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print(f"Email notification sent successfully for {trade_details['symbol']}.")
        return True
    except Exception as e:
        print(f"Failed to send email notification: {e}")
        return False
