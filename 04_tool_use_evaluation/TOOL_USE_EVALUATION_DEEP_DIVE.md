# Tool Use Evaluation — A Deep Dive

Tool use is the seam where a language model stops *talking* and starts *acting*. The moment an agent emits a function call, its words become side effects: a database row is written, an email is sent, $4,000 is refunded. This is precisely where agents fail most often and most silently — a plausible-looking call with a wrong argument returns a `200 OK`, the transcript reads fine, and no one notices until a customer does. Evaluating tool use well means checking not just *whether* the agent called a tool, but whether it called the **right** tool, with the **right** arguments, in the **right** order, recovered when the tool **failed**, and — just as important — **refrained** from calling a tool when none applied. This chapter gives you a taxonomy, ground-truth construction methods, precise metrics, working scoring code, and a tour of the 2025–2026 benchmarks (BFCL, τ-bench, ToolBench, API-Bank) that define the state of the art.

---

## 1. Core intuition: why tool use is where agents silently fail

A chat model that hallucinates a fact produces text a human can read and doubt. A tool-using agent that hallucinates an *argument* produces an API call that a machine executes without doubt. The failure surface is different in three ways:

1. **Errors are structured, not prose.** A wrong `account_id` is not "a bad sentence" — it is a valid-looking token in a valid-looking JSON object. Text-quality metrics (BLEU, "does it sound right") are blind to it.
2. **Success signals are misleading.** Tools return status codes, not correctness. `refund(order="A123", amount=500)` may succeed at the HTTP level while being the wrong order and the wrong amount. Execution success ≠ task success.
3. **The failure compounds downstream.** In a chain — `search → pick_id → fetch_details → book` — a subtly wrong `id` at step 2 poisons every step after it. The agent then confidently narrates a correct-sounding summary of a wrong result.

The consequence: **you cannot evaluate tool use by reading transcripts or scoring final answers alone.** You must inspect the *structured call trace* — the sequence of `(tool_name, arguments)` tuples the agent emitted — and compare it against a specification of what correct behavior looks like. Everything in this chapter is about how to build that comparison rigorously.

---

## 2. What to evaluate — a taxonomy

Tool-use quality decomposes into seven distinct capabilities. Evaluate them **separately**, because an agent can be strong on one and catastrophic on another, and a single blended score hides that.

| # | Dimension | Question it answers | Canonical failure |
|---|-----------|--------------------|--------------------|
| 1 | **Selection** | Did the agent pick the correct tool(s) for the task? | Uses `web_search` when the answer needs `sql_query` |
| 2 | **Argument construction** | Are the parameters correct, well-typed, and schema-valid? | Right tool, `date="tomorrow"` instead of `2026-08-04` |
| 3 | **Execution-result handling** | Does the agent read the tool's output correctly and act on it? | Tool returns `error: not_found`, agent proceeds as if success |
| 4 | **Chaining / ordering** | Are dependent calls issued in a valid order with data flowing correctly? | Calls `book(flight_id)` before `search_flights` returns the id |
| 5 | **Error recovery** | On failure, does the agent retry sensibly, adjust, or escalate? | Repeats the identical failing call 5×; or gives up on a transient 503 |
| 6 | **Efficiency** | Did it reach the goal without redundant, wasteful, or looping calls? | Re-fetches unchanged data every turn; 3 tools where 1 sufficed |
| 7 | **Safety / irrelevance** | Does it avoid destructive or unwarranted calls, and *not* call when it shouldn't? | Calls `delete_account` on an ambiguous "clean up my stuff"; invents a tool |

Definitions worth pinning down:

