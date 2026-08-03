# Tool Use Evaluation — A Deep Dive

Tool use is the seam where a language model stops *talking* and starts *acting*. The moment an agent emits a function call, its words become side effects: a database row is written, an email is sent, $4,000 is refunded. This is precisely where agents fail most often and most silently — a plausible-looking call with a wrong argument returns a `200 OK`, the transcript reads fine, and no one notices until a customer does. Evaluating tool use well means checking not just *whether* the agent called a tool, but whether it called the **right** tool, with the **right** arguments, in the **right** order, recovered when the tool **failed**, and — just as important — **refrained** from calling a tool when none applied. This chapter gives you a taxonomy, ground-truth construction methods, precise metrics, working scoring code, and a tour of the 2025–2026 benchmarks (BFCL, τ-bench, ToolBench, API-Bank) that define the state of the art.

---

## 1. Core intuition: why tool use is where agents silently fail

A chat model that hallucinates a fact produces text a human can read and doubt. A tool-using agent that hallucinates an *argument* produces an API call that a machine executes without doubt. The failure surface is different in three ways:

1. **Errors are structured, not prose.** A wrong `account_id` is not "a bad sentence" — it is a valid-looking token in a valid-looking JSON object. Text-quality metrics (BLEU, "does it sound right") are blind to it.
2. **Success signals are misleading.** Tools return status codes, not correctness. `refund(order="A123", amount=500)` may succeed at the HTTP level while being the wrong order and the wrong amount. Execution success ≠ task success.
3. **The failure compounds downstream.** In a chain — `search → pick_id → fetch_details → book` — a subtly wrong `id` at step 2 poisons every step after it. The agent then confidently narrates a correct-sounding summary of a wrong result.

The consequence: **you cannot evaluate tool use by reading transcripts or scoring final answers alone.** You must inspect the *structured call trace* — the sequence of `(tool_name, arguments)` tuples the agent emitted — and compare it against a specification of what correct behavior looks like. Everything in this chapter is about how to build that comparison rigorously.
One more property makes tool-use failures uniquely corrosive: **they are asymmetric in cost.** A read that returns the wrong row wastes a few cents of tokens; a write that mutates the wrong row can cost a refund, a reputation, or a compliance breach. A good evaluation harness therefore does not treat all calls as equal-weight classification targets — it weights the loss by the *blast radius* of the tool. Reading `get_weather("Paris")` wrong and calling `wire_transfer(amount=50000)` wrong are not the same event and must not average into the same scalar. This is the through-line of the chapter: measure per-dimension, and weight by consequence.


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
For destructive tools this taxonomy needs a fourth safety sub-case beyond irrelevance, over-call, and under-call: **duplication under retry.** When a `charge_card` or `send_email` call times out, the *result* is unknown but the *effect* may already have happened. A correct agent either uses an idempotency key so a retry is a no-op, or reads state (`get_recent_charges`) before re-issuing. An evaluation that only checks "did the final charge exist" will pass an agent that charged twice; you must count **effect multiplicity** — how many times the side effect actually fired — not just whether it fired at least once.


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
Multi-turn state deserves special emphasis because it is where 2025–2026 benchmarks moved the goalposts. In single-turn evaluation the world is stateless: you score one call against one reference and reset. In multi-turn evaluation (BFCL V3, τ-bench, τ²-bench) the backend is a *persistent database* that the agent mutates across many turns, and the reference is the **end-state of that database plus the set of facts the agent must have surfaced to the user.** Scoring becomes: run the whole episode against a sandboxed backend seeded to a known initial state, then diff the final state against the golden end-state with a canonicalizing comparator (sort collections, ignore auto-generated timestamps/ids, normalize money to minor units). Two things make this hard in practice — **hidden coupling** (a write in turn 3 invalidates an assumption the agent made in turn 1) and **user-simulator noise** (the LLM playing the user may volunteer or withhold information inconsistently, so you must run many seeds and report variance, not a point estimate).


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

## 10. The 2025–2026 landscape

The benchmark tour in §7 is the map; this section is the *territory as it stands in 2025–2026*. Tool-use evaluation moved fast in this window along three axes: (1) from single-turn call matching to **multi-turn, stateful, agentic** evaluation; (2) from bespoke per-vendor function-calling schemas to a **standard tool interface (MCP)**; and (3) from "did it call the right function" to "did it behave reliably and safely across a whole *session* with a *real user in the loop*." Know these by name and date — an interviewer will expect it.

### 10.1 BFCL: V3 (multi-turn) → V4 (agentic)

The **Berkeley Function-Calling Leaderboard** (Gorilla group, UC Berkeley) is the most-cited call-level benchmark, and it is a moving target.

- **BFCL V1 (early 2024)** established **AST accuracy** and **executable accuracy** over *simple / multiple / parallel / parallel-multiple* single-turn calls, plus a **relevance/irrelevance** split for should-not-call behavior.
- **BFCL V2 · "Live" (Aug 2024)** replaced synthetic prompts with **live, user-contributed** function-calling data to fight contamination and better reflect real distributions.
- **BFCL V3 (Sep 2024)** introduced **multi-turn and multi-step** evaluation with **state-based checking**: the agent operates across turns against a stateful backend (file system, trading, travel-booking APIs), and scoring diffs the **final backend state** against a golden end-state. V3 added the categories that matter most for agents: **missing-parameter** (the agent must ask, not guess), **missing-function** (the needed tool isn't provided, so the agent must recognize it can't proceed), **long-context**, and **composite**. Blog: <https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html>.
- **BFCL V4 · "Agentic" (July 2025 onward)** is the current frontier and adds three agentic tracks:
  - **Web search (released 2025-07-17):** ~100 multi-hop questions where the agent must issue real search queries (DuckDuckGo API) and fetch/parse web pages, scored by exact-match on normalized answers. Blog: <https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html>.
  - **Memory (released 2025-07-17):** the agent must read/write persistent memory through tool calls across five domains (advising, support, productivity, healthcare, finance), tested against three backends — **key-value (BM25+)**, **vector store (all-MiniLM-L6-v2 embeddings)**, and **recursive summarization (a bounded text buffer the model must compress)**. This directly evaluates whether an agent can *use a memory tool correctly*, a capability MCP servers increasingly expose. Blog: <https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html>.
  - **Format sensitivity (2025):** the same tasks under 26 perturbations of return format, function-doc style, and prompt formatting — measuring how brittle selection/argument accuracy is to cosmetic changes. Blog: <https://gorilla.cs.berkeley.edu/blogs/17_bfcl_v4_prompt_variation.html>.

  V4's headline score is a weighted blend (Agentic ~40%, Multi-Turn ~30%, Live ~10%, Non-Live ~10%, Hallucination ~10%), and the project was written up at **ICML 2025** ("The Berkeley Function-Calling Leaderboard: From Tool Use to Agentic Evaluation," <https://openreview.net/forum?id=2GmDdhBdDk>). The trajectory — V1 call-matching → V3 state-based → V4 agentic web/memory — is itself the story of where the field went. Leaderboard: <https://gorilla.cs.berkeley.edu/leaderboard.html>.

