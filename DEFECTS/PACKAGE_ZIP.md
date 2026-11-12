# Package ZIP decoder independent defects

## D01: file/ancestor collision, closed after retest

Independent review found `raw/a` + `raw/a/b` in either order returned HTTP500 and could leave a synthetic blob. Case-fold alias `raw/A` + `raw/a/b` was incorrectly accepted on Linux. Three new independent tests failed before correction; original evidence is retained in `logs/package-boundary-independent-ancestor-red.txt`.

Resolution: validate the complete inventory before decoding payloads; reject any normalized file key that occupies a slash-delimited ancestor of another entry, independent of order and case. Explicit directory descendants are included. The unchanged independent suite then passed 61/61, with all frozen hashes matching. See `logs/package-boundary-independent-review.md` for scope, exact hashes and limits.

No open defect remains within the selected ZIP decoder scope. Resource budgets, imported JSON/schema validation, authenticity, case identifiers, and atomic filesystem transactions remain outside this slice and are not declared resolved.
