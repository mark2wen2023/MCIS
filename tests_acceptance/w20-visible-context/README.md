# W20.2 current-source confirmation guard (synthetic Linux)

Fixed application base `7dfb3261522ff6241b9f5b44f809dd405b28ffde`.
The original mounted panel source Git blob is `842563abf7e352494b7f86ae4df0af951f21da30`.
This is the W5 InterviewPage's existing W20.2 panel, not the separate research-only single-seat UI.
The change does not connect/mount the research seats, change service contracts or grant permissions.

Before, a previously checked row disabled its checkbox if the current transcript lost the quotation,
but could leave confirmation enabled. Now acknowledgments belong to current visible transcript context;
changed current content (even with the same quoted substring), draft, or missing/ambiguous source
requires a fresh human review. Exactly one current round and exact unique quotation are required.
The saved draft citation remains labeled separately from currently readable context. The unchanged
service is the final authority for permissions/source revisions. The UI's equality check is not
a cryptographic or semantic proof and does not detect changes the current transcript read has not received.

From the repository root with existing dependencies, run:

    MCIS_NODE_MODULES="$PWD/web/node_modules" \
    MCIS_HAPPY_DOM_PATH=/absolute/installed/happy-dom/lib/index.js \
    MCIS_HOST_PYTHON=/absolute/pinned-service-venv/bin/python \
    bash tests_acceptance/w20-visible-context/run.sh

Without a repository checkout, runner arguments may point to candidate files root, exact fixed
web root, and exact fixed service root respectively. No install or network is performed.

Observed on fixed Linux: Original-mounted reviewer fails the regression (missing source still enables
Confirm); candidate passes mounted React seven phases. Real FastAPI HTTP handlers via in-process
TestClient and temporary SQLite: one synthetic draft generated through a controlled fake model,
new source turn added, stale confirm gets 409 SOURCE_CHANGED, reopened DB still PendingReview with
zero written statements. The mounted React and API tests are separate (no browser click→API here).
No shipped browser run, actual LLM, credentials, remote network, deployment, or human expert
semantics partly or fully validated. This closes only the current-source acknowledgment product defect.
