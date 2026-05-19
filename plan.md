## Episodic & Durative Memory Plan

### How to construct episodic memory

- Batch chat turns per session and extract grounded facts with a local model (REST API).
- Consolidate all grounded facts and create compact summaries per entity using supporting chat turns (same local model).

Challenges

- Avoid reliance on paid/free external APIs; prefer local models.
- Optimize for latency vs. quality when batching.

Advanced

- Tune batching size for a balance between latency and extraction quality.
- Track and include relevant context responsible for each summary.

### Structure of memory

Directory layout (memory_store):

```
memory_store/
│
├── question_001/
│   ├── raw_facts.json          ← TKG facts extracted per turn
│   ├── entity_summaries.json   ← consolidated entity summaries
│   ├── topic_summaries.json    ← durative: clustered topics per month
│   ├── persona_summary.json    ← durative: user persona per month
│   └── graph.json              ← full graph (nodes + edges)
│
├── question_002/
│   ├── raw_facts.json
│   ├── entity_summaries.json
│   ...
│
└── results/
    ├── answers.json            ← generated answers
    └── scores.json             ← benchmark scores per category
```

### Model specifications

- Architecture: LFM2
- Size: 354M
- Context length: 128000
- Embedding length: 1024
- Quantization: unknown
- Capabilities: completion
- Stop tokens: `<|im_start|>`, `<|im_end|>`
- License: LFM Open License v1.0

Template

```
{{- range .Messages }}<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}<|im_start|>assistant
```

### Consolidation to durative memory

- Build a timeline of events across sessions (use haystack_dates/haystack_sessions).
- Cluster semantically related events and represent facts in a knowledge graph.
- Consolidate clusters into durative summaries (topics, persona, timelines).

### Utilizing and updating memory

- Use entity summaries and graph to answer queries requiring aggregation, tracking, and temporal reasoning.
- When new evidence contradicts or augments existing facts, update raw_facts.json and regenerate affected summaries/graph.
- Implement abstention when evidence is insufficient or contradictory.

### Benchmarks

- Use LongMemEval_S (longmemeval_s_cleaned.json) to evaluate on:
  - Information extraction (entities, relations, attributes)
  - Multi-session reasoning (aggregation, tracking, inference)
  - Temporal reasoning (ordering, durations, recurrence)
  - Knowledge updates (conflict resolution, updates over time)
  - Abstention (refuse when insufficient/contradictory evidence)

Dataset notes

- longmemeval_s_cleaned.json: top-level JSON array with ~500 records.
- Each record fields: question_id, question_type, question, question_date, answer, answer_session_ids, haystack_dates, haystack_session_ids, haystack_sessions.
- haystack_sessions: list of sessions; each session is a list of messages {role, content}.

### Duration-aware memory construction

- Requirements: timeline of events, semantic clustering, knowledge-graph representation, consolidation to durative memory.

### Open questions

- How to build an effective dialogue timeline?
- How to cluster related events robustly across sessions and time?