- **Selection** is a *classification* problem over the tool set (including the null tool "answer directly"). **Irrelevance detection** — recognizing that *no* tool applies — is a first-class selection sub-case that most naive agents fail by over-calling.
- **Argument construction** splits into **schema validity** (does it parse against the JSON Schema — right keys, types, enums, required fields?) and **semantic correctness** (is `amount=500` the *right* value given the task?). Schema validity is cheap and mechanical; semantic correctness needs ground truth.
- **Chaining** introduces **data-dependency ordering**: call B consumes an output of call A, so B must follow A *and* use A's actual returned value, not a hallucinated one. This is where "the id it booked doesn't match any id search returned" bugs live.
- **Safety** covers **non-idempotent / destructive** operations (writes, deletes, payments, sends) where a spurious or duplicated call causes irreversible harm — a stricter bar than read-only tools.

---

## 3. Ground truth for tools

To score a call trace you need a reference. There are three families of ground truth, in increasing order of flexibility (and cost).

### 3.1 Exact-match on calls (AST comparison)

The reference is one or more expected `(tool_name, args)` objects. You compare the agent's emitted call to the reference **structurally**, not as a string. This is what the **Berkeley Function-Calling Leaderboard** calls *AST accuracy*: parse the model's output into an abstract syntax tree of the function call, then check the function name, then check each argument against allowed values — ignoring formatting, key order, and whitespace. String matching would fail on `f(a=1, b=2)` vs `f(b=2, a=1)`; AST comparison treats them as equal.

Two refinements make exact-match usable in practice:

- **Value sets, not single values.** A reference argument is often a *set* of acceptable values: `{"units": ["metric", "celsius"]}` because either is a correct rendering. BFCL's checker accepts a call if each argument matches any allowed value for that parameter.
- **Optional vs required parameters.** The reference marks which parameters must be present and which are optional; supplying an omittable default is not an error.

### 3.2 Executable / state-based checks

Instead of matching the call *text*, you **run** it and check the *effect*. Two variants:

- **Executable accuracy** (BFCL "executable" categories): actually invoke the function against a live or mock API and assert the *return value* matches an expected result. Robust to multiple call phrasings that produce the same output.
- **State-based evaluation** (BFCL V3 multi-turn, τ-bench): after the episode, compare the **final backend state** (database rows, object fields) to an annotated golden end-state. This is the gold standard for write/delete operations: it does not care *how* the agent got there, only that the world ended up correct. τ-bench computes reward by diffing the database against the expected state *and* checking that required information appears in the agent's reply.

State-based checks elegantly solve the **"any valid path" problem** (§3.4) for writes — but they say nothing about *efficiency* or *read-only* correctness, so you pair them with trajectory checks.

### 3.3 Golden trajectories

For chaining and process quality, the reference is an entire **golden trajectory**: an ordered (or partially-ordered) list of calls with their expected arguments and expected returns. You score the agent's trajectory against it with alignment metrics (§5): how many reference steps were hit, in a valid order, with correct args. Golden trajectories are the most informative and the most expensive to author and maintain.

### 3.4 The "any valid path" problem

The central difficulty: **many correct trajectories exist.** To answer "what's the weather in Paris and Tokyo," `[weather(Paris), weather(Tokyo)]` and `[weather(Tokyo), weather(Paris)]` are both correct — parallel, order-insensitive. Some tasks admit genuinely different tool *choices* (search-then-filter vs. a single richer query) that are equally valid. Over-strict exact-match punishes correct agents; over-loose matching passes wrong ones.

Practical resolutions, in order of preference:

1. **Match on outcome, not path** (state-based) whenever the task has an observable end-state.
2. **Encode the reference as a partial order + value sets** — mark independent calls as order-insensitive, dependent calls as ordered, and each argument as a set of acceptable values. Score with order-insensitive matching (the code in §6 does this).
3. **Use a rubric/LLM-judge** for the residual genuinely-open cases, with the schema and task as context — but treat judge scores as noisy and calibrate against human labels.

---

## 4. Metrics

Notation: an episode produces a list of *predicted* calls \( P = [p_1, \dots, p_m] \) and a reference \( G = [g_1, \dots, g_n] \). Each call is a pair \( (\text{name}, \text{args}) \).

