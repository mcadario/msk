## design decisions

**why sqlite + qdrant instead of just one**
sqlite for structured queries (by_type, by_level_band, stats, get by id). qdrant for semantic search. tried doing everything in sqlite with json embedding column — too slow for cosine scan at scale. qdrant handles the vector part, sqlite handles the rest. save() writes both.

**why graph-based KNodeTriggers and KNodeRelations**
original design had hardcoded fields (keywords: list[str], task_types: list[str] etc). adding a new trigger type required model change. refactored to KNodeTrigger(entity_id, entity_type, weight) so new types are just data. old field names (keywords, task_types, tool_names) kept as @property for backwards compat. this means old code still works but new code should use .add() and .of_type()

**why ActivationPacket.agent_activations is dict not list**
went through: dict → list[AgentActivation] → back to dict. list version required AgentActivation wrapper class with agent_id field. added complexity for no benefit since agent names are simple strings and we never need edge metadata on the agent relationship. dict[str, AgentBias] is simpler and faster for 3-4 agents.

**why no_llm mode**
demo needs to run without API key to show investors/BAINSA. LLM calls are in 3 places: bplane classify, formation extract, workflow planner+evaluator. each has a deterministic fallback. bplane uses heuristic keyword matching. formation uses rule-based event scanning. planner uses _fallback_plan which reads preferred_commands from activation packet. evaluator uses returncode check. the whole system is demonstrable without a single API call.

**why seed_demo_knowledge()**
without seeding, phase 1 shows no reactivation (kplane is empty). seeding puts one make test-integration knode in before phase 1, so the audience sees reactivation working immediately. without seed you'd need to run 2 tasks before seeing any memory effect.

**why jaccard for dedup and not cosine**
laziness at the time. cosine via store._embed() would be better. jaccard uses word overlap which misses paraphrases. threshold 0.65 is arbitrary. worth fixing later but not critical.

**level-band numbers**
1=raw traces, 2=episode/fact, 3=strategy/skill, 4=governance. B-plane maps task types to bands: narrow→(1,2), procedural→(2,3), diagnostic→(1,3), strategic→(3,4), high_risk→(1,4). these are completely made up, not empirically validated. the paper presents them as a proposal, not a result.

## implementation gotchas

- KNodeStore(":memory:") creates in-memory qdrant — fresh every time, no persistence. pass file path for persistence
- sentence-transformers downloads on first import (~80MB). in offline/CI will hang or fail
- Pydantic v2: model_dump_json() not dict(). model_validate_json() not parse_raw(). if you see old pydantic methods something was missed
- LangGraph state is a TypedDict — all node functions must return {**state, "changed_key": new_value} not mutate state in place
- workflow._route() is the conditional edge — if success=True goes to memory_updater, else loops to executor. max_iterations prevents infinite loops
- formation._extract_rule_based() checks event.tool_name == "shell" — hardcoded. only works for shell tool events. other tools wont form knodes in no_llm mode
- consolidation.run() is called after EVERY task in memory_updater. can be slow with many knodes. background process would be better but not implemented

## things that dont work as expected

- K-recursion: data model has it (relations between knodes), consolidation does episode→strategy abstraction, but formation never composes a new knode from existing knodes. true K-recursion would mean "i remember X because i remember Y and Z together". not there yet.
- coactivation: coactivates_with edges are written but never read in reactivation. the reactivation planner doesnt do graph traversal. so the K-plane graph is richer than what actually gets used.

## debugging notes

if demo shows wrong behavior check in this order:
1. is evaluator stopping early? look for "Evaluator: ✓ success" after step 1
2. is formation creating ls/cat knodes? look for "Command succeeded: ls" in memory log
3. is make knode being strengthened when it should weaken? check memory_updater per-node logic, preferred_commands must be in content.structured
4. is qdrant empty? check store.stats() output in memory log

## env setup
mamba activate msk  
cd msk_v0  
python demo.py # no_llm mode if no .env  
python evaluate.py # same
**if ANTHROPIC_API_KEY in .env it uses LLM mode automatically

