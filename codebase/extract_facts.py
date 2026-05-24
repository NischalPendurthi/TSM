import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv
from groq import Groq

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "longmemeval_s_cleaned.json")
MEMORY_STORE = os.path.join(os.path.dirname(__file__), "..", "memory_store")
MODEL = "llama-3.3-70b-versatile"
BATCH_SIZE = 5  # max user-assistant pairs per batch

_groq = Groq(api_key=os.environ["GROQ_API_KEY"])

# Set by main() before each question; raw LLM responses are appended here immediately
_raw_log_path: Optional[str] = None


def _log_raw(entry: dict) -> None:
    if _raw_log_path:
        with open(_raw_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def parse_date(date_str: str) -> Optional[datetime]:
    # "2023/05/20 (Sat) 02:21" -> datetime
    try:
        clean = re.sub(r'\s*\([A-Za-z]+\)\s*', ' ', date_str).strip()
        return datetime.strptime(clean, "%Y/%m/%d %H:%M")
    except Exception:
        return None


def mean_timestamp(dates: List[datetime]) -> Optional[str]:
    if not dates:
        return None
    avg = sum(d.timestamp() for d in dates) / len(dates)
    return datetime.fromtimestamp(avg).strftime("%Y-%m-%dT%H:%M:%S")


def format_batch(session_idx: int, pairs: List[tuple], pair_offset: int) -> str:
    lines = []
    for i, (user_msg, asst_msg) in enumerate(pairs):
        ref = f"{session_idx}.{pair_offset + i + 1}"
        lines.append(f"[{ref}] User: {user_msg}")
        lines.append(f"[{ref}] Assistant: {asst_msg}")
    return "\n".join(lines)


def call_model(messages: List[Dict]) -> str:
    response = _groq.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.1,
        max_tokens=1024,
    )
    return response.choices[0].message.content


def pass1_extract_entities(chat_batch: str, meta: Optional[dict] = None) -> List[str]:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an entity extraction system. Extract all named entities from the chat history. "
                'Return ONLY a valid JSON array of entity name strings. Example: ["Alice", "Google", "2024-01-15"] '
                "Do not include generic nouns or the words User or Assistant. No markdown, no explanation."
            ),
        },
        {"role": "user", "content": f"Extract named entities from this chat:\n{chat_batch}"},
    ]
    raw = call_model(messages)
    _log_raw({"pass": 1, "raw": raw, **(meta or {})})
    raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return [str(e) for e in result if str(e) not in ("User", "Assistant", "")]
    except json.JSONDecodeError:
        pass
    return re.findall(r'"([^"]{2,})"', raw)


def pass2_extract_relations(entities: List[str], chat_batch: str, meta: Optional[dict] = None) -> List[Dict]:
    if len(entities) < 2:
        return []
    messages = [
        {
            "role": "system",
            "content": (
                "You are a relation extraction system. For each pair of entities, check whether a relation exists in the chat. "
                "Return ONLY a JSON array of relation objects using this exact schema: "
                '[{"Es": "subject entity", "Eo": "object entity", "R": "relation", "Evidences": ["turn refs like 1.2"]}] '
                "No markdown, no explanation."
            ),
        },
        {
            "role": "user",
            "content": f"Entities: {json.dumps(entities)}\nChat:\n{chat_batch}",
        },
    ]
    raw = call_model(messages)
    _log_raw({"pass": 2, "raw": raw, **(meta or {})})
    raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return [r for r in result if isinstance(r, dict) and "Es" in r]
        if isinstance(result, dict) and "Es" in result:
            return [result]
    except json.JSONDecodeError:
        pass
    # Fallback: extract individual {...} objects that have the required keys
    return _extract_relation_objects(raw)


def _extract_relation_objects(text: str) -> List[Dict]:
    """Pull out any {...} blobs that look like valid relation objects."""
    results = []
    for match in re.finditer(r'\{[^{}]+\}', text, re.DOTALL):
        try:
            obj = json.loads(match.group())
            if isinstance(obj, dict) and "Es" in obj and "Eo" in obj and "R" in obj:
                results.append(obj)
        except json.JSONDecodeError:
            pass
    return results


def process_session(
    session_idx: int,
    session: List[Dict],
    session_date: str,
    haystack_dates: List[str],
) -> Dict:
    # Build user-assistant pairs from consecutive turns
    pairs = []
    i = 0
    while i < len(session) - 1:
        if session[i]["role"] == "user" and session[i + 1]["role"] == "assistant":
            pairs.append((session[i]["content"], session[i + 1]["content"]))
            i += 2
        else:
            i += 1

    all_entities: List[str] = []
    all_relations = []
    for batch_start in range(0, max(len(pairs), 1), BATCH_SIZE):
        batch_pairs = pairs[batch_start : batch_start + BATCH_SIZE]
        if not batch_pairs:
            break

        batch_text = format_batch(session_idx, batch_pairs, batch_start)
        meta = {"session": session_idx, "batch": batch_start // BATCH_SIZE}
        entities = pass1_extract_entities(batch_text, meta)
        for e in entities:
            if e not in all_entities:
                all_entities.append(e)
        if not entities:
            continue

        relations = pass2_extract_relations(entities, batch_text, meta)

        for rel in relations:
            ref_dates = []
            for ref in rel.get("Evidences", []):
                try:
                    s_idx = int(str(ref).split(".")[0]) - 1  # 1-based -> 0-based
                    if 0 <= s_idx < len(haystack_dates):
                        d = parse_date(haystack_dates[s_idx])
                        if d:
                            ref_dates.append(d)
                except (ValueError, IndexError):
                    pass
            if not ref_dates:
                d = parse_date(session_date)
                if d:
                    ref_dates.append(d)
            rel["timestamp"] = mean_timestamp(ref_dates)
            all_relations.append(rel)

    return {
        "session_index": session_idx,
        "session_date": session_date,
        "entities": all_entities,
        "relations": all_relations,
    }


def progress_bar(current: int, total: int, prefix: str = "", width: int = 40):
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = 100.0 * current / total
    print(f"\r{prefix} [{bar}] {current}/{total} ({pct:.1f}%)", end="", flush=True)


def main():
    with open(DATA_PATH) as f:
        questions = json.load(f)

    os.makedirs(MEMORY_STORE, exist_ok=True)
    total = len(questions)

    for q_idx, question in enumerate(questions):
        q_num = f"{q_idx + 1:03d}"
        q_dir = os.path.join(MEMORY_STORE, f"question{q_num}")
        os.makedirs(q_dir, exist_ok=True)
        raw_facts_path = os.path.join(q_dir, "raw_facts.json")

        global _raw_log_path
        _raw_log_path = os.path.join(q_dir, "raw_responses.jsonl")
        open(_raw_log_path, "w").close()  # reset file for this question

        sessions = question.get("haystack_sessions", [])
        haystack_dates = question.get("haystack_dates", [])

        print(f"\n[{q_num}/{total:03d}] {question['question_id']} — {len(sessions)} sessions")

        facts = []
        for s_idx, session in enumerate(sessions):
            session_date = haystack_dates[s_idx] if s_idx < len(haystack_dates) else ""
            result = process_session(s_idx + 1, session, session_date, haystack_dates)
            facts.append(result)

            with open(raw_facts_path, "w") as f:
                json.dump(facts, f, indent=2)

            progress_bar(s_idx + 1, len(sessions), prefix="  sessions")

        print()


if __name__ == "__main__":
    main()
