# MSK Repository

MSK is an experimental agent-memory architecture inspired by
Marvin Minsky's K-lines and related cognitive-memory theories.

## Repository map

Core MSK implementation:
- `msk/`

Simulation environment:
- `sim/`

Main workflow and runnable entry points:
- `workflow.py`
- `demo.py`
- `evaluate.py`

Architecture documentation:
- `docs/architecture/`

Development status and maintenance notes:
- `docs/development/`

Research and theoretical background:
- `docs/research/`

Codex reports and handoff material:
- `docs/reports/`

Demo progression:
- `DEMO_PHASES.md`

## Core implementation

The main MSK package is under `msk/`.

Relevant modules currently include:

- `msk/models.py` — core data models and shared structures
- `msk/formation.py` — memory formation
- `msk/storage.py` — persistence and storage behavior
- `msk/reactivation.py` — memory reactivation
- `msk/consolidation.py` — memory consolidation
- `msk/bplane.py` — B-plane / higher-level control logic

The source code is authoritative for what is currently implemented.

Do not infer that functionality exists merely because it appears in documentation,
research notes, reports, comments, TODOs, or model fields.

## Documentation roles

Different documentation directories have different purposes.

### `docs/architecture/`

Contains the intended architecture and implementation-facing design documentation.

Current files include:

- `architecture.md`
- `models.md`
- `api-notes.md`

Use these files to understand how MSK is intended to be structured.

If architecture documentation and source code disagree, do not silently choose one.
Identify the discrepancy explicitly.

When an architectural change is made, update the relevant architecture documentation
when appropriate.

### `docs/development/`

Contains living documentation about the current state of the repository.

Current files include:

- `current-state.md`
- `known-issues.md`
- `debugging.md`
- `next-steps.md`
- `testing.md`

These files are expected to evolve with the main branch.

Update them when relevant:

- update `current-state.md` when implemented behavior or capabilities materially change;
- update `known-issues.md` when issues are discovered, resolved, invalidated, or better understood;
- update `debugging.md` when important debugging knowledge is gained;
- update `testing.md` when testing strategy or coverage changes;
- update `next-steps.md` when priorities materially change.

Do not leave resolved issues documented as active problems.

### `docs/research/`

Contains theoretical background, research notes, candidate mechanisms, and experiments.

Current files include:

- `ACT-R.md`
- `CollinLoftus-spreading-activation.md`
- `experiments.md`
- `notes.md`

These files are research inputs, not implementation specifications.

Concepts from K-lines, ACT-R, Collins–Loftus spreading activation, or other
cognitive architectures should not be treated as requirements unless they have
been explicitly adopted into the MSK architecture.

Do not modify MSK merely to make it resemble one of its theoretical influences.

### `docs/reports/`

Contains Codex investigations and handoff material.

Current files include:

- `codex-report.md`
- `handoff.md`

Reports may describe the repository at a particular point in time and can become stale.

Do not treat a report as authoritative over current source code or current architecture
documentation.

## Simulation and workflows

The `sim/` package contains the simulation environment used by the project.

Root-level files such as:

- `workflow.py`
- `demo.py`
- `evaluate.py`

exercise or evaluate the MSK system and are useful for understanding how the components
interact in practice.

When investigating runtime behavior, trace these entry points into the `msk/` package
rather than reasoning only from data models.

## Working principles

Before making a substantial change:

1. Inspect the relevant source code.
2. Read the corresponding files in `docs/architecture/`.
3. Check `docs/development/current-state.md`.
4. Check `docs/development/known-issues.md`.
5. Consult `docs/research/` when the change concerns a research or cognitive mechanism.
6. Inspect the workflow, demo, evaluation, or simulation code when runtime behavior matters.

Always distinguish between:

- what the source code currently does;
- what the architecture documentation says MSK should do;
- what development documents say is incomplete or problematic;
- what research documents propose or investigate;
- what reports observed at an earlier point in time.

Prefer executable code and tests when describing current behavior.

## Architectural changes

Do not make broad architectural changes merely because an alternative appears cleaner.

First identify:

- the current behavior;
- the reason the existing design appears to exist;
- affected modules and workflows;
- relevant known issues;
- whether the proposed change follows from the intended architecture or represents a new one.

If a change intentionally alters the architecture, make that explicit and update the
relevant documentation.

## Research and experiments

Research documents are intended to support exploration rather than dictate implementation.

Experimental mechanisms should preferably be evaluated before being integrated into
the core `msk/` package.

Record meaningful experimental findings in `docs/research/experiments.md` or another
appropriate research document.

If an experiment changes the intended architecture, propagate that conclusion into
`docs/architecture/`.

If it changes the known implementation state or resolves a problem, update the relevant
files under `docs/development/`.

## Keeping documentation synchronized

The documentation should follow the evolution of the main branch.

When completing meaningful implementation work, check whether the change also requires
updates to:

- `docs/architecture/`
- `docs/development/current-state.md`
- `docs/development/known-issues.md`
- `docs/development/next-steps.md`
- `docs/development/testing.md`
- `docs/research/experiments.md`

Do not update documents mechanically if the change does not affect them.
Do update them when leaving them unchanged would make them misleading.