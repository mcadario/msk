
**[BUG] consolidation: old KNodeRelations API**
- symptom: crash or silent wrong behavior during dedup/abstraction
- cause: _detect_contradictions uses `.relations.contradicts.append()`, _make_strategy_node uses KNodeRelations(specializes=[...]) — both are pre-refactor syntax
- KNodeRelations is now graph-based: only has `edges: list[KNodeEdge]`, accessed via .add() and .of_type()
- severity: HIGH — consolidation will crash or produce wrong graph
- fix: use `.relations.add(target_id, relation_type)` everywhere
- file: msk/consolidation.py, lines in _detect_contradictions and _make_strategy_node
- confirmed: yes

---

**[BUG] consolidation: datetime.utcnow() deprecated**
- symptom: DeprecationWarning in python 3.12, potential comparison errors if mixing aware/naive datetimes
- cause: _decay() uses datetime.utcnow()
- fix: `from datetime import timezone` then `datetime.now(timezone.utc)`
- severity: LOW now, will break later
- file: msk/consolidation.py, _decay()
- confirmed: yes

---

**[BUG] evaluator: no_llm path may still short-circuit on ls**
- symptom: task marked SUCCESS after step 1 (ls), make/npm never run
- cause: no_llm fallback in _evaluator used `last["success"]` directly
- fix was applied: now scans all results for test_keywords
- BUT: verify the fix is actually in the file, claude and user were editing simultaneously at points
- severity: HIGH for demo correctness
- file: workflow.py, _evaluator()
- confirmed: fix was discussed and written, application uncertain — CHECK

---

**[BUG] sim_score vs bm25_score naming**
- symptom: none (functional), but misleading parameter name
- cause: parameter was bm25_score, renamed to sim_score in discussion, unclear if rename applied to actual file
- file: msk/bplane.py, compute_activation_score()
- severity: cosmetic
- fix: grep for bm25_score in bplane.py

---

**[FRAGILE] dual-write not atomic**
- symptom: sqlite and qdrant out of sync after partial failure
- cause: save() writes sqlite first, then qdrant. no rollback.
- severity: MEDIUM — hard to detect, causes missing search results
- workaround: restart with fresh qdrant if search seems wrong
- file: msk/storage.py, save()

---

**[MISSING] graph traversal not implemented**
- symptom: coactivates_with edges exist but never used in reactivation
- cause: _collect_candidates() only does semantic search + type search, no graph walk
- severity: MEDIUM — paper claims graph channel, implementation doesn't have it
- file: msk/reactivation.py, _collect_candidates()

---

**[FRAGILE] TRIVIAL_COMMANDS exact match only**
- symptom: "ls -l" or "cat Readme.md" still form knodes
- cause: set membership check, no fuzzy matching
- severity: LOW — cosmetic noise in kplane
- file: msk/formation.py, TRIVIAL_COMMANDS

---

**[FRAGILE] _fallback_plan backtick extraction**
- symptom: preferred commands from activation packet not picked up if not backtick-wrapped
- cause: regex looks for `cmd` in agent_guidance string
- severity: MEDIUM — means memory doesnt influence fallback plan correctly
- file: workflow.py, _fallback_plan()
