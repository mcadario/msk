---
name: msk-architecture-audit
description: Audit MSK's actual runtime architecture against its intended architecture. Use for architecture reviews, architectural drift, dead or disconnected abstractions, ownership/coupling problems, or planning structural refactors. Do not use for ordinary one-file bug fixes or style cleanup.
---

# MSK Architecture Audit

Perform an evidence-led architecture audit. The goal is to understand what MSK actually does, where that differs from intent, and which differences matter. This is not a lint pass and not an invitation to redesign the project from taste alone.

## Ground rules

1. Read `AGENTS.md` first and obey its source-of-truth rules.
2. Treat executable code as authoritative for current behavior.
3. Treat `docs/architecture/` as intended architecture, `docs/development/` as living status, `docs/research/` as research input, and `docs/reports/` as potentially stale observations.
4. Do not infer behavior from a model field, enum, comment, TODO, or document unless a runtime path actually consumes it.
5. Do not modify code or docs unless the user explicitly asks for changes after the audit.

## Inspection order

Start broad, then narrow:

1. `workflow.py`, `demo.py`, and `evaluate.py` to establish real entry points and observable behavior.
2. `msk/models.py`, `msk/storage.py`, `msk/bplane.py`, `msk/formation.py`, `msk/reactivation.py`, and `msk/consolidation.py` to reconstruct ownership and interfaces.
3. `sim/` when environment behavior affects the conclusion.
4. `docs/architecture/architecture.md`, `docs/architecture/models.md`, and `docs/architecture/api-notes.md` for intended design.
5. `docs/development/current-state.md`, `known-issues.md`, `testing.md`, and `next-steps.md` to separate known debt from newly discovered debt.
6. Relevant research or reports only after the implementation is understood.

Confirm paths and symbols still exist before relying on this list; the repository evolves.

## Build the actual architecture

Reconstruct, from calls and data movement:

- task entry and LangGraph control flow;
- B-plane classification and control decisions;
- K-plane formation, persistence, search, scoring, reactivation, lifecycle updates, and consolidation;
- S-plane consumption of `ActivationPacket` / `AgentBias` and the resulting behavioral effect;
- short-term versus persistent state;
- SQLite/Qdrant ownership and consistency boundaries;
- graph relation producers and consumers;
- error and retry boundaries;
- points where LLM and `no_llm` paths diverge.

For important structures, perform a write/read/effect audit: where is the value created, where is it persisted, where is it read, and what observable decision does it change?

## Evidence status

Use these labels precisely when useful:

- **EXECUTED** — reached on a demonstrated runtime path.
- **REACHABLE** — callable from current code, but not demonstrated in the inspected path.
- **REPRESENTED_ONLY** — exists in schema/storage/config but has no verified behavioral consumer.
- **DOCUMENTED_ONLY** — claimed by docs but not found in current code.
- **STALE_OR_UNKNOWN** — evidence conflicts or is insufficient.

A represented field is not an implemented mechanism. A stored edge is not graph traversal. A selected K-node is not behavioral influence unless downstream code consumes it.

## What to look for

Prioritize architectural findings such as:

- responsibilities split across modules in contradictory ways;
- state duplicated across representations with unclear authority;
- abstractions that are populated but behaviorally inert;
- behavior hidden in root workflow code that docs attribute to another plane;
- interfaces whose data shape leaks module internals;
- graph or activation concepts that stop at retrieval/ranking rather than influencing agents;
- lifecycle/consolidation operations whose effects cannot reach later decisions;
- accidental coupling between demo assumptions and core architecture;
- failure modes that can silently desynchronize persistent representations;
- architecture docs that materially misdescribe current behavior.

Ignore cosmetic naming and minor style unless they conceal a real architectural ambiguity.

## Simplicity challenge

For each major mechanism, ask whether a materially simpler design could reproduce the same current observable behavior. In particular, distinguish effects attributable to:

- ordinary semantic top-k retrieval;
- metadata filtering/scoring;
- explicit agent configuration via `ActivationPacket`;
- graph relations or propagation;
- lifecycle adaptation;
- consolidation/abstraction;
- B-plane control.

Do not claim a mechanism is unnecessary merely because a simpler baseline is conceivable. State what experiment would establish equivalence or difference.

## Output

Return a compact architecture report with:

1. **Runtime map** — actual control/data flow.
2. **State and ownership map** — where authoritative state lives.
3. **Intent vs implementation** — only material discrepancies.
4. **Behaviorally inert or partial abstractions** — with write/read/effect evidence.
5. **Top findings** — ranked by architectural consequence, each citing file and symbol.
6. **Simplest competing explanation** — what current behavior could be reproduced by a simpler memory system.
7. **Next experiments** — the smallest tests that would resolve the most important uncertainty.

Separate confirmed facts from inference. If the evidence does not establish a claim, say so.