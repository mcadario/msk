---
name: msk-research-bridge
description: Translate a cognitive-memory paper or research mechanism into testable MSK hypotheses without treating the source as a specification. Use for K-lines, ACT-R, Collins-Loftus spreading activation, memory surveys, or new literature when deciding whether a mechanism belongs in MSK.
---

# MSK Research Bridge

Map research into MSK carefully, preserving the difference between source claims, engineering analogy, and project decisions.

## Goal

Extract mechanisms that may illuminate an MSK design problem, then turn them into testable architectural hypotheses. Do not retrofit MSK to resemble a source for historical or aesthetic reasons.

## Source discipline

When the user provides papers or project research notes:

1. Ground the analysis in what the source actually states.
2. Preserve the source's terminology where it matters.
3. Separate:
   - **SOURCE CLAIM** — directly supported by the source;
   - **MSK ANALOGY** — a mapping proposed for this repository;
   - **HYPOTHESIS** — a testable claim about MSK;
   - **DESIGN DECISION** — something already adopted in architecture/code.
4. Never promote analogy to fact.
5. If the source does not specify an engineering detail, do not invent one and attribute it to the source.

## Establish current MSK first

Read `AGENTS.md`, relevant code, and `docs/architecture/` before drawing mappings. Use `docs/development/current-state.md` and `known-issues.md` to avoid mapping a paper onto behavior that is currently broken or absent.

For activation/memory work, inspect at minimum:

- `msk/models.py`;
- `msk/bplane.py`;
- `msk/reactivation.py`;
- `msk/formation.py`;
- `msk/consolidation.py`;
- `msk/storage.py`;
- downstream use in `workflow.py`.

Confirm these paths still exist before relying on them.

## Mechanism extraction

Reduce the source to mechanisms rather than slogans. For each relevant mechanism capture:

- state/representation;
- trigger or retrieval condition;
- update rule;
- propagation/control rule;
- inhibition/competition/forgetting if present;
- abstraction or hierarchy if present;
- success criterion or claimed functional role;
- assumptions the source depends on.

For example, “spreading activation” is not a sufficient extraction. Identify what quantity spreads, across which links, according to what rule, how it attenuates/accumulates, and how the result is used.

## Mapping table

For each extracted mechanism, compare:

- closest existing MSK construct;
- whether it is implemented, partial, represented-only, or absent;
- important semantic mismatch;
- what adopting it would change in observable behavior;
- whether a simpler existing MSK mechanism already serves the same function.

Do not force one-to-one mappings.

## Hypothesis generation

Convert promising mappings into falsifiable claims, for example:

- multi-path activation accumulation improves relevant secondary recall over semantic top-k;
- level-band control reduces stale/specific interference without losing useful strategies;
- lifecycle strength improves adaptation across environment shifts;
- graph relations add value beyond metadata filtering;
- B-plane control improves task-dependent memory selection compared with a fixed retrieval policy.

The exact hypothesis must follow from the source and current code, not from these examples.

For each hypothesis, define the simplest competing explanation and the experiment needed to separate them. Use the `msk-experiment-designer` skill when a full protocol is needed.

## Anti-patterns

Avoid:

- “Minsky/ACT-R/Collins-Loftus did X, therefore MSK should implement X”;
- treating biological plausibility as software evidence;
- claiming that embedding similarity is equivalent to spreading activation without showing the functional mapping;
- calling any graph retrieval “K-recursion”;
- assuming a stored relation has behavioral effect;
- importing source terminology into code when MSK already has a clearer native abstraction;
- broad redesigns before a discriminating experiment exists.

## Output

Return:

1. **Source mechanisms** — only the relevant ones.
2. **MSK mapping** — exact code/docs correspondence and mismatches.
3. **What MSK already captures**.
4. **What is genuinely absent or different**.
5. **Candidate hypotheses** — ranked by expected information gain.
6. **Minimal experiment for the top hypothesis**.
7. **Recommendation** — adopt, prototype, defer, or reject, with evidence level.

Keep literature interpretation and repository inference visibly separate.