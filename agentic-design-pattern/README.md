# Agentic Design Patterns

This folder holds the design-pattern track of the guide: the catalog of recurring shapes that show
up once you start assembling language models into systems that actually do things, and — more to the
point — how to *talk about them* in a system-design interview.

Two things live here.

**[The Agentic Design Patterns Interview Playbook](AGENTIC_DESIGN_PATTERNS_PLAYBOOK.md)** is the main
event: all twenty-one patterns, each written as a complete interview preparation unit. For every
pattern you get a realistic scenario the way an interviewer would actually phrase it, a plain-English
explanation of what the pattern is and what problem it solves, a walkthrough of how the design works
including where it breaks, and then a long model answer written the way you would *say* it out loud in
a fifteen-minute design discussion — clarifying questions, tradeoffs, failure modes, evaluation, cost,
and a whiteboard diagram you could sketch. It closes with a pattern picker mapping common scenarios to
the patterns they call for, and four composed mega-scenarios showing how the patterns stack in real
answers.

It assumes no production-systems vocabulary. Terms like idempotency, tail latency, backpressure, and
circuit breakers are defined in plain language the first time they appear, because half of sounding
senior in an interview is using those words comfortably and the other half is knowing what they mean
when the interviewer says them first.

**`Agentic_Design_Patterns.pdf`** is Antonio Gulli's book, the source catalog the playbook is built
around. The playbook is a companion, not a replacement — the book carries the code examples and
framework-level detail (LangChain, LangGraph, Google ADK, CrewAI) that the playbook deliberately sets
aside to focus on explanation and delivery. Read the book for implementation; read the playbook to
rehearse.

There is also a good hour-long video summary of the same catalog at
<https://www.youtube.com/watch?v=e2zIr_2JMbE>. The playbook's final appendix maps its timestamps to
the chapters here so you can watch a section, pause, and immediately practice the matching answer.

## How this relates to the rest of the guide

The numbered chapters (`01_` through `12_`) are about **evaluating** agents — measuring whether they
work, catching regressions, monitoring them in production. This folder is about **architecting** them.
The two meet constantly: Pattern 19 in the playbook is the interview-level view of evaluation, and it
points into those chapters for the depth. Similarly, `AGENT_ENGINEERING_FOUNDATIONS.md` at the repo
root covers hands-on building — frameworks, MCP, RAG, memory, cost engineering — with runnable code.

A reasonable path through all three: read the playbook to learn the shapes and rehearse talking about
them, read the foundations doc to build one for real, and read the numbered chapters to prove it works.
