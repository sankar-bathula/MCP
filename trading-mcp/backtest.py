import os
import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from src.agents.trading_agent import TradingAgent
from dotenv import load_dotenv

load_dotenv()

async def run_backtest(symbol: str, days: int = 30):
    print(f"--- Starting Backtest for {symbol} (Last {days} Days) ---")
    
    # 1. Fetch actual historical data
    ticker_map = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "RELIANCE": "RELIANCE.NS"}
    ticker_symbol = ticker_map.get(symbol)
    if not ticker_symbol:
        print(f"No ticker mapping for {symbol}")
        return

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Download 5-minute data for high-frequency signal detection
    df = yf.download(ticker_symbol, start=start_date, end=end_date, interval="5m")
    
    if df.empty:
        print("No historical data found.")
        return

    # Convert DataFrame to the list-of-dicts format the TradingAgent expects
    # We use .values to ensure we get the scalar values if it's a single-column DataFrame
    full_history = []
    for index, row in df.iterrows():
        # Handle potential multi-index or Series types by ensuring scalar conversion
        full_history.append({
            "open": float(row['Open'].iloc[0]) if hasattr(row['Open'], 'iloc') else float(row['Open']),
            "high": float(row['High'].iloc[0]) if hasattr(row['High'], 'iloc') else float(row['High']),
            "low": float(row['Low'].iloc[0]) if hasattr(row['Low'], 'iloc') else float(row['Low']),
            "close": float(row['Close'].iloc[0]) if hasattr(row['Close'], 'iloc') else float(row['Close'])
        })

    # Initialize Agent
    agent = TradingAgent(github_api_key=os.getenv("GITHUB_API_KEY"))
    
    trades = []
    
    # Simulate a rolling window (sliding window)
    # We need at least 20 candles to detect patterns
    window_size = 20
    for i in range(window_size, len(full_history)):
        # Slice the history up to the current point in time
        current_window = full_history[i-window_size:i]
        current_price = full_history[i]['open']
        
        # Simulate the state for the agent
        state = {
            "symbol": symbol,
            "historical_data": current_window,
            "market_data": {
                "symbol": symbol,
                "current_price": current_price,
                "day_high": max(h['high'] for h in current_window),
                "day_low": min(h['low'] for h in current_window),
            },
            "messages": [HumanMessage(content="AUTO_SCAN")] # We simulate the prompt
        }
        
        # Note: TradingAgent.make_decision is async and used inside the graph.
        # To bypass the graph and test the logic directly:
        # We'll use the internal breakout pattern detection
        signal = agent._detect_breakout_patterns(symbol, current_window)
        
        if signal:
            # This is a "Virtual Trade"
            # We track it to see if it hit Target or SL first in the subsequent candles
            trade_result = {
                "entry_time": df.index[i],
                "type": signal['type'],
                "entry": signal['buy_price'],
                "sl": signal['stop_loss'],
                "tp": signal['target'],
                "outcome": "OPEN"
            }
            
            # Look ahead to see if TP or SL was hit first
            for j in range(i, len(full_history)):
                candle = full_history[j]
                if signal['type'] == "BUY":
                    if candle['low'] <= trade_result['sl']:
                        trade_result['outcome'] = "LOSS"
                        break
                    if candle['high'] >= trade_result['tp']:
                        trade_result['outcome'] = "WIN"
                        break
                else: # SELL
                    if candle['high'] >= trade_result['sl']:
                        trade_result['outcome'] = "LOSS"
                        break
                    if candle['low'] <= trade_result['tp']:
                        trade_result['outcome'] = "WIN"
                        break
            
            trades.append(trade_result)

    # Results Calculation
    if not trades:
        print("No trades were triggered during the backtest period.")
        return

    print("\n--- Detailed Trade Log ---")
    print(f"{'Entry Time':<20} | {'Type':<5} | {'Entry':<10} | {'SL':<10} | {'TP':<10} | {'Outcome':<10}")
    print("-" * 70)
    for t in trades:
        print(f"{str(t['entry_time']):<20} | {t['type']:<5} | {t['entry']:<10.2f} | {t['sl']:<10.2f} | {t['tp']:<10.2f} | {t['outcome']:<10}")
    print("-" * 70)

    wins = len([t for t in trades if t['outcome'] == "WIN"])
    losses = len([t for t in trades if t['outcome'] == "LOSS"])
    open_trades = len([t for t in trades if t['outcome'] == "OPEN"])
    win_rate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0
    
    print(f"\n--- Final Results for {symbol} ---")
    print(f"Total Signals: {len(trades)}")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Still Open: {open_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Profit Factor (approx): {(wins * 2.5) / (losses if losses > 0 else 1):.2f}")
    print("-" * 30)

# Need to import HumanMessage because we simulate the agent's input
from langchain_core.messages import HumanMessage

if __name__ == "__main__":
    asyncio.run(run_backtest("NIFTY"))
