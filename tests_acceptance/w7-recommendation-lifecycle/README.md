# W7 safety recommendation lifecycle (synthetic API gate)

Needs Git, Python 3.10+, and existing MCIS service test dependencies (including pytest and FastAPI TestClient). Point at a separate local Git worktree checked out at 7dfb3261522ff6241b9f5b44f809dd405b28ffde. Run using an existing environment, from a neutral directory:

    PYTHONDONTWRITEBYTECODE=1 /path/to/python /path/to/w7-recommendation-lifecycle/check.py --base-checkout /absolute/path/to/fixed-worktree

The checkout is read only. The runner checks the exact commit and each of 183 regular-file Git tree entries and blob bytes, materializes only those pinned Git blobs to a temporary source folder, and does not use working-tree edits/untracked files. The fresh SQLite, synthetic data, and copied source are temporary. No external networking, account, deployments, notifications, or real case material.

TestClient calls actual FastAPI routes. A single synthetic case and recommendation go from edited draft to a separately recorded consultation round (45-day declaration, reply, decision, waiver, closure), then local Issued, reply, progress, Implemented and Closed. There are two database engine disposals/reopens, exact body and history reads, seven recommendation and five consultation audit entries and hash-chain verification. Checks also cover invalid state jumps, premature round closure, missing rationale, denied body read, and rejection of edits after local issue.

The consultation's draft version and optional digest are self-reported. This test orders actions after review but does not represent a server-enforced cross-entity gate, a separate approval state, production authorization, web UI/real browser, legal verification, external delivery, or completion of all of W7. It does not change product code.
