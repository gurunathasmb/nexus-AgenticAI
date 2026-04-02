def build_prompt(query, schema, tables):
    # Convert relevant schema into readable text
    schema_text = "\n".join(
        [f"{t}: {', '.join(schema[t])}" for t in tables if t in schema]
    )

    prompt = f"""
User Query: {query}

Relevant Schema:
{schema_text}

Rules:
- Only SELECT statements allowed.
- Use only columns from schema.
- Ensure safe SQL.

Generate SQL now.
"""
    return prompt.strip()