**Evaluation implication.** If you cite "we hit X% on BFCL," an interviewer will ask *which version and which split*. V4 web/memory is a different animal from V1 AST accuracy; a model can top V1 and be mediocre at V3 multi-turn state.

### 10.2 τ-bench → τ²-bench: tool-agent-user, reliability, and dual control

**τ-bench** (Sierra, June 2024; "A Benchmark for Tool-Agent-User Interaction in Real-World Domains," arXiv:2406.12045) evaluates agents in **realistic multi-turn dialogue** in *retail* and *airline* domains. Its two enduring contributions:

1. **State-based reward with an info check.** An episode passes only if (a) the backend database's final state matches the golden end-state **and** (b) the agent surfaced the required information to the user. This kills "right words, wrong action" and "right action, silent about it" simultaneously.
2. **pass^k reliability.** τ-bench popularized reporting **pass^k** (probability *all* k i.i.d. trials succeed) alongside pass@k, exposing that agents strong on a single try are often inconsistent. Frontier models showed pass^8 collapsing well below pass^1 in retail — the single most quoted "agents aren't reliable yet" datapoint. Repo: <https://github.com/sierra-research/tau-bench>.

**τ²-bench** (Sierra, June 2025; "τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment," arXiv:2506.07982, submitted 2025-06-09) raises the bar to **dual control**: in a **telecom** troubleshooting domain, *both the agent and the user* can act on the shared environment with tools (the user can reboot their own router, toggle a setting), modeled as a **Dec-POMDP**. The agent must not just call tools but *guide the user to call theirs* — coordinating, instructing, and verifying. Key finding: agents that do fine in the "no-user-action" setting **drop sharply** when the user is also an actor, isolating *communication/coordination* failure from *reasoning* failure. τ²-bench also ships a **compositional task generator** (verifiable tasks from atomic components) and a tightly-coupled user simulator. Repo: <https://github.com/sierra-research/tau2-bench>; paper: <https://arxiv.org/abs/2506.07982>. Note the community follow-ups: **τ²-bench-verified** (Amazon AGI) corrects task/policy/DB misalignments in the original set (<https://github.com/amazon-agi/tau2-bench-verified>) — a reminder that even flagship benchmarks carry annotation bugs you should audit before trusting a number.

**Why this matters for building.** τ-bench/τ²-bench are the reference design for a *product-grade* tool-use eval: sandboxed stateful backend, LLM user-simulator, state-diff reward, reliability over many seeds, and policy-adherence checks. When you design your own harness (§11, §12), you are essentially building a domain-specific τ-bench.

### 10.3 ToolBench / StableToolBench and API-Bank: breadth and graded ability

- **ToolLLM / ToolBench** (OpenBMB, ICLR 2024; arXiv:2307.16789) covers **16k+ real RapidAPI tools** with single- and multi-tool instructions, solved with a DFSDT search and scored by **ToolEval** (**pass rate** + LLM-judge **win rate** vs. a reference). Its weakness is *reproducibility*: live third-party APIs go down or change, so runs aren't comparable over time. Repo: <https://github.com/OpenBMB/ToolBench>.
- **StableToolBench** (2024; arXiv:2403.07714) fixes that by replacing live APIs with a **cached, LLM-simulated API server**, trading a little realism for reproducible, always-on evaluation — the pattern you should copy for your own CI (a recorded/mock tool sandbox, not live prod APIs). Repo/paper: <https://arxiv.org/abs/2403.07714>.
- **API-Bank** (EMNLP 2023; arXiv:2304.08244) cleanly separates the **decision to call** from the **ability to call** with graded levels — **Call**, **Retrieve+Call**, **Plan+Retrieve+Call** — and remains the crispest framework for diagnosing *which* sub-skill an agent lacks (knowing *when*, knowing *which*, knowing *how*). Older/smaller API set, but conceptually clarifying.

### 10.4 MCP: the tool interface is standardizing — and it changes what you evaluate

The **Model Context Protocol (MCP)** — introduced by Anthropic in **November 2024**, open-specced at <https://modelcontextprotocol.io/> and <https://spec.modelcontextprotocol.io/> — is not a benchmark. It is a **standard JSON-RPC interface** for exposing **tools, resources, and prompts** to a model, the "USB-C port for AI tools." By late 2025 it is the de-facto standard: the **November 25, 2025 spec revision (`2025-11-25`)** added **task-based/async workflows** (SEP-1686: states `working / input_required / completed / failed / cancelled` with polling), **simplified OAuth** via Client ID Metadata Documents (SEP-991), an **extensions framework**, **sampling-with-tools** so a server can run its own agentic loop (SEP-1577), and standardized tool naming (SEP-986). Adoption spans **OpenAI, Google, Microsoft, AWS, GitHub, Hugging Face, Block, Okta**, and the **MCP Registry** grew ~407% since September 2025 to roughly 2,000 servers (anniversary post, 2025-11-25: <https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/>).

Why an evaluation chapter cares about a *plumbing* standard — four concrete shifts:

1. **The tool schema becomes the object under test.** MCP tools ship a structured name, JSON-Schema input, and a **natural-language description** the model reads to decide *whether and how* to call. Empirically, **tool-description quality dominates selection accuracy** — the same underlying function with a vague description gets mis-selected far more often. So your eval must treat the *description text* as a variable, not a constant: A/B test descriptions, and include BFCL-V4-style *format-sensitivity* perturbations. When selection regresses after someone "cleaned up" a tool doc, this is why.
2. **Server-side tools you don't control become part of your trust boundary.** With MCP, an agent may load tools from a third-party server at runtime. Evaluation must now cover **tool-poisoning / prompt-injection via tool descriptions and results** (a malicious server can embed instructions in a description or return field), **name collisions** across servers (two servers both expose `search`), and **over-broad scopes**. "Does the agent refuse a tool whose description tries to redirect it" is a first-class safety eval in an MCP world.
3. **Async / long-running tools break turn-synchronous scoring.** The 2025-11 task model means a tool call may return `input_required` or stay `working` across turns. Your scorer can no longer assume one call → one immediate result; it must model pending tasks, polling, and cancellation, and evaluate whether the agent *waits, polls, and handles `failed`/`cancelled`* correctly.
4. **Standardized schemas make harnesses portable.** Because MCP normalizes the tool contract, an evaluation harness that ingests MCP tool definitions natively can point at *any* MCP server — your scorer, your golden traces, and your sandbox all speak one schema. This is the practical reason to build your §11 scorer around the MCP tool shape (`name`, `inputSchema`, `description`) rather than a vendor-specific one.

**Update — the 2026-07-28 spec superseded several of the mechanics above.** MCP dropped the stateful session/handshake model entirely (no more `initialize`/session IDs — every request is now self-contained), which is squarely good news for eval infrastructure: point 3 above ("async tools break turn-synchronous scoring") gets easier, not harder, because a stateless core means your harness can parallelize tool-call evaluations across workers without session-affinity bugs corrupting results. The new spec also adds **Multi Round-Trip Requests (MRTR)** — a cleaner mechanism than the old task-polling model for "the server needs more input mid-call" — and moves the 2025-11-25 Tasks feature into a formal extension framework rather than the core spec. Two more evaluation-relevant details: tool/method names now travel in HTTP headers (`Mcp-Method`, `Mcp-Name`), which matters if your harness sniffs traffic rather than instrumenting the client directly; and Dynamic Client Registration is being superseded by Client ID Metadata Documents for auth, tightening the security-eval surface from point 2. Roots, Sampling, and Logging are deprecated on a 12-month sunset — if your eval harness depends on any of those subsystems, that's a migration to plan now, not later. [2026-07-28 spec](https://blog.modelcontextprotocol.io/posts/2026-07-28/).

