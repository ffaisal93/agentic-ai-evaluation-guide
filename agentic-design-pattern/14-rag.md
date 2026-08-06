# Pattern 14: Knowledge Retrieval (RAG) — Giving the Model an Open Book

## The interview scenario

This is arguably the single most-asked agent design question in industry interviews. It
sounds like:

- "Design a support bot that answers questions from our internal docs — and never makes
  things up."
- "Our LLM keeps confidently citing product features that don't exist. How would you fix
  that?"
- "We have 50,000 pages of company wikis, policies, and manuals. Design a system so
  employees can just ask questions and get accurate, sourced answers."

Any time the question involves *private data* ("our docs"), *freshness* ("this changes
weekly"), or *trust* ("it must not hallucinate," "answers need citations"), the expected
backbone of your answer is Retrieval-Augmented Generation.

## What this pattern is, in plain words

A language model is a closed-book exam-taker. Everything it knows was baked in during
training, which means its knowledge is frozen at a point in time, and it has never seen
your company's private documents at all. Ask it about your refund policy and it faces a
bad choice: admit ignorance, or improvise something plausible. Improvising something
plausible-but-false is what everyone calls *hallucination*, and it's the core disease
this pattern treats.

Retrieval-Augmented Generation — RAG — turns the closed-book exam into an open-book one.
Before the model answers, the system goes and *looks things up*: it searches your
document collection for the passages most relevant to the question, staples those
passages onto the prompt, and instructs the model to answer *using only what it just
read* — and to cite it. The model stops being the source of facts and becomes a reading-
comprehension engine over facts you supplied. That reframing — "the model reasons, the
retrieval system knows" — is the one-line essence of RAG.

Unpack the name and you've explained the architecture: *Retrieval* (find the relevant
passages), *Augmented* (add them to the prompt), *Generation* (write the answer grounded
in them).

Why this beats the alternatives is a guaranteed follow-up, so have it ready. Versus
*fine-tuning* — actually retraining the model on your documents — RAG is cheaper,
updates instantly (fix the doc, the next answer is fixed; no retraining cycle), and
gives you citations, which fine-tuning fundamentally can't, because knowledge absorbed
into model weights has no page number. Fine-tuning is for teaching *style and skills*;
RAG is for teaching *facts*. Versus *long context* — just shoveling all your documents
into the model's prompt window — RAG wins on scale (50,000 pages won't fit no matter how
big the window gets), on cost (you pay for every token you send, every single question),
and often on accuracy, since models get demonstrably distracted digging a needle out of
a huge haystack of mostly-irrelevant text. The honest nuance: for a handful of
documents, skip RAG and use long context; the pipeline earns its complexity when the
corpus is big, changing, or needs access controls.

## How the design actually works

Tell the pipeline as a story in two acts: an offline act that prepares the library, and
an online act that answers a question. Every term below is one an interviewer may poke
at, so define each as you go.

**Act one: building the library (offline, runs whenever docs change).**

*Chunking* comes first: cutting documents into bite-sized passages. You can't treat a
50-page manual as one searchable unit — a question about one error code would match the
whole manual weakly instead of the right paragraph strongly. So you split along natural
seams: sections, then paragraphs, typically a few hundred words per chunk, with a slight
*overlap* between neighboring chunks so a sentence straddling a boundary isn't orphaned
from its context. Chunking sounds mundane and is actually one of the highest-leverage
quality decisions in the whole system: chunks too small lose context ("click the button"
— which button? in what dialog?), chunks too big bury the relevant sentence in noise.
You also attach *metadata* to each chunk — source document, section title, last-updated
date, access permissions — which pays off later for citations, freshness filtering, and
security.

*Embeddings* come second: turning each chunk of text into coordinates so similar
meanings sit near each other. An embedding model maps text to a long list of numbers — a
vector, a point in a space with hundreds or thousands of dimensions — arranged such that
texts with similar *meaning* land close together. "Furry feline companion" and "domestic
cat" share almost no words, but their points sit practically on top of each other, while
"car" is far away in another neighborhood. This is the trick that lets search understand
*meaning* instead of matching *words*.

