# MSK Repository

MSK is an experimental agent-memory architecture inspired by
Minsky's K-lines and related cognitive-memory theories.

## Where to look

Current architecture:
- docs/architecture/

Theoretical background:
- docs/theory/

Current implementation status:
- docs/development/current-state.md

Known problems:
- docs/development/known-issues.md

Experiments:
- experiments/
- docs/research/

Codex investigations:
- docs/reports/

## Important distinction

Files under docs/theory describe theoretical influences.
They are NOT specifications of how MSK must be implemented.

Files under docs/architecture describe the intended MSK architecture.

The source code is authoritative for what is currently implemented.

Files under contracts/, when present, define invariants that should
not be changed without explicitly treating the change as an
architectural decision.

Files under development/ are meant to be edited and modified each time a known issue is found or one is resolved, or whenever the current state of the repo makes steps forward. 