**One-line summary for an interview:** *"BFCL is the call-level microscope, τ-bench/τ²-bench is the multi-turn reliability and dual-control microscope, ToolBench/StableToolBench is breadth-with-reproducibility, API-Bank separates when/which/how, and MCP is the interface layer that turns tool descriptions and async task-handling into things you must evaluate — not just plumbing."*

---

## 11. Build it in practice: a runnable tool-call scorer

The §5 scorer teaches the idea. This section is the *thing you would actually ship in CI* — it ingests real provider payloads (OpenAI `tool_calls` **and** MCP/generic shapes), does AST-style structured comparison with value sets, handles **order-insensitive parallel calls** as a partial order, runs a **data-flow (chain) check** that an argument traces to a prior call's output, flags **hallucinated tools and args**, scores **irrelevance / should-not-call** tasks, folds in an **execution log** for exec-success and **error-recovery**, and aggregates a dataset with **pass@k vs pass^k**. It is dependency-free (Python 3.10+ stdlib) and the `__main__` block runs four illustrative tasks.

Design decisions worth defending in an interview:

- **Parse first, compare second.** `parse_tool_calls` normalizes provider quirks (arguments arriving as a JSON *string*, MCP `arguments` vs. legacy `args`) into a uniform `ToolCall`. Malformed JSON is *recorded* (`__unparsable__`), never silently dropped — a call the model emitted but you couldn't parse is a finding, not a non-event.
- **Value sets + three matchers.** Each reference argument may specify `allowed` (a set of acceptable values), `from_call` (must trace to a prior output — the data-flow/chain check), and/or `predicate` (an arbitrary callable, e.g. "is a valid ISO date"). This spans exact-match, semantic, and structural checks in one grammar.
- **Partial order, not a single golden path.** Calls carry a `group`; same-group calls are order-insensitive (parallel), and a matched call in a later group that appears *before* an earlier group's calls is an `order_violation`. This is how you avoid punishing `weather(Tokyo), weather(Paris)`.
- **Consequence-aware accounting.** Hallucinated tools (name not in the registry) and destructive over-calls are surfaced as their own counters, not blended into arg accuracy — because §2's blast-radius point demands it.
- **Reliability is first-class.** `pass_at_k` rewards luck; `pass_pow_k` measures consistency. The demo prints both for a task that succeeded 5 of 8 runs, and you can see pass@3 (0.98) look great while pass^3 (0.18) tells the deployable truth.

