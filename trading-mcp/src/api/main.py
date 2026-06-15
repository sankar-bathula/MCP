from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from src.agents.trading_agent import TradingAgent
from src.broker.client import AngelOneClient
from src.db.models import SessionLocal, Trade, ExecutionLog, init_db
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Trading MCP API")

# Initialize DB on startup
@app.on_event("startup")
def startup():
    # init_db() # Uncomment when DB is ready
    pass

class TradeRequest(BaseModel):
    symbol: str
    message: str

class TradeResponse(BaseModel):
    status: str
    message: str

@app.get("/")
async def root():
    return {"message": "Welcome to Trading MCP API"}

@app.post("/trade", response_model=TradeResponse)
async def execute_trade(request: TradeRequest):
    """Triggers the LangGraph trading agent."""
    agent = TradingAgent(google_api_key=os.getenv("GOOGLE_API_KEY"))
    try:
        # Running the agent asynchronously
        # For simplicity in this demo, we just trigger it
        await agent.run(request.message)
        return {"status": "success", "message": f"Agent triggered for {request.symbol}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades")
def get_trades():
    """Fetches all trades from the database."""
    db = SessionLocal()
    trades = db.query(Trade).all()
    db.close()
    return trades

@app.get("/broker/profile")
def get_broker_profile():
    """Fetches profile from Angel One."""
    client = AngelOneClient(
        api_key=os.getenv("ANGEL_ONE_API_KEY"),
        client_id=os.getenv("ANGEL_ONE_CLIENT_ID"),
        password=os.getenv("ANGEL_ONE_PASSWORD"),
        totp_secret=os.getenv("ANGEL_ONE_TOTP_SECRET")
    )
    try:
        client.login()
        return client.get_profile()
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
