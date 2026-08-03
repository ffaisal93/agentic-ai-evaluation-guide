# Benchmark Datasets for Agent Evaluation

> **Why this matters.** Your evaluation is only as good as its data. You can build the most careful harness, the most rigorous metrics, and the most beautiful dashboards — and if the underlying tasks are ambiguous, mislabeled, too easy, or already sitting in your model's pretraining corpus, every number you report is fiction. This chapter is deliberately *not* about metrics (that is Chapter 3). It is about the **data**: how to use standard benchmarks without fooling yourself, how to build a custom benchmark for your own agent and domain, how to prove the dataset is actually good (coverage, calibration, label correctness, inter-annotator agreement), how to keep it out of the training set, when synthetic data helps and when it lies, and how to version, license, and document what you ship.

---

## 1. Core intuition: the dataset is the ruler

A benchmark dataset is a **measuring instrument**. When you report "our agent scores 71%," you are reading a number off a ruler. If the ruler's tick marks are unevenly spaced (difficulty not calibrated), some marks are in the wrong place (bad labels), or the ruler has been photographed and memorized by the thing you are measuring (contamination), the reading is meaningless — no matter how precisely you read it.

Three intuitions carry the whole chapter:

1. **Garbage tasks beat good models.** A single ambiguous task with a wrong golden answer can flip a leaderboard ranking. SWE-bench's original test set had tasks where the hidden unit tests rejected *correct* patches; OpenAI found this affected a majority of samples (§4). If your data is noisy, you are ranking noise.
2. **A benchmark answers exactly one question, and you must know which.** "Can the agent book a flight?" and "Can the agent book a flight *reliably across 8 tries under an adversarial user*?" are different questions requiring different data. τ-bench exists because the second question needs multi-trial tasks with state-based checks, not single-shot Q&A.
3. **Every public benchmark is decaying the moment it is published.** The internet ingests it, the next pretraining run swallows it, and contamination silently inflates scores. A good data strategy plans for this from day one with held-out and canary sets.

---

## 2. Anatomy of a good benchmark dataset

Whether you use one off the shelf or build your own, a benchmark dataset has the same load-bearing parts. If any are missing, be suspicious.

| Component | What it is | Why it matters |
|---|---|---|
| **Task instances** | The individual problems the agent must solve (a GitHub issue, a customer request, a web goal) | These *are* the benchmark; everything else supports them |
| **Ground truth** | The correct answer, final state, or reference trajectory | Determines what "success" means; the #1 source of silent error |
| **Verifier / scorer** | The mechanism that decides pass/fail (unit tests, state diff, exact match, LLM judge) | A benchmark is task + verifier; a task with no reliable verifier is not a benchmark |
| **Difficulty spread** | A range from easy to hard, ideally with labeled tiers | Flat difficulty gives no signal; you need discrimination across systems |
| **Metadata** | Per-task tags: domain, tools required, length, source, license, creation date | Enables slicing, contamination checks, and honest reporting |
| **Splits** | Public/dev vs. held-out/private vs. canary | Lets you develop without overfitting and detect leakage |
| **Datasheet** | Human-readable documentation of provenance, collection, and intended use | The difference between a dataset and a pile of JSON |

### 2.1 What ground truth looks like for agents

For agents, "ground truth" is rarely a single string. It comes in three common shapes:

- **Outcome / state-based** (τ-bench, WebArena): success = the final world state matches an annotated goal state (the DB row was updated, the item is in the cart). Robust to *how* the agent got there. Requires an executable environment.
- **Reference-answer** (GAIA): success = the agent's final answer matches a single unambiguous gold answer under quasi-exact match. Cheap to score, but only works when the answer is short and unique.
- **Reference-trajectory / test-based** (SWE-bench): success = the agent's artifact (a code patch) makes a set of `FAIL_TO_PASS` and `PASS_TO_PASS` tests go green. Verifiable and objective, but only as fair as the tests.

> Rule of thumb: prefer *executable* ground truth (tests, state diffs) over *judged* ground truth (LLM-as-judge, human rubric) whenever the domain allows it. Executable checks do not drift, do not have mood, and cost nothing to re-run.