```python
"""
tool_eval.py -- production-shaped tool-call scorer.

Ingests an agent's emitted tool calls (OpenAI-style or MCP-style), compares
them structurally (AST-style) against a per-task reference spec, and reports
selection / argument / execution / chain / recovery metrics. Handles:
  * order-insensitive parallel calls (partial order via `group`)
  * value-set + optional + predicate argument matching
  * data-flow (chain) checks: an arg must trace to a prior call's output
  * hallucinated tools (name not in registry) and hallucinated args
  * irrelevance / should-not-call tasks (empty reference == must not call)
  * execution success and error-recovery from an execution log
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# --------------------------------------------------------------------------- #
# 1. Parsing: normalize provider payloads into ToolCall objects.
# --------------------------------------------------------------------------- #
@dataclass
class ToolCall:
    name: Optional[str]
    args: dict
    call_id: Optional[str] = None


def parse_tool_calls(raw: list[dict]) -> list[ToolCall]:
    """Accept OpenAI-style ({'function':{'name','arguments'}}) or MCP/generic
    ({'name','arguments'|'args'}). Arguments may be a JSON string or a dict."""
    out: list[ToolCall] = []
    for item in raw:
        if "function" in item:                       # OpenAI tool_call shape
            fn = item["function"]
            name = fn.get("name")
            a = fn.get("arguments", {})
            cid = item.get("id")
        else:                                        # MCP / generic shape
            name = item.get("name")
            a = item.get("arguments", item.get("args", {}))
            cid = item.get("id") or item.get("call_id")
        if isinstance(a, str):                       # arguments came as JSON text
            try:
                a = json.loads(a) if a.strip() else {}
            except json.JSONDecodeError:
                a = {"__unparsable__": a}            # malformed args are recorded
        out.append(ToolCall(name=name, args=a or {}, call_id=cid))
    return out


# --------------------------------------------------------------------------- #
# 2. Argument matching (AST-style, tolerant normalization + value sets).
# --------------------------------------------------------------------------- #
def _norm(v: Any) -> Any:
    if isinstance(v, str):
        return v.strip().lower()
    if isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


def _arg_matches(pred_val: Any, spec: dict, produced: set) -> bool:
    """A reference arg-spec supports three matchers (any present => must pass):
       allowed:   value must be in a set of acceptable values
       from_call: value must trace to an earlier call's output (data flow)
       predicate: a callable returning bool."""
    if "allowed" in spec:
        if _norm(pred_val) not in {_norm(a) for a in spec["allowed"]}:
            return False
    if "from_call" in spec:
        if _norm(pred_val) not in produced:          # hallucinated / broken chain
            return False
    if "predicate" in spec:
        if not spec["predicate"](pred_val):
            return False
    return True


def score_call(pred: ToolCall, ref: dict, produced: set) -> dict:
    name_ok = pred.name == ref["name"]
    ref_args: dict = ref.get("args", {})
    pred_args: dict = pred.args
    graded = correct = 0
    missing_required, wrong_value, chain_broken = [], [], []
    for key, spec in ref_args.items():
        if key not in pred_args:
            if not spec.get("optional", False):
                graded += 1
                missing_required.append(key)
            continue
        graded += 1
        if _arg_matches(pred_args[key], spec, produced):
            correct += 1
        else:
            wrong_value.append(key)
            if "from_call" in spec and _norm(pred_args[key]) not in produced:
                chain_broken.append(key)
    hallucinated_arg = [k for k in pred_args if k not in ref_args]
    per_arg = correct / graded if graded else 1.0
    exact = name_ok and per_arg == 1.0 and not hallucinated_arg
    return dict(name_ok=name_ok, per_arg=per_arg, exact=exact,
                missing_required=missing_required, wrong_value=wrong_value,
                hallucinated_arg=hallucinated_arg, chain_broken=chain_broken)


# --------------------------------------------------------------------------- #
# 3. Order-insensitive matching within a partial order (`group`).
# --------------------------------------------------------------------------- #
def _match(preds: list[ToolCall], refs: list[dict], produced: set):
    """Greedy best-match assignment (name-match first, then arg accuracy).
    Returns matched pairs (ref, pred|None, score, pred_index) and spurious preds."""
    used = [False] * len(preds)
    pairs = []
    for ref in refs:
        best = (-1, -1.0)   # (name_ok, per_arg)
        best_i = None
        for i, p in enumerate(preds):
            if used[i]:
                continue
            s = score_call(p, ref, produced)
            key = (int(s["name_ok"]), s["per_arg"])
            if key > best:
                best, best_i, best_s = key, i, s
        if best_i is not None and best_s["name_ok"]:
            used[best_i] = True
            pairs.append((ref, preds[best_i], best_s, best_i))
        else:
            miss = score_call(ToolCall(None, {}), ref, produced)
            pairs.append((ref, None, miss, None))
    spurious = [(i, preds[i]) for i in range(len(preds)) if not used[i]]
    return pairs, spurious


# --------------------------------------------------------------------------- #
# 4. Full-trace report.
# --------------------------------------------------------------------------- #
@dataclass
class TraceReport:
    task_id: str
    should_not_call: bool = False
    over_called: bool = False              # irrelevance task but agent called
    n_ref: int = 0
    selection_hits: int = 0
    arg_acc_sum: float = 0.0
    exact_calls: int = 0
    missed: int = 0
    spurious: int = 0
    hallucinated_tools: int = 0
    hallucinated_args: int = 0
    order_violations: int = 0
    chain_ok: bool = True
    exec_calls: int = 0
    exec_ok: int = 0
    hit_error: bool = False
    recovered: bool = False

    @property
    def selection_acc(self): return self.selection_hits / self.n_ref if self.n_ref else 1.0
    @property
    def arg_acc(self):       return self.arg_acc_sum / self.n_ref if self.n_ref else 1.0
    @property
    def exact_call_acc(self): return self.exact_calls / self.n_ref if self.n_ref else 1.0
    @property
    def exec_success(self):  return self.exec_ok / self.exec_calls if self.exec_calls else 1.0


def collect_produced(exec_log: list[dict]) -> set:
    """Flatten every scalar reachable in tool outputs into a set of normalized
    values -- the pool a later argument may legitimately have come from."""
    produced: set = set()
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, (list, tuple)):
            for v in x: walk(v)
        else:
            produced.add(_norm(x))
    for e in exec_log:
        walk(e.get("output"))
    return produced


def score_trace(task_id, pred_raw, spec_calls, registry, exec_log=None) -> TraceReport:
    exec_log = exec_log or []
    preds = parse_tool_calls(pred_raw)
    produced = collect_produced(exec_log)
    rep = TraceReport(task_id=task_id, n_ref=len(spec_calls))

    # --- irrelevance / should-not-call task: reference is empty ---
    if not spec_calls:
        rep.should_not_call = True
        rep.over_called = len(preds) > 0
        rep.spurious = len(preds)
        rep.hallucinated_tools = sum(1 for p in preds if p.name not in registry)
        # execution/recovery still computed below
    else:
        groups = sorted({c.get("group", i) for i, c in enumerate(spec_calls)})
        cursor = 0
        last_max_idx = -1
        for gid in groups:
            refs = [c for i, c in enumerate(spec_calls) if c.get("group", i) == gid]
            window = preds[cursor: cursor + len(refs)]
            pairs, spurious = _match(window, refs, produced)
            group_pred_idxs = []
            for ref, pred, s, local_i in pairs:
                if pred is None:
                    rep.missed += 1
                    rep.chain_ok = False if ref.get("args") else rep.chain_ok
                else:
                    rep.selection_hits += int(s["name_ok"])
                    rep.exact_calls += int(s["exact"])
                    rep.arg_acc_sum += s["per_arg"]
                    rep.hallucinated_args += len(s["hallucinated_arg"])
                    if s["chain_broken"]:
                        rep.chain_ok = False
                    group_pred_idxs.append(cursor + local_i)
            # ordering: every matched call in this group must come after the
            # last call of all earlier groups.
            for gi in group_pred_idxs:
                if gi < last_max_idx:
                    rep.order_violations += 1
            if group_pred_idxs:
                last_max_idx = max(last_max_idx, max(group_pred_idxs))
            for _, p in spurious:
                rep.spurious += 1
                if p.name not in registry:
                    rep.hallucinated_tools += 1
            cursor += len(refs)
        for p in preds[cursor:]:
            rep.spurious += 1
            if p.name not in registry:
                rep.hallucinated_tools += 1

    # --- execution + recovery ---
    rep.exec_calls = len(exec_log)
    rep.exec_ok = sum(1 for e in exec_log if e.get("ok"))
    err_seen = False
    for e in exec_log:
        if not e.get("ok"):
            rep.hit_error = True
            err_seen = True
        elif err_seen:
            rep.recovered = True            # a success followed a prior error
    return rep


# --------------------------------------------------------------------------- #
# 5. Dataset aggregation + pass^k / pass@k over repeated trials.
# --------------------------------------------------------------------------- #
from math import comb

def pass_at_k(n, c, k):
    if n - c < k: return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)

def pass_pow_k(n, c, k):
    if c < k: return 0.0
    return comb(c, k) / comb(n, k)


def aggregate(reports: list[TraceReport]) -> dict:
    rel = [r for r in reports if not r.should_not_call]
    irr = [r for r in reports if r.should_not_call]
    errd = [r for r in reports if r.hit_error]
    def mean(xs): return sum(xs) / len(xs) if xs else 1.0
    return {
        "selection_acc":   mean([r.selection_acc for r in rel]),
        "arg_acc":         mean([r.arg_acc for r in rel]),
        "exact_call_acc":  mean([r.exact_call_acc for r in rel]),
        "chain_completion": mean([1.0 if (r.chain_ok and r.missed == 0
                                          and r.order_violations == 0) else 0.0
                                  for r in rel]),
        "exec_success":    mean([r.exec_success for r in reports]),
        "recovery_rate":   (mean([1.0 if r.recovered else 0.0 for r in errd])
                            if errd else float("nan")),
        "irrelevance_acc": (mean([0.0 if r.over_called else 1.0 for r in irr])
                            if irr else float("nan")),
        "hallucinated_tools": sum(r.hallucinated_tools for r in reports),
        "spurious_calls":     sum(r.spurious for r in reports),
    }


# --------------------------------------------------------------------------- #
# 6. Demo: four tasks -- parallel-correct, wrong-arg, chain+recovery, irrelevance.
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    registry = {"search_flights", "book_flight", "get_weather", "send_email"}

    # Task A: order-insensitive parallel reads, both correct (OpenAI shape).
    specA = [
        {"name": "get_weather", "args": {"city": {"allowed": ["Paris"]}}, "group": 0},
        {"name": "get_weather", "args": {"city": {"allowed": ["Tokyo"]}}, "group": 0},
    ]
    predA = [
        {"id": "1", "function": {"name": "get_weather",
                                 "arguments": '{"city": "tokyo"}'}},
        {"id": "2", "function": {"name": "get_weather",
                                 "arguments": '{"city": "PARIS"}'}},
    ]
    rA = score_trace("A_parallel", predA, specA, registry)

    # Task B: right tool, wrong argument value, plus an invented tool call.
    specB = [
        {"name": "book_flight",
         "args": {"flight_id": {"allowed": ["F100"]}, "seats": {"allowed": [1, 2]}},
         "group": 0},
    ]
    predB = [
        {"name": "book_flight", "args": {"flight_id": "F100", "seats": 3}},
        {"name": "delete_booking", "args": {"id": "F100"}},   # hallucinated tool
    ]
    rB = score_trace("B_wrong_arg", predB, specB, registry)

    # Task C: chained search->book with a data-flow check, and error+recovery.
    specC = [
        {"name": "search_flights",
         "args": {"origin": {"allowed": ["SFO"]}, "dest": {"allowed": ["JFK"]}},
         "group": 0},
        {"name": "book_flight",
         "args": {"flight_id": {"from_call": "search_flights"},
                  "seats": {"allowed": [1]}},
         "group": 1},
    ]
    predC = [
        {"name": "search_flights", "args": {"origin": "SFO", "dest": "JFK"}},
        {"name": "book_flight",    "args": {"flight_id": "F777", "seats": 1}},
    ]
    execC = [
        {"ok": False, "error": "503 upstream", "output": None},          # first try fails
        {"ok": True, "output": {"results": [{"id": "F777"}, {"id": "F778"}]}},  # retry ok
        {"ok": True, "output": {"confirmation": "OK"}},
    ]
    rC = score_trace("C_chain_recovery", predC, specC, registry, execC)

    # Task D: irrelevance -- no tool applies, correct behavior is to NOT call.
    predD = [{"name": "get_weather", "args": {"city": "Paris"}}]  # over-called!
    rD = score_trace("D_irrelevance", predD, [], registry)

    reports = [rA, rB, rC, rD]
    for r in reports:
        print(f"[{r.task_id:>16}] sel={r.selection_acc:.2f} arg={r.arg_acc:.2f} "
              f"exact={r.exact_call_acc:.2f} chain_ok={r.chain_ok} "
              f"order_viol={r.order_violations} halluc_tool={r.hallucinated_tools} "
              f"over_called={r.over_called} recovered={r.recovered}")

    print("\n--- aggregate ---")
    agg = aggregate(reports)
    for k, v in agg.items():
        print(f"{k:>20}: {v}")

    # reliability over repeated trials of one task: 8 runs, 5 successes
    print("\n--- reliability (n=8, c=5) ---")
    print("pass@1 =", round(pass_at_k(8, 5, 1), 3),
          " pass@3 =", round(pass_at_k(8, 5, 3), 3))
    print("pass^1 =", round(pass_pow_k(8, 5, 1), 3),
          " pass^3 =", round(pass_pow_k(8, 5, 3), 3))
```

