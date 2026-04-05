# AIML Nexus - Synthetic Agent Orchestrator

AIML Nexus is a state-of-the-art multi-agent academic platform that natively queries, audits, and presents database metrics using a sleek glassmorphic frontend UI and an incredibly fast backend Orchestrator powered by LLaMA and DeepSeek.

## 🚀 Quick Start Guide

You must run both the Backend Orchestrator and the Frontend React Server simultaneously in two separate terminals.

### 1. Start the FastAPI Backend (Terminal 1)

The backend orchestrates all AI sub-agents (SQL Generation, Auditing, Table Pruning).

1. Open PowerShell and navigate to the `synthetic-agent` folder.
2. create your Python Virtual Environment and install requirements.
3. Export your NVIDIA API Key (or OpenAI key).
4. Run the Uvicorn server.

```powershell
cd E:\7th sem\LLM\new\nexus-AgenticAI\synthetic-agent
.\venv\Scripts\Activate.ps1
$env:NVIDIA_API_KEY="nvapi-your-key-here"
uvicorn main:app --reload --port 8000
```
> *(The server will start successfully at `http://127.0.0.1:8000`)*

### 2. Start the React Frontend (Terminal 2)

The frontend is a beautiful interface that streams your requests securely to the backend.

1. Open a **new** PowerShell tab.
2. Navigate to the `frontend` folder.
3. Start the node server.

```powershell
cd E:\7th sem\LLM\new\nexus-AgenticAI\frontend
npm start
```

Your browser will automatically open `http://localhost:3000`. 
Log in, head to the Dashboard, and start conversing with the AIML Nexus assistants!

---

## 🛠️ Architecture Highlights
- **Direct Async Engine**: Replaced legacy synchronous blocking wrappers (like CrewAI loops) with raw native `AsyncOpenAI` for blistering fast execution speeds under 1 second.
- **SQL Guardrails & Auditing**: Before any query executes, the pipeline rigidly blocks disruptive commands (UPDATE, DELETE).
- **Glassmorphic Markdown UI**: Auto-generates fully responsive tabular interfaces whenever academic results are pulled natively from the SQL DB.
