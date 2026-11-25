# W17 bounded 1.4 process restart and re-export

This test pins exactly 190 service and contract blobs from MCIS product commit
`d40e3b5fd2e208af84c84d6faf61095d0a0a89fb`. No product or contract edits.
Existing TestClient tests cover multi-generation restore; this gate adds an OS
process restart on the same restored SQLite and file store before re-export.

On Linux, from a Git checkout that already has the fixed commit object, use a
trusted existing project virtual environment (including Uvicorn and application
dependencies). From the source checkout root:

```sh
set -eu
SOURCE="$(mktemp -d)"
trap 'rm -rf -- "$SOURCE"' EXIT
COMMIT=d40e3b5fd2e208af84c84d6faf61095d0a0a89fb
git archive --format=tar "$COMMIT" service contracts > "$SOURCE/source.tar"
tar -xf "$SOURCE/source.tar" -C "$SOURCE"
"$PYTHON" -I -B /path/to/tests_acceptance/w17-restart-reexport/run.py --source "$SOURCE"
```

Set `PYTHON` to the existing environment's Python before running. An exact,
already extracted source tree is also accepted; the runner independently checks
all 190 Git blob hashes before launching any process. It only copies the pinned
bytes to a temporary tree, rejects missing, substituted and symlinked pinned
files, and does not write to supplied source. To exercise rejection, use an
isolated copy of the exported source and append a newline to
`contracts/archive-export-safety-v1.md`; the command exits 2 before the server
starts.

Uses installed Python/Uvicorn and existing dependencies. Fresh ephemeral loopback sockets 127.0.0.1 only; not external network. Unseeded actual processes: original A, fresh restore B, stop/restart B with identical SQLite and blob path, fresh second-generation restore C. All children and temp stores are removed afterward. Local role headers, not production authentication.

One registered synthetic restricted original, one report and one source-linked non-millisecond timeline event produce server archive 1.4. B accepts strict preview/commit. After real restart B, nonauthorized role cannot read originals or export (403), and old active receipt is historical-only (409). Only explicit historical read appends one Access. Report original/current hashes are unchanged and reference archive SHA A. Ordinary re-export retains source path/hash/bytes, authoritative timeline and mirror byte-for-byte, archive A as exact named ancestor, receipt/lineage metadata, and valid audit chain with original prefix. Fresh C strictly restores re-export, reads original bytes, preserves inactive receipt and validates provenance against B's archive. Output hashes describe one independent run, not immutable artifact pins. No ZIP or synthetic originals retained by the runner.

No repeated browser first import, actual vault or production identity, broad archive or unsupported business data, crash recovery, .NET, Unity, Git writes, CI, or deployment.
