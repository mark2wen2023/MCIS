# EXPERTRECEIPT: offline consistency foundation

This main-based candidate copies only receipt.py byte-for-byte from expert source
1d5262c9f8a491fd7b1d8037c4dff8988865770c. Its parent is main
4a6e72939c1d740707d65abb505b6eb90d585708. No preview history, CLI,
Pi runner, credentials, provider transport, browser route or case service is included.
This is NOT integration of the expert meeting feature into the product.

## Contract and limits

Use only trusted private local directories with a single writer. A valid completion
manifest means local artifact consistency, including when runStatus is failed,
partial, cancelled or unknown. It does not authenticate authors/providers, prove
model calls, certify public provenance, approve facts, or compute consensus.
Final directory and leaf links are refused; ancestor links are not prohibited.
Separate reads are not a concurrent immutable snapshot. Do not expose this as a
hostile upload/import service or reuse it as the case evidence filesystem boundary.
The receipt row schema is not fully strict (True compares equal to version 1),
transportMocked is returned without type validation, and event phases do not
validate a business state machine. Consumers must independently validate their
versioned business schema and label declarations as unverified.
Metadata token restrictions are not secret detection: callers must supply no
credentials, personal data or private cases. Failed writes may leave incomplete
files; no implicit retry or completion claim is allowed. This module performs no
network calls. Authenticity is always false in its verification result.

## Dependency split and integration sequence

1. This standard-library receipt foundation: self-contained offline checks.
2. Group packet/validation and meeting state machine: machine imports engine
   helpers; engine's raw online paths must remain refused (498f807). Extract final
   reviewed files rather than applying later security commits without their bases.
3. Bridge and executor: depend on group/machine, then process ownership fixes
   6f8f429 (exclusive reaper, stable SIGCHLD, ECHILD loss of ownership).
4. Remote transport/worker: retain credential echo rejection (75b3ef4), raw-key
   refusal, deadlines/cancellation and shared budgets. Managed binding remains
   unavailable/fail-closed; do not enable based on a self-declared ready flag.
5. Versioned meeting receipts and workbench: connect final parser/UI together,
   preserve f296f3d missing/failed/unknown status semantics and human-authored
   counterexample labels. Fixed report quotations differ from model selections.
6. Offline execution intents are preparation, not authorization or a browser
   authenticated execution service. Platform credential binding is still absent.

The complete expert delta and main overlap only REQUESTS.md and ROADMAP.md;
excluding those two, git apply --check --cached succeeded on main. This is textual
compatibility evidence only, not full runtime integration. The expert source is
17 commits beyond its shared base 3aba2bf; none of those commits is an ancestor
added by this extraction. Safety patches alone lack required modules on main.
See logs/EXPERTRECEIPT-baseline.json for exact evidence; reconcile progress docs
manually instead of replacing main's entries. Later layers require independent
review and their own tests before promotion. No 97-commit preview stack is used.

## Reproduction

From repository root, with the supported service pytest environment:
`PYTHONPATH=. service/.venv/bin/python -m pytest -q tests_acceptance/EXPERTRECEIPT`
The isolated cloud run used the existing service venv from mcis-local-export;
no packages or environment settings were changed. Synthetic temporary artifacts
are protocol tests, never model capability evidence. Real DeepSeek requests: 0.
Real browser and authenticated product integration: untested. Real execution HOLD.
