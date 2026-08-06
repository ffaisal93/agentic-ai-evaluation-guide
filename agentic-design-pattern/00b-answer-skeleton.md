# The universal answer skeleton

Here's a secret that removes most of the fear from system-design interviews: every good answer has the same skeleton.
The pattern changes, the product changes, but the *shape* of a strong fifteen-minute answer is remarkably constant.
Learn the skeleton once and you'll never face a blank whiteboard again — you'll face a fill-in-the-blanks exercise.
Let me walk you through the seven moves, what each sounds like out loud, and — importantly — *why* each one earns you points, because knowing what the interviewer is scoring changes how you play.

**Move 1: Clarify the requirements before designing anything.**
When the question lands — "design a system that summarizes support tickets" — do not start drawing.
Ask three or four sharp questions first: Who consumes the output, a human or another system? How many tickets a day — ten or ten thousand? Does it need to answer in seconds, or is overnight fine? What does a mistake cost — mild annoyance or real money?
Then *state your assumptions out loud* — "I'll assume a few thousand tickets a day, results needed within a minute, and errors are embarrassing but not catastrophic" — so the interviewer can correct you early.
Why this earns points: junior engineers solve the problem they imagined; senior engineers solve the problem that exists.
Clarifying questions are the fastest possible signal of seniority, and they also buy you two minutes of thinking time while looking proactive rather than stalled.
The answers genuinely change the design — a ten-requests-a-day system and a ten-thousand-requests-a-day system are different machines.

**Move 2: State the simplest thing that could work.**
Before any architecture, say the baseline: "The dumbest version is one LLM call with a good prompt. For some fraction of cases that's honestly enough, so let me establish why we need more."
Why this earns points: it proves you're not an architecture-astronaut who reaches for complexity by reflex — a real disease in AI engineering, and interviewers screen for it deliberately.
It also sets up a narrative: everything you add from here on is *justified* by a specific failure of the simple version, which makes your whole answer feel reasoned instead of memorized.

**Move 3: Name the pattern you're reaching for, and say why.**
This is where this playbook pays off.
Say the name: "This is a prompt-chaining problem, because the task has distinct stages where each depends on the previous one," or "I'd put a router in front, because the inputs fall into genuinely different categories that need different handling."
Why this earns points: naming a pattern tells the interviewer you've seen this movie before — you're pattern-matching from experience, not improvising.
It also compresses communication: one sentence conveys a whole architecture, and the interviewer can immediately engage at a higher level.
Just make sure the *because* clause is there; a pattern name without a reason sounds like buzzword bingo.

**Move 4: Draw the boxes and walk the data flow.**
Now the whiteboard.
Draw a small number of boxes — the entry point, the orchestrator, each processing step, the tools and data stores — and then *narrate one request's journey* through them: "The email lands here, this step extracts these fields into a JSON object, that JSON flows into this step, which..."
Be concrete about what data moves along each arrow — vague arrows are where designs go to die.
Why this earns points: this is the core demonstration that you can decompose a problem, and walking a single concrete request through the diagram proves the design actually *works* end-to-end rather than just looking plausible.
It's also where the interviewer's mental checklist lives; give them a clean flow and they can tick most of their boxes at once.

**Move 5: Call out the failure modes before the interviewer does.**
This is the highest-leverage move in the entire skeleton.
Unprompted, say: "Now, three ways this breaks. The model can return malformed output, so I validate every step and retry with the error message included. An early mistake compounds downstream, so I put checks between stages. And the whole thing can be slow, so here are my timeouts and my fallback."
Why this earns points: every interviewer keeps a private list of holes in your design, waiting to spring them.
Every hole you name first gets transferred from their column to yours.
Candidates who find their own failure modes read as people who have operated systems, not just built demos — and with LLMs, where the components are *probabilistic* (meaning the same input can produce different outputs on different runs), showing you expect failure is table stakes for being trusted with production.

**Move 6: Explain how you'd evaluate and monitor it.**
Answer the question nobody asked yet: "How do I know it works — today, and next month?"
Cover both halves.
Before launch: a test set of examples with known-good answers, scored automatically where possible (did the JSON parse? is the category right?) and by an LLM-as-judge or a human sample where quality is fuzzy.
After launch: tracing on every request, dashboards for latency, error rate, and cost, an SLO to alarm on, and a periodic human review of a random sample of outputs to catch quality drifting downward.
Why this earns points: this is the single most common gap between candidates who've shipped LLM systems and candidates who've only played with them.
Models get updated, users find weird inputs, quality decays silently — and interviewers know it.
Volunteering an evaluation story is often the moment the interview's tone shifts in your favor.