*The vector database* comes third: a database purpose-built to store millions of these
points and answer, extremely fast, "which stored points are nearest to this query
point?" — using clever indexing algorithms (HNSW is the name worth knowing) so it
doesn't have to compare against every point. Names to drop if asked: Pinecone, Weaviate,
Chroma, Milvus, Qdrant, or plain Postgres with the pgvector extension — that last one is
a great pragmatic answer for teams that don't want a new database to operate.

**Act two: answering a question (online, per query).**

The user's question gets embedded with the same model, becoming a point in the same
space. *Vector search* finds the nearest chunk-points — semantically closest, even when
the wording differs completely. In practice you run *hybrid search*: semantic search
plus a classic keyword ranker called BM25, which scores literal word matches. Why both?
Semantic search can fumble exact identifiers — part numbers, error codes, names like
"ERR-4402" — that keyword search nails, while keyword search misses paraphrases that
semantic search nails. Merge both result lists and you cover each other's blind spots.

Then *reranking*: the first retrieval pass is built for speed across millions of chunks,
so it's approximate. You take its top fifty candidates and run a slower, smarter model
that reads the actual query and each actual chunk together and scores true relevance,
keeping the best five or so. Cheap-and-broad, then careful-and-narrow — the same two-
pass structure as a recruiter screening résumés before the hiring manager interviews
finalists.

Finally *grounded generation*: the winning chunks are pasted into the prompt with
instructions that boil down to "answer using only the context below; cite which passage
supports each claim; if the context doesn't contain the answer, say you don't know."
That refusal instruction is your primary hallucination valve — you're giving the model
explicit permission to not know, which removes its incentive to improvise. Citations do
double duty: users can verify, and you can audit.

**The evolution step: agentic RAG.** Classic RAG is a fixed pipeline — retrieve once,
answer, done, even if the retrieval was garbage. Agentic RAG puts an agent in charge of
retrieval as a *decision*, not a reflex. The agent decides *whether* to retrieve at all
(skip it for "hi there"), *what* to search for (rewriting vague user phrasing into sharp
queries, or decomposing "compare our pricing to Competitor X's" into several sub-
searches whose results it synthesizes), *whether the results are good* (judging
relevance, preferring the official 2025 policy over a stale 2020 blog post, reconciling
a proposal that says €50,000 against a financial report that says €65,000 by trusting
the more authoritative source), and *what to do about bad results* (retry with a
reformulated query, or fall back to a live web search when the internal knowledge base
has a gap). The trade: each judgment loop is more model calls, so agentic RAG buys
reliability with latency and cost. Related buzzword to acknowledge in one line: GraphRAG
stores knowledge as a graph of entities and relationships instead of a bag of chunks,
which shines when answers require connecting facts scattered across documents — at
substantially higher build-and-maintain cost.

## The complete interview answer, spoken

Here's the whole thing spoken aloud for "design a support bot over our internal docs
that never makes things up."

"Let me start with a few questions. How big is the corpus and how fast does it change —
thousands of pages updated daily, or hundreds updated quarterly? Who are the users —
customers, or internal support engineers? And do documents have access restrictions, or
can anyone see everything?"

*(Interviewer: ~40,000 pages of product docs and internal runbooks, updated daily, used
by support engineers; some runbooks are restricted.)*

"Perfect — that profile rules out the two lazy solutions immediately. Fine-tuning is out
as the knowledge store because daily updates would mean perpetual retraining, and it
can't cite sources, which we need for trust. Stuffing everything into the context window
is out because 40,000 pages won't fit, and even if it did, we'd pay to reprocess the
entire corpus on every single question. So this is a textbook RAG system, and given the
'never makes things up' requirement, I'll layer agentic retrieval and grounding checks
on top of the basic pipeline. Whiteboard:

