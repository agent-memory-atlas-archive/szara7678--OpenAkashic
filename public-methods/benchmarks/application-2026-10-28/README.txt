Public benchmark bundle: six synthetic corpus-aligned tasks, 18 one-shot generated answers.
All supplied records came from anonymous public read-only API routes. No private records, credentials, agent session logs or provider key metadata are included.
The protocol-v2 SHA was fixed before answer generation. Rejected corrupted initial fixtures are intentionally excluded from this publication bundle; their existence is disclosed in protocol-v2/report.
Review model requested through collaboration.spawn_agent: gpt-6-sol; generation gpt-6-luna. No provider usage receipts available.
Original blind ratings are immutable audit evidence. objective_* keys in those original ratings mean semantic model review, not automatic objective testing.
Task6 scoring ambiguity is separately documented in grade-adjudication.json. Both consistent strict and permissive readings tie all three conditions; do not claim the original one-point gap is superiority.
No generation reruns or rubric changes were made. The adjudication is unblinded coordinator review, not independent second grading.
Reproduce deterministic checks: python3 verify_bundle.py; python3 verify_artifacts.py; python3 build_report.py.
These scripts need only Python standard library and the bundled files. Original input token estimates used o200k_base; actual provider usage, costs and task execution outcomes are unavailable.
Hash verification is for the delivered snapshot; rerunning build_report changes generated_at and report hash, so perform verify_bundle first.
