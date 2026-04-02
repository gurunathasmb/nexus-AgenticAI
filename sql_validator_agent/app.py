from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from validator import SQLValidator


DB_URI = "postgresql://user:password@localhost:5432/academic_db"  # TODO: update with real credentials

app = FastAPI()
validator = SQLValidator(DB_URI)


class QueryRequest(BaseModel):
    query: str


@app.post("/validate")
def validate_query(request: QueryRequest):
    is_valid, results = validator.validate(request.query)
    if is_valid:
        return {"valid": True, "message": "Query is valid", "results": results}
    raise HTTPException(
        status_code=400,
        detail={"valid": False, "results": results},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
