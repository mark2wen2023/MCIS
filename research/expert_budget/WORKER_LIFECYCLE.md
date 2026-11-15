# Worker lifecycle prerequisite — offline only

Basec87035f (readiness memo), parent3a99009; independent branch
feat/offline-worker-lifecycle-budget. Existing production/permissions untouched.

Read-only inspection of complete hold candidate498f807 executor.py/ownership.py
confirmed dependency on Bridge, fixed runner hash, Pi packages1.5.2, bounded
pipes, exclusive reaper with stable SIGCHLD, waitid WNOWAIT checks and process
cleanup. Its remote constructor explicitly rejects raw_key_disabled. Historical
ownership6f8f429 requirements are not proof this environment satisfies them.
No ownership probe, process launch, restricted test or secret lookup was run.
Main has two-role protocol, not this worker/bridge stack. FourChair is a separate
four-role simulation. There is no safe drop-in adapter between them.

Added worker_lifecycle.py is the smallest offline ordering/budget experiment:
reservation commits first; result alone cannot settle; zero exit plus cleanup
must also be declared. Unknown/stop consumes the pending attempt, blocks reuse;
late results cannot become success. Four seats share the existing16 counter.
These declarations explicitly do NOT authenticate process ownership or terminate
anything. Actual integration still requires trusted managed bootstrap, owned
worker observations, ticket/context/result validation, deadlines, tool limits,
non-replayable dispatch and sanitized durable receipts. Token/cost limits absent.
Do not remove HOLD or wire public caller claims to real execution.

Developer synthetic command:
PYTHONPATH=. service/.venv/bin/pytest -q research/expert_budget research/expert_meeting tests_acceptance/EXPERTRECEIPT
Result150 passed in1.31s;11 new cases included (not additional150+11).
Coverage: four roles/two rounds/exhaustion; stop at four pending boundaries;
wrong sequence/failed exit/lost ownership/early cleanup; wrong attempt; pending
exclusion; injected settlement rollback and sticky unknown state. Tests use only
temporary SQLite and declared events, not real Pi, DeepSeek, subprocess termination,
credentials, browser or independent acceptance. No production performance claim.
