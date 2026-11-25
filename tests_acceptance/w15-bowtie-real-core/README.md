# W15 offline positive Bow-tie gate

Tests-only successor to the separate unavailable-core browser candidate
`9ca1c12d04db524e385f2509a4e2cae5cb44605c`. Product source
`2c72d022f3d3275af637b0cdc6e545735e3200a9` and the negative candidate stay
unchanged. This runner does not launch a browser and does not reuse the historical
no-sandbox browser runner. The negative test remains independent.

The runner checks the 339 prior source pins and 15 core paths (12 declared
build inputs, launcher, recipe, original `tests_acceptance/W153/test_cli.py`).
The launcher and recipe overlap, for 352 unique pinned product files. Three
unchanged negative gate helper files are checked separately. Staging restores
the exact pinned file modes, including the executable launcher, in a fresh
temporary tree. No runtime files, product edits, or Git metadata are included
in this test change.

From the fixed candidate checkout, using the existing product checkout as a
read-only source (or repeated disjoint, already verified exports):

```sh
gate=tests_acceptance/w15-bowtie-real-core/run.py
python3 -B "$gate" --candidate "$PWD" \
  --source-dir /absolute/2c72d02-checkout --verify-only
```

For full acceptance, use a Linux runner with an already-installed .NET SDK
8.0.428, existing service Python with pytest, and an already isolated offline
network namespace with only loopback active. The runner refuses other network
interfaces. Do not alter sandbox policy, bypass SDK initialization, install
packages, or try an external feed. If the runner is already successfully
initialized under its normal home, it uses that home without forging or
forcing any first-use state. All restored package locations and the empty
restore source are new task-local paths. Run:

```sh
python3 -B "$gate" --candidate "$PWD" \
  --source-dir /absolute/2c72d02-checkout \
  --dotnet /absolute/preinstalled/dotnet \
  --host-python /absolute/existing/service/venv/bin/python \
  --evidence /absolute/new-w15-core-evidence
```

The unchanged launcher must execute the original CLI and the official synthetic
W153 regression. The artifact manifest must match the SDK, recipe, all 12
declared source and output artifact digests from the actual build. The unchanged
FastAPI service then uses that core on localhost and a disposable SQLite
database. The known synthetic positive preview must produce 5 nodes / 4 edges;
the unknown endpoint must return a construction diagnostic and cannot become a
successful partial graph. Both responses retain hypothesis-only scope and
registered source metadata, without a safety/risk verdict. After service
shutdown and restart the two synthetic source bindings still read separately,
and the database dump matches the pre-preview digest. A blocked or failed stage
leaves no success receipt.

Local verification: 352 unique exact Git blob/mode pins and 3 unchanged helper
pins passed. Full execution stopped at missing preinstalled executable .NET
(exit 2); CLI, artifact manifest, live HTTP/SQLite positive tests, browser and
production remain unverified. No real identity, data, model, Unity, deployment,
or business judgment is tested.
