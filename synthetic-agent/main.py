from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uuid
import sys
import os

# Add parent dir to path so we can import other agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from synthetic_agent import SyntheticAgent
from db_modifier import db_modifier

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
sessions = {}
agent = SyntheticAgent()

# Track mock agent states just for UI toggle purposes
frontend_agents = [
    {"name": "Synthetic_Orchestrator", "enabled": True},
    {"name": "Intent_Agent", "enabled": True},
    {"name": "Table_Agent", "enabled": True},
    {"name": "Column_Pruning_Agent", "enabled": True},
    {"name": "SQL_Generator", "enabled": True},
    {"name": "SQL_Validator", "enabled": True},
    {"name": "Audit_Agent", "enabled": True},
]


@app.post("/chat/session")
async def create_session():
    session_id = str(uuid.uuid4())
    sessions[session_id] = {"history": []}
    return {"session_id": session_id}


@app.get("/agents/")
async def get_agents():
    return frontend_agents


@app.post("/agents/{action}/{agent_name}")
async def toggle_agent(action: str, agent_name: str):
    enabled = action == "enable"
    for a in frontend_agents:
        if a["name"] == agent_name:
            a["enabled"] = enabled
    return {"status": "success"}


@app.post("/chat/send")
async def send_message(session_id: str, text: str, persona: str = "default"):
    if session_id not in sessions:
        sessions[session_id] = {"history": []}
    
    # Process through orchestrator
    result = await agent.orchestrate(text, persona, sessions[session_id]["history"])
    
    # Save to history
    sessions[session_id]["history"].append({"user": text, "bot": result["response"]})
    
    return result


@app.post("/chat/modify")
async def modify_database(text: str, email: str):
    """
    Direct endpoint for INSERT/UPDATE operations.
    """
    result = await db_modifier.process_modification(text, email)
    return result

if __name__ == "__main__":
    import uvicorn
    # Check DB before startup
    from table_agent.ranker import _database_url
    print(f"Starting server... Connected to DB check: {'Passed' if _database_url() else 'Warning: No DB URL'}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
