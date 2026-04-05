import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# Load master .env from root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# --------------------------------------------------
# Main agent function
# --------------------------------------------------
def generate_sql_with_agent(user_query: str) -> str:
    """
    Accepts a natural language query and returns a safe SQL query directly via LLM.
    """
    api_key = os.getenv("NVIDIA_API_KEY") or os.getenv("OPENAI_API_KEY")
    is_nv = api_key.startswith("nvapi-")
    
    kwargs = {"api_key": api_key, "timeout": 10.0}
    if is_nv:
        kwargs["base_url"] = "https://integrate.api.nvidia.com/v1"
        model = "meta/llama-3.1-8b-instruct"
    else:
        model = "gpt-3.5-turbo"
        
    client = OpenAI(**kwargs)

    prompt = f"""
### MISSION: GENERATE RAW DATA SELECT QUERIES ONLY.

STRICT RULES (FAILURE TO FOLLOW = CRASH):
1. FORBIDDEN: NEVER use AVG(), SUM(), MAX(), or COUNT().
2. FORBIDDEN: NEVER use GROUP BY or HAVING.
3. FORBIDDEN: DO NOT calculate CGPA in SQL. The Python orchestrator handles all math.
4. SCHEMA LOCKDOWN: ONLY use 'aiml_academic.' tables.
5. IDENTITY ANCHOR: If 'GROUND TRUTH IDENTITY' is provided, use that EXACT USN.
6. RESILIENT JOIN: Always JOIN students s ON r.student_usn = s.student_usn. 
7. TABLE MAPPING: 'sgpa' is in 'student_semester_results'. 'numeric_marks' is in 'student_subject_results'.
8. Output RAW SQL only. No markdown. No comments.

REQUIRED PATTERN (FOLLOW THIS 100%):
SELECT s.student_usn, s.student_name, r.sgpa, r.percentage, r.grand_total 
FROM aiml_academic.students s 
JOIN aiml_academic.student_semester_results r ON s.student_usn = r.student_usn 
WHERE s.student_usn = '[USN]'

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


