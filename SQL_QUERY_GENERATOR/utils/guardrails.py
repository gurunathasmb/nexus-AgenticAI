FORBIDDEN = ["insert", "update", "delete", "drop", "alter", "truncate"]

def validate_sql(sql: str):
    s = sql.lower()

    if not s.startswith("select"):
        return False, "Only SELECT queries are allowed."

    for f in FORBIDDEN:
        if f in s:
            return False, f"Forbidden keyword detected: {f}"

    return True, "Safe"

