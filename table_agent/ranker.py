from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


def _database_url() -> str:
    url = os.getenv("AIML_RESULTS_DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "AIML_RESULTS_DATABASE_URL is not set. "
            "Point it at the PostgreSQL database that has schema aiml_academic "
            "(see results_aiml_normalized_postgres.sql)."
        )
    return url


_SEM_WORDS = {
    1: ("1st", "first", "sem 1", "sem1", "semester 1", "1 sem"),
    2: ("2nd", "second", "sem 2", "sem2", "semester 2", "2 sem"),
    3: ("3rd", "third", "sem 3", "sem3", "semester 3", "3 sem"),
    4: ("4th", "fourth", "sem 4", "sem4", "semester 4", "4 sem"),
    5: ("5th", "fifth", "sem 5", "sem5", "semester 5", "5 sem"),
    6: ("6th", "sixth", "sem 6", "sem6", "semester 6", "6 sem"),
    7: ("7th", "seventh", "sem 7", "sem7", "semester 7", "7 sem"),
    8: ("8th", "eighth", "sem 8", "sem8", "semester 8", "8 sem"),
}


def _infer_semesters(text: str) -> set[int]:
    t = text.lower()
    found: set[int] = set()
    for n, phrases in _SEM_WORDS.items():
        for p in phrases:
            if p in t:
                found.add(n)
                break
    m = re.search(r"sem(?:ester)?\s*(\d)", t)
    if m:
        found.add(int(m.group(1)))
    return found


def _infer_years(text: str) -> set[int]:
    return {int(x) for x in re.findall(r"\b(20[1-2]\d)\b", text)}


def _row_matches_semester(row: dict[str, Any], sem_q: set[int]) -> bool:
    if not sem_q:
        return True
    sn = row.get("semester_no")
    if sn is None:
        return False
    return int(sn) in sem_q


def _row_matches_year(row: dict[str, Any], years_q: set[int]) -> bool:
    """Match academic-year folders: DB column and/or path like 2022/2022/..."""
    if not years_q:
        return True
    fy = row.get("source_folder_year")
    if fy is not None and int(fy) in years_q:
        return True
    path = "/".join(
        [
            str(row.get("source_relative_path") or "").replace("\\", "/"),
            str(row.get("source_file_name") or ""),
        ]
    )
    for y in years_q:
        ystr = str(y)
        if f"/{ystr}/" in path or path.startswith(f"{ystr}/"):
            return True
    return False


def _narrow_rows_for_query(rows: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    sem_q = _infer_semesters(query)
    years_q = _infer_years(query)

    if not sem_q and not years_q:
        return [dict(r) for r in rows]

    narrowed = [
        dict(r)
        for r in rows
        if _row_matches_semester(r, sem_q) and _row_matches_year(r, years_q)
    ]
    if narrowed:
        return narrowed
    return []


def _tokens(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if len(w) > 1}


def _short_table_label(row: dict[str, Any]) -> str:
    label = (row.get("session_label") or "").strip()
    if label:
        part = label.split()[0] if label.split() else label
        if len(part) > 24:
            return part[:21] + "..."
        return part
    path = row.get("source_relative_path") or row.get("source_file_name") or ""
    base = os.path.basename(path.replace("\\", "/"))
    return (base[:24] + ("..." if len(base) > 24 else "")) if base else ""


def _table_id_slug(row: dict[str, Any]) -> str:
    rel = (row.get("source_relative_path") or row.get("source_file_name") or "").strip()
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", rel.replace("\\", "/")).strip("_").lower()
    sid = row.get("session_id")
    if slug:
        return "aiml_" + slug
    return f"aiml_session_{sid}"


def _source_file_display(row: dict[str, Any]) -> str:
    return (row.get("source_relative_path") or row.get("source_file_name") or "").strip()


@dataclass
class RankedTable:
    table: str
    score: float
    table_id: str
    source_file: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "score": round(self.score, 4),
            "table_id": self.table_id,
            "source_file": self.source_file,
        }


