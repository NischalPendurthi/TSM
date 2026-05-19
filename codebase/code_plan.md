## what to extract
- every time we creating memory start creating with memory_store folder
- in that for each question in data/longmemeval_s_cleaned.json create question{i} folder since i can upto 500 use three digit to represent for eg. 1 as 001
- in that question{i} folder i want to dump all entities i extracted from the chat turns

- creating chat batch
    - for each session in the question we generate entities one or more times based on the chat size
    - if chat size more than a threshold , we should batch them in to buckets and extract for each of them

- we represent grounded fact as (Es, R , Eo , T)

    - Es is subject entity
    - Eo is object entity
    - R is relation
    - T is timestamp where the fact is valid

- using structured prompt we request for the above json format
- to see the progress give loader in the terminal to see what is completed ( simple but understandable )

- collect all chat pointers for each entity where it is supported

- with addition to facts we want summaries for each entity

    - collect all diffrent entities and now using map of all chats , build a context for compact summary generation

- challenges

    - it is difficult to claim that timestamp of chat turn is the timestamp of fact extracted from that chat
    - i saw the model we took is not generating the expected json , we need tune the model or code for the exact response we need
    - 
