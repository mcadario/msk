---
name: msk-change-validation
description: Validate a proposed or completed MSK code change against runtime behavior, architecture docs, known issues, and current manual test expectations. Use before merging changes that touch core memory behavior, workflow control, persistence, reactivation, consolidation, models, or evaluation.
---

# MSK Change Validation

Review a concrete change for correctness and repository consistency without expanding scope unnecessarily.

## Inputs

Use this skill for:

- a diff, branch, commit, or PR;
- a set of edited files;
- a completed bug fix;
- a proposed refactor whose impact needs validation.

Do not use it as a generic architecture audit when no concrete change exists.

## Establish the contract of the change

Before judging code, identify:

1. what behavior is intended to change;
2. what behavior must remain unchanged;
3. which known issue, experiment, or architecture decision motivates it;
4. the smallest observable acceptance criteria.

If the change description is vague, infer the intended contract from the diff and relevant docs, but label the inference.

## Inspect impact, not just edited lines

Read `AGENTS.md` and inspect:

- callers of changed functions/classes;
- downstream consumers of changed data shapes;
- persistence/serialization boundaries when models change;
- LLM and `no_llm` branches if the changed path can reach both;
- `demo.py`, `evaluate.py`, and `sim/` when they exercise the behavior;
- relevant `docs/architecture/` and `docs/development/` files.

For core K-node changes, explicitly check formation -> storage -> reactivation -> packet consumption -> feedback/consolidation.

## Validation dimensions

### Behavioral correctness

Does the implementation satisfy the intended contract on the actual runtime path?

### Regression risk

Look for prior fragile areas recorded in `docs/development/known-issues.md` and `testing.md`, especially when nearby code changes.

### Data-model compatibility

When `KNode`, triggers, relations, activation, lifecycle, governance, `ActivationPacket`, or `AgentBias` change, check constructors, serialization, storage payloads, property accessors, and old API usage across the repository.

### Persistence consistency

When storage changes, consider both SQLite and Qdrant paths and whether partial failure can create divergent state.

### Behavioral influence

For reactivation changes, verify that newly selected/propagated information is actually consumed downstream. Do not accept “appears in selected_k_node_ids” as sufficient evidence of agent influence.

### Evaluation validity

Check that success metrics do not accidentally reward irrelevant steps or short-circuit before the task's meaningful criterion is met.

### Documentation consistency

Only require doc updates where leaving the current docs unchanged would make them false or materially misleading. Do not churn documentation for incidental implementation details.

## Test strategy

First inspect `docs/development/testing.md` and reuse existing manual checks where applicable.

Prefer the smallest test sequence that covers the change:

1. focused model/module smoke test;
2. targeted deterministic `no_llm` workflow test;
3. `python demo.py` when lifecycle behavior changes;
4. `python evaluate.py` when comparative memory behavior or metrics change;
5. LLM-mode check only when the change specifically affects LLM behavior or deterministic paths are insufficient.

If formal tests do not exist, say so. Do not pretend manual execution provides unit-level coverage.

When a known bug is fixed, recommend a regression test that would fail on the old code and pass on the new code.

## Scope control

Classify findings as:

- **BLOCKING** — violates intended behavior, corrupts state, breaks a runtime path, or invalidates evaluation;
- **SHOULD FIX** — significant regression/maintenance risk directly related to the change;
- **FOLLOW-UP** — real but not required for this change;
- **OUT OF SCOPE** — unrelated observation.

Do not hold a focused fix hostage to unrelated architectural debt.

## Output

Return:

1. intended change contract;
2. affected runtime path;
3. validation performed;
4. blocking/should-fix findings with file + symbol evidence;
5. test gaps and the smallest regression test worth adding;
6. docs that need updating, if any;
7. final verdict: **safe to merge**, **safe after fixes**, or **not ready**.

Keep the verdict evidence-based. If tests could not be run, distinguish static confidence from runtime verification.