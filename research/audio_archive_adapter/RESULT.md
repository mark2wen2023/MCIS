# Native audio-v3 internal adapter developer validation

Branch candidate/audio-v3-archive-adapter; parent bce6f5bd7c0563d7434ed56ad074a0cdfe49e78e.

Only the9 new explicitly selected ordinary test nodes listed in nodeids.txt were run. Prefix (repository root):
```
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service /workspace/mcis-pr104-supported-archive/service/.venv/bin/python -m pytest -q -p no:cacheprovider --rootdir=/workspace/mcis-sensevoice-review
```
Append the9 listed nodeids then `--tb=short`. Final result **9 passed in2.63s**, zero failures/skips. Earlier6-node run is a subset and must not be added. No whole test file/repository, collection-only run, paused node or write-refusal/security probe was run.

The actual optional audio app/SQLite HTTP workflow creates generated PCM registration, task and revisions. The executor is explicitly stubbed with fabricated recognizer output; failure/timeout tests inject ordinary exceptions before publication, not real worker termination or an uncertain SQLite commit. No real case, speech recognition/model/API or browser is exercised. Native load_receipt is used for actual generated-source byte reads.

Assertions preserve full revision0 and two human revisions, raw recognizer output and exact audit associations; two separate successful tasks sharing one original invoke load_receipt once. Imported v2, additional recommendation state, missing receipt result and failed/unknown task refuse. Unknown task remains interrupted_unknown and is not dispatched again. Ambiguity fixture APPENDS one additional synthetic event using the normal audit helper; no existing protected row/trigger is edited, deleted or bypassed. One node confirms same session is used and audit lines are unchanged after extraction. No permissions-denial test is selected.

Frozen files include new module/tests/contract/report/nodeids. No source media, models, databases or credentials are included. No HTTP/default app/production exporter, whitelist or permissions change; no merge/deployment. Limited developer verification only; independent acceptance and genuine file/DB concurrency, original reader safety, production identity and complete export/restore remain outstanding.
