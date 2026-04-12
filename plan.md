## how to construct memory?

## how to consolidate constructed memory to durative memory?

## how to utilize the memory?

## how to update existing memory?

## what are our benchmarks?

---

## First Part is Duration-aware memory construction.

## Our Dataset 

- The file `longmemeval_s_cleaned.json` is a top-level JSON array with 500 records.

- Each record is a dictionary with these fields:

  - question_id: string identifier  
  - question_type: string label, for example single-session-user  
  - question: the query text  
  - question_date: timestamp-like string, for example 2023/05/30 (Tue) 23:40  
  - answer: usually a string, but sometimes an integer  
  - answer_session_ids: array of session ID strings  
  - haystack_dates: array of timestamp strings  
  - haystack_session_ids: array of session ID strings  
  - haystack_sessions: array of conversations  

- The nested haystack_sessions field is the most structured part:

  - it is a list of sessions  
  - each session is a list of message objects  
  - each message object has:
    - role: typically user or assistant  
    - content: the message text  

---

## Why need durative memory?

- Point-Wise memory representations break temporally continous experiences.

---

## Why need dialogue-timeline?

- To construct durative memory.

---

## How to construct duration aware memory?

- we need time line of events  
- we need semantically related events  
- represent these facts in a knowledge graph  
- and consolidate it to generate duration aware memory  

---

## How to dialogue-timeline the events?

## How to cluster related events?
