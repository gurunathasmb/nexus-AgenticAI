import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
from sql_agent import generate_sql_with_agent
import uvicorn

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("sql-query-generator")

# --------------------------------------------------
# Router — so this can be imported into main.py
# just like table_agent
# --------------------------------------------------
router = APIRouter()

class TableHint(BaseModel):
    table: str
    score: float = 0.0
    source_file: str = ""
    table_id: str = ""

class SQLRequest(BaseModel):
    query: str
    intent: str = ""
    confidence: float = None
    entities: dict = {}
    tables: list[TableHint] = []
    pruned_columns: list[str] = []
    removed_columns: list[str] = []
    column_reasons: dict = {}

class SQLResponse(BaseModel):
    sql: str
    input_query: str
    intent: str = ""
    tables_used: list[str] = []
    columns_used: list[str] = []
    status: str = "success"

@router.get("/health")
def health():
    return {"status": "healthy", "service": "SQL Query Generator"}

@router.post("/generate-sql", response_model=SQLResponse)
def generate_sql(request: SQLRequest):
    logger.info(f"Received query: {request.query}")

    enriched_query = request.query

    if request.intent:
        enriched_query += f"\n[Intent: {request.intent}]"

    table_names = []
    if request.tables:
        table_names = [t.table for t in request.tables]
        enriched_query += f"\n[Relevant tables: {', '.join(table_names)}]"

    if request.pruned_columns:
        enriched_query += f"\n[Use ONLY these columns: {', '.join(request.pruned_columns)}]"

    if request.entities:
        entity_str = ", ".join(f"{k}={v}" for k, v in request.entities.items())
        enriched_query += f"\n[Entities: {entity_str}]"

    try:
        sql = generate_sql_with_agent(enriched_query)
        logger.info(f"Generated SQL: {sql}")
        return SQLResponse(
            sql=sql,
            input_query=request.query,
            intent=request.intent,
            tables_used=table_names,
            columns_used=request.pruned_columns,
            status="success"
        )
    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Agent error: {e}")
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")


# --------------------------------------------------
# Standalone mode — python app.py still works
# --------------------------------------------------
app = FastAPI(
    title="SQL Query Generator",
    description="Converts natural language into SQL queries.",
    version="1.0.0"
)
app.include_router(router)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


