## what and how to extract

- Create a root folder named `memory_store` whenever memory extraction starts.
- For each question in `data/longmemeval_s_cleaned.json`, create a folder as `question{i}` using 3-digit zero padding (e.g., `001`, `002`, ..., up to `500`).
- Inside each `question{i}` folder, create `raw_facts.json`.
- Continuously append/flush extracted outputs to `raw_facts.json` during processing.

- Chat batching
    - For each session in a question, run entity extraction one or more times depending on chat length.
    - If chat length exceeds a threshold, split it into buckets/batches and process each batch separately.

- Processing pipeline
    - Pass 1: Extract entities from each chat batch.
    - Pass 2: For each entity pair, detect whether a relation exists; if yes, return structured relation data.

- Expected LLM output
    - Pass 1: list of entities.
    - Pass 2: relation objects in this format:

```json
{
    "Es": "subject entity",
    "Eo": "object entity",
    "R": "relation",
    "Evidences": ["supporting chat turn references"]
}
```

- Pass 2 prompt (with context)
    - Prompt: "For each pair of entities, check whether a relation exists. If yes, return it in the required data format."
    - Context must include: extracted entities + current chat batch.

- Chat turn reference format for evidence
    - Each user-assistant pair should be indexed as `sessionIndex.pairIndex`.
    - Example: second pair in third session = `3.2`.
    - Use these references inside `Evidences` for retrieved relations.

- Prompting and progress visibility
    - Use a structured prompt to enforce JSON output format.
    - Show a simple terminal loader/progress indicator so completion status is easy to track.

- raw_facts.json
    - when storing in raw_facts we need a timestamp mapping also 
    - for that we need the mean time timestamp of evidences supprting the relations

- for claude
    - if any of rules are added or updated by you or as i instructed to do , then append them to these file, before you do changes to the codebase

## implementation decisions (claude)

- BATCH_SIZE = 5 user-assistant pairs per batch (10 turns); sessions longer than this are split
- Session and pair indices in evidence references are 1-based (e.g., session 1, pair 1 = "1.1")
- Timestamp for a relation = mean unix time of `haystack_dates` at the referenced session indices, converted back to ISO string; falls back to the current session's date if no valid refs
- `haystack_dates` format parsed: `"2023/05/20 (Sat) 02:21"` → strip day-of-week → `strptime("%Y/%m/%d %H:%M")`
- Pass 1 returns a flat list of entity name strings (not typed objects)
- Pass 2 prompt includes entity list as JSON + full formatted batch; relation schema matches plan spec
- `raw_facts.json` is flushed to disk after every session so progress survives interruption
- Progress shown via `\r` overwrite on a single terminal line per question
- Paths resolved relative to `__file__`: data at `../data/longmemeval_s_cleaned.json`, store at `../memory_store/`