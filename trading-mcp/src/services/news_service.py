import os
import asyncio
import datetime
from typing import List
from src.agents.news_agent import NewsAgent
from src.utils.telegram_notifier import send_telegram_notification
from dotenv import load_dotenv

load_dotenv()

class NewsService:
    """
    Orchestrates the news fetching, analysis, and notification flow.
    """
    
    def __init__(self, github_api_key: str):
        self.news_agent = NewsAgent(github_api_key)

    async def run_news_cycle(self, symbols: List[str]):
        """
        Complete cycle: Fetch -> Analyze -> Notify.
        """
        print(f"[{datetime.datetime.now()}] Starting News Cycle for {symbols}...")
        
        # 1. Fetch news
        raw_news = await self.news_agent.fetch_news(symbols)
        
        # 2. Analyze impact via LLM
        high_impact_news = await self.news_agent.analyze_news_impact(raw_news)
        
        # 3. Notify via Telegram
        if not high_impact_news:
            print("No high-impact news found in this cycle.")
            return

        for news in high_impact_news:
            sentiment_emoji = {
                "Bullish": "🟢",
                "Bearish": "🔴",
                "Neutral": "🟡"
            }.get(news['sentiment'], "⚪")

            notification_payload = {
                "symbol": news['symbol'],
                "type": f"{sentiment_emoji} {news['sentiment']}",
                "quantity": "Market Moving",
                "price": news['summary']
            }
            
            # We reuse the send_telegram_notification function.
            # Note: In a real scenario, we'd create a separate 'send_news_notification' 
            # to avoid the 'Quantity' and 'Price' labels in the trade notification template.
            send_telegram_notification(notification_payload)
            
        print(f"Sent {len(high_impact_news)} news alerts to Telegram.")

async def main():
    github_api_key = os.getenv("GITHUB_API_KEY")
    if not github_api_key:
        print("GITHUB_API_KEY not found in .env")
        return

    # Symbols to monitor
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE"]
    service = NewsService(github_api_key)
    
    # Run one cycle for testing
    await service.run_news_cycle(symbols)

if __name__ == "__main__":
    asyncio.run(main())
