from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from src.agents.trading_agent import TradingAgent
from src.broker.client import AngelOneClient
from src.db.models import SessionLocal, Trade, ExecutionLog, init_db
import os
import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Trading MCP API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB on startup
@app.on_event("startup")
def startup():
    try:
        init_db()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization failed: {e}")

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
    broker = AngelOneClient(
        api_key=os.getenv("ANGEL_API_KEY"),
        client_id=os.getenv("ANGEL_CLIENT_CODE"),
        password=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    
    try:
        broker.login()
    except Exception as e:
        print(f"Broker login failed: {e}. Agent will run in simulation mode.")
        broker = None

    agent = TradingAgent(github_api_key=os.getenv("GITHUB_API_KEY"), broker_client=broker)
    try:
        final_state = await agent.run(request.symbol, request.message)
        
        # Save to DB if a trade was executed
        if final_state and "order_details" in final_state and final_state["next_action"] == "execute":
            details = final_state["order_details"]
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
                print(f"DB Error: {db_e}")
            finally:
                db.close()

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
