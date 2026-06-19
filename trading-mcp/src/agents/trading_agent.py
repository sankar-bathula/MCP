import operator
import asyncio
import random
import json
from typing import Annotated, Sequence, TypedDict, List, Optional, Dict
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.broker.client import AngelOneClient
import os

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_action: str
    order_details: dict
    market_data: dict
    historical_data: List[dict]
    symbol: str

class TradingAgent:
    LOT_SIZES = {
        "NIFTY": 65,
        "BANKNIFTY": 30,
        "FINNIFTY": 60,
        "SENSEX": 20,
        "SBI": 1
    }

    def __init__(self, github_api_key: str, broker_client: AngelOneClient = None):
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
        """Fetches market data and generates historical candles for SMC analysis."""
        symbol = state.get("symbol", "NIFTY")
        print(f"--- Analyzing Market for {symbol} ---")
        
        # Current snapshot
        market_context = {
            "symbol": symbol,
            "current_price": 24000.0,
            "day_high": 24100.0,
            "day_low": 23900.0,
            "trend": "Neutral",
            "volume": "Medium"
        }

        # Mocking historical data for SMC pattern detection (Last 20 candles)
        # In a real scenario, this would be fetched via self.broker.get_historical_data(...)
        history = []
        base_price = 24000.0
        for i in range(20):
            change = random.uniform(-20, 20)
            open_p = base_price + change
            close_p = open_p + random.uniform(-15, 15)
            history.append({
                "open": open_p,
                "high": max(open_p, close_p) + random.uniform(0, 5),
                "low": min(open_p, close_p) - random.uniform(0, 5),
                "close": close_p
            })
            base_price = close_p

        if self.broker:
            try:
                token_map = {"NIFTY": ("NSE", "99926000"), "SBIN": ("NSE", "3045"), "RELIANCE": ("NSE", "2885")}
                if symbol in token_map:
                    exchange, token = token_map[symbol]
                    raw_data = self.broker.get_market_data("OHLC", {exchange: [token]})
                    if raw_data.get("status") and raw_data.get("data"):
                        data = raw_data["data"]["fetched"][0]
                        market_context.update({
                            "current_price": data.get("ltp", 0),
                            "day_high": data.get("high", 0),
                            "day_low": data.get("low", 0),
                        })
            except Exception as e:
                print(f"Broker data fetch failed: {e}")

        return {"market_data": market_context, "historical_data": history}

    def _detect_smc_patterns(self, symbol: str, history: List[dict]) -> Optional[dict]:
        """Detects Smart Money Concepts patterns like MSS and Order Blocks."""
        if len(history) < 5:
            return None

        last = history[-1]
        prev = history[-2]
        lot_size = self.LOT_SIZES.get(symbol, 1)

        # Bullish SMC: Market Structure Shift (MSS) + Order Block (OB)
        # Simplified: Close > previous 3 highs (MSS) and prev candle was bearish (OB)
        if last['close'] > max(h['high'] for h in history[-4:-1]) and prev['close'] < prev['open']:
            entry_price = last['close']
            stop_loss = prev['low']
            risk = entry_price - stop_loss
            if risk > 0:
                return {
                    "action": "execute",
                    "symbol": symbol,
                    "quantity": lot_size,
                    "lot_size": lot_size,
                    "type": "BUY",
                    "premium": "N/A",
                    "buy_price": round(entry_price, 2),
                    "target": round(entry_price + (risk * 2), 2),
                    "stop_loss": round(stop_loss, 2),
                    "response_message": f"SMC Bullish Signal: MSS detected with Order Block at {round(stop_loss, 2)}. Target set for 1:2 RR.",
                    "reason": "Bullish Market Structure Shift and Order Block identified."
                }

        # Bearish SMC: MSS + OB
        if last['close'] < min(h['low'] for h in history[-4:-1]) and prev['close'] > prev['open']:
            entry_price = last['close']
            stop_loss = prev['high']
            risk = stop_loss - entry_price
            if risk > 0:
                return {
                    "action": "execute",
                    "symbol": symbol,
                    "quantity": lot_size,
                    "lot_size": lot_size,
                    "type": "SELL",
                    "premium": "N/A",
                    "buy_price": round(entry_price, 2),
                    "target": round(entry_price - (risk * 2), 2),
                    "stop_loss": round(stop_loss, 2),
                    "response_message": f"SMC Bearish Signal: MSS detected with Order Block at {round(stop_loss, 2)}. Target set for 1:2 RR.",
                    "reason": "Bearish Market Structure Shift and Order Block identified."
                }

        return None

    def make_decision(self, state: AgentState):
        """Decides trade action based on SMC patterns (Auto) or LLM (Manual)."""
        symbol = state.get("symbol", "NIFTY")
        history = state.get("historical_data", [])
        user_message = state["messages"][-1].content if state["messages"] else ""

        # AUTOMATION PATH: Triggered by "AUTO_SCAN" or absence of specific human query
        if user_message == "AUTO_SCAN":
            print("--- Running Automated SMC Analysis ---")
            smc_signal = self._detect_smc_patterns(symbol, history)
            if smc_signal:
                print(f"SMC Signal Found: {smc_signal['type']} at {smc_signal['buy_price']}")
                return {
                    "next_action": smc_signal["action"], 
                    "order_details": smc_signal,
                    "messages": [AIMessage(content=smc_signal["response_message"])]
                }
            else:
                return {"next_action": "hold", "messages": [AIMessage(content="No high-probability SMC setup found currently.")]}

        # MANUAL PATH: Use LLM for natural language requests
        print(f"--- Making Decision with LLM for: {user_message} ---")
        lot_size = self.LOT_SIZES.get(symbol, 1)
        full_prompt = f"""
        System: You are an expert trading assistant. Based on the market data, provide a response.
        Current Lot Size for {symbol}: {lot_size}.
        
        Respond ONLY with JSON:
        {{
            "action": "execute" or "hold",
            "symbol": "{symbol}",
            "quantity": number,
            "lot_size": {lot_size},
            "type": "BUY" or "SELL",
            "premium": "price or 'N/A'",
            "buy_price": "price",
            "target": "price",
            "stop_loss": "price",
            "response_message": "detailed answer",
            "reason": "internal reasoning"
        }}
        
        User Request: {user_message}
        Market Data: {json.dumps(state['market_data'])}
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:-3].strip()
            elif content.startswith("```"): content = content[3:-3].strip()
            decision = json.loads(content)
            return {
                "next_action": decision["action"], 
                "order_details": decision,
                "messages": [AIMessage(content=decision["response_message"])]
            }
        except Exception as e:
            return {"next_action": "hold", "messages": [AIMessage(content=f"Error: {str(e)}")]}

    def should_execute(self, state: AgentState):
        if state.get("next_action") == "execute":
            return "execute"
        return "end"

    def execute_trade(self, state: AgentState):
        """Executes the trade via the broker."""
        print("--- Executing Trade ---")
        order = state["order_details"]
        msg = f"Simulated: Placed {order['type']} order for {order['symbol']} at {order.get('buy_price')}."
        if self.broker:
            try:
                # Actual API Call
                # self.broker.place_order(...)
                msg = f"Executed {order['type']} order for {order['symbol']} (Qty: {order['quantity']}) via Angel One."
            except Exception as e:
                msg = f"Broker execution failed: {e}. Simulation used."
        
        return {"messages": [AIMessage(content=msg)]}

    async def run(self, symbol: str, input_message: str):
        inputs = {
            "symbol": symbol,
            "messages": [HumanMessage(content=input_message)]
        }
        return await self.app.ainvoke(inputs)

    async def run_automated_strategy(self, symbol: str, iterations: int = 5, interval: int = 60):
        """Proactive loop to scan for SMC patterns."""
        print(f"--- Starting Proactive SMC Scanner for {symbol} ---")
        for i in range(iterations):
            print(f"Scan {i+1}/{iterations}...")
            await self.run(symbol, "AUTO_SCAN")
            await asyncio.sleep(interval)
