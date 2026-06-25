import os
import json
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

class SummaryAgent:
    """
    Agent responsible for synthesizing multiple high-impact news items 
    into a concise, coherent market narrative.
    """
    def __init__(self, github_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=github_api_key,
            base_url="https://models.inference.ai.azure.com",
            temperature=0
        )

    async def summarize_news(self, high_impact_news: List[Dict], symbol: str) -> str:
        """
        Synthesizes high-impact news into a professional market summary.
        """
        if not high_impact_news:
            return f"No high-impact news found for {symbol} at this time."

        print(f"--- Summarizing news for {symbol} ---")
        
        prompt = f"""
        You are a senior market strategist. Your task is to synthesize the following high-impact news items for {symbol} into a concise, professional market narrative.
        
        News Items:
        {json.dumps(high_impact_news, indent=2)}
        
        The summary should:
        1. Highlight the primary driver of current price action.
        2. Note any conflicting reports.
        3. Conclude with the overall prevailing sentiment (Bullish/Bearish/Neutral).
        
        Keep it under 3 sentences. Be punchy and data-driven.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            return response.content.strip()
        except Exception as e:
            print(f"Error in SummaryAgent: {e}")
            return "Error synthesizing market news."
