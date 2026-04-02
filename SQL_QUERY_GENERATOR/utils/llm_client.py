def call_llm(prompt: str):
    # You can later replace this with Groq/OpenAI when needed.
    # For now we return a static demo SQL.
    return "SELECT id, name FROM student WHERE year = 3;"

