import re
import os
from crewai import Agent, Task, Crew, LLM

# --------------------------------------------------
# Config from environment variables (Docker/K8s ready)
# --------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL   = os.getenv("LLM_MODEL", "llama3:latest")
LLM_TEMP    = float(os.getenv("LLM_TEMPERATURE", "0.0"))

# Use CrewAI's native LLM class with ollama/ prefix
llm = LLM(
    model=f"ollama/{LLM_MODEL}",
    base_url=OLLAMA_HOST,
    temperature=LLM_TEMP
)

# --------------------------------------------------
# Guardrails
# --------------------------------------------------
ALLOWED_TABLES = [
    "semesters",
    "students",
    "subjects",
    "result_sessions",
    "session_subjects",
    "student_semester_results",
    "student_subject_results"
]

FORBIDDEN_KEYWORDS = [
    "delete", "drop", "update", "insert", "alter",
    "truncate", "create", "replace"
]


def guardrail_check(sql_query: str) -> str:
    """Reject forbidden SQL keywords and tables not in the allowed schema."""

    sql_lower = sql_query.lower()

    # 1. Block forbidden DML/DDL (whole-word match to avoid blocking
    #    column names like "created_at")
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf'\b{keyword}\b', sql_lower):
            raise ValueError(
                f"Forbidden SQL keyword detected: '{keyword}'. "
                "Only SELECT queries are allowed."
            )

    # 2. Block tables not in the schema
    tables_used = re.findall(r'(?:FROM|JOIN)\s+(?:aiml_academic\.)?(\w+)', sql_query, re.IGNORECASE)
    for table in tables_used:
        if table.lower() not in ALLOWED_TABLES:
            raise ValueError(
                f"Invalid table referenced: '{table}'. Not in allowed schema."
            )

    return sql_query


# --------------------------------------------------
# Main agent function
# --------------------------------------------------
def generate_sql_with_agent(user_query: str) -> str:
    """
    Accepts a natural language query (optionally pre-enriched with
    intent/entities from the Intent Agent) and returns a safe SQL query.
    """

    prompt = f"""
You are an expert SQL generator for a college academic results system.

Database schema (PostgreSQL, schema: aiml_academic):

aiml_academic.semesters(semester_no, study_year, semester_label)
  - semester_no: 1 to 8
  - study_year: 1 to 4

aiml_academic.students(student_usn, student_name, admission_year)
  - student_usn: primary key e.g. '1DS20AI001'
  - admission_year: the batch/year the student joined

aiml_academic.subjects(subject_code, subject_label)

aiml_academic.result_sessions(session_id, source_folder_year, semester_no, session_label, study_year, result_scale)
  - result_scale: 'marks' or 'grades'

aiml_academic.session_subjects(session_subject_id, session_id, subject_code, subject_order)

aiml_academic.student_semester_results(semester_result_id, session_id, student_usn, student_name_snapshot, sgpa, percentage, grand_total)
  - sgpa: semester grade point average
  - percentage: overall percentage
  - grand_total: total marks

aiml_academic.student_subject_results(subject_result_id, semester_result_id, session_subject_id, raw_result, numeric_marks, grade_text, result_kind)
  - numeric_marks: marks scored in a subject
  - grade_text: grade if result_scale is grades

Rules:
- Use ONLY SELECT statements. Never use DELETE, DROP, UPDATE, INSERT, ALTER.
- Always prefix tables with schema: aiml_academic.<table_name>
- "Batch year" or "admission year" refers to students.admission_year
- "Semester" refers to semesters.semester_no
- "SGPA" refers to student_semester_results.sgpa
- "Percentage" refers to student_semester_results.percentage
- "Marks in a subject" refers to student_subject_results.numeric_marks
- For top N students, use ORDER BY <metric> DESC LIMIT N
- Output ONLY the raw SQL query. No explanation. No markdown. No code fences.

User query:
{user_query}
"""

    sql_agent = Agent(
        role="SQL Generator",
        goal="Convert natural language queries into correct PostgreSQL SELECT statements",
        backstory="You are a senior database engineer expert in writing clean, safe SQL for academic databases.",
        llm=llm,
        verbose=False
    )

    task = Task(
        description=prompt,
        expected_output="A single SQL SELECT query with no markdown, no explanation.",
        agent=sql_agent
    )

    crew = Crew(
        agents=[sql_agent],
        tasks=[task],
        verbose=False
    )

    result = crew.kickoff()

    # --- Robust SQL extraction ---
    sql_query = str(result)

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

    # Apply guardrails before returning
    return guardrail_check(sql_query)