Running it produces (verified output):

```text
[      A_parallel] sel=1.00 arg=1.00 exact=1.00 chain_ok=True order_viol=0 halluc_tool=0 over_called=False recovered=False
[     B_wrong_arg] sel=1.00 arg=0.50 exact=0.00 chain_ok=True order_viol=0 halluc_tool=1 over_called=False recovered=False
[C_chain_recovery] sel=1.00 arg=1.00 exact=1.00 chain_ok=True order_viol=0 halluc_tool=0 over_called=False recovered=True
[   D_irrelevance] sel=1.00 arg=1.00 exact=1.00 chain_ok=True order_viol=0 halluc_tool=0 over_called=True recovered=False

--- aggregate ---
       selection_acc: 1.0
             arg_acc: 0.8333333333333334
      exact_call_acc: 0.6666666666666666
    chain_completion: 1.0
        exec_success: 0.9166666666666666
       recovery_rate: 1.0
     irrelevance_acc: 0.0
  hallucinated_tools: 1
      spurious_calls: 2

--- reliability (n=8, c=5) ---
pass@1 = 0.625  pass@3 = 0.982
pass^1 = 0.625  pass^3 = 0.179
```

Read the numbers the way you would in a review. `B_wrong_arg` has `selection=1.00` but `arg=0.50` and `exact=0.00` — the agent picked the right tool and confidently passed the wrong `seats`, exactly the wrong-but-plausible failure of §6; the invented `delete_booking` shows up as `halluc_tool=1`, not as a silent efficiency ding. `C_chain_recovery` passes its data-flow check because the booked `flight_id` (`F777`) actually appeared in the `search_flights` output, and `recovered=True` because a success followed the injected `503`. `D_irrelevance` scores `over_called=True` and drives aggregate `irrelevance_acc` to `0.0` — the suite refuses to let a tool-happy agent hide. And the reliability block is the punchline: **pass@3 = 0.98 vs pass^3 = 0.18** for the same 5-of-8 task. In production you would swap the in-memory `execC` for a real **sandbox** (§12): seed a database, let the agent act, and diff final state instead of trusting the reference call text.

---

## 12. Production case studies & war stories

Benchmarks tell you where a model sits on a leaderboard. They do not tell you how a *team* keeps a shipping agent from writing the wrong row at 3 a.m. This section is the practitioner layer: how real agent products actually evaluate tool use, and a couple of concrete failure incidents (composited from common, widely-reported patterns) with the lesson each burned in.

### 12.1 How real agent products evaluate tool use

The teams that run tool-using agents in production converge on a small set of practices, regardless of vertical:

- **Golden trajectories mined from production, not hand-written.** The cheapest source of realistic tasks is your own logs. Pick sessions a human confirmed as successful, freeze the `(user_request → tool calls → final state)` triple as a **golden trajectory**, and scrub PII. Over time you accumulate a regression suite that reflects *your* traffic distribution, not a benchmark's. Hand-authored tasks fill the gaps (rare tools, dangerous edge cases) but the backbone is mined.
- **State-based checks against a sandbox, not string-matching the calls.** The dominant production pattern (and the one τ-bench formalized) is a **hermetic sandbox**: a copy of the backend — order DB, ledger, CRM — seeded to a known initial state. Run the agent against it, then **diff the final state** against the golden end-state with a canonicalizing comparator. This is robust to the "any valid path" problem and is the only honest way to grade writes. Crucially the sandbox must be *hermetic and reset per run* — a test that mutates shared state poisons the next test.
- **A tiered eval pyramid.** (1) **Unit-level**: schema validation and AST checks on single calls, run on every commit, milliseconds each. (2) **Trajectory-level**: golden-trajectory + state-diff on a few hundred tasks, run pre-merge, minutes. (3) **Reliability**: pass^k over many seeds on a smaller, high-stakes subset (anything that writes/charges/sends), run nightly. (4) **Online**: shadow/canary in production with live monitoring of the call trace. Each tier catches what the tier below cannot, at increasing cost.
- **LLM-as-judge only where structure runs out — and calibrated.** For genuinely open steps (was this clarifying question reasonable?), a rubric-driven judge is used, but *gated*: teams measure the judge's agreement with human labels on a holdout, report it, and re-check it when the judge model changes. A judge whose agreement isn't measured is a random-number generator with good manners.
- **Read/write asymmetry baked into scoring.** Read tools get partial credit and semantic tolerance. Write/charge/delete tools get **binary, strict, and heavily weighted** scoring plus a **safety gate** that can fail the whole episode on a single spurious destructive call regardless of task success.
- **Injected-failure suites.** A dedicated set where the sandbox is rigged to return 5xx, timeouts, empty results, and malformed payloads, purely to measure recovery and maladaptive-retry — because you cannot wait for prod to supply enough failures to characterize the behavior.

