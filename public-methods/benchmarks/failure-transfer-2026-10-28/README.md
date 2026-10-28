# Prior-risk experience transfer pilot

This is a targeted synthetic implementation pilot, not a general agent benchmark.
Three fresh agents requested as `gpt-6-luna` each implement the same three Python
contracts: SQLite backup audit, table-key join audit, and literal/explicit-alias
source-preserving search. One implementation per family and condition, six
frozen fixture cases per implementation: **9 programs / 54 case executions**.
The independent generation unit is a program; the 54 cases are not 54 independent
trials. Each arm agent implements all three families, allowing within-arm context
carryover. Actual provider identity, billed tokens, and cost were unavailable.

Conditions:

- `method_only`: full existing method, including caveats, and complete task specs.
- `raw_experience`: same plus all stored public application reports and opinions.
- `linked_experience`: exact same full report/opinion objects, regrouped only by
  stored `outcome_id`. No new recommendations, omitted failures, or extra facts.

Public examples were selected manually. The prior join report successfully
identified a risk; it is not an actual failed join. The backup report found
foreign-key inconsistency, and the search reports contain missed retrievals.
These experiences are controlled public examples, not private customer records.
The strong baseline already contains relevant warnings and the same detailed
current task requirements. Ceiling effects are possible. No automatic retrieval,
graph navigation, real-user productivity, financial outcome or billing effect
is measured here.

## Reproduce

Use Linux with Python 3 and Docker. The pinned public image is:

```sh
docker pull python@sha256:5789aa194f757888f41fa3d48e14b6feaa1b57c0af0b56fcb1372d6474d3bff0
python3 verify_frozen.py
python3 harness.py selftest
python3 harness.py evaluate candidate-manifest.json
python3 build_report.py
```

Run from this directory in a **copy** to preserve original reports. The frozen
inputs and generation files are hashed; result timestamps may differ on replay.
`prepare_inputs.py` documents the original setup and must not be rerun during
verification because it regenerates the pre-generation freeze. Optional tiktoken
is used only for input-material estimates, never as actual billed usage.

The candidate runner mounts only its module, runner, and current fixture input;
it strips gold before mounting. It has no network, readonly root, no secrets,
unprivileged UID, dropped capabilities, process/memory/CPU/time limits, and a
temporary writable directory. The supervisor independently reopens the actual
backup and compares contents; a claimed success is insufficient. Docker is risk
reduction, not a formal hostile-code boundary: candidate and supervisor share a
UID inside the container. Do not substitute unreviewed hostile code.

`fixtures.json` has manually computed expected values. The separate reference
implementation and targeted mutants validate the checker before candidate
creation. A transport corruption in draft Korean strings was corrected before
freeze and generation; the rejected draft was not a scored output. No candidate
was repaired after scoring. See `test-harness.json`, `freeze.json`,
`generation-freeze.json`, `candidate-results.json`, and `report.json`.


## Preserved primary and transport follow-up

The primary execution passed 17/18, 17/18, and 18/18 cases. Both failures were
`search-1`, with observed doubled Unicode escapes or question-mark substitution
in generated source. That gap is **not evidence of graph or experience benefit**.
`transport-audit.json` records this confound; the original programs remain intact.

A separate follow-up was frozen after seeing that problem and before generating
any follow-up code. It uses all three arms again with fresh agents, the same
contracts and reference information, and direct UTF-8 file writes. No old code,
test inputs or grades were supplied to those agents. **All** nine programs were
regenerated, not only failures. This is an explicitly post-primary follow-up on
the same frozen fixtures, not a new holdout or a repair of the original results.
Run the same commands inside `transport-followup/` for its separate results.
Both rounds total 18 generated programs and 108 clustered case executions.


## Prior-risk implementation pilot (2026-10-28)

A separately frozen executable pilot compared full methods alone, methods plus
stored reports/opinions, and the exact same reports grouped by outcome ID. Three
families (SQLite backup, table-key audit, source-preserving search), one program
per family/condition, six fixture cases per program. All conditions received the
same complete current task contract; existing method caveats were not removed.
The primary passed 17/18, 17/18, 18/18 cases but its only differences involved
Unicode source transport/escaping failures. These originals are preserved.

A predeclared follow-up regenerated ALL nine programs with fresh agents and one
direct UTF-8 file-writing route. It reused the same fixtures, so is not a new
holdout. Results: **methods alone 18/18; raw experience 17/18; linked experience
18/18**. The raw-experience join implementation omitted blank-key rows from
unmatched and outer-join counts. No general benefit or harm is established.
There were three independent generated programs per arm, not 18 independent
trials. Both rounds contain 18 original programs and 108 clustered case checks.
The requested model was gpt-6-luna; actual provider identity and billed usage
were unavailable. Follow-up input material estimates: 3345/6537/6599 o200k tokens,
not billing. Adding all prior experience increased supplied material here.

The checker independently opens produced backups, checks source preservation,
schema/row equality and FK integrity; it also checks payload preservation and
exact source ID/quote/hash for search. Eighteen reference cases and targeted
fault mutations validate the checker. This is bounded synthetic correctness,
not a security audit or proof of human productivity. Original inputs, frozen
hashes, programs, failures and replay instructions are in
this directory. The evidence supports careful selective
use of prior experience; it does not justify promising better outputs merely
because more records or graph links were supplied.
