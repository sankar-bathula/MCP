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
    """Triggers the LangGraph trading agent."""
    # Initialize Broker Client
    broker = AngelOneClient(
        api_key=os.getenv("ANGEL_API_KEY"),
        client_id=os.getenv("ANGEL_CLIENT_CODE"),
        password=os.getenv("ANGEL_PASSWORD"),
        totp_secret=os.getenv("ANGEL_TOTP_SECRET")
    )
    
    try:
        print("Logging into broker...")
        broker.login()
    except Exception as e:
        print(f"Broker login failed: {e}. Agent will run in simulation mode.")
        broker = None

    agent = TradingAgent(github_api_key=os.getenv("GITHUB_API_KEY"), broker_client=broker)
    try:
        # Running the agent asynchronously
        final_state = await agent.run(request.symbol, request.message)
        
        # Collect all AI messages from this run
        # Since we use operator.add, the final_state contains the full history.
        # We want the messages after the last HumanMessage (which we just sent).
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
    db = SessionLocal()
    trades = db.query(Trade).all()
    db.close()
    return trades

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