### 12.2 War story #1: the wrong-but-plausible argument that shipped a bad write

*The incident.* A customer-support agent handled "I was double-charged for order 8842, please refund the duplicate." The catalog had two orders that day, **8842** and **8842-R** (a return-shipping fee). The agent called:

```text
issue_refund(order_id="8842-R", amount=payment.total, reason="duplicate charge")
```

Every layer said green. The tool was **correct** (`issue_refund`). The arguments were **schema-valid** (a real order id, a valid amount, a non-empty reason). Execution returned **`200 OK`**. The final summary to the user read fluently: *"I've refunded your duplicate charge of $128.40."* The offline eval — which scored the *final answer* for helpfulness — **passed it**. Only three days later did reconciliation flag that the *wrong order* was refunded for the *wrong amount* (the full payment, not the duplicate line).

*Why every guardrail missed it.* This is the canonical §6 failure: **right tool, schema-valid args, wrong value.** Nothing textual or structural was off. Execution success was actively misleading — the disaster *succeeded* at the HTTP layer. And because the eval scored prose, the confident, wrong summary sailed through.

*What caught it in the postmortem — and became permanent eval.* Three changes:
1. **State-diff ground truth.** The golden reference became the *ledger end-state* (`refund on order 8842 for the duplicate line amount`), not the call text or the summary. Under a state-diff comparator, `8842-R` for `total` fails instantly — the world ended up wrong.
2. **A value-provenance check.** `amount` must trace (via `from_call`, as in §11) to a *specific line item* returned by a prior `get_order` call, not to `payment.total`. A refund amount that doesn't match any retrieved line is a hard fail.
3. **Confirm-before-write on ambiguity.** With two orders matching "8842", the *correct* behavior was to ask "Do you mean order 8842 or the 8842-R return fee?" The reference for underspecified writes was rewritten to reward the clarifying question and **penalize a confident write on a guess** — you cannot express that unless your reference format can say "the right action here is to ask, not act" (§6).

*The lesson, in one line:* **a `200 OK` on a schema-valid call is not a success signal; it is the absence of a syntax error.** Grade the *effect on the world*, and make ambiguous writes ask.

### 12.3 War story #2: the timeout that charged the customer twice

*The incident.* A billing agent called `charge_card(customer, amount=4999)`. The payment processor was slow; the call **timed out** at the agent's HTTP layer *after* the charge had actually posted. The agent, seeing a timeout (which reads like a failure), did the "sensible" thing: **retried the identical call.** The customer was charged **twice**. Worse, the offline eval had a *recovery* test that *rewarded* retry-after-error — so it had actively trained the team to think this agent's retry behavior was good.

*Why it slipped through.* The recovery metric (§4.5) as first written measured "did a success follow an error" — and a double-charge *does* produce a trailing success. The eval conflated **retry** with **safe retry**. For a non-idempotent tool, a blind retry on an *ambiguous* outcome (timeout ≠ known failure) is precisely the wrong move.