**Move 7: Mention cost, and what you'd cut under pressure.**
Close with money and pragmatism: "Rough cost: four calls per request, mostly on a small cheap model, the big model only for the final synthesis — order of a cent per request, so a thousand a day is ten dollars, fine. If leadership needed this shipped in a week, I'd cut the reflection loop and the fancy router, ship the two-step chain with good logging, and add the rest once real traffic tells us where quality actually hurts."
Why this earns points: cost-awareness signals business maturity, and the "what would you cut" answer signals judgment — knowing which parts of your own design are load-bearing and which are polish.
Ending here also leaves the interviewer with the impression of an engineer who ships, which is the impression that gets hired.

Here's the whole skeleton as a pocket reference — worth photographing into your brain:

| # | Move | Sounds like | What it's really scoring |
|---|------|-------------|--------------------------|
| 1 | Clarify | "Before I design — who consumes this, and what does a mistake cost?" | Seniority; solving the real problem |
| 2 | Baseline | "The dumbest version is one LLM call, and here's why that's not enough" | Judgment; resistance to over-engineering |
| 3 | Name the pattern | "This is a routing problem, because..." | Pattern recognition from experience |
| 4 | Boxes + data flow | "The email lands here, becomes this JSON, flows to..." | Decomposition; does it actually work |
| 5 | Failure modes | "Three ways this breaks, and here's my handling for each" | Production maturity |
| 6 | Eval + monitoring | "Golden set before launch; traces, dashboards, and an SLO after" | Have you ever shipped one of these |
| 7 | Cost + cuts | "About a cent a request; under deadline I'd cut X and keep Y" | Business sense; knowing what's load-bearing |

To make the skeleton concrete, here's the whole thing compressed into a thirty-second flyby — the kind of opening you might give before diving deep, using a toy question like "design an AI that answers questions about our product docs":
"Quick clarifications: internal users or customers, and how bad is a wrong answer? Assuming customers and that confident wrongness is the enemy.
Simplest version: stuff the docs in the prompt and ask — breaks the moment the docs outgrow the context window.
So: retrieval-augmented — embed the docs, fetch the relevant passages per question, ground the answer in them, and route the no-good-passage case to 'I don't know, here's a human.'
Flow: question in, retrieve top passages, one grounded LLM call, cite sources out.
Failure modes: retrieval misses — I tune and monitor that; hallucination — grounding instruction plus citation checks; latency — cache the frequent questions.
Eval: golden set of question-answer pairs, groundedness scored by judge; monitor answer rate, escalation rate, p95.
Cost: one small retrieval, one model call — a fraction of a cent; under deadline I ship retrieval plus honest 'I don't know' and skip the polish."
That's all seven moves in under a minute — in a real interview each move expands to two or three minutes, but the spine is identical, and having the spine means you can scale the same answer to whatever time the interviewer gives you.

A word on whiteboard mechanics, since the physical act trips people up more than the content.
Draw small and label everything — five boxes with named arrows beat twelve boxes of spaghetti, and the arrow labels (*what data* flows, not just that something flows) are where the credit lives.
Narrate while you draw; silence at the whiteboard reads as being lost even when you aren't.
Leave white space deliberately, because follow-ups will make you extend the diagram — the candidate who planned room for the retry loop looks prophetic; the one squeezing boxes into a corner looks surprised.
And when a question knocks you sideways, go back to the diagram and trace the flow with your finger — it restarts your thinking and shows the interviewer *where* in the system you're reasoning, which keeps the conversation concrete.

While we're being honest about scoring, let me also tell you the four most common ways candidates *lose* points, because avoiding a mistake is cheaper than earning a merit.
First: diving straight into architecture without clarifying — the single most frequent error, and it can sink an otherwise brilliant answer, because the interviewer watches you confidently build the wrong thing.
Second: complexity worship — proposing five agents, three loops, and a vector database for a problem one well-validated chain would solve; interviewers read this not as sophistication but as inexperience, because people who've carried a pager know every component is a thing that breaks at 2 a.m.
Third: the happy-path-only answer — a design narrated as if models never return garbage, APIs never time out, and users never type nonsense; with LLM systems this is disqualifying, because the components are *guaranteed* to misbehave some percent of the time.
Fourth: no numbers anywhere — never estimating latency, volume, or cost; you don't need precision, but an answer with zero numbers in it floats free of reality, and interviewers notice the weightlessness.

One last piece of advice on using the skeleton: don't recite it like a checklist — *inhabit* it.
The moves should come out as one flowing story: here's what you asked for, here's the simple version, here's why it's not enough, here's the pattern that fixes it, here's the machine, here's how it breaks, here's how I'd know, here's the bill.
Every model answer in this playbook follows exactly that arc, so by the fourth pattern the skeleton will be in your bones.
Now let's meet the patterns.
