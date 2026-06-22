import os
import datetime
from dotenv import load_dotenv
from src.agents.trading_agent import TradingAgent
from src.broker.client import AngelOneClient
from src.db.models import SessionLocal, Trade
from src.utils.email_notifier import send_trade_notification

load_dotenv()

class TradingService:
    """
    Handles the end-to-end trade execution flow:
    Broker Login -> Agent Analysis -> DB Logging -> Email Notification.
    """
    
    async def execute_trade_flow(self, symbol: str, message: str):
        # 1. Initialize Broker
        broker = AngelOneClient(
            api_key=os.getenv("ANGEL_API_KEY"),
            client_id=os.getenv("ANGEL_CLIENT_CODE"),
            password=os.getenv("ANGEL_PASSWORD"),
            totp_secret=os.getenv("ANGEL_TOTP_SECRET")
        )
        
        try:
            broker.login()
        except Exception as e:
            print(f"Broker login failed for {symbol}: {e}. Agent will run in simulation mode.")
            broker = None

        # 2. Run Trading Agent
        agent = TradingAgent(github_api_key=os.getenv("GITHUB_API_KEY"), broker_client=broker)
        try:
            final_state = await agent.run(symbol, message)
            
            # 3. Save to DB and Notify if a trade was executed
            if final_state and "order_details" in final_state and final_state["next_action"] == "execute":
                details = final_state["order_details"]
                
                # Database Log
                db = SessionLocal()
                try:
                    new_trade = Trade(
                        symbol=details.get("symbol"),
                        quantity=details.get("quantity"),
                        price=float(details.get("buy_price", 0)),
                        transaction_type=details.get("type"),
                        order_id=f"ORD_{int(datetime.datetime.now().timestamp())}",
                        status="COMPLETED"
                    )
                    db.add(new_trade)
                    db.commit()
                except Exception as db_e:
                    print(f"DB Error for {symbol}: {db_e}")
                finally:
                    db.close()

                # Email Notification
                try:
                    send_trade_notification({
                        "symbol": details.get("symbol"),
                        "quantity": details.get("quantity"),
                        "price": details.get("buy_price"),
                        "type": details.get("type")
                    })
                except Exception as mail_e:
                    print(f"Email notification error for {symbol}: {mail_e}")

            return final_state
        except Exception as e:
            print(f"Error executing trade flow for {symbol}: {e}")
            return None
