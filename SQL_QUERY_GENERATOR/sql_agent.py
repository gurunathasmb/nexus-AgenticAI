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

    # Apply guardrails before returning
    return guardrail_check(sql_query)