### 4.1 Tool-selection accuracy

Fraction of episodes (or steps) where the predicted tool name matches the reference, treating "no call" as a valid label:

\[
\text{SelAcc} = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}\!\left[\text{name}(p_i) = \text{name}(g_i)\right]
\]

For irrelevance detection, report it as a **confusion matrix** instead of a single number — you care about both false calls (called when it should not) and missed calls. Define:

\[
\text{IrrelevanceAcc} = \frac{\#\{\text{correctly emitted no tool}\}}{\#\{\text{tasks where no tool applies}\}}
\]

*Micro-example.* Over 4 tasks the reference tools are `[sql, none, search, none]` and the agent emits `[sql, search, search, none]`. Selection accuracy = 3/4 = 0.75. On the two irrelevance tasks (positions 2,4) the agent got 1 right → IrrelevanceAcc = 0.5 (it over-called on task 2).

### 4.2 Argument accuracy

Given the tool name is correct, the fraction of arguments that match the reference value set. For a single call with reference args \( g \):

\[
\text{ArgAcc}(p, g) = \frac{1}{|K_g|}\sum_{k \in K_g} \mathbb{1}\!\left[p[k] \in \text{allowed}_g(k)\right]
\]

where \( K_g \) is the set of reference parameter keys. Report both **per-argument** accuracy (partial credit) and **exact-call accuracy** (all arguments correct — the stricter, more honest number for high-stakes tools).

*Micro-example.* Reference `book(date=2026-08-04, seats={1,2})`; prediction `book(date=2026-08-04, seats=3)`. Per-arg = 1/2 = 0.5; exact-call = 0.

### 4.3 Execution success rate

Fraction of emitted calls that execute without error (schema-valid, no exception, non-error status):

\[
\text{ExecSuccess} = \frac{\#\{\text{calls returning non-error}\}}{\#\{\text{calls emitted}\}}
\]

Crucial caveat: **high ExecSuccess with low ArgAcc means the agent is confidently calling the wrong thing successfully.** Always read the two together.

### 4.4 Chain completion (trajectory success)

Did the agent complete the full dependency chain and reach the goal? Binary per episode, averaged:

\[
\text{ChainCompletion} = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}\!\left[\text{all required steps of } G_i \text{ satisfied in valid order}\right]
\]

A softer version is **step recall** — fraction of reference steps hit — which gives partial credit and helps localize *where* chains break.

### 4.5 Recovery rate

Of the episodes that hit at least one tool error, the fraction where the agent subsequently reached task success:

\[
\text{RecoveryRate} = \frac{\#\{\text{episodes with an error that still succeeded}\}}{\#\{\text{episodes that encountered} \geq 1 \text{ tool error}\}}
\]

Complement with **maladaptive-retry rate**: fraction of errors followed by an *identical* retry (same name + args) — a sign the agent is not learning from the error message.

### 4.6 Redundant-call rate (efficiency)

\[
\text{RedundantRate} = \frac{m - u}{m}, \quad m = \#\text{calls emitted}, \; u = \#\text{calls that were necessary}
\]

where "necessary" calls are those whose removal would change the outcome (approximated by: not a duplicate of an earlier call with identical args and unchanged state, and on the path to the goal). A related headline number is **call efficiency** \( = n_{\text{golden}} / m \) — reference call count over actual — capped at 1.

*Micro-example.* Agent emits 5 calls; two are identical repeats of an earlier `get_balance()` with no state change. \( u = 3 \), RedundantRate \( = (5-3)/5 = 0.4 \).

### 4.7 Reliability: pass@k vs pass^k

A single run hides variance. τ-bench introduced **pass^k**, the probability that **all** \( k \) i.i.d. trials of a task succeed — a reliability (consistency) measure — versus the familiar **pass@k**, the probability that **at least one** of \( k \) succeeds. With \( c \) successes out of \( n \) trials for a task:

\[
\text{pass@}k = \mathbb{E}\!\left[\,1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}\right], \qquad
\text{pass}^{k} = \mathbb{E}\!\left[\frac{\binom{c}{k}}{\binom{n}{k}}\right]
\]

pass@k *rewards* lucky single successes; pass^k *punishes* inconsistency. For production tool agents, pass^k is the honest metric: τ-bench found strong models whose pass@1 looked healthy but whose pass^8 collapsed below 25% in the retail domain — i.e., they rarely do the same task correctly eight times running.

---

## 5. A fully worked scoring example

The code below scores an agent's emitted tool calls against an expected specification. It does **structured** comparison (not string match), supports **value sets** and **optional** parameters, and handles **order-insensitive parallel calls** via a greedy best-match assignment. It returns per-dimension metrics from §4.

```python
"""
tool_trace_scorer.py — structured scoring of agent tool calls.

Reference spec ("golden") is a list of expected calls. Each expected call:
  {
    "name": "book_flight",
    "args": {                       # only reference keys are graded
        "flight_id": {"allowed": ["F100"]},        # value set
        "seats":     {"allowed": [1, 2]},
        "notify":    {"allowed": [True], "optional": True},  # omittable
    },
    "order_group": 1,   # calls in the same group are order-insensitive (parallel);
                        # a higher group must come strictly after a lower one.
  }

Prediction is a list of emitted calls: {"name": str, "args": dict}.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


def _norm(v: Any) -> Any:
    """Normalize a scalar for tolerant comparison (dates, casing, numerics)."""
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _arg_matches(pred_val: Any, spec: dict) -> bool:
    allowed = [_norm(a) for a in spec["allowed"]]
    return _norm(pred_val) in allowed


def score_call(pred: dict, ref: dict) -> dict:
    """Score one predicted call against one reference call."""
    name_ok = pred.get("name") == ref["name"]
    ref_args: dict = ref.get("args", {})
    pred_args: dict = pred.get("args", {})

    graded = correct = 0
    missing_required, wrong_value, hallucinated_arg = [], [], []

    for key, spec in ref_args.items():
        optional = spec.get("optional", False)
        if key not in pred_args:
            if not optional:
                graded += 1
                missing_required.append(key)
            continue
        graded += 1
        if _arg_matches(pred_args[key], spec):
            correct += 1
        else:
            wrong_value.append(key)

    # arguments the agent invented that the schema/reference did not define
    hallucinated_arg = [k for k in pred_args if k not in ref_args]

    per_arg = correct / graded if graded else 1.0
    exact = name_ok and per_arg == 1.0 and not hallucinated_arg
    return {
        "name_ok": name_ok,
        "per_arg_acc": per_arg,
        "exact_call": exact,
        "missing_required": missing_required,
        "wrong_value": wrong_value,
        "hallucinated_arg": hallucinated_arg,
    }


def _match_group(preds: list[dict], refs: list[dict]) -> list[tuple]:
    """Order-insensitive greedy assignment within one parallel group.

    Pairs each reference call with the still-unused predicted call that
    scores best against it (name match first, then arg accuracy). Returns
    (ref, matched_pred_or_None, score_dict) tuples plus leftovers.
    """
    used = [False] * len(preds)
    pairs = []
    for ref in refs:
        best_i, best_score, best_key = None, None, (-1, -1.0)
        for i, pred in enumerate(preds):
            if used[i]:
                continue
            s = score_call(pred, ref)
            key = (int(s["name_ok"]), s["per_arg_acc"])
            if key > best_key:
                best_key, best_i, best_score = key, i, s
        if best_i is not None and best_score["name_ok"]:
            used[best_i] = True
            pairs.append((ref, preds[best_i], best_score))
        else:                      # no acceptable prediction -> missed call
            pairs.append((ref, None, score_call({"name": None, "args": {}}, ref)))
    extra = [preds[i] for i in range(len(preds)) if not used[i]]  # spurious calls
    return pairs, extra


@dataclass
class TraceReport:
    n_ref: int = 0
    selection_hits: int = 0
    exact_calls: int = 0
    arg_acc_sum: float = 0.0
    spurious: int = 0            # emitted calls with no reference match
    hallucinated_tools: int = 0  # names not in the tool registry
    missed: int = 0
    details: list = field(default_factory=list)

    @property
    def selection_acc(self): return self.selection_hits / self.n_ref if self.n_ref else 1.0
    @property
    def arg_acc(self):       return self.arg_acc_sum / self.n_ref if self.n_ref else 1.0
    @property
    def exact_call_acc(self): return self.exact_calls / self.n_ref if self.n_ref else 1.0
    @property
    def redundant_rate(self):
        emitted = self.n_ref - self.missed + self.spurious
        return self.spurious / emitted if emitted else 0.0


def score_trace(pred_calls: list[dict], golden: list[dict],
                registry: set[str]) -> TraceReport:
    """Score a full trajectory: group by order_group, match within groups."""
    rep = TraceReport(n_ref=len(golden))

    # split predictions into groups by reference order structure.
    groups = sorted({g.get("order_group", idx) for idx, g in enumerate(golden)})
    # naive positional slicing of predictions across groups by reference size:
    refs_by_group = {gid: [g for g in golden if g.get("order_group", i) == gid]
                     for i, gid in enumerate(groups)}

    cursor = 0
    for gid in groups:
        refs = refs_by_group[gid]
        preds = pred_calls[cursor: cursor + len(refs)]
        cursor += len(refs)
        pairs, extra = _match_group(preds, refs)
        for ref, pred, s in pairs:
            if pred is None:
                rep.missed += 1
            else:
                rep.selection_hits += int(s["name_ok"])
                rep.exact_calls += int(s["exact_call"])
                rep.arg_acc_sum += s["per_arg_acc"]
            rep.details.append((ref["name"], s))
        for e in extra:
            rep.spurious += 1
            if e.get("name") not in registry:
                rep.hallucinated_tools += 1

    # any predictions beyond the last group are spurious too
    for e in pred_calls[cursor:]:
        rep.spurious += 1
        if e.get("name") not in registry:
            rep.hallucinated_tools += 1
    return rep


if __name__ == "__main__":
    registry = {"search_flights", "book_flight", "send_email"}
    golden = [
        {"name": "search_flights",
         "args": {"origin": {"allowed": ["SFO"]}, "dest": {"allowed": ["JFK"]}},
         "order_group": 0},
        {"name": "book_flight",
         "args": {"flight_id": {"allowed": ["F100"]},
                  "seats": {"allowed": [1, 2]}},
         "order_group": 1},
    ]
    # Agent booked the right flight but wrong seat count, and invented a tool.
    pred = [
        {"name": "search_flights", "args": {"origin": "sfo", "dest": "JFK"}},
        {"name": "book_flight",    "args": {"flight_id": "F100", "seats": 3}},
        {"name": "delete_booking", "args": {"id": "F100"}},   # hallucinated tool
    ]
    r = score_trace(pred, golden, registry)
    print(f"selection_acc   = {r.selection_acc:.2f}")   # 1.00
    print(f"arg_acc         = {r.arg_acc:.2f}")          # 0.75
    print(f"exact_call_acc  = {r.exact_call_acc:.2f}")   # 0.50
    print(f"redundant_rate  = {r.redundant_rate:.2f}")   # 0.33
    print(f"hallucinated    = {r.hallucinated_tools}")   # 1
```

Running it prints selection 1.00, arg 0.75 (3 of 4 graded args correct), exact-call 0.50 (the `book` call had a wrong `seats`), a redundant rate of 0.33 (the spurious `delete_booking`), and one hallucinated tool. Note the design choices that matter: **AST-style value-set matching** (`SFO`/`sfo` normalize equal), **partial credit per argument** alongside a **strict exact-call** number, **order-insensitive matching within a parallel group**, and explicit accounting of **spurious/hallucinated** calls. For production use you would layer in state-based checks (§3.2) and a data-flow validator that confirms `flight_id` passed to `book_flight` actually appeared in a prior `search_flights` result.

---

## 6. Hard cases

**Hallucinated tools.** The agent calls a function that does not exist in the registry (`delete_booking` above). Detect by validating every emitted name against the declared tool set; a nonzero hallucinated-tool count is a hard failure regardless of other scores. Well-designed harnesses also test *tool-name confusability* — two similarly named tools (`get_user` vs `get_users`) to see if the model disambiguates.

**Wrong-but-plausible arguments.** The most dangerous case: right tool, schema-valid args, wrong *value*. `transfer(amount=1000)` when the task said $100; `date="2026-08-03"` when it meant next month. These pass schema validation and execution, so only **semantic ground truth** (value sets, or state-based checks) catches them. This is why ArgAcc must be reported next to ExecSuccess — a gap between them is exactly this failure.

**Irrelevance / should-NOT-call.** Many tasks are answerable directly, or the available tools simply do not fit ("What's the capital of France?" with only a `weather` tool). A well-calibrated agent answers without calling. BFCL and its "relevance/irrelevance" splits score this explicitly; over-calling ("tool-happy" agents) is a common, penalized failure. Always include no-tool tasks in your suite, or you will only measure the easy half of selection.

**Non-idempotent and destructive tools.** For `send_email`, `charge_card`, `delete_*`, a *duplicated* or *spurious* call is not a minor inefficiency — it is real harm. Evaluate these with stricter rules: any extra destructive call is a critical failure; the agent should prefer read-then-confirm patterns; and idempotency keys (if the API supports them) should be checked. Reliability metrics (pass^k) matter most here because "usually correct" is not good enough when the tail event charges a customer twice.

**Uncertain writes / underspecified requests.** "Cancel my order" when the user has three orders. The correct behavior is often to **ask a clarifying question, not to call a write tool** on a guess. Ground truth for these cases should reward the *no-op-plus-question* trajectory and penalize a confident wrong write — which means your reference format must be able to express "the correct action here is to ask, not to act."

---

## 7. Benchmark tour

| Benchmark | What it measures | How it scores | Notable limitations |
|-----------|------------------|---------------|---------------------|
| **BFCL** (Berkeley Function-Calling Leaderboard; Gorilla, UC Berkeley) | Single-turn *simple / multiple / parallel / parallel-multiple* calls; **irrelevance detection**; V3 **multi-turn / multi-step** with missing-parameter, missing-function, long-context, composite splits; V4 adds agentic (web search, memory, format sensitivity) | **AST accuracy** (structural call match against value sets) + **executable accuracy** (run and compare returns) + **state-based** eval for multi-turn writes; irrelevance as accuracy on no-call tasks | AST checks can be brittle on genuinely open tasks; static API snapshots; strong contamination pressure as it is widely trained against |
| **τ-bench / τ2-bench** (Sierra) | Realistic **tool-agent-user** dialogue in *retail* and *airline* domains; policy adherence; multi-turn info-gathering | **DB final-state** comparison to golden end-state + required-info check in reply; reliability via **pass^k** | Two domains only; user is LLM-simulated (its own noise); labor-intensive to author policies |
| **ToolBench / ToolLLM** (OpenBMB, ICLR'24) | Real-world tool use over 16k+ RapidAPI tools; single- and multi-tool instructions | **ToolEval**: **pass rate** (task solved) + **win rate** (LLM judge vs. a reference solution); DFSDT solver | Live-API instability makes runs non-reproducible (→ **StableToolBench** adds a cached API simulator); LLM-judge noise |
| **API-Bank** (EMNLP'23) | Graded tool abilities: **Call**, **Retrieve+Call**, and **Plan+Retrieve+Call**; when-to-call and how-to-call | Correctness of API calls and of the model's response given returns; leveled by difficulty | Smaller, older API set; less agentic/multi-turn than BFCL V3+ |
| **NexusRaven V2** (Nexusflow) | Open, commercially-permissive function-calling model + its evaluation on **nested / composite** and multi-function calls | Correctness of (possibly nested) generated calls vs. reference | It is primarily a model + targeted eval, not a broad standardized leaderboard |
| **MCP** (Model Context Protocol; Anthropic, open spec) | *Not a benchmark* — a standard **interface** for exposing tools/resources/prompts to models over JSON-RPC | N/A (evaluation implication: standardized schemas + tool descriptions become the object under test) | Standardizes plumbing, not quality; recent work shows tool-*description* quality strongly affects selection accuracy |

How to read this tour: **BFCL** is your microscope for call-level correctness and irrelevance; **τ-bench** is your microscope for *reliability* and policy-following in multi-turn service settings; **ToolBench** stresses breadth and real APIs (with reproducibility caveats); **API-Bank** cleanly separates the *decision to call* from the *ability to call*. **MCP** is the interface layer — increasingly what your tools are actually described in, and therefore what your evaluation harness should ingest natively.

---

## 8. Failure modes & pitfalls in evaluating tool use

- **String-matching function calls.** `f(a=1,b=2)` ≠ `f(b=2,a=1)` under string match but they are identical. Always parse to a structured form (AST) and compare with value sets. This is the single most common home-grown-eval bug.
- **Scoring only the final answer.** A correct-sounding summary over a wrong tool result passes end-to-end checks and hides the failure. Inspect the call trace.
- **Conflating execution success with correctness.** `200 OK` on the wrong `order_id` is a "successful" disaster. Report ArgAcc alongside ExecSuccess.
- **Forgetting irrelevance tasks.** A suite with only tool-required tasks measures half of selection and rewards over-calling. Include no-tool and wrong-tool-available cases.
- **Over-strict single golden path.** Punishing valid alternate orderings/choices depresses scores of good agents. Use partial orders, value sets, or outcome-based checks.
- **Single-run reporting.** Tool agents are high-variance; one lucky run is not a capability. Report pass^k or at least variance over ≥5 seeds, especially for destructive tools.
- **Benchmark contamination & staleness.** Popular leaderboards leak into training data and static API snapshots drift. Rotate held-out private tasks; prefer state-based checks that are harder to game than fixed reference strings.
- **LLM-judge without calibration.** Using a model to grade calls is convenient but noisy and biased; calibrate against human labels and report agreement before trusting it.
- **Ignoring cost/latency.** An agent that "succeeds" with 12 calls and $0.40 per task may be unusable. Track calls-per-task and dollars-per-task next to accuracy.

---

## 9. What an interviewer or reviewer will probe

**Q1. Why not just check the agent's final answer?**
Because tool errors are silent: a wrong `id` produces a valid result and a fluent, wrong summary. End-to-end scoring cannot localize *where* the trajectory broke, cannot catch a correct answer reached through an unsafe or duplicated write, and cannot measure efficiency. You must score the structured call trace, not the prose.

**Q2. How do you compare tool calls without brittle string matching?**
Parse each call into a structured form (name + arg dict), then compare via AST-style rules: exact name match, and each reference argument matched against a *set* of allowed values with type/format normalization. Order-insensitive for parallel/independent calls; ordered for data-dependent ones. This is what BFCL's AST accuracy does.

**Q3. There are many correct ways to solve the task. How do you avoid punishing valid alternates?**
Prefer **outcome/state-based** evaluation — diff the final backend state against a golden end-state, ignoring path. Where the path matters, encode the reference as a **partial order with value sets** so independent calls can appear in any order, and reserve an LLM-judge (calibrated) only for genuinely open residuals.

**Q4. What's the difference between pass@k and pass^k, and which do you report?**
pass@k is the probability at least one of k trials succeeds (rewards luck); pass^k is the probability all k succeed (measures consistency). For production tool agents — especially with destructive tools — report **pass^k**, because a model that succeeds once in eight tries is not deployable even if pass@8 looks great. τ-bench showed strong models with pass^8 under 25%.

**Q5. How do you evaluate whether an agent *shouldn't* have called a tool?**
Include irrelevance tasks where no tool applies or the answer is direct, and score the no-call as the correct action (BFCL relevance/irrelevance splits). Report it separately as a confusion matrix — over-calling (false tool invocations) and under-calling are different, and destructive over-calls are critical.

**Q6. How do you test error recovery specifically?**
Inject failures — 5xx errors, timeouts, empty results, malformed returns — and measure recovery rate (errored episodes that still reach success) plus maladaptive-retry rate (identical retries after an error). A good agent reads the error message and *changes* the call or escalates; a bad one loops the same failing call or ignores the error and proceeds.

**Q7. How do you handle destructive / non-idempotent tools in evaluation?**
Stricter rules: any spurious or duplicated write/charge/delete is a critical failure, not an efficiency ding; check for idempotency keys and read-then-confirm patterns; require a clarifying question on underspecified writes; and weight reliability (pass^k) heavily because tail-event double-charges are the real risk.

**Q8. Your BFCL score is high but production tool use is unreliable — reconcile this.**
Leaderboard scores are single-turn, static-snapshot, and contamination-prone; production is multi-turn, stateful, and adversarial. Bridge the gap with state-based multi-turn evals (BFCL V3, τ-bench), private held-out tasks, reliability metrics over many seeds, injected-failure recovery tests, and live production monitoring of call traces — not a single leaderboard number.

---

## 10. Further reading

- Berkeley Function-Calling Leaderboard (BFCL), Gorilla / UC Berkeley — leaderboard and category docs: <https://gorilla.cs.berkeley.edu/leaderboard.html>
- BFCL V3 multi-turn / multi-step blog (state-based eval, missing params/functions): <https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html>
- BFCL dataset on Hugging Face: <https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard>
- τ-bench paper — "A Benchmark for Tool-Agent-User Interaction in Real-World Domains" (arXiv 2406.12045): <https://arxiv.org/abs/2406.12045>
- τ²-bench code (Sierra Research): <https://github.com/sierra-research/tau2-bench>
- Sierra blog — τ-bench overview and pass^k motivation: <https://sierra.ai/blog/tau-bench-shaping-development-evaluation-agents>
- ToolLLM / ToolBench (OpenBMB, ICLR'24) — ToolEval pass rate & win rate: <https://arxiv.org/abs/2307.16789> · code: <https://github.com/OpenBMB/ToolBench>
- StableToolBench — reproducible tool-use benchmarking via API simulator: <https://arxiv.org/abs/2403.07714>
- API-Bank — "A Comprehensive Benchmark for Tool-Augmented LLMs" (EMNLP'23, arXiv 2304.08244): <https://arxiv.org/abs/2304.08244>
- NexusRaven V2 (Nexusflow) — commercially-permissive function-calling model: <https://openreview.net/pdf?id=5lcPe6DqfI>
- Model Context Protocol (MCP) specification and docs: <https://modelcontextprotocol.io/> · spec: <https://spec.modelcontextprotocol.io/>
- Anthropic — "Code execution with MCP: building more efficient AI agents": <https://www.anthropic.com/engineering/code-execution-with-mcp>

---

*Practitioner's takeaway:* evaluate tool use on the **structured call trace**, not the prose; score selection, arguments, chaining, recovery, efficiency, and safety **separately**; prefer **state/outcome-based** ground truth to escape the "any valid path" trap; always include **irrelevance** and **injected-failure** cases; and report **reliability (pass^k)**, not a single lucky run — especially anywhere a tool can write, charge, send, or delete.
