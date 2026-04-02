def map_tables(query: str):
    q = query.lower()

    keywords = {
        "student": ["student", "name", "roll", "year", "id"],
        "marks": ["marks", "score", "cgpa", "subject"]
    }

    matched = [table for table, words in keywords.items() if any(w in q for w in words)]

    return matched or ["student"]

