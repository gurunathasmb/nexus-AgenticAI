import os
import re
from openai import OpenAI

# --------------------------------------------------
# Main agent function
# --------------------------------------------------
def generate_sql_with_agent(user_query: str) -> str:
    """
    Accepts a natural language query and returns a safe SQL query directly via LLM.
    """
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    is_nv = api_key.startswith("nvapi-")
    
    kwargs = {"api_key": api_key, "timeout": 10.0}
    if is_nv:
        kwargs["base_url"] = "https://integrate.api.nvidia.com/v1"
        model = "meta/llama-3.1-8b-instruct"
    else:
        model = "gpt-3.5-turbo"
        
    client = OpenAI(**kwargs)

    prompt = f"""
You are an expert SQL generator for a college academic results system.
Your goal is to generate HIGHLY ACCURATE SELECT statements using ONLY the normalized schema.

IF A 'GROUND TRUTH IDENTITY' IS PROVIDED BELOW, YOU MUST USE THAT EXACT USN AND NAME IN YOUR QUERY.

Database schema (PostgreSQL, schema: aiml_academic):
aiml_academic.students (student_usn PRIMARY KEY, student_name, admission_year)
aiml_academic.student_semester_results (semester_result_id PK, session_id, student_usn FK, sgpa, percentage, grand_total)
aiml_academic.student_subject_results (subject_result_id PK, semester_result_id FK, raw_result, numeric_marks, grade_text)

STRICT RULES:
1. SCHEMA LOCKDOWN: ONLY use tables prefixed with 'aiml_academic.'.
2. NO HALLUCINATION: If a 'GROUND TRUTH IDENTITY' is provided, ignore fuzzy matching and use the provided USN.
3. RESILIENT JOIN: Always JOIN students s ON r.student_usn = s.student_usn. 
4. USN DATA QUIRK: If no ground truth is provided and a direct match fails, use ILIKE '%[USN]%' for USN or Name columns.
5. MULTI-SEMESTER: Fetch ALL rows for that USN so we can show a progression. ALWAYS include 'student_usn' and 'student_name'.
6. Output raw SQL only. No markdown. No comments.

User query & Context:
{user_query}
"""

    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": prompt}]
    )
    
    sql_query = completion.choices[0].message.content.strip()

    # Strip markdown code fences if LLM added them
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

    # Extract the SELECT statement
    match = re.search(r"(SELECT[\s\S]+?)(?:;|\Z)", sql_query, re.IGNORECASE)
    if match:
        sql_query = match.group(1).strip()
    else:
        raise ValueError(
            f"No valid SQL SELECT found in LLM output. Got: {sql_query[:200]}"
        )

    return sql_query


