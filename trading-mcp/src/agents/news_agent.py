import os
import json
import httpx
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()

class NewsAgent:
    """
    Agent responsible for fetching stock market news and filtering for 
    high-impact events using an LLM.
    """
    
    def __init__(self, github_api_key: str):
        self.llm = ChatOpenAI(
            model="gpt-4o", 
            api_key=github_api_key,
            base_url="https://models.inference.ai.azure.com",
            temperature=0
        )

    async def fetch_news(self, symbols: List[str]) -> List[Dict]:
        """
        Fetches latest news for the given symbols.
        In a production environment, this would use a News API (e.g., NewsAPI.org, Bloomberg, etc.).
        For this implementation, we simulate fetching news headlines.
        """
        print(f"--- Fetching news for {symbols} ---")
        
        # Simulated news data. 
        # In reality, we would use: response = await httpx.get(f"https://newsapi.org/v2/everything?q={symbol}&apiKey={...}")
        mock_news = {
            "NIFTY": [
                {"title": "RBI maintains repo rate, market reacts positively", "sentiment": "Bullish", "impact": "High"},
                {"title": "Global markets dip due to inflation concerns", "sentiment": "Bearish", "impact": "Medium"},
                {"title": "New regulatory guidelines for F&O trading announced", "sentiment": "Neutral", "impact": "High"},
            ],
            "BANKNIFTY": [
                {"title": "HDFC Bank reports stellar quarterly results", "sentiment": "Bullish", "impact": "High"},
                {"title": "Banking sector faces liquidity crunch", "sentiment": "Bearish", "impact": "Medium"},
            ],
            "RELIANCE": [
                {"title": "Reliance expands green energy portfolio", "sentiment": "Bullish", "impact": "Medium"},
                {"title": "Reliance announces new retail partnership", "sentiment": "Bullish", "impact": "Low"},
            ]
        }

        all_news = []
        for symbol in symbols:
            if symbol in mock_news:
                for item in mock_news[symbol]:
                    all_news.append({"symbol": symbol, **item})
        
        return all_news

    async def analyze_news_impact(self, news_items: List[Dict]) -> List[Dict]:
        """
        Uses LLM to filter and summarize news items, keeping only those 
        that are 'Market Moving' (High Impact).
        """
        if not news_items:
            return []

        print(f"--- Analyzing {len(news_items)} news items for impact ---")
        
        prompt = f"""
        You are a financial analyst. Analyze the following stock market news items and determine which ones are 'Market Moving' (High Impact).
        
        News Items:
        {json.dumps(news_items, indent=2)}
        
        Respond ONLY with a JSON list of objects for the high-impact news. 
        Each object should contain:
        {{
            "symbol": "symbol",
            "headline": "original headline",
            "summary": "a 1-sentence punchy summary for Telegram",
            "sentiment": "Bullish/Bearish/Neutral",
            "impact": "High"
        }}
        
        If no news is high impact, return an empty list [].
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            content = response.content.strip()
            if content.startswith("```json"): content = content[7:-3].strip()
            elif content.startswith("```"): content = content[3:-3].strip()
            
            filtered_news = json.loads(content)
            return filtered_news if isinstance(filtered_news, list) else []
        except Exception as e:
            print(f"Error analyzing news impact: {e}")
            return []
