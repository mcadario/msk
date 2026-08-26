---
name: msk-experiment-designer
description: Design small falsifiable experiments for MSK mechanisms before they are integrated into core architecture. Use when evaluating activation, graph propagation, level-bands, lifecycle updates, consolidation, B-plane policy, retrieval strategies, or any cognitively inspired mechanism whose value is not yet demonstrated.
---

# MSK Experiment Designer

Turn an architectural or research idea into the smallest experiment that can disconfirm or support it.

## Principle

Do not begin from “how should MSK implement this?” Begin from:

- what claim is being made;
- what observable behavior should differ if the claim is true;
- what simpler explanation could produce the same result;
- what minimal comparison separates them.

Research ideas in `docs/research/` are hypotheses, not requirements.

## Read before designing

1. `AGENTS.md`.
2. Relevant code in `msk/`, `workflow.py`, `evaluate.py`, `demo.py`, and `sim/`.
3. `docs/development/current-state.md`, `known-issues.md`, and `testing.md` so the experiment does not confuse an existing bug with the mechanism under study.
4. Relevant `docs/architecture/` files.
5. Only then, relevant `docs/research/` material.

## Experimental template

For each proposed experiment, define:

### Claim
A single sentence that could be false.

### Mechanism under test
The exact code path or conceptual mechanism being isolated.

### Competing explanation
The simplest baseline that could explain the same apparent benefit.

### Conditions
Prefer 2–4 conditions. Typical examples:

- no memory;
- semantic retrieval only;
- current MSK behavior;
- one targeted mechanism added or removed.

Do not change multiple mechanisms at once unless the interaction itself is the hypothesis.

### Cases
Use cases that expose failure modes, not only happy paths. Depending on the mechanism, include:

- relevant vs irrelevant semantic neighbors;
- useful and misleading graph edges;
- contradictions/supersession;
- sparse and dense neighborhoods;
- short and long paths;
- stale versus recently successful memories;
- low/high abstraction tasks;
- environment migration (for example v1 -> v2 behavior);
- LLM and `no_llm` modes when both matter.

### Metrics
Choose metrics tied to the claim. Examples:

- task success rate;
- steps/iterations to success;
- first useful command rank/position;
- selected K-node precision/recall against a hand-labeled set;
- irrelevant activation count or mass;
- graph nodes visited / propagation depth;
- activation concentration/entropy;
- contradiction error rate;
- stale-memory interference;
- persistence consistency failures;
- lifecycle adaptation across repeated trials.

Avoid vanity metrics that do not distinguish architectures.

### Expected discriminating result
State what result would support the mechanism, what result would refute it, and what result would remain ambiguous.

### Minimal implementation surface
Identify the fewest files/functions that need temporary instrumentation or a prototype. Prefer isolated experiment code over editing core behavior first.

## Baseline discipline

For memory experiments, always consider whether ordinary retrieval can reproduce the effect. A strong MSK experiment should distinguish at least some of:

- semantic similarity;
- metadata/level filtering;
- composite ranking;
- agent-specific bias/configuration;
- graph propagation;
- lifecycle adaptation;
- consolidation/abstraction;
- B-plane control.

Do not attribute a win to “reactivation” if the same inputs and ranking would make a top-k context baseline win too.

## Reproducibility

Specify:

- seed/setup state;
- initial K-nodes and their lifecycle values;
- environment version;
- task sequence;
- LLM/no-LLM mode;
- top-k and thresholds that matter;
- what artifacts/results to record.

Prefer deterministic `no_llm` experiments for mechanism isolation when possible, then use LLM runs as a robustness check rather than the only evidence.

## Repository hygiene

Do not add experiment infrastructure unless necessary. Reuse `evaluate.py`, `demo.py`, `sim/`, and existing data models where practical.

When the user asks to implement an experiment:

- keep experimental code isolated and easy to delete;
- avoid silently changing production defaults;
- do not turn a research hypothesis into architecture documentation before results justify it;
- record meaningful completed results in `docs/research/experiments.md` if requested or clearly appropriate.

## Output

Return a compact experiment plan with:

1. hypothesis;
2. baseline(s) and treatment;
3. setup/cases;
4. metrics;
5. pass/refute criteria;
6. minimal implementation plan;
7. major confounds;
8. what architectural decision the result would actually justify.

Prefer one decisive experiment over a broad benchmark suite when one will answer the question.