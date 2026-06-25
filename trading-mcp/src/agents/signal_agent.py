import os
import json
from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

class SignalAgent:
    """
    Agent responsible for translating a market narrative into a 
    concrete trading signal (BUY/SELL/HOLD).
    """
    def __init__(self, github_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=github_api_key,
            base_url="https://models.inference.ai.azure.com",
            temperature=0
        )

    async def generate_signal(self, summary: str, symbol: str) -> Dict:
        """
        Analyzes a market summary to produce a trade signal.
        """
        print(f"--- Generating signal for {symbol} based on summary ---")
        
        prompt = f"""
        You are a quantitative trading signal generator. Analyze the following market summary for {symbol} and decide on a trading action.
        
        Market Summary:
        {summary}
        
        Respond ONLY with a JSON object:
        {{
            "signal": "BUY" | "SELL" | "HOLD",
            "confidence": "High" | "Medium" | "Low",
            "reason": "Brief explanation of why this signal was generated",
            "urgency": "Immediate" | "Wait for Retracement" | "None"
        }}
        
        If the summary is neutral or inconclusive, return "HOLD".
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:-3].strip()
            elif content.startswith("```"): content = content[3:-3].strip()
            
            signal_data = json.loads(content)
            return signal_data
        except Exception as e:
            print(f"Error in SignalAgent: {e}")
            return {"signal": "HOLD", "confidence": "Low", "reason": f"Error generating signal: {str(e)}", "urgency": "None"}
