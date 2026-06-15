from typing import Annotated, Sequence, TypedDict, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import os

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    next_action: str
    order_details: dict
    market_data: dict

class TradingAgent:
    def __init__(self, google_api_key: str):
        self.llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=google_api_key)
        self.workflow = StateGraph(AgentState)
        self._setup_graph()

    def _setup_graph(self):
        # Define the nodes
        self.workflow.add_node("analyze_market", self.analyze_market)
        self.workflow.add_node("make_decision", self.make_decision)
        self.workflow.add_node("execute_trade", self.execute_trade)

        # Set the entry point
        self.workflow.set_entry_point("analyze_market")

        # Define the edges
        self.workflow.add_edge("analyze_market", "make_decision")
        
        # Conditional edge for decision
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
        """Node for analyzing market data."""
        # Logic to fetch and analyze data would go here
        print("--- Analyzing Market ---")
        return {"market_data": {"symbol": "NIFTY", "price": 22000}}

    def make_decision(self, state: AgentState):
        """Node for making a trading decision using LLM."""
        print("--- Making Decision ---")
        # In a real scenario, we'd pass market data to the LLM
        # For now, we simulate a decision
        return {"next_action": "execute", "order_details": {"symbol": "NIFTY", "quantity": 1, "type": "BUY"}}

    def should_execute(self, state: AgentState):
        """Conditional logic to decide whether to execute a trade."""
        if state.get("next_action") == "execute":
            return "execute"
        return "end"

    def execute_trade(self, state: AgentState):
        """Node for executing the trade via the broker."""
        print("--- Executing Trade ---")
        # Integration with AngelOneClient would happen here
        return {"messages": [AIMessage(content="Order executed successfully.")]}

    async def run(self, input_message: str):
        inputs = {"messages": [HumanMessage(content=input_message)]}
        async for output in self.app.astream(inputs):
            for key, value in output.items():
                print(f"Output from node '{key}':")
                print("---")
                print(value)
            print("\n---\n")
