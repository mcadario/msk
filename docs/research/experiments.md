## planned evaluation (not run yet)

3 conditions:
- none: no memory, bare agent
- repository: top-k semantic retrieval, context injection only
- msk: full B-plane + activation packet

tasks: 6 debugging prompts v1 (make works) + 6 v2 (npm only)
runs: minimum 3 per condition for any statistical claim

for persistence: use KNodeStore("msk_eval.db") not ":memory:"
otherwise knodes dont accumulate across tasks

## metrics to track
- success rate (did correct test command run and pass)
- correct_cmd_v2 (did agent use npm without trial-and-error on v2 tasks)
- steps_to_solution (how many commands before success)
- repeated_mistake_rate (did agent retry known-failed command)
- knode strength evolution (does make weaken, npm strengthen)

evaluate.py already collects most of these. check _record() function.

## what to expect
- none: should always try make first on v2, fail, then maybe find npm
- repository: should retrieve make knode as context but not be guided to npm
- msk: should reactivate make knode, make fails, npm knode forms, next run uses npm directly

if none and msk perform similarly → B-plane not adding value, activation packet not working
if repository and msk perform similarly → context injection equivalent to configuration (bad for paper)

## ablations worth running
a) msk with level_band disabled (all levels always) → isolates level-band contribution
b) msk with no graph relations → isolates graph contribution (not much since graph traversal not implemented anyway)
c) msk rule-based formation vs llm formation → isolates formation quality

## second domain (needed for publication)
customer support is the natural fit:
- user facts (preferences, history)
- policies that change (like npm migration)
- tool patterns (crm commands, ticket systems)
needs: second SimulatedEnvironment class, second task set