def fetch_sessions(
    conn,
    semester_nos: list[int] | None = None,
    years: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Load sessions. When semester_nos and/or years are set, apply SQL filters so
    only rows tied to that semester / calendar folder year enter ranking.
    """
    where_parts: list[str] = []
    params: list[Any] = []

    if semester_nos:
        where_parts.append("semester_no IN %s")
        params.append(tuple(int(x) for x in semester_nos))

    if years:
        yt = tuple(int(x) for x in years)
        year_clauses = ["source_folder_year IN %s"]
        params.append(yt)
        for y in yt:
            year_clauses.append(
                "(source_relative_path LIKE %s OR source_relative_path LIKE %s "
                "OR source_file_name LIKE %s OR source_file_name LIKE %s)"
            )
            params.extend(
                (
                    f"%/{y}/%",
                    f"{y}/%",
                    f"%/{y}/%",
                    f"{y}/%",
                )
            )
        where_parts.append("(" + " OR ".join(year_clauses) + ")")

    where_sql = " AND ".join(where_parts) if where_parts else "TRUE"
    sql = f"""
        SELECT session_id, session_label, source_file_name, source_relative_path,
               semester_no, source_folder_year, study_year, result_scale
        FROM aiml_academic.result_sessions
        WHERE {where_sql}
        ORDER BY session_id
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def score_row(query: str, row: dict[str, Any]) -> float:
    q_tok = _tokens(query)
    doc_parts = [
        str(row.get("session_label") or ""),
        str(row.get("source_file_name") or ""),
        str(row.get("source_relative_path") or ""),
        f"semester {row.get('semester_no')}",
        f"year {row.get('source_folder_year')}",
        f"study {row.get('study_year')}",
        str(row.get("result_scale") or ""),
    ]
    doc = " ".join(doc_parts).lower()
    d_tok = _tokens(doc)

    overlap = sum(1.0 for t in q_tok if t in d_tok)
    score = overlap * 1.2

    sem_q = _infer_semesters(query)
    if sem_q and row.get("semester_no") is not None and int(row["semester_no"]) in sem_q:
        score += 4.0

    years_q = _infer_years(query)
    fy = row.get("source_folder_year")
    if years_q and fy is not None and int(fy) in years_q:
        score += 3.0
    if "batch" in query.lower() and years_q and row.get("study_year") is not None:
        if int(row["study_year"]) in years_q:
            score += 2.0

    if row.get("session_id") is not None and str(row["session_id"]) in query:
        score += 2.0

    return score


def rank_tables(query: str, top_k: int = 5) -> tuple[list[dict[str, Any]], str | None]:
    if top_k < 1:
        top_k = 1
    if top_k > 50:
        top_k = 50

    sem_q = _infer_semesters(query)
    years_q = _infer_years(query)
    sem_list = sorted(sem_q) if sem_q else None
    year_list = sorted(years_q) if years_q else None

    conn = None
    try:
        conn = psycopg2.connect(_database_url())
        rows = fetch_sessions(conn, semester_nos=sem_list, years=year_list)
    except RuntimeError as e:
        return [], str(e)
    except Exception as e:
        return [], f"Database error: {e}"
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    if not rows:
        if sem_q or years_q:
            hint = []
            if sem_q:
                hint.append(f"semester(s) {sorted(sem_q)}")
            if years_q:
                hint.append(f"year(s) {sorted(years_q)}")
            return [], (
                "No result_sessions match " + " and ".join(hint) + ". Try different wording or check the DB."
            )
        return [], "No rows in aiml_academic.result_sessions (load the normalized SQL dump first)."

    candidates = _narrow_rows_for_query(rows, query)
    if not candidates and (sem_q or years_q):
        hint = []
        if sem_q:
            hint.append(f"semester(s) {sorted(sem_q)}")
        if years_q:
            hint.append(f"year(s) {sorted(years_q)}")
        return [], "No result_sessions match " + " and ".join(hint) + ". Try different wording or check the DB."

    scored: list[tuple[float, dict[str, Any]]] = []
    for row in candidates:
        rdict = dict(row)
        s = score_row(query, rdict)
        scored.append((s, rdict))

    scored.sort(key=lambda x: x[0], reverse=True)
    max_s = scored[0][0] if scored else 0.0
    if max_s <= 0:
        max_s = 1.0
        scored = [(max(0.01, s / 10.0), r) for s, r in scored]
        max_s = max(x[0] for x in scored) or 1.0

    out: list[RankedTable] = []
    for s, r in scored[:top_k]:
        norm = min(1.0, s / max_s) if max_s else 0.0
        sid = r.get("session_id")
        short = _short_table_label(r) or f"session_{sid}"
        out.append(
            RankedTable(
                table=short,
                score=norm,
                table_id=_table_id_slug(r),
                source_file=_source_file_display(r),
            )
        )

    return [x.as_dict() for x in out], None
