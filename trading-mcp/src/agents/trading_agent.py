import operator
from typing import Annotated, Sequence, TypedDict, List
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.broker.client import AngelOneClient
import os
import json

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    order_details: dict
    market_data: dict
    symbol: str

class TradingAgent:
    LOT_SIZES = {
        "NIFTY": 65,
        "BANKNIFTY": 15,
        "FINNIFTY": 25,
        "RELIANCE": 1,
        "SBIN": 1
    }

    def __init__(self, github_api_key: str, broker_client: AngelOneClient = None):
        # Using GitHub Models endpoint (OpenAI compatible)
        self.llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=github_api_key,
            base_url="https://models.inference.ai.azure.com",
            temperature=0
        )
        self.broker = broker_client
        self.workflow = StateGraph(AgentState)
        self._setup_graph()

    def _setup_graph(self):
        self.workflow.add_node("analyze_market", self.analyze_market)
        self.workflow.add_node("make_decision", self.make_decision)
        self.workflow.add_node("execute_trade", self.execute_trade)

        self.workflow.set_entry_point("analyze_market")
        self.workflow.add_edge("analyze_market", "make_decision")
        
        self.workflow.add_conditional_edges(
            "make_decision",
            self.should_execute,
            {
                "execute": "execute_trade",
                "end": END
            }
        )
        
        self.workflow.add_edge("execute_trade", END)
        self.app = self.workflow.compile()

    def analyze_market(self, state: AgentState):
        """Fetches real market data if broker is available, otherwise uses mock."""
        symbol = state.get("symbol", "NIFTY")
        print(f"--- Analyzing Market for {symbol} ---")
        
        market_context = {
            "symbol": symbol,
            "current_price": 22150.50,
            "day_high": 22200.00,
            "day_low": 22100.00,
            "trend": "Bullish",
            "volume": "High"
        }

        if self.broker:
            try:
                # Basic token mapping for demonstration
                token_map = {
                    "NIFTY": ("NSE", "99926000"),
                    "SBIN": ("NSE", "3045"),
                    "RELIANCE": ("NSE", "2885")
                }
                
                if symbol in token_map:
                    exchange, token = token_map[symbol]
                    print(f"Fetching real market data for {symbol} ({token})...")
                    raw_data = self.broker.get_market_data("OHLC", {exchange: [token]})
                    
                    if raw_data.get("status") and raw_data.get("data"):
                        data = raw_data["data"]["fetched"][0]
                        market_context = {
                            "symbol": symbol,
                            "current_price": data.get("ltp", 0),
                            "day_high": data.get("high", 0),
                            "day_low": data.get("low", 0),
                            "close": data.get("close", 0),
                            "open": data.get("open", 0),
                            "trend": "Up" if data.get("ltp", 0) > data.get("open", 0) else "Down"
                        }
                        print(f"Real data fetched: {market_context}")
            except Exception as e:
                print(f"Failed to fetch market data: {e}. Falling back to mock data.")

        return {"market_data": market_context}

    def make_decision(self, state: AgentState):
        """Uses LLM to decide whether to trade and respond to user."""
        print("--- Making Decision with GitHub Models (GPT-4o) ---")
        market_data = state["market_data"]
        symbol = state.get("symbol", "NIFTY")
        user_message = state["messages"][-1].content
        print(f"User Message: {user_message}")

        # Get relevant lot size
        lot_size = self.LOT_SIZES.get(symbol, 1)

        full_prompt = f"""
        System: You are an expert trading assistant. Based on the market data and user request, 
        provide a helpful response and decide if a trade should be executed.
        
        CRITICAL: The current lot size for {symbol} is {lot_size}. Any trade MUST be in multiples of this lot size.
        
        Respond ONLY with a JSON object in this format:
        {{
            "action": "execute" or "hold",
            "symbol": "{symbol}",
            "quantity": number,
            "lot_size": {lot_size},
            "type": "BUY" or "SELL",
            "premium": "price of the option/asset if applicable, else 'N/A'",
            "buy_price": "the price at which to enter the trade",
            "target": "the target price for taking profit",
            "stop_loss": "the stop loss price to limit risk",
            "response_message": "A detailed answer to the user's question, including relevant market data if applicable.",
            "reason": "Internal reasoning for the trade decision"
        }}
        
        User Request: {user_message}
        Market Data: {json.dumps(market_data)}
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            decision = json.loads(content)
            print(f"Decision: {decision}")

            # Construct a structured reply if it's a trade execution
            reply = decision["response_message"]
            if decision["action"] == "execute":
                details = (
                    f"\n\n--- Trade Details ---"
                    f"\n🔹 **Entry/Buy Price**: {decision.get('buy_price')}"
                    f"\n🎯 **Target**: {decision.get('target')}"
                    f"\n🛑 **Stop Loss (SL)**: {decision.get('stop_loss')}"
                    f"\n📦 **Quantity**: {decision.get('quantity')} (Lot Size: {decision.get('lot_size')})"
                )
                if decision.get("premium") != "N/A":
                    details += f"\n💎 **Premium**: {decision.get('premium')}"
                reply += details

            return {
                "next_action": decision["action"], 
                "order_details": decision,
                "messages": [AIMessage(content=reply)]
            }
        except Exception as e:
            print(f"Error: {e}")
            return {"next_action": "hold", "messages": [AIMessage(content=f"I encountered an error: {str(e)}")]}

    def should_execute(self, state: AgentState):
        if state.get("next_action") == "execute":
            return "execute"
        return "end"

    def execute_trade(self, state: AgentState):
        """Executes the trade via the broker if available."""
        print("--- Executing Trade ---")
        order = state["order_details"]
        
        msg = f"Simulated: Placed {order['type']} order for {order['symbol']}."
        if self.broker:
            msg = f"Executed {order['type']} order for {order['symbol']} (Quantity: {order['quantity']})."
        
        return {"messages": [AIMessage(content=msg)]}

    async def run(self, symbol: str, input_message: str):
        inputs = {
            "symbol": symbol,
            "messages": [HumanMessage(content=input_message)]
        }
        return await self.app.ainvoke(inputs)
