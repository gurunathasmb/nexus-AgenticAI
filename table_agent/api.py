from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from table_agent.ranker import rank_tables

router = APIRouter()


class TableRankRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language query")
    top_k: int = Field(3, ge=1, le=50, description="Number of tables to return")


class TableRankResponse(BaseModel):
    query: str
    tables: list[dict[str, Any]]


@router.post("/rank", response_model=TableRankResponse)
def rank_tables_endpoint(body: TableRankRequest) -> TableRankResponse:
    tables, err = rank_tables(body.query.strip(), body.top_k)
    if err:
        raise HTTPException(status_code=503, detail=err)
    return TableRankResponse(query=body.query, tables=tables)