*The fix that became eval policy.*
1. **Effect-multiplicity scoring.** The sandbox counts *how many times the side effect fired*, not whether it fired ≥1 time. Two `charge` effects for a one-charge task is a **critical failure**, overriding task success (§2's destructive sub-case).
2. **Idempotency-key checks.** The reference now requires that a retry of a write carry the *same idempotency key* as the original, so the backend collapses duplicates. An agent that retries without one fails the safety gate.
3. **Read-before-retry on ambiguous outcomes.** On a timeout (unknown result), the golden trajectory is `get_recent_charges → decide`, not `charge again`. The injected-failure suite specifically distinguishes *timeout* (unknown) from *explicit 5xx with a body confirming no-op* (safe to retry).

*The lesson:* **"recovered" is not a virtue for destructive tools unless it is *safe* recovery.** Measure the number of real side effects, require idempotency, and treat *unknown* outcomes differently from *known failures*.

### 12.4 War story #3: the tool-description edit that quietly tanked selection

*The incident.* Selection accuracy on a subset of tasks dropped ~9 points overnight with **no model change**. The cause: someone "tidied" an MCP tool's description, shortening `search_orders` — *"Find orders by customer, date range, status, or SKU; use this before any refund or cancellation"* — to a terse *"Search orders."* The model stopped reaching for it before refunds and started guessing order ids.

*Why it matters.* In an MCP world (§10.4) the **tool description is part of the prompt the model reasons over**, and its quality dominates selection. A "cosmetic" doc edit is a *behavioral* change. The team had no eval gate on tool-description edits because they thought of descriptions as documentation, not as model inputs.

*The fix.* Tool descriptions were put **under version control with a selection-eval gate**: any change to a tool's `description` or `inputSchema` triggers the §11 selection/irrelevance suite in CI, and a regression blocks the merge. They also added **format-sensitivity** runs (BFCL-V4 style, §10.1) so they'd know how brittle each tool's selection was to wording before it bit them in prod.

*The lesson:* **treat tool descriptions and schemas as code.** In an MCP ecosystem they are load-bearing model inputs; gate them with the same eval you gate the model with.

### 12.5 The composite takeaway from the war stories

Every incident above shares a shape: **a layer reported success while the world was wrong.** HTTP said OK; the summary read fine; the retry "recovered"; the description "looked cleaner." Production tool-use evaluation is the discipline of *not trusting local green signals* — grading the end-state, counting real side effects, gating the inputs (descriptions/schemas) as well as the outputs, and weighting everything by blast radius.

---

## 13. Interview mastery

§9 covered eight probes an interviewer will open with. This section is the rest of the kit: a crisp 60-second answer to the field's signature question, a full system-design walkthrough, decision tables you can draw on a whiteboard, a longer Q&A bank, and the red-flag/green-flag heuristics that let a reviewer smell a weak eval in thirty seconds.

### 13.1 "Explain in 60 seconds why tool use is where agents silently fail"

> Tool use is the moment the model stops producing *text a human can doubt* and starts producing *a structured call a machine executes without doubt*. Three things make it fail silently. First, the errors are **structured, not prose**: a wrong `account_id` is a valid-looking token in valid JSON, invisible to any text-quality metric. Second, the success signals **lie**: tools return status codes, so `refund(wrong_order, wrong_amount)` comes back `200 OK` and execution success gets mistaken for correctness. Third, the damage **compounds and gets narrated away**: one wrong id early in a chain poisons every downstream step, and the model then writes a fluent, confident summary of a wrong result. So you cannot evaluate tool use by reading transcripts or scoring final answers — you have to inspect the structured call trace and grade the *effect on the world*, weighted by how much damage each tool can do. That's the whole game: reads are cheap to get wrong, writes are not, and the eval has to know the difference.

That is deliberately memorizable: *structured-not-prose, signals-lie, damage-compounds → grade the trace and the end-state, weighted by blast radius.*

### 13.2 System-design prompt: "Design tool-use evaluation for a payments agent"

A payments agent can `get_balance`, `list_transactions`, `get_payee`, `create_payee`, `send_payment`, and `cancel_payment`. Design its evaluation. A strong answer moves through five layers; here is the sketch.

**1. Threat-model the tools first (blast radius).** Split the tool set by consequence before writing a single metric:
- **Read** (`get_balance`, `list_transactions`, `get_payee`): wrong = wasted tokens. Partial credit, semantic tolerance.
- **Non-idempotent write** (`send_payment`, `create_payee`): wrong or duplicated = irreversible money movement. Binary, strict, safety-gated.
- **Compensating** (`cancel_payment`): matters for recovery paths and must itself be evaluated for correctness.

**2. Ground truth = sandbox end-state, not call text.** Stand up a hermetic ledger sandbox seeded per task. The reference for each task is the **final ledger state** (balances, a payment row with exact payee + minor-unit amount + idempotency key) plus **required facts surfaced to the user** (confirmation number, new balance). Diff with a canonicalizing comparator (money in minor units, ignore auto ids/timestamps). This is the τ-bench pattern applied to money.

**3. Metrics, per dimension, consequence-weighted.**
- Selection accuracy + **irrelevance** (must *not* pay on "what's my balance?").
- Argument accuracy with a hard **value-provenance** rule: `payee` and `amount` must trace to a prior `get_payee` / `list_transactions` output — never fabricated.
- **Effect multiplicity** on `send_payment`: exactly-once. Two payments for a one-payment task = critical fail, overrides everything.
- Chain completion (get_payee → send_payment) and order violations.
- Recovery vs. **safe** recovery: on a `send_payment` timeout, the golden path is `list_transactions`/status-check → decide, *not* re-send; retries must carry the same idempotency key.

**4. Safety gates and confirmation policy.** Any spurious/duplicated `send_payment`, any payment to a payee not confirmed by the user, or any write on an ambiguous request ("pay John" with two Johns) **fails the episode** regardless of task-level success. Underspecified payments must ask a clarifying question — the reference rewards the no-op-plus-question.

**5. Reliability + online.** Report **pass^k (k≥5)** on the payment subset — "usually pays correctly" is not deployable when the tail double-pays. Add an injected-failure suite (processor 5xx/timeouts) for recovery, and in production, **shadow-mode** the agent with live call-trace monitoring and an amount-threshold human-in-the-loop before real money moves.

ASCII sketch of the harness:

```text
  task (seed) ──► [ hermetic ledger sandbox ] ◄── agent tool calls
                          │
        ┌─────────────────┼──────────────────────────┐
        ▼                 ▼                           ▼
  state-diff vs      call-trace scorer          injected-failure
  golden end-state   (§11: sel/arg/chain/        rig (5xx/timeout)
  + required facts    provenance/halluc)               │
        │                 │                            ▼
        └───────► safety gate (effect-multiplicity,  recovery /
                  provenance, confirm-on-ambiguity)   safe-retry
                          │
                          ▼
                 per-dim metrics + pass^k(k≥5)  ──►  ship / block
```

The single most important sentence to say out loud: *"For a payments agent I grade the ledger end-state and count real side effects, not the call text or the summary — and a single spurious payment fails the run no matter how good the rest looks."*

### 13.3 Tradeoff tables

**Ground-truth strategy: exact-match vs. semantic vs. state-based**

| | Exact/AST match on calls | Semantic (value-set / judge) | State-based (end-state diff) |
|---|---|---|---|
| **What it grades** | The call text, structurally | Whether values *mean* the right thing | The effect on the world |
| **"Any valid path" robustness** | Poor (one golden path) | Medium | Excellent (path-agnostic) |
| **Catches wrong-but-plausible args** | Only if value in reference set | Yes | Yes (world ends up wrong) |
| **Cost to author/maintain** | Low | Medium (judge calibration) | High (sandbox + seeds) |
| **Reproducible in CI** | Yes | Judge-dependent | Yes, if sandbox is hermetic |
| **Best for** | Single-turn call correctness, fast unit gates | Open steps, phrasing-tolerant reads | Writes/deletes/payments, multi-turn |
| **Blind spot** | Alternate valid calls; efficiency | Judge noise/bias | Read-only correctness; efficiency |

*Rule of thumb:* AST for the unit tier, state-based for anything that writes, semantic/judge only for the open residual — and never rely on one alone.

**Single-turn vs. multi-turn evaluation**

| | Single-turn | Multi-turn (stateful) |
|---|---|---|
| **World model** | Stateless; one call, reset | Persistent backend mutated across turns |
| **Reference** | Expected call(s) | End-state + required-info + policy adherence |
| **Failures exposed** | Selection, arg construction | + coordination, memory, recovery, drift, coupling |
| **Reliability** | pass@1 often fine | pass^k essential (variance explodes) |
| **Representative of** | Wrapped-API calls | Real agents / assistants |
| **Cost & flakiness** | Low | High (user-simulator noise, seeds) |
| **Benchmarks** | BFCL V1/V2 (Live), API-Bank (Call) | BFCL V3, τ-bench, τ²-bench |

### 13.4 Q&A bank (interview-ready)

**Q9. When would you *prefer* AST/exact-match over state-based eval?** For fast unit gates on single calls where standing up a sandbox is overkill, and where the space of correct calls is genuinely narrow (a well-specified read with one right shape). It runs in milliseconds on every commit and localizes arg/selection bugs precisely. You just never let it be your *only* gate for writes.

**Q10. How do you catch a hallucinated tool vs. a hallucinated argument?** A hallucinated *tool* is a name not in the declared registry — validate every emitted `name` against the tool set; nonzero count is a hard fail. A hallucinated *argument* is a key not in the tool's schema, or a value with no provenance (a `flight_id` that appears in no prior tool output). The §11 scorer surfaces both as separate counters; they have different fixes (tighter tool-listing prompt vs. provenance checks).

**Q11. An agent asks a clarifying question instead of acting. Right or wrong?** It depends on whether the request was underspecified. For an ambiguous *write* ("cancel my order" with three orders), asking is the *correct* action and a confident guess-write is a failure — your reference must be able to reward the no-op-plus-question. For a fully-specified request, asking is an unnecessary turn and a mild efficiency ding. So this is not a bug or a virtue in the abstract; it's graded against whether ground truth says the request was answerable.

**Q12. How do you evaluate an agent that uses tools you don't control (third-party MCP servers)?** Add a trust-boundary layer: test resistance to **tool-poisoning** (a malicious description or return field trying to redirect the agent), **name collisions** across servers, and **over-broad scope** use. Grade "does it refuse a tool whose description contains injected instructions" as a first-class safety task, and pin/version the server's tool manifest so a silent upstream change to a description can't move behavior unnoticed.

**Q13. How do async / long-running tools change your scorer?** They break one-call-one-result. Under the MCP 2025-11 task model a call may return `input_required` or stay `working` across turns, so the scorer must model pending tasks, polling, cancellation, and terminal `failed`/`completed`. You evaluate whether the agent *waits and polls* rather than assuming instant completion, handles `cancelled`, and doesn't fire a duplicate side effect while a task is still `working`.

**Q14. Your judge and your state-diff disagree on a task. Who wins?** State-diff, for anything with an observable end-state — it's deterministic and grades reality. The judge is for open steps the state can't capture (tone, whether a clarifying question was reasonable). If they disagree on a *write*, the judge is wrong or the task is mis-specified; investigate rather than average them.

**Q15. How do you keep an eval suite from going stale or getting contaminated?** Rotate a **private held-out** set that never ships to a leaderboard or training corpus; refresh golden trajectories from recent production traffic; prefer **state-based** references (harder to memorize than fixed call strings); and periodically re-audit that "passing" tasks still exercise the tool (a schema change can turn a real test into a no-op).

**Q16. What's the single number you'd put on a dashboard for a destructive-tool agent, and why?** **pass^k (k≈5–8) on the write subset**, with a hard **safety-gate failure rate** next to it. Averages and pass@1 hide the tail, and the tail is where a customer gets double-charged. If forced to one number, it's the reliability of the dangerous subset, not the mean over everything.

**Q17. How do you measure efficiency without punishing legitimate exploration?** Compare against the golden call count for *necessary* calls only (dedupe identical calls with unchanged state), and report `call_efficiency = n_golden / m` capped at 1 alongside dollars- and latency-per-task. Exploration that changes state or gathers required info counts as necessary; a re-fetch of unchanged data or a duplicate write does not.

**Q18. How would you detect that an agent read a tool's error but ignored it?** Pair the error-injection suite with a check that the *next* action changed in response: after an `error: not_found`, did the agent adjust the call / escalate / stop, or did it proceed as if success (or repeat the identical failing call)? Track **maladaptive-retry rate** (identical name+args after an error) as the tell for "ignored the error message."

**Q19. Interviewer says "we just use an LLM to grade the whole trajectory." What's your pushback?** Convenient but under-specified: LLM judges are noisy, biased toward fluent narration (the exact failure mode of a wrong-but-plausible call), and drift when the judge model changes. I'd keep the judge only for open residual steps, gate it on measured agreement with human labels, and put deterministic state-diff + provenance checks under everything that writes. A judge you haven't calibrated is not a metric.

**Q20. How do you evaluate memory/tool use over a long session?** Treat the memory backend as a tool and score read/write correctness through it (BFCL V4 memory pattern): can the agent *store* the right fact, *retrieve* it later against a rephrased query, and not *hallucinate* a memory that was never written? Run multi-session tasks where a fact set early must resurface turns later, and report accuracy per backend (key-value vs. vector vs. summarization) since the failure profiles differ.

### 13.5 Red flags vs. green flags

An interviewer (or a code reviewer) reads the *shape* of your eval, not just the score. Signals they weigh:

| Red flag (weak eval) | Green flag (strong eval) |
|---|---|
| Scores only the final answer / summary | Grades the structured call trace **and** the end-state |
| String-matches function calls | AST/structured comparison with value sets |
| `200 OK` treated as success | Exec-success reported *next to* arg accuracy and state-diff |
| One golden path per task | Partial orders, value sets, or outcome-based checks |
| No should-not-call / irrelevance tasks | Explicit irrelevance suite scored as a confusion matrix |
| All tools weighted equally | Consequence-weighted; writes strict + safety-gated |
| Single run / pass@1 headline | pass^k over many seeds on the high-stakes subset |
| Retry-after-error rewarded blindly | *Safe* recovery: effect-multiplicity, idempotency keys |
| Tool descriptions treated as docs | Descriptions/schemas version-controlled + eval-gated |
| Live third-party APIs in CI | Hermetic, reset-per-run sandbox (StableToolBench pattern) |
| Uncalibrated LLM judge as the metric | Judge gated on measured human agreement, open steps only |
| One leaderboard number cited as "capability" | Version/split named; private held-out set; online monitoring |

---

## 14. Further reading

**Berkeley Function-Calling Leaderboard (BFCL)**
- Leaderboard (currently V4) and category docs: <https://gorilla.cs.berkeley.edu/leaderboard.html>
- BFCL V3 multi-turn / multi-step blog (state-based eval, missing params/functions): <https://gorilla.cs.berkeley.edu/blogs/13_bfcl_v3_multi_turn.html>
- BFCL V4 web-search track (2025-07-17): <https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html>
- BFCL V4 memory track (key-value / vector / summarization, 2025-07-17): <https://gorilla.cs.berkeley.edu/blogs/16_bfcl_v4_memory.html>
- BFCL V4 format-sensitivity track (26 perturbations): <https://gorilla.cs.berkeley.edu/blogs/17_bfcl_v4_prompt_variation.html>
- BFCL paper, "From Tool Use to Agentic Evaluation" (ICML 2025): <https://openreview.net/forum?id=2GmDdhBdDk>
- BFCL dataset on Hugging Face: <https://huggingface.co/datasets/gorilla-llm/Berkeley-Function-Calling-Leaderboard>

**τ-bench / τ²-bench (Sierra)**
- τ-bench paper, "A Benchmark for Tool-Agent-User Interaction in Real-World Domains" (arXiv:2406.12045): <https://arxiv.org/abs/2406.12045>
- τ-bench code: <https://github.com/sierra-research/tau-bench>
- τ²-bench paper, "Evaluating Conversational Agents in a Dual-Control Environment" (arXiv:2506.07982, 2025-06-09): <https://arxiv.org/abs/2506.07982>
- τ²-bench code: <https://github.com/sierra-research/tau2-bench>
- τ²-bench-verified (Amazon AGI corrected dataset): <https://github.com/amazon-agi/tau2-bench-verified>
- Sierra blog — τ-bench overview and pass^k motivation: <https://sierra.ai/blog/tau-bench-shaping-development-evaluation-agents>

**ToolBench / StableToolBench / API-Bank / NexusRaven**
- ToolLLM / ToolBench (OpenBMB, ICLR 2024, arXiv:2307.16789): <https://arxiv.org/abs/2307.16789> · code: <https://github.com/OpenBMB/ToolBench>
- StableToolBench — reproducible tool-use benchmarking via API simulator (arXiv:2403.07714): <https://arxiv.org/abs/2403.07714>
- API-Bank — "A Comprehensive Benchmark for Tool-Augmented LLMs" (EMNLP 2023, arXiv:2304.08244): <https://arxiv.org/abs/2304.08244>
- NexusRaven V2 (Nexusflow) — commercially-permissive function-calling model: <https://openreview.net/pdf?id=5lcPe6DqfI>

**Model Context Protocol (MCP)**
- MCP spec and docs: <https://modelcontextprotocol.io/> · versioned spec: <https://spec.modelcontextprotocol.io/>
- MCP first-anniversary / November 2025 spec release (`2025-11-25`: async tasks, OAuth, extensions, sampling-with-tools): <https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/>
- Anthropic — "Code execution with MCP: building more efficient AI agents": <https://www.anthropic.com/engineering/code-execution-with-mcp>
- Anthropic — introducing MCP (Nov 2024): <https://www.anthropic.com/news/model-context-protocol>

---

*Practitioner's takeaway:* evaluate tool use on the **structured call trace**, not the prose; score selection, arguments, chaining, recovery, efficiency, and safety **separately**; prefer **state/outcome-based** ground truth to escape the "any valid path" trap; always include **irrelevance** and **injected-failure** cases; and report **reliability (pass^k)**, not a single lucky run — especially anywhere a tool can write, charge, send, or delete.
