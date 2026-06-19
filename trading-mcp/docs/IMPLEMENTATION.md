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
- **Language:** Python 3.12+

---

## 2. Key Implementations

### A. Smart Money Concepts (SMC) Logic
The system has been upgraded from a simple prompt-responder to a proactive trading agent using SMC.

#### Pattern Detection (`_detect_smc_patterns`)
The agent analyzes historical candle data to identify high-probability setups:
- **Market Structure Shift (MSS):** Occurs when the price breaks the recent swing highs (for bullish) or lows (for bearish), signaling a change in trend.
- **Order Blocks (OB):** Identifies the last opposing candle before a strong impulsive move that caused the MSS. This area is treated as a high-probability entry zone.
- **Fair Value Gaps (FVG):** (Conceptual) used to identify price imbalances.

#### Risk-to-Reward (RR) Management
Every automated trade is strictly bound to a minimum **1:2 Risk-to-Reward ratio**:
- **Risk:** The distance between the entry price and the Stop Loss (placed at the edge of the Order Block).
- **Reward:** The Target price is automatically calculated as `Entry + (Risk * 2)` for BUYs and `Entry - (Risk * 2)` for SELLs.

### B. Automated Execution Workflow
The system supports two distinct operating modes:

1.  **Manual Mode:** Triggered by user prompts. The LLM interprets the request and decides whether to trade.
2.  **Automated Mode (`AUTO_SCAN`):**
    - Triggered by the keyword `AUTO_SCAN` or via the `run_automated_strategy` method.
    - Bypasses the LLM for the decision phase and uses the deterministic SMC logic.
    - Ensures execution is based on technical patterns rather than LLM "sentiment."

### C. Database & Logging System
A robust logging system has been implemented to track performance and maintain a trade audit trail.

- **Trade Table:** Stores `symbol`, `quantity`, `price`, `transaction_type`, `order_id`, `status`, and `timestamp`.
- **Execution Logs:** Stores the raw input/output of each node in the LangGraph workflow for debugging.
- **Schema Sync:** The system uses SQLAlchemy to ensure the PostgreSQL schema matches the application models.

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

**2. Automated SMC Scan:**
```python
test_agent("NIFTY", "AUTO_SCAN")
```

### Switching Models
To change the LLM model, modify the `TradingAgent` constructor in `src/agents/trading_agent.py`:
```python
self.llm = ChatOpenAI(
    model="gpt-4o", # Change to "gpt-4o-mini" or other supported models
    api_key=github_api_key,
    base_url="https://models.inference.ai.azure.com",
    temperature=0
)
```

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
