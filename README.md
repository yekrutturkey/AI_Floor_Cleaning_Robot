# AI_Floor_Cleaning_Robot

## Project Introduction

A LangChain and LangGraph based ReAct agent for floor-cleaning robot knowledge assistance, with RAG, tool calling, Chroma vector storage and a Streamlit interface.

## Features

- ReAct agent workflow for robot knowledge assistance.
- RAG retrieval over a local floor-cleaning robot knowledge base.
- Chroma vector storage for persisted document embeddings.
- Tool calling for weather, user context, report context and external records.
- Streamlit chat interface.
- GitHub content downloader utility.

## Tech Stack

- Python 3.12
- uv
- LangChain
- LangGraph
- Streamlit
- Chroma
- DashScope
- RAG
- Tool Calling

## Project Structure

```text
.
├── app.py
├── pyproject.toml
├── README.md
├── tests/
└── src/
    └── agent_item/
        ├── agent/
        ├── config/
        ├── data/
        ├── models/
        ├── prompts/
        ├── rag/
        ├── services/
        └── utils/
```

## Installation

```bash
git clone https://github.com/yekrutturkey/AI_Floor_Cleaning_Robot.git
cd AI_Floor_Cleaning_Robot
uv sync
```

## Configuration

Create a local environment file from the example before running the application.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Set the required API keys in `.env`. Do not commit real API keys, tokens or other secrets.

## Run

```bash
uv run streamlit run app.py
```

## Tests

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Notes

- The Python package name remains `agent_item`.
- Local Chroma database files are runtime artifacts and should not be committed.
- `src/agent_item/md5.txt` is generated from loaded knowledge files and may contain local cache state.
- `.env.example` is safe to commit; `.env` must remain local.
