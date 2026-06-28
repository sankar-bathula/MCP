# Trading MCP: Implementation Documentation

This document provides a comprehensive overview of the implementations, architectural decisions, and usage instructions for the AI-powered trading assistant.

## 1. System Overview
The Trading MCP is an AI-driven trading system that combines Large Language Models (LLMs) with deterministic trading strategies. It follows the Model Context Protocol (MCP) and utilizes a graph-based workflow to analyze markets and execute trades.

### Tech Stack
- **LLM:** GPT-4o (via GitHub Models endpoint)
- **Orchestration:** [LangGraph](https://langchain-ai.github.io/langgraph/)
- **API Layer:** FastAPI
- **Broker Integration:** Angel One SmartAPI
- **Database:** PostgreSQL (for trade logging and history)
- **Notifications:** Telegram Bot API
- **News Data:** Yahoo Finance (yfinance)
- **Language:** Python 3.12+

---

## 2. Key Implementations

### A. High-Conviction Trading Pipeline
The system has been upgraded from a simple pattern-detector to a strict validation pipeline. A trade is only executed and notified if it passes the following checks:

#### 1. Technical Analysis (SMC & S/R)
The agent identifies high-probability setups:
- **Market Structure Shift (MSS):** Detects trend changes by breaking recent swing highs/lows.
- **Order Blocks (OB):** Identifies high-probability entry zones.
- **Support & Resistance (S/R):** Maps recent swing points to ensure entries occur in "Value Zones."

#### 2. Real-Time News Sentiment
A dedicated **News Agent** fetches live headlines via `yfinance` and uses an LLM to:
- **Filter Impact**: Only "High Impact" market-moving news is considered.
- **Consolidate Sentiment**: Determines a global sentiment (Bullish/Bearish/Neutral) for the symbol.
- **Alignment Check**: Rejects technical signals that contradict the news sentiment (e.g., no BUYs during strong Bearish news).

#### 3. Strict Risk-to-Reward (RR) Management
Every automated trade is strictly bound to a minimum **1:2.5 Risk-to-Reward ratio**:
- **Risk**: The distance between the entry price and the Stop Loss (placed beyond S/R levels).
- **Reward**: The Target is automatically calculated as `Entry + (Risk * 2.5)` for BUYs.
- **Zone Validation**: Targets must be realistic relative to existing S/R levels.

### B. Notification System
The system uses a Telegram Bot to provide real-time alerts:
- **Trade Alerts**: Notifies the user when a high-conviction trade is executed.
- **News Alerts**: Notifies the user when a high-impact, market-moving news event is detected.

### C. Automated Execution Workflow
The system supports two distinct operating modes:

1.  **Manual Mode**: Triggered by user prompts. The LLM interprets the request and decides whether to trade.
2.  **Automated Mode (`AUTO_SCAN`)**:
    - Triggered by the keyword `AUTO_SCAN` or via the `run_automated_strategy` method.
    - Passes through the **High-Conviction Pipeline** (Technical $\rightarrow$ Sentiment $\rightarrow$ Zone $\rightarrow$ RR).

### D. Database & Logging System
A robust logging system tracks performance and maintains a trade audit trail.

- **Trade Table**: Stores `symbol`, `quantity`, `price`, `transaction_type`, `order_id`, `status`, and `timestamp`.
- **Execution Logs**: Stores the raw input/output of each node in the LangGraph workflow for debugging.

---

## 3. Configuration & Usage

### Running the Project
To start the FastAPI server:
```bash
python -m src.api.main
```

### Triggering Trades
You can interact with the system via the API or the `client_test.py` script.

**1. Manual Prompt:**
```python
test_agent("NIFTY", "The market is breaking out. Should I buy?")
```

**2. Automated High-Conviction Scan:**
```python
test_agent("NIFTY", "AUTO_SCAN")
```

### Switching Models
To change the LLM model, modify the `TradingAgent` constructor in `src/agents/trading_agent.py`.

### Checking Trade History
Use the provided utility script to view today's trades:
```bash
python check_trades.py
```

---

## 4. API Reference

| Endpoint | Method | Description | Payload |
| :--- | :--- | :--- | :--- |
| `/` | GET | Returns the frontend index.html | N/A |
| `/trade` | POST | Triggers the Trading Agent | `{"symbol": "...", "message": "..."}` |
| `/trades` | GET | Fetches all logged trades from DB | N/A |
| `/broker/profile` | GET | Fetches Angel One user profile | N/A |

---

## 5. Future Roadmap
- [ ] Integration of real-time historical data streaming.
- [ ] Multi-timeframe analysis (e.g., 15m for structure, 1m for entry).
- [ ] Implementation of a trailing stop-loss mechanism.
- [ ] Dashboard for visualizing Trade RR and Win Rate.