```
 OFFLINE (ingestion, runs on every doc change)
 docs --> chunker --> embedding model --> vector DB
             |                              (chunks + metadata:
             +--> metadata extraction        source, date, ACL)

 ONLINE (per query)
 question --> [agent: retrieve? rewrite? decompose?]
                  |
                  v
       hybrid search (vector + keyword BM25, ACL-filtered)
                  |         top ~50
                  v
              reranker  --> top ~5 chunks
                  |
        agent judges quality ----- weak? ---> rewrite query & retry
                  | good                      (max 2 retries, then
                  v                            say "I don't know")
       LLM: grounded generation
       "answer ONLY from context, cite sources, else say so"
                  |
                  v
       groundedness check --> answer + citations --> engineer
```

Start with ingestion, because RAG quality is mostly decided offline. A pipeline watches
the doc sources; when a page changes, we re-chunk and re-embed just that page —
incremental, not a nightly full rebuild, since stale answers about a runbook that
changed this morning are dangerous in support. I'd chunk along the docs' own structure —
headings and sections, a few hundred words with overlap — because these are manuals, and
a section is the natural unit of one topic. Every chunk carries metadata: source URL,
section title, last-modified date, and crucially an access-control list. Restricted
runbooks get filtered *inside* the search query by the asking engineer's permissions —
retrieval must never surface a chunk the user couldn't open directly, otherwise the bot
becomes a data-leak machine. That's a security point most candidates miss.

Online path: an engineer asks 'customer's export job hangs at 90% — what do I check?'
The agent first decides whether retrieval is needed — here, obviously yes — and rewrites
the conversational phrasing into sharper search queries, maybe two: one about export job
failures, one about job-queue diagnostics. Hybrid search runs both: vector search
catches runbooks that say 'stalled batch processing' without ever using the word
'hangs,' while the keyword side catches exact error codes and product names that
embeddings are wobbly on. Top fifty candidates go to the reranker, which reads query and
chunk together and keeps the best handful.

Now the step that earns the 'never makes things up' requirement. Before generating, the
agent sanity-checks the winners: are these actually about the export feature? Are any
obsolete — superseded by a newer runbook, judged by that last-modified metadata? If two
chunks conflict, prefer the authoritative, current one. If the whole result set is weak,
don't answer from garbage: reformulate the query and retry, at most twice. And if
retrieval still comes up empty, the bot says 'I couldn't find this in the docs' and
offers to file a doc-gap ticket. A support bot that knows when it doesn't know is the
entire ballgame — an 'I don't know' costs an escalation to a human; a confident
fabrication costs a wrong fix on a customer system and the team's trust in the bot
forever. The failure modes have wildly asymmetric costs, so I bias every threshold
toward refusal.

Generation is strictly grounded: the prompt says answer only from the provided context,
attach a citation to each claim, say so if the context is insufficient. Then one more
guard: a groundedness check, a cheap second model pass asking 'is every claim in this
answer supported by the retrieved text?' Unsupported claims get stripped or the answer
gets demoted to 'here are the relevant docs' with links. Belt and suspenders, because
the requirement was *never*.

Failure handling beyond that: vector DB down — degrade to keyword-only search over a
standard search index, worse but alive. Ingestion pipeline stuck — alert on index
staleness, and surface each answer's source dates so engineers can see they're reading
last week's truth. Embedding-model upgrades are a subtle one: new model means new
coordinate space, so you must re-embed the entire corpus — you can't mix vectors from
two models in one index. That's a planned migration, blue-green: build the new index
alongside, flip, keep the old one for rollback.

Evaluation, because 'never makes things up' must be measurable. I'd build a golden set
of a few hundred real support questions with expert-verified answers and source pages,
and track three layers: retrieval recall — did the right chunk appear in the top
results? — answer correctness against the golden answers, and groundedness — what
fraction of claims are supported by citations? Layered metrics matter because they
localize failures: bad retrieval means fix chunking or search; good retrieval but bad
answers means fix the prompt or model. This suite runs on every change to chunking,
models, or prompts — chunking tweaks feel harmless and can quietly wreck recall. In
production: thumbs-up/down from engineers, citation click-through as a proxy for trust,
and the 'I don't know' rate — rising might mean doc gaps, falling might mean the refusal
valve is loosening.

