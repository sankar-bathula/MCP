# Trading MCP

An AI-powered trading assistant using Gemini Pro and LangGraph, following the Model Context Protocol (MCP).

## Stack

- **LLM:** Gemini Pro
- **Agent Framework:** [LangGraph](https://langchain-ai.github.io/langgraph/)
- **API Layer:** [FastAPI](https://fastapi.tiangolo.com/)
- **Broker:** [Angel One SmartAPI](https://smartapi.angelone.in/)
- **Database:** [PostgreSQL](https://www.postgresql.org/)
- **Cache:** [Redis](https://redis.io/)
- **Deployment:** [Microsoft Azure](https://azure.microsoft.com/)
- **Protocol:** [MCP](https://modelcontextprotocol.io/)

## Project Structure

- `src/`: Main source code
  - `api/`: FastAPI application and routes
  - `agents/`: LangGraph agents and workflows
  - `broker/`: Angel One SmartAPI integration
  - `db/`: PostgreSQL database models and migrations
  - `cache/`: Redis caching logic
- `tests/`: Unit and integration tests
- `docs/`: Documentation
