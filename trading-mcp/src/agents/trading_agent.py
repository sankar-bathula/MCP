from typing import Annotated, Sequence, TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from src.broker.client import AngelOneClient
import os
import json

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    next_action: str
    order_details: dict
    market_data: dict
    symbol: str

class TradingAgent:
    def __init__(self, google_api_key: str, broker_client: AngelOneClient = None):
        # Use gemini-2.0-flash which is confirmed available
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", 
            google_api_key=google_api_key,
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
        
        # In a real scenario, we'd use self.broker.get_market_data(symbol)
        # For now, we simulate data that the LLM will process
        market_context = {
            "symbol": symbol,
            "current_price": 22150.50,
            "day_high": 22200.00,
            "day_low": 22100.00,
            "trend": "Bullish",
            "volume": "High"
        }
        return {"market_data": market_context}

    def make_decision(self, state: AgentState):
        """Uses Gemini Pro to decide whether to trade based on market data."""
        print("--- Making Decision with Gemini Pro ---")
        market_data = state["market_data"]
        # Ensure messages exist and have content
        if not state["messages"] or not state["messages"][-1].content:
             print("Error: No message content found for LLM.")
             return {"next_action": "hold", "messages": [AIMessage(content="No user message provided.")]}
             
        user_message = state["messages"][-1].content
        print(f"User Message: {user_message}")

        full_prompt = f"""
        System: You are an expert trading assistant. Based on the following market data and user request, 
        decide if a trade should be executed.
        
        Respond ONLY with a JSON object in this format:
        {{
            "action": "execute" or "hold",
            "symbol": "string",
            "quantity": number,
            "type": "BUY" or "SELL",
            "reason": "short explanation"
        }}
        
        User Request: {user_message}
        Market Data: {json.dumps(market_data)}
        """
        
        try:
            print("Invoking LLM with merged prompt...")
            response = self.llm.invoke([HumanMessage(content=full_prompt)])
            print(f"LLM Raw Response: {response.content}")
            
            # Clean up response content if it contains markdown formatting
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()
                
            decision = json.loads(content)
            print(f"Decision: {decision}")
            return {
                "next_action": decision["action"], 
                "order_details": decision,
                "messages": [AIMessage(content=f"Decision: {decision['action']}. Reason: {decision.get('reason')}")]
            }
        except Exception as e:
            print(f"Error during LLM invocation or parsing: {e}")
            return {"next_action": "hold", "messages": [AIMessage(content=f"Error: {str(e)}")]}

    def should_execute(self, state: AgentState):
        if state.get("next_action") == "execute":
            return "execute"
        return "end"

    def execute_trade(self, state: AgentState):
        """Executes the trade via the broker if available."""
        print("--- Executing Trade ---")
        order = state["order_details"]
        
        if self.broker:
            # result = self.broker.place_order(...)
            return {"messages": [AIMessage(content=f"Executed {order['type']} order for {order['symbol']} (Quantity: {order['quantity']})")]}
        
        return {"messages": [AIMessage(content="Broker not connected. Simulation: Order placed.")]}

    async def run(self, symbol: str, input_message: str):
        inputs = {
            "symbol": symbol,
            "messages": [HumanMessage(content=input_message)]
        }
        final_state = None
        async for output in self.app.astream(inputs):
            for key, value in output.items():
                print(f"Node '{key}' completed.")
                # The output contains the updates from the node
                if not final_state:
                    final_state = inputs.copy()
                final_state.update(value)
            print("---")
        return final_state