Cost, briefly: embeddings are cheap — pennies per thousand pages, so ingestion is a
rounding error. The per-query cost is dominated by generation, a few cents with a mid-
tier model; the agentic judgment loops maybe double it, and at internal-support volume —
thousands of queries a day, not millions — that's tens of dollars a day. Against ten
minutes of engineer search time saved per query, the ROI argument makes itself. If
volume ever explodes, the levers are caching answers to repeated questions and routing
easy queries to a cheaper generation model — which is really the resource-aware pattern,
and I'd say so.

Summary: an incrementally-updated, permission-aware index built on careful chunking;
hybrid retrieval plus reranking to find truth; an agent that judges and retries
retrieval instead of trusting it blindly; generation that's grounded, cited, and allowed
to say 'I don't know'; and a layered eval suite so 'never makes things up' is a number
we track, not a hope."

## Follow-ups they will ask

**"Why not just fine-tune the model on our docs?"** Fine-tuning teaches style and
skills, not reliable facts: knowledge melts into the weights with no citation, no per-
document update (daily doc changes would mean perpetual retraining), no per-user access
control, and no strong guarantee against hallucination. RAG gives instant updates,
citations, and permission filtering. Best-of-both answer: fine-tune for tone and format,
RAG for facts.

**"Context windows are getting huge — is RAG dead?"** No, but its boundary moved. For a
handful of documents, long context is simpler and better — no pipeline to build. RAG
still wins when the corpus can't fit (tens of thousands of pages), when you'd pay to
resend the corpus with every query, when retrieval-then-read beats needle-in-haystack
attention over mostly-irrelevant text, and when you need per-user permission filtering —
you can't put restricted docs in a shared prompt.

**"What's your chunking strategy and why does it matter so much?"** Chunking decides
what a 'searchable unit of meaning' is. Split on document structure
(sections/paragraphs), a few hundred words, with overlap so boundary sentences keep
context; attach metadata. Too small loses context, too big buries the signal. Say that
you'd A/B chunking against retrieval-recall metrics rather than picking by folklore —
that's the senior move.

**"The answer needs facts from three different documents. Now what?"** Single-shot
retrieval's classic weakness. Answers: retrieve more chunks and let the model
synthesize; agentic decomposition — split the question into sub-queries, retrieve per
sub-query, synthesize; or GraphRAG, which pre-encodes cross-document relationships as an
entity graph — strongest for relationship-hopping questions, priciest to build and keep
current.

**"How do you actually measure hallucination?"** Groundedness checking: for each claim
in the answer, verify it's entailed by the retrieved passages — via an LLM-as-judge pass
at serving time or offline over samples, plus a golden set with known answers, and human
audits of a sample of "confident" answers. Track unsupported-claim rate as a first-class
metric with an alerting threshold, like any error rate.

**"When retrieval returns nothing good, what should the system do?"** Escalating ladder:
rewrite the query and retry; broaden filters; fall back to an alternative source (web
search, if policy allows) clearly labeled as external; finally refuse honestly and route
to a human or file a doc-gap ticket. The one forbidden behavior is answering anyway from
the model's parametric memory while *appearing* grounded — that's the exact
hallucination path RAG exists to close.

## Say it in one breath

"RAG turns a closed-book model into an open-book one: chop documents into bite-sized
chunks, embed them as coordinates where similar meanings sit near each other, store them
in a vector database, retrieve the nearest chunks to each question with hybrid search
plus a reranker, and have the model answer only from what it just read, with citations
and permission to say 'I don't know' — beating fine-tuning on freshness and attribution
and long context on scale and cost — and in the agentic version the agent decides when
and what to retrieve, judges the results, retries bad retrievals, and reconciles
conflicts before it ever generates a word."
