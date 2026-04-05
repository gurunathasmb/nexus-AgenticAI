import os
import sys
import asyncio
from openai import AsyncOpenAI

# Add parent path to allow cross-folder imports of sibling agents
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from Intent_Agent3.intent_agent import HierarchicalIntentAgent
except ImportError:
    HierarchicalIntentAgent = None

try:
    from audit_agent import AuditAgent
except ImportError:
    AuditAgent = None

# Connect sibling agents
try:
    from table_agent.agent import TableAgent
except ImportError:
    TableAgent = None

try:
    from column_pruning_agent.agent import ColumnPruningAgent
except ImportError:
    ColumnPruningAgent = None

try:
    from SQL_QUERY_GENERATOR.sql_agent import generate_sql_with_agent
except ImportError:
    generate_sql_with_agent = None

try:
    from sql_validator_agent.validator import SQLValidator
    from table_agent.ranker import _database_url
except ImportError:
    SQLValidator = None
    _database_url = None

class Message:
    def __init__(self, text, metadata=None, sender="user"):
        self.text = text
        self.metadata = metadata or {}
        self.sender = sender

class SyntheticAgent:
    def __init__(self):
        # Smartly detect API key type to prevent 401 Unauthorized errors
        self.api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
        
        kwargs = {"api_key": self.api_key, "timeout": 10.0}
        if self.api_key.startswith("nvapi-"):
            kwargs["base_url"] = "https://integrate.api.nvidia.com/v1"
            self.model = "meta/llama-3.1-8b-instruct"
        else:
            # Fallback to standard OpenAI or groq if it starts with sk-
            self.model = "gpt-3.5-turbo" 
            
        self.client = AsyncOpenAI(**kwargs)
        
        self.intent_agent = HierarchicalIntentAgent() if HierarchicalIntentAgent else None
        self.table_agent = TableAgent() if TableAgent else None
        self.col_pruning_agent = ColumnPruningAgent() if ColumnPruningAgent else None
        self.audit_agent = AuditAgent() if AuditAgent else None
        
        # Instantiate SQLValidator if DB URL is available
        self.validator = None
        if SQLValidator and _database_url:
            url = _database_url()
            if url: self.validator = SQLValidator(url)

    async def orchestrate(self, text: str, persona: str, history: list) -> dict:
        intent, confidence, entropy, reasoning = "default", 0.8, 0.5, "Pipeline starting."
        
        # 1. Intent Phase
        if self.intent_agent:
            msg = Message(text, metadata={"persona": persona})
            try:
                res_msg = await self.intent_agent.handle_message(msg)
                intent = res_msg.metadata.get("intent", intent)
                confidence = res_msg.metadata.get("confidence", confidence)
                entropy = res_msg.metadata.get("entropy_reduction", entropy)
                reasoning = res_msg.metadata.get("reasoning", "")
            except Exception as e:
                reasoning += f" (Intent Err: {e})"
        
        context_str = ""
        sql_query = ""

        # 2. Table & Column Pruning Phase
        if self.table_agent and self.col_pruning_agent:
            try:
                table_res = await self.table_agent.handle_message(Message(text))
                tables = table_res.metadata.get("ranked_tables", [])
                if tables:
                    col_res = await self.col_pruning_agent.handle_message(Message(text))
                    kept_cols = col_res.metadata.get("kept", [])
                    table_name = col_res.metadata.get("table", tables[0]["table"])
                    context_str = f"Target Table: {table_name}. Relevant Columns: {', '.join(kept_cols)}."
                    reasoning += f" | Table Context: Pulled {table_name} schema."
            except Exception as e:
                pass
                
        # 3. SQL Gen Phase
        if generate_sql_with_agent:
            try:
                sql_input = f"{text}\nContext hint: {context_str}"
                sql_query = await asyncio.to_thread(generate_sql_with_agent, sql_input)
                reasoning += " | SQL Gen: Drafted."
            except Exception as e:
                pass

        # 4. Filter / Validate SQL & Execute
        if self.validator and sql_query:
            is_valid, v_res = await asyncio.to_thread(self.validator.validate, sql_query)
            if not is_valid:
                sql_query = ""
                reasoning += " | SQL Validation: Rejected (blocked for security)."
            else:
                reasoning += " | SQL Validation: Passed Check."
                # Execute against the database!
                try:
                    from sqlalchemy import create_engine, text
                    engine = create_engine(_database_url())
                    with engine.connect() as conn:
                        result = conn.execute(text(sql_query))
                        rows = [dict(row._mapping) for row in result.fetchmany(10)]
                        context_str += f"\nDatabase Execution Results (Top 10): {rows}"
                        reasoning += " | DB Execution: Fetched rows successfully."
                except Exception as db_err:
                    reasoning += f" | DB Execution: Failed ({db_err})"

        # 5. Final LLM Generation
        prompt = f"""You are AIML Nexus, an Orchestrator. User persona: {persona}. Intent: {intent}
Query: "{text}"
Database Context & Results: {context_str}

Formulate a helpful conversational response to the user USING the Database Execution Results above. Do not return raw errors. Use formatting."""

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": prompt}]
            )
            final_resp = completion.choices[0].message.content.strip()
        except Exception as e:
            final_resp = f"I failed to generate a response via LLM gracefully. Error: {e}"

        # 6. Audit Pipeline Phase
        if self.audit_agent:
            try:
                a_res = await asyncio.to_thread(self.audit_agent.audit, text, sql_query, final_resp)
                if not a_res["passed"]:
                    final_resp = "Response blocked by Audit for safety compliance."
            except Exception:
                pass
                
        return {
            "response": final_resp,
            "sender": "synthetic_agent",
            "intent": intent,
            "confidence": confidence,
            "entropy_reduction": entropy,
            "reasoning": reasoning
        }
