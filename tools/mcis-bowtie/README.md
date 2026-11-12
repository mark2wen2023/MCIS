# Bow-tie hypothesis structure CLI

Run `tools/mcis-bowtie/mcis-bowtie.sh` with the model object from
`contracts/bowtie-preview-v1.md` on stdin, no arguments. Requires existing .NET
SDK 8.0.428 and Python 3 on Linux; set MCIS_DOTNET if not ~/.dotnet/dotnet.
Only the explicit ten unchanged domain/core source files in the project compile.
No W11 adapter, ECFC import, source registry or file persistence is invoked.

All nodes are ToBeVerified and all barriers Unknown. Ordinary nodes are added
before escalation factors, preserving input order within each group, then edges
in input order. The first core construction failure stops processing and returns
no validation issues. Counts include the top event and only accepted temporary
items. Construction and structure issues are successful protocol responses
(exit 0), not operational failures. Protocol rejection exits 4; unexpected
operation failure exits 1. Build failures may produce no JSON. Diagnostics go to
stderr, JSON to stdout. Never interpret empty/unavailable output as valid.

`structureValid` means only that existing project graph rules found no errors.
It does not establish facts, causality, safe/adequate barriers, risk, compliance,
or liability. A direct path with no barrier can be structurally valid. No scores,
confirmed state, reference verification, legal conclusions or automatic analysis.
The 128KiB/64-node/128-edge limits are engineering limits, not professional rules.

Builds are serialized by an isolated lock, source snapshots and artifact SHA256
receipts are verified, and deterministic SDK/configuration/path mapping is used.
`out/` contains generated files and is not for publication. The receipt binds
compiled inputs and artifact hashes; it is not a signature or an authorization.

Run synthetic tests: `python tools/mcis-bowtie/test_cli.py` with SDK environment.
The rebuild/concurrency test invalidates this adapter's cached receipt; only run
when not serving preview requests. No reports or case databases are read.
