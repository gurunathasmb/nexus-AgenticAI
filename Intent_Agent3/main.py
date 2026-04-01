import sys
import os
import json
from datetime import datetime
from dotenv import load_dotenv

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_REPO_ROOT, ".env"))

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from API_Integrations.db.setup import get_db, using_sqlite
from Intent_Agent3 import init_agents
from Intent_Agent3.registry import dispatcher
from Intent_Agent3.base import Message
from table_agent.api import router as table_agent_router
from column_pruning_agent.router import router as column_pruning_router
from SQL_QUERY_GENERATOR.app import router as sql_router

# Folder to save intent classification JSONs
INTENT_LOGS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "API_Integrations", "intent_logs"
)
os.makedirs(INTENT_LOGS_DIR, exist_ok=True)

app = FastAPI(title="Nexus Intent Agent v3 — Hierarchical Fusion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize all agents on startup
init_agents()

app.include_router(table_agent_router, prefix="/table-agent", tags=["table-agent"])
app.include_router(column_pruning_router, prefix="/column-pruning", tags=["column-pruning"])
app.include_router(sql_router, prefix="/sql-agent", tags=["sql-agent"])


# ── Chat routes ──────────────────────────────────────────────────────────


@app.post("/chat/session")
def create_session(conn=Depends(get_db)):
    cursor = conn.cursor()
    if using_sqlite():
        cursor.execute(
            "INSERT INTO ChatSessions (user_id, title) VALUES (?, ?)",
            (1, "New Chat Session"),
        )
        conn.commit()
        session_id = cursor.lastrowid
    else:
        cursor.execute("""
        INSERT INTO ChatSessions (user_id, title)
        OUTPUT INSERTED.id
        VALUES (?, ?)
        """, (1, "New Chat Session"))
        session_id = cursor.fetchone()[0]
        conn.commit()
    return {"session_id": session_id}


@app.post("/chat/send")
async def send_message(session_id: int, text: str, persona: str = "default", conn=Depends(get_db)):
    cursor = conn.cursor()

    # store user message
    cursor.execute("""
    INSERT INTO ChatMessages (session_id, role, text)
    VALUES (?, ?, ?)
    """, (session_id, "user", text))
    conn.commit()

    # dispatch through router with persona metadata
    msg = Message(sender="user", text=text, metadata={"persona": persona})
    response = await dispatcher.dispatch(msg, "router_agent")

    # save intent classification JSON to intent_logs
    if response.metadata:
        log_data = {
            "query": text,
            "persona": persona,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            **{k: response.metadata.get(k) for k in
               ("intent", "confidence", "entropy_reduction", "delta_h", "reasoning", "action", "scores")},
        }
        filename = f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        with open(os.path.join(INTENT_LOGS_DIR, filename), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

    # save agent response
    cursor.execute("""
    INSERT INTO ChatMessages (session_id, role, sender_agent, text)
    VALUES (?, ?, ?, ?)
    """, (session_id, "agent", response.sender, response.text))
    conn.commit()

    # return response + intent metadata
    return {
        "response": response.text,
        "sender": response.sender,
        "intent": response.metadata.get("intent"),
        "confidence": response.metadata.get("confidence"),
        "entropy_reduction": response.metadata.get("entropy_reduction"),
        "reasoning": response.metadata.get("reasoning"),
        "scores": response.metadata.get("scores"),
    }


@app.get("/chat/stream")
async def stream_response(session_id: int, text: str):
    agent = dispatcher.get("llm_agent")

    async def event_generator():
        async for token in agent.stream(text):
            yield token

    return StreamingResponse(event_generator(), media_type="text/plain")


@app.get("/chat/history/{session_id}")
def get_history(session_id: int, conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
    SELECT role, sender_agent, text, timestamp
    FROM ChatMessages
    WHERE session_id = ?
    ORDER BY timestamp
    """, (session_id,))
    rows = cursor.fetchall()
    return [
        {"role": r[0], "sender_agent": r[1], "text": r[2], "timestamp": str(r[3])}
        for r in rows
    ]


@app.get("/chat/sessions")
def list_sessions(conn=Depends(get_db)):
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, user_id, title, created_at
    FROM ChatSessions
    ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    return [
        {"id": r[0], "user_id": r[1], "title": r[2], "created_at": str(r[3])}
        for r in rows
    ]


# ── Intent classification endpoint (saves JSON to file) ─────────────────


class IntentRequest(BaseModel):
    query: str
    persona: str = "default"


@app.post("/intent/classify")
async def classify_intent(req: IntentRequest):
    from Intent_Agent3.intent_agent import HierarchicalIntentAgent

    agent = dispatcher.get("intent_agent")
    result = agent.classify(req.query, req.persona)

    result["query"] = req.query
    result["persona"] = req.persona
    result["timestamp"] = datetime.now().isoformat()

    filename = f"intent_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    filepath = os.path.join(INTENT_LOGS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return {**result, "saved_to": filename}


# ── Agent management routes ─────────────────────────────────────────────


@app.get("/agents/")
def list_agents():
    return [
        {"name": name, "enabled": agent.enabled}
        for name, agent in sorted(dispatcher.agents.items(), key=lambda x: x[0])
    ]


@app.post("/agents/disable/{agent_name}")
def disable_agent(agent_name: str):
    agent = dispatcher.get(agent_name)
    if not agent:
        return {"error": "Agent not found"}
    agent.enabled = False
    return {"status": f"{agent_name} disabled"}


@app.post("/agents/enable/{agent_name}")
def enable_agent(agent_name: str):
    agent = dispatcher.get(agent_name)
    if not agent:
        return {"error": "Agent not found"}
    agent.enabled = True
    return {"status": f"{agent_name} enabled"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