### 2.2 Case studies: how the majors built their data

**SWE-bench Verified** — the canonical lesson in why data quality dominates. The original SWE-bench scraped real GitHub issues + PRs from popular Python repos and used the PR's tests as the verifier. But OpenAI, working with the SWE-bench authors, had **93 experienced Python developers** manually screen **1,699** randomly sampled instances, producing a filtered set of **500** ("Verified"). They rated two failure modes on a 0–3 severity scale: **underspecified problem statements** (found in ~38% of samples) and **unit tests that would reject a valid solution** (~61%). Each sample was independently annotated by **3 developers**, ensembled by taking the *highest* severity label (conservative — bias toward exclusion). GPT-4o jumped from ~16% on the original set to ~33% on Verified — the same model, a cleaner ruler. ([OpenAI](https://openai.com/index/introducing-swe-bench-verified/), [dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified))

**GAIA** — **466** questions that are "conceptually simple for humans yet challenging for advanced AIs," designed so that **humans score ~92%** while GPT-4 with plugins scored **~15%**. Three difficulty **levels** by the number of steps and tools required: Level 1 (few steps, at most one tool), Level 2 (several steps, multiple tools), Level 3 (long open-ended tool use). Each question has a **single unambiguous answer** graded by quasi-exact match, and 300 answers are held private for the leaderboard. The design philosophy is a deliberate inversion of "make it harder for humans." ([arXiv](https://arxiv.org/abs/2311.12983))

**τ-bench** — tasks in **retail** and **airline** domains where a language agent talks to an **LLM-simulated user** while calling domain APIs under written policy. Success is scored by **comparing the final database state to an annotated goal state** — objective, no judge. It introduced **pass^k** (the probability all k independent trials of a task succeed) to measure *reliability*, not just average success; even strong models fell below 25% pass^8 in retail. Task authoring bundles a database schema, an API/tool set, a policy document, and per-task goal states. ([arXiv](https://arxiv.org/abs/2406.12045), [Sierra](https://github.com/sierra-research/tau2-bench))

**WebArena** — **812** tasks over **self-hostable, reproducible** web apps (a fork of GitLab, a Reddit-like forum, an e-commerce CMS, a wiki). Because the sites are self-hosted and deterministic, evaluation uses **functional correctness** — programmatic checks on the resulting page/DB state or exact information match — rather than screenshots. The reproducible environment *is* the ground truth. ([arXiv](https://arxiv.org/pdf/2307.13854), [repo](https://github.com/web-arena-x/webarena))

The pattern across all four: **objective, executable verifiers + explicit human quality control + difficulty tiers.** Copy that pattern.

---

## 3. Using standard benchmarks correctly

Off-the-shelf benchmarks are tempting because they give you comparability. They also give you a dozen ways to lie to yourself.

**Do:**
- **Pin the exact version and split.** "SWE-bench" is ambiguous; "SWE-bench Verified, 500 instances, HF revision `abc123`" is not.
- **Report the harness.** The same tasks under different scaffolds (retrieval, max turns, tool set) produce wildly different scores. State yours.
- **Report trials and variance.** Agents are stochastic. One seed is an anecdote. Report pass@k / pass^k and dispersion (Chapter 3).
- **Slice by metadata.** A single aggregate hides that you fail every Level-3 GAIA task. Break down by difficulty tier and domain.
- **Check the benchmark's own known errata.** Most mature benchmarks publish a list of retired/broken tasks. Use it.

**Don't:**
- **Don't tune on the test set.** If you iterate against the public benchmark, you are overfitting to it. Keep a private slice you look at rarely.
- **Don't compare across harness versions** as if they were the same experiment.
- **Don't assume the benchmark measures what its name says.** SWE-bench measures "resolve a scraped GitHub issue whose PR had good tests," which is narrower than "software engineering." Read the datasheet.
- **Don't ignore contamination just because the benchmark is popular** — popularity *causes* contamination (§6).

---

## 4. Building a custom benchmark, step by step

Standard benchmarks rarely match your agent's actual job. When you build your own, treat it as a small research project with reviews and acceptance criteria, not a spreadsheet someone fills in on a Friday.

**Step 1 — Define the question and the unit of evaluation.** Write one sentence: "Can our support agent resolve a billing dispute end-to-end, correctly updating the ledger, under our refund policy?" That sentence fixes the domain, the ground-truth shape (state-based ledger diff), and the verifier.

**Step 2 — Source raw tasks.** Prefer real distribution over invented tasks. Good sources, roughly in order of value:
- **Production logs / transcripts** (anonymized) — the true distribution of what users ask. Sample stratified by intent so rare-but-critical cases appear.
- **Domain experts** authoring realistic scenarios the logs miss (edge cases, adversarial users).
- **Existing tickets, docs, or issue trackers** — like SWE-bench mining GitHub.
- **Synthetic generation** (§7) — to fill coverage gaps, never as the backbone.

**Step 3 — Author golden answers / trajectories.** For each task, produce the ground truth and, crucially, the *verifier*. This is where most of the work is:
- For state-based tasks: write the goal-state assertion (SQL/JSON diff) and a **seed database** the task runs against.
- For answer-based tasks: write the unambiguous gold answer *and* the matching rule (exact, numeric-tolerance, set-equality).
- For trajectory-based tasks: write reference tests, and — as SWE-bench learned — also `PASS_TO_PASS` guards so an agent cannot "fix" the issue by breaking everything else.

**Step 4 — Calibrate difficulty.** Run 2–3 baselines (a weak model, a strong model, a human). Bucket tasks by observed solve rate: **easy** (>80% solve), **medium** (20–80%), **hard** (<20%). A benchmark where every task is solved or none is has zero discriminative power. Aim for a spread centered where you expect frontier systems to sit, so the ruler has ticks near the interesting region.

**Step 5 — Review.** Every task gets independent review by ≥2 people who did *not* author it, checking: (a) is the problem statement fully specified? (b) is the gold answer correct? (c) does the verifier accept all correct solutions and reject all wrong ones? Adopt SWE-bench's conservative ensembling: if any reviewer flags a severe problem, pull the task.

**Step 6 — Measure quality.** Compute inter-annotator agreement (§5), coverage against your intent taxonomy, and a contamination scan (§6) before you trust a single score.

**Step 7 — Version, document, license (§8).** Freeze it, datasheet it, and split off a held-out canary set before anyone runs an agent on it.

> Coverage checklist: build an explicit **taxonomy** of the capabilities/intents you care about (e.g., refund, address-change, plan-upgrade, fraud-hold) and require ≥N tasks per cell, including the adversarial and multi-tool cells. Coverage is a property you *design in*, not one you hope for.

---

## 5. Validating quality: inter-annotator agreement

If two competent humans disagree about whether a task's answer is correct, the *task* is broken, not the annotators. Inter-annotator agreement (IAA) quantifies this. Raw percent agreement is misleading because raters agree partly **by chance** — if 90% of items are "pass," two raters who guess "pass" blindly agree 81% of the time while knowing nothing. Chance-corrected agreement fixes this.

### 5.1 Cohen's kappa (two annotators)

Cohen's \( \kappa \) compares observed agreement to chance agreement:

\[
\kappa = \frac{p_o - p_e}{1 - p_e}
\]

where \( p_o \) is the observed proportion of items the two raters agree on, and \( p_e \) is the agreement expected by chance, computed from each rater's marginal label frequencies:

\[
p_e = \sum_{c} \left( \frac{n_{1c}}{N} \cdot \frac{n_{2c}}{N} \right)
\]

Here \( c \) indexes categories, \( n_{1c} \) is how many items rater 1 put in category \( c \), and \( N \) is the number of items. \( \kappa = 1 \) is perfect agreement, \( \kappa = 0 \) is chance-level, and negative means worse than chance.

**Worked calculation.** Two reviewers label \( N = 100 \) agent outputs as **pass** or **fail**. The confusion matrix:

|  | R2: pass | R2: fail | R1 total |
|---|---|---|---|
| **R1: pass** | 45 | 10 | 55 |
| **R1: fail** | 15 | 30 | 45 |
| **R2 total** | 60 | 40 | 100 |

Observed agreement (the diagonal):
\[
p_o = \frac{45 + 30}{100} = 0.75
\]

Chance agreement from the marginals (R1 pass = 0.55, R2 pass = 0.60; R1 fail = 0.45, R2 fail = 0.40):
\[
p_e = (0.55 \times 0.60) + (0.45 \times 0.40) = 0.33 + 0.18 = 0.51
\]

Therefore:
\[
\kappa = \frac{0.75 - 0.51}{1 - 0.51} = \frac{0.24}{0.49} \approx 0.49
\]

So despite 75% raw agreement, chance-corrected agreement is only **~0.49 — "moderate."** That is a warning sign: a nontrivial share of your tasks are ambiguous enough that trained reviewers split on them, and any score you compute on this set inherits that noise.

### 5.2 Interpreting kappa (Landis & Koch scale)

| \( \kappa \) | Interpretation |
|---|---|
| < 0.00 | Worse than chance |
| 0.00–0.20 | Slight |
| 0.21–0.40 | Fair |
| 0.41–0.60 | Moderate |
| 0.61–0.80 | Substantial |
| 0.81–1.00 | Almost perfect |

For a benchmark you will publish scores from, target **\( \kappa \ge 0.7 \)** on label correctness. Below that, revise task wording and rubrics before proceeding — low agreement is a data-quality bug, not a personality difference.

### 5.3 Fleiss' kappa (three or more annotators)

When each item is rated by \( n \) raters (possibly a different panel per item) across \( k \) categories, use Fleiss' \( \kappa \). Build \( N \times k \) matrix \( M \) where \( M_{ij} \) = number of raters assigning item \( i \) to category \( j \) (each row sums to \( n \)).

Per-item agreement:
\[
P_i = \frac{1}{n(n-1)} \left( \sum_{j=1}^{k} M_{ij}^2 - n \right)
\]

Mean observed agreement and per-category expected probability:
\[
\bar{P} = \frac{1}{N} \sum_{i=1}^{N} P_i, \qquad p_j = \frac{1}{N n} \sum_{i=1}^{N} M_{ij}, \qquad P_e = \sum_{j=1}^{k} p_j^2
\]

\[
\kappa = \frac{\bar{P} - P_e}{1 - P_e}
\]

The same [0,1] interpretation applies. Beyond the aggregate score, the per-item \( P_i \) tells you *which* tasks are contentious — those are the ones to fix or cut.

---

## 6. Contamination and leakage

**Contamination** is when your evaluation data (or something too close to it) has leaked into the model's training set, so the model "solves" tasks by recall rather than capability. It is the single most under-reported source of inflated agent scores.

### 6.1 How it happens

- **Direct ingestion.** You benchmark on a public dataset; a later pretraining crawl scoops up the dataset, its GitHub repo, and every blog post quoting it.
- **Solution leakage.** For SWE-bench-style tasks, the *fixing PR and its discussion* are on the public web — the model may have seen the exact patch.
- **Indirect / paraphrase leakage.** The model saw a reworded version (a tutorial, a Kaggle notebook, a Stack Overflow answer), so n-gram checks miss it.
- **Dev-to-test bleed.** Your team tunes prompts against the "held-out" set until it is effectively training data. This is contamination you cause yourself.

### 6.2 How to detect it

| Method | How it works | Access needed | Catches |
|---|---|---|---|
| **N-gram / string overlap** | Look for long exact substrings shared between test items and the training corpus | Training corpus | Direct copies |
| **Canary strings** | Embed a unique GUID in the dataset; later, prompt the model to reproduce it | Model (black-box) | Whole-dataset ingestion |
| **Perplexity / Min-K%** | Memorized text has anomalously low perplexity / few low-probability tokens vs. fresh text | Token logprobs | Memorization |
| **Guided / quiz prompting** | Give the first half of a test item; see if the model completes the exact continuation | Model (black-box) | Instance memorization |
| **Perturbation probing** | Offer the original vs. reworded variants; a model that always picks the original memorized it | Model (black-box) | Instance memorization |
| **Timestamp / recency split** | Score tasks created *after* the model's training cutoff separately | Metadata | Temporal leakage |

([Survey on data contamination](https://arxiv.org/html/2502.14425v2))

### 6.3 How to prevent it

- **Canary GUID.** Ship the dataset with a unique random string and publicly ask trainers to exclude any document containing it (the BIG-bench canary convention). It does not stop contamination but makes it detectable and gives trainers a filter.
- **Hold out a private test set.** Publish a dev split; keep the scoring split behind an API or fully offline. GAIA keeps 300 answers private; τ-bench and SWE-bench evolve. This is the only robust defense.
- **Rotate and refresh.** Treat benchmarks as perishable. Add new post-cutoff tasks each cycle; retire tasks once solve rates saturate suspiciously.
- **Encrypt / gate.** Distribute test payloads encrypted or under access agreements so crawlers cannot ingest raw text.
- **Recency-stratify.** Always keep a slice of tasks provably created after the newest model's cutoff, and watch for a score cliff between pre- and post-cutoff tasks — that cliff *is* the contamination signal.

> Discipline beats cleverness here: a well-guarded held-out set of 50 fresh tasks is worth more than a 5,000-task public benchmark everyone (and every crawler) has seen.

---

## 7. Synthetic data for evals

LLM-generated tasks are attractive: cheap, scalable, and able to hit coverage gaps on demand. **Self-Instruct** is the canonical recipe — bootstrap from a small pool of human-written seed tasks (the paper used **175** seeds) and prompt an LLM to generate many more (they reached **~52K** instructions), then **filter** aggressively for validity and diversity (e.g., drop new tasks whose ROUGE-L overlap with existing ones exceeds a threshold). ([Self-Instruct](https://arxiv.org/abs/2212.10560))

**When synthetic data helps:**
- **Coverage of rare/edge cases** you cannot find enough of in logs (fraud attempts, policy-corner requests).
- **Scaling up structure** once you have a validated template and verifier (parameterize a known-good task family).
- **Adversarial/red-team inputs** where you want systematic variation.
- **Privacy** — generating synthetic analogues of sensitive real transcripts.

**The risks — and they are serious for evals specifically:**
- **The generator's blind spots become the benchmark's blind spots.** If a model generates and (implicitly) knows how to solve the tasks, you measure agreement with the generator, not capability.
- **Self-contamination.** Tasks generated by model X are trivially easy for model X and its relatives.
- **Distribution drift.** Synthetic tasks cluster around the generator's priors and miss the messy, ungrammatical, contradictory reality of real users.
- **Unverified gold answers.** LLM-authored "correct" answers are frequently wrong. Never trust a synthetic label without a check.

**Rules for using synthetic eval data safely:** (1) always pass every synthetic task through **human filtering** and an **independent verifier**; (2) use a *different, stronger* model to generate than the ones you evaluate, and never the one under test; (3) keep synthetic tasks a labeled *minority* of the benchmark, sitting on top of a real-data core; (4) report the synthetic fraction. Synthetic data is a coverage tool, not a foundation.

---

## 8. A fully worked example

The code below (a) computes Cohen's and Fleiss' kappa on annotations and flags low-agreement items for review, and (b) runs a simple n-gram contamination check between test tasks and a training corpus. Pure standard library plus optional scikit-learn.

```python
"""Benchmark dataset QA: inter-annotator agreement + contamination check."""
from collections import Counter
from itertools import combinations


# ---------- 1. Cohen's kappa (2 annotators) ----------
def cohens_kappa(a, b):
    """a, b: equal-length lists of categorical labels from two raters."""
    assert len(a) == len(b) and len(a) > 0
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n           # observed agreement
    ca, cb = Counter(a), Counter(b)
    cats = set(ca) | set(cb)
    p_e = sum((ca[c] / n) * (cb[c] / n) for c in cats)    # chance agreement
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


# ---------- 2. Fleiss' kappa (n raters, per-item panel) ----------
def fleiss_kappa(ratings):
    """ratings: list of items; each item is a list of labels (one per rater).
    Assumes a fixed number of raters n per item."""
    cats = sorted({lbl for item in ratings for lbl in item})
    idx = {c: j for j, c in enumerate(cats)}
    N = len(ratings)
    n = len(ratings[0])
    assert all(len(item) == n for item in ratings), "fixed rater count required"

    M = [[0] * len(cats) for _ in range(N)]               # N x k count matrix
    for i, item in enumerate(ratings):
        for lbl in item:
            M[i][idx[lbl]] += 1

    P_i = [(sum(c * c for c in M[i]) - n) / (n * (n - 1)) for i in range(N)]
    P_bar = sum(P_i) / N
    p_j = [sum(M[i][j] for i in range(N)) / (N * n) for j in range(len(cats))]
    P_e = sum(p * p for p in p_j)
    kappa = 1.0 if P_e == 1 else (P_bar - P_e) / (1 - P_e)
    return kappa, P_i                                     # P_i flags contentious items


def flag_low_agreement(ratings, threshold=0.5):
    """Return indices of items whose per-item agreement P_i is below threshold."""
    _, P_i = fleiss_kappa(ratings)
    return [i for i, p in enumerate(P_i) if p < threshold]


# ---------- 3. Simple n-gram contamination check ----------
def ngrams(text, n=8):
    toks = text.lower().split()
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def contamination_score(test_item, corpus_ngrams, n=8):
    """Fraction of the test item's n-grams that appear in the training corpus.
    ~0 = clean; near 1 = the item is essentially in the corpus."""
    tg = ngrams(test_item, n)
    if not tg:
        return 0.0
    return len(tg & corpus_ngrams) / len(tg)


def scan_contamination(test_items, corpus_texts, n=8, flag_at=0.5):
    corpus_ngrams = set()
    for doc in corpus_texts:
        corpus_ngrams |= ngrams(doc, n)
    flagged = []
    for i, item in enumerate(test_items):
        s = contamination_score(item, corpus_ngrams, n)
        if s >= flag_at:
            flagged.append((i, round(s, 3)))
    return flagged


# ---------- Demo ----------
if __name__ == "__main__":
    # Two reviewers labeling 6 agent outputs pass(1)/fail(0)
    r1 = [1, 1, 0, 1, 0, 1]
    r2 = [1, 0, 0, 1, 0, 1]
    print("Cohen's kappa:", round(cohens_kappa(r1, r2), 3))

    # Three reviewers per item, 6 items
    panel = [
        [1, 1, 1],   # unanimous pass
        [1, 0, 1],   # split -> low P_i
        [0, 0, 0],   # unanimous fail
        [1, 1, 0],   # split
        [0, 0, 0],
        [1, 1, 1],
    ]
    k, P_i = fleiss_kappa(panel)
    print("Fleiss' kappa:", round(k, 3))
    print("Low-agreement items:", flag_low_agreement(panel, threshold=0.5))

    # Contamination: test task vs. a training corpus containing a near-copy
    tests = ["reset the user password and email a confirmation to the account owner"]
    corpus = ["to reset the user password and email a confirmation to the account owner you call ..."]
    print("Contamination flags:", scan_contamination(tests, corpus, n=6, flag_at=0.4))
```

Notes on correctness and use:
- `cohens_kappa` reproduces the §5.1 worked value on the 100-item matrix (feed it the expanded label lists) and returns ~0.49.
- `fleiss_kappa` returns both the aggregate and the per-item \( P_i \); route items below your threshold back to a third reviewer or cut them.
- The n-gram scanner is a **screen, not a proof** — it catches direct/near-direct copies at the chosen `n`. Lower `n` catches more (and more false positives); it will *not* catch paraphrase leakage, for which you need the perplexity/probing methods in §6.2. In production, hash n-grams and use a Bloom filter or MinHash/LSH so you can scan a test set against a terabyte-scale corpus without holding it in RAM.

---

## 9. Versioning, licensing, and datasheets

A benchmark you cannot cite exactly is a benchmark you cannot trust. Treat datasets like software releases.

**Versioning.**
- **Immutable, semantic versions.** `v1.0.0`, `v1.1.0` (added tasks), `v2.0.0` (changed a verifier — breaking). Never mutate a released version in place; a score is only comparable within a fixed version.
- **Content-hash every task** and record the set hash for a release, so anyone can verify they ran the exact data you did.
- **Changelog + errata.** Log every task added, retired, or corrected, with a reason. Retire (don't silently delete) broken tasks so old results remain interpretable.
- **Track provenance and creation date per task** — essential for the recency-stratified contamination check.

**Licensing.**
- **Know the license of every source.** Scraped GitHub code carries the repo's license; production transcripts carry privacy obligations; another benchmark's tasks carry *its* license (many are research-only / non-commercial).
- **Choose a clear license for your release.** Permissive (CC-BY, Apache-2.0, MIT) maximizes reuse; a custom eval license or gated access may be warranted for a held-out set you must keep uncontaminated.
- **PII and consent.** If tasks derive from real user data, anonymize, get consent where required, and document the process. This is a legal and ethical requirement, not a nicety.

**Datasheets.** Ship a **datasheet** (Gebru et al.) alongside the data answering: *motivation* (why it was created, by whom, funded how), *composition* (what a task is, how many, what's labeled, sensitive content), *collection* (sources, sampling, who annotated, IAA achieved), *preprocessing/cleaning*, *uses* (intended and out-of-scope), *distribution and license*, and *maintenance* (who owns it, how errata are handled, how it's versioned). This is the artifact that turns your JSON into an instrument other people can trust and critique. ([Datasheets for Datasets](https://arxiv.org/pdf/1803.09010))

---

## 10. Failure modes and pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| **Ambiguous tasks** | Low inter-annotator \( \kappa \); reviewers argue | Rewrite for a single unambiguous answer; cut irreparable ones |
| **Wrong golden answers** | Strong agents "fail" tasks humans solve trivially | Independent gold-answer review; executable verifiers |
| **Over-strict verifiers** | Correct solutions rejected (SWE-bench's original flaw) | Add `PASS_TO_PASS` guards; test the verifier against known-good and known-bad solutions |
| **Flat difficulty** | Every system scores ~the same | Calibrate with baselines; ensure an easy/medium/hard spread |
| **Contamination** | Score cliff between pre- and post-cutoff tasks; suspicious jumps | Canary strings, held-out set, recency split |
| **Test-set overfitting** | Dev score climbs, real-world flat | Freeze a private slice; look at it rarely |
| **Synthetic monoculture** | High scores that don't transfer to production | Human-filter; keep synthetic a minority; verify labels |
| **Aggregate-only reporting** | One number hides total failure on a whole category | Report per-slice and per-difficulty; publish variance |
| **Silent mutation** | Old and new scores incomparable | Semantic versioning + content hashes + changelog |
| **Too small** | Score swings wildly between runs | Power-check size; report confidence intervals |

---

## 11. Tools and datasets

| Name | Type | What it gives you | Link |
|---|---|---|---|
| SWE-bench / Verified | Coding benchmark | 500 human-vetted real GitHub issues, test-based scoring | [swebench.com](https://www.swebench.com/verified.html) |
| GAIA | General-assistant benchmark | 466 tool-use questions, 3 difficulty levels, private answers | [arXiv](https://arxiv.org/abs/2311.12983) |
| τ-bench / τ²-bench | Tool-agent-user | State-based scoring, pass^k reliability, retail/airline | [repo](https://github.com/sierra-research/tau2-bench) |
| WebArena | Web agents | 812 tasks on self-hostable reproducible sites | [repo](https://github.com/web-arena-x/webarena) |
| BIG-bench | Broad LM benchmark | Canary-string convention for contamination | [repo](https://github.com/google/BIG-bench) |
| Hugging Face Datasets | Data platform | Versioned hosting, revisions, dataset cards | [hf.co/datasets](https://huggingface.co/datasets) |
| scikit-learn | Library | `cohen_kappa_score`, metrics | [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html) |
| statsmodels | Library | `fleiss_kappa`, IAA stats | [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html) |
| datasketch | Library | MinHash / LSH for scalable overlap scans | [datasketch](https://github.com/ekzhu/datasketch) |

---

## 12. Interviewer Q&A

**Q1. Why did SWE-bench Verified score higher than the original SWE-bench for the same model, and what does that teach you?**
Because ~68% of original tasks were filtered out for underspecified problem statements or unit tests that reject valid patches; 93 developers triple-annotated 1,699 samples down to 500 clean ones. GPT-4o went from ~16% to ~33% on the *same model* — the benchmark got more accurate, not the model better. Lesson: label/verifier quality can dominate the score more than model capability.

**Q2. You have 78% raw agreement between two reviewers. Is the benchmark trustworthy?**
Not from that number alone. Raw agreement ignores chance; on a skewed label distribution you can hit 78% while knowing nothing. Compute Cohen's \( \kappa \). If \( \kappa \) is ~0.4 (moderate), a meaningful fraction of tasks are ambiguous and you should revise wording/rubrics before publishing scores.

**Q3. How would you detect that a public benchmark has contaminated the model you're testing?**
Multiple signals: (1) recency split — compare tasks created before vs. after the training cutoff; a score cliff is a red flag; (2) n-gram overlap between tasks and any available training corpus; (3) black-box probes — guided completion of a masked task, or preferring the original over perturbed variants; (4) perplexity/Min-K% memorization tests. No single method is proof; triangulate.

**Q4. When is synthetic eval data appropriate, and how do you keep it honest?**
For coverage of rare/edge/adversarial cases and for scaling a validated task template — never as the benchmark's backbone. Keep it honest by: generating with a different, stronger model than any under test; passing every task through human filtering and an independent verifier; verifying gold labels rather than trusting them; keeping synthetic tasks a labeled minority; and reporting the synthetic fraction.

**Q5. Why does τ-bench score by database state instead of an LLM judge, and why introduce pass^k?**
State comparison is objective, cheap, and drift-free — the ledger either matches the goal or it doesn't, no judge bias. pass^k measures *reliability*: the probability that all k independent trials succeed. Average success hides that an agent that passes 60% of the time may pass all 8 tries only 20% of the time — which is what deployment actually cares about.

**Q6. What belongs in a datasheet, and why bother?**
Motivation, composition, collection process (including who annotated and the IAA achieved), preprocessing, intended and out-of-scope uses, distribution/license, and maintenance/versioning. It bothers because it makes provenance auditable, surfaces license and PII constraints, and lets others reproduce and critique your scores. A dataset without a datasheet is an instrument with no calibration certificate.

**Q7. How do you calibrate difficulty when building a custom benchmark?**
Run 2–3 baselines (a weak model, a strong model, and ideally a human) and bucket tasks by observed solve rate into easy/medium/hard. Ensure a spread — if everything solves or nothing does, the benchmark has no discriminative power. Center the mass of medium tasks where you expect frontier systems to sit so the ruler has ticks in the region you care about.

**Q8. Your held-out set has been used for prompt tuning over six months. What's the problem and the fix?**
It is no longer held out — you've turned it into training data by overfitting your prompts/scaffold to it, a self-inflicted contamination. Fix: retire it to the "dev" tier, cut a fresh private test set you look at rarely (ideally with post-cutoff tasks), and enforce a policy that scoring runs on the private set are infrequent and logged.

---

## 13. Further reading

- Introducing SWE-bench Verified — OpenAI: https://openai.com/index/introducing-swe-bench-verified/
- SWE-bench Verified dataset — Hugging Face: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified
- GAIA: a benchmark for General AI Assistants — arXiv 2311.12983: https://arxiv.org/abs/2311.12983
- τ-bench: Tool-Agent-User Interaction — arXiv 2406.12045: https://arxiv.org/abs/2406.12045
- τ²-bench (Sierra) repo: https://github.com/sierra-research/tau2-bench
- WebArena: A Realistic Web Environment — arXiv 2307.13854: https://arxiv.org/pdf/2307.13854
- WebArena code: https://github.com/web-arena-x/webarena
- A Survey on Data Contamination for LLMs — arXiv 2502.14425: https://arxiv.org/html/2502.14425v2
- Self-Instruct — arXiv 2212.10560: https://arxiv.org/abs/2212.10560
- Datasheets for Datasets (Gebru et al.) — arXiv 1803.09010: https://arxiv.org/pdf/1803.09010
- Are "Solved Issues" in SWE-bench Really Solved Correctly? — arXiv 2503.15223: https://arxiv.org/html/2503.15223v1
- BIG-bench (canary string convention): https://github.com/google/BIG-bench
