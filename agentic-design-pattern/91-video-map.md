# Appendix: watch-along map for the video summary

There is a popular hour-long video that walks through this same material as a plain-English
summary of the 400-page guide: **"20 Agentic AI Design Patterns"** —
<https://www.youtube.com/watch?v=e2zIr_2JMbE>. It is a genuinely good first pass, and a lot of
people meet these patterns there before they ever open the book.

It is worth knowing how the two line up, because the video collapses the book's twenty-one
patterns into twenty and reorders a few of them. The most common point of confusion: the video
covers **Human-in-the-Loop before Retrieval**, and it folds the book's separate treatment of
**Goal Setting** and **Exception Handling** into a different running order than the book uses.
Nothing is missing — it is the same catalog, walked in a slightly different sequence.

Use this table to jump from a timestamp straight to the matching chapter here. My suggestion:
watch a section, pause, then read the corresponding pattern below and try the spoken answer out
loud before moving on. The video gives you the shape in five minutes; this playbook gives you the
twenty minutes of talk that an interviewer actually wants to hear.

| Video timestamp | Video's name for it | Pattern in this playbook |
|---|---|---|
| 0:54 | Prompt Chaining | Pattern 1 — Prompt Chaining |
| 5:42 | Routing | Pattern 2 — Routing |
| 9:30 | Parallelization | Pattern 3 — Parallelization |
| 13:16 | Reflection | Pattern 4 — Reflection |
| 15:51 | Tool Use | Pattern 5 — Tool Use |
| 18:19 | Planning | Pattern 6 — Planning |
| 20:49 | Multi-Agent Collaboration | Pattern 7 — Multi-Agent Collaboration |
| 23:45 | Memory Management | Pattern 8 — Memory Management |
| 26:42 | Learning and Adaptation | Pattern 9 — Learning and Adaptation |
| 29:17 | Goal Setting and Monitoring | Pattern 11 — Goal Setting and Monitoring |
| 31:34 | Exception Handling and Recovery | Pattern 12 — Exception Handling and Recovery |
| 34:11 | Human-in-the-Loop | Pattern 13 — Human-in-the-Loop |
| 36:01 | Retrieval (RAG) | Pattern 14 — Knowledge Retrieval (RAG) |
| 38:14 | Inter-Agent Communication | Pattern 15 — Inter-Agent Communication (A2A) |
| 43:08 | Resource-Aware Optimization | Pattern 16 — Resource-Aware Optimization |
| 46:35 | Reasoning Techniques | Pattern 17 — Reasoning Techniques |
| 49:57 | Evaluation and Monitoring | Pattern 19 — Evaluation and Monitoring |
| 52:44 | Guardrails and Safety | Pattern 18 — Guardrails and Safety |
| 56:04 | Prioritization | Pattern 20 — Prioritization |
| 59:29 | Exploration and Discovery | Pattern 21 — Exploration and Discovery |

The one pattern the video does not give its own segment to is **Pattern 10 — Model Context
Protocol (MCP)**. Do not skip it. MCP has moved faster than almost anything else in this list
since the book was written, and it is the single most likely "what's new in the field?" question
you will get in a 2026 interview. The chapter here covers it properly, including the July 2026
spec revision that made the protocol stateless.

Two closing notes the video makes that are worth repeating, because interviewers reward both.
First, **do not over-engineer**: most real systems are two or three of these patterns combined,
not ten. Reaching for the smallest combination that solves the problem is a senior signal; naming
every pattern you know is a junior one. Second, **every pattern costs you something** — usually
latency, usually dollars, always complexity. If you introduce a pattern in an interview without
naming what it costs, you have given half an answer.
