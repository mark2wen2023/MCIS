# Existing display controller: date/source rejection checks

Parent `154013683fd4a567918ec69582bc04f3a3acdfa2`; product main inspected separately
at `94d5e38c926fda232bb987b60fa9145e4bcf01a7`. Main TimelineEvent has a UTC/timeSec
and optional source label/evidence IDs, not the raw-time/clock-review binding.
This change does not connect these two product paths or invent that binding.

The existing registered display already separates original-record UTC, display
alignment UTC, and “校时依据未交付、人审未签”. At T100 B records 12:01:28Z,
+12 seconds displays 12:01:40Z, without establishing event order. Gap/no-point,
wrong internal protocol, context changes and late callbacks already have tests.
No additional timeline component or ClockCorrected record is needed here.

Only five missing negative assertions are added to the existing `display_ui.cjs`:
missing time; foreign frame case; February 30; inconsistent correction arithmetic;
wrong per-vessel aligned UTC. Each first displays valid B detail, then rejects
the invalid frame and checks previous source/offset/pointer/aligned time cleared,
including an obsolete detail callback. Production validator and all frozen
HTML/source inputs remain unchanged. These are ordinary synthetic data errors.

## Reuse an existing frozen artifact without ingestion or database

Requires Node and standard-library Python only. Supply the already generated
pin-free synthetic HTML described in DISPLAY-BROWSER.md. Do not run its generator
for this check: that is a separate temporary-registration scope. Expected HTML
SHA-256: `917cfd7eee4ffac24b129a76a43e251d22b965e2fcd3ccfa07494530e402bead`.
Missing artifact or digest mismatch stops; no network or fallback.

From this candidate root:

```sh
node --check tests_acceptance/registered-trajectory-pair/display_ui.cjs
python -I -B - /absolute/path/to/existing-display-only.html <<'PY'
import hashlib,json,runpy,subprocess,sys,tempfile
from pathlib import Path
root=Path.cwd()
raw=Path(sys.argv[1]).read_bytes()
assert hashlib.sha256(raw).hexdigest()=='917cfd7eee4ffac24b129a76a43e251d22b965e2fcd3ccfa07494530e402bead'
text=raw.decode(); assert text.count('const frames=')==1
frames,_=json.JSONDecoder().raw_decode(text.split('const frames=',1)[1])
record={'scope':'synthetic-display-only','caseId':frames[0]['caseId'],'frames':frames}
with tempfile.TemporaryDirectory() as d:
    shell=Path(d)/'shell.html'
    runpy.run_path(str(root/'tools/replay_evidence_workbench/registered_build.py'))['build'](shell,display_only=True)
    subprocess.run(['node',str(root/'tests_acceptance/registered-trajectory-pair/display_ui.cjs'),str(shell)],input=json.dumps(record),text=True,check=True)
PY
```

Author run: both commands exit 0, five new rejection cases plus the existing
controller assertions passed. Initial test failed because its error-text pattern
did not match the existing product message; corrected to assert that exact
message without changing the controller. This is Node with handwritten DOM and
simulated transport, not SSR, browser, current authorization, fresh Access audit,
source authenticity, human clock sign-off or production timeline integration.
The fixture is fixed synthetic evidence, never a reusable authorization token.
No backend, API, schema, data, production code, signing, ingest or archive change.
