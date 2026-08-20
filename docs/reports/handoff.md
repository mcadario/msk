## 5 most important things

1. **demo still broken in a subtle way** — evaluator fix was applied but verify it actually runs make AND npm before declaring success. last seen output showed ls triggering success. check workflow.py _evaluator, look for test_keywords scan
2. **two consolidation bugs unfixed** — _detect_contradictions and _make_strategy_node still use old KNodeRelations syntax (direct field assignment, not .add()). will silently fail or crash during consolidation
3. **graph traversal not implemented** — coactivates_with edges exist in data model but reactivation.py never follows them. K-recursion is data-model-only, not operational
4. **models.py changed significantly** — KNodeTriggers and KNodeRelations are now graph-based (edges with typed relations, .add() method). old code that constructs them with keyword args will break silently or loudly depending on pydantic version. formation.py was updated, consolidation.py was NOT fully updated
5. **no_llm mode is the demo path** — dont try to demo with API, use no_llm=True. seed_demo_knowledge() must be called before phase 1 or reactivation wont show anything

## where things stand
- paper: MSK-proposal_deduped.tex is the working source. position paper, no empirical results
- implementation: msk_v0/ runs but has bugs listed above. demo mostly works in no_llm mode
- bainsa proposal: BAINSA_MSK_proposal.docx done, needs second team member

## biggest risks
- consolidation module is the most fragile, least tested, has outdated syntax
- evaluator logic is subtle — easy to reintroduce the ls-triggers-success bug
- qdrant + sqlite dual-write in save() — if one fails the stores go out of sync, no transaction

## do first
1. run demo.py with no_llm=True and check all 4 phases show correct behavior
2. fix consolidation.py (see KNOWN_ISSUES.md)
3. add missing citations to paper

## other files
- CURRENT_STATE.md — whats working, whats not, module map
- NEXT_STEPS.md — prioritized todo
- KNOWN_ISSUES.md — bugs with fix directions
- PROJECT_NOTES.md — design decisions, gotchas
- ARCHITECTURE_QUICKREF.md — component map

## stuff claude might know that isnt written anywhere else

- the "Brain B" term used in the paper — not 100% sure this is literally minsky's term or a reconstruction by singh. verify before citing as direct minsky
- ActivationPacket used to have target_agents: dict[str, AgentBias], was briefly changed to list[AgentActivation], then changed BACK to dict. workflow.py uses for_agent() method not direct dict access. if you see target_agents["planner"] anywhere thats old code
- TRIVIAL_COMMANDS set in formation.py — {"ls", "ls -la", "pwd", "cat README.md", "cat readme.md"} — completely hardcoded, will miss variations like "ls -l" or "cat readme.MD"
- sentence-transformers downloads model on first run (~80MB), cached after. if running in CI or offline this will fail silently or hang
- qdrant ":memory:" path means a fresh collection every run — intentional for demo, not for evaluation. use file path for persistence
- the composite activation score (eq 2 in paper) uses bm25_score parameter name in bplane.py but now actually receives cosine similarity from sentence-transformers. parameter was renamed to sim_score in discussion but CHECK if the rename was actually applied to the code
- Quillian 1968 appeared in a Minsky-edited MIT Press volume — worth mentioning this in paper, makes the intellectual lineage explicit
- jaccard similarity in consolidation uses SIMILARITY_THRESHOLD = 0.65 — completely arbitrary, never tuned
- the _fallback_plan in workflow.py extracts preferred commands from agent_guidance string by looking for backtick-wrapped text — fragile regex-ish logic, will miss commands not wrapped in backticks