from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.agents.trading_agent import TradingAgent
from src.broker.client import AngelOneClient
from src.db.models import SessionLocal, Trade, ExecutionLog, init_db
from src.services.trading_service import TradingService
from src.utils.email_notifier import send_trade_notification
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Trading MCP API")
trading_service = TradingService()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def perform_scheduled_scan(scan_symbols: List[str], service: TradingService):
    """Task to be run by the scheduler for continuous scanning."""
    print(f"[{datetime.datetime.now()}] Starting scheduled market scan...")
    for symbol in scan_symbols:
        print(f"Scanning {symbol}...")
        try:
            await service.execute_trade_flow(symbol, "AUTO_SCAN")
        except Exception as e:
            print(f"Error during scheduled scan for {symbol}: {e}")
    print(f"[{datetime.datetime.now()}] Scheduled market scan completed.")

# Initialize DB on startup
@app.on_event("startup")
async def startup():
    # Initialize DB
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")

    # Initialize Scheduler
    scheduler = AsyncIOScheduler()
    
    scan_symbols_str = os.getenv("SCAN_SYMBOLS", "")
    scan_symbols = [s.strip() for s in scan_symbols_str.split(",") if s.strip()]
    scan_interval = int(os.getenv("SCAN_INTERVAL_MINUTES", "15"))

    if scan_symbols:
        print(f"Starting continuous scanner for: {scan_symbols} every {scan_interval} minutes.")
        scheduler.add_job(perform_scheduled_scan, 'interval', minutes=scan_interval, args=[scan_symbols, trading_service])
        scheduler.start()
    else:
        print("No symbols configured for continuous scanning. Background scheduler not started.")

class TradeRequest(BaseModel):
    symbol: str
    message: str

class TradeResponse(BaseModel):
    status: str
    message: str

@app.get("/")
async def root():
    return FileResponse("src/api/index.html")

@app.post("/trade", response_model=TradeResponse)
async def execute_trade(request: TradeRequest):
    """Triggers the LangGraph trading agent and logs the trade to DB."""
    try:
        final_state = await trading_service.execute_trade_flow(request.symbol, request.message)
        
        if not final_state:
             raise HTTPException(status_code=500, detail="Agent execution failed.")

        agent_messages = []
        if final_state and "messages" in final_state:
            for msg in reversed(final_state["messages"]):
                if isinstance(msg, HumanMessage):
                    break
                if isinstance(msg, AIMessage):
                    agent_messages.insert(0, msg.content)
        
        agent_response = "\n\n".join(agent_messages) if agent_messages else "No response from agent."
        return {"status": "success", "message": agent_response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
def get_trades():
    """Fetches all trades from the database."""
    try:
        db = SessionLocal()
        trades = db.query(Trade).all()
        # Convert SQLAlchemy objects to dicts for JSON response
        trade_list = [
            {
                "id": t.id,
                "symbol": t.symbol,
                "quantity": t.quantity,
                "price": t.price,
                "transaction_type": t.transaction_type,
                "order_id": t.order_id,
                "status": t.status,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None
            }
            for t in trades
        ]
        db.close()
        return trade_list
    except Exception as e:
        print(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/broker/profile")
def get_broker_profile():
    """Fetches profile from Angel One."""
    client = AngelOneClient(
        api_key=os.getenv("ANGEL_API_KEY"),
        client_id=os.getenv("ANGEL_CLIENT_CODE"),
        password=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    try:
        client.login()
        return client.get_profile()
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
