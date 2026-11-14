# Isolated terminal demo final results

Base4f5ceb0aae5486334265b962431892a7dbcaaa0b. Standalone new demo; prior services
unchanged. Actual subprocess command with --choice both --json returned two sources,
one conflict candidate delta5deg, uncalibrated warning and unreviewed status.

Primary5 pass3.77s; independent12 pass7.31s; independent final primary5+ind12=17/17
zero skips11.33s. Full prior400+new primary5=405/405 zero skips115.14s; independent12
not included in that full run, covered separately final17. Counts overlap.
MCIS_PREFLIGHT_REAL_CORE=/tmp/mcis-preflight-core.sh; PYTHONPATH=service python -m pytest.
New tests test_isolated_demo.py and test_isolated_demo_independent.py; prior full
regression inventory remains in logs/investigator-host-client-results.md.

Native implementation and native independent reviewer, no separate Codex desktop
app claim. Real SQLite/ASGI/core and subprocess/terminal interaction, not browser,
IdP, LLM, real accident data or deployment. Python socket bind/connect hooks prove
that Python flow does not use them, not whole-OS core subprocess network audit.
Case/source preparation direct existing trusted-host functions, no legacy app mount.

Temporary data cleanup ordinary success/cancel/failure tested; abrupt kill/OS failure
not guaranteed. Stored result deliberately deleted with temporary run. Summary is
not archive/approval/import authority. No credentials printed, user DB unchanged.
Product hash and detailed independent coverage in tests_acceptance/ISOLATED_DEMO/REPORT.md.
No merge/deployment or production-login claim.
