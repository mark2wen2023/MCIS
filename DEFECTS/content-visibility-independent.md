# Independent acceptance — restricted evidence content visibility

2026-11-14. Isolated /workspace/mcis-content-visibility, base0991857.
Product delta inspected: only two lines in GET content after load_item, applying existing
filter_evidence to the target case's current policy and returning403 if hidden. Existing
BEGIN/WRITE_LOCK, recorded digest, descriptor-safe read, Restricted testimony and ZIP
container gates remain. Strict Base64 repair is not part of this tree/delta.
Reviewer changed only acceptance tests and this report; no product edits, commits, push,
merge or deployment. Frozen router hash verifies OK after tests.

## Actual independent execution

From service/:

```sh
MCIS_FIELD_RULE_OUTPUT=/workspace/mcis-content-visibility/tests_acceptance/content-visibility-independent/resolved-blocker.jsonl \
.venv/bin/python -m pytest -q --import-mode=importlib \
 ../tests_acceptance/content-visibility-independent tests/test_content_visibility.py
```

**10 passed in2.37s**, no skipped cases: unchanged copies of2 prior independent failing
source/restore probes,4 newly independent checks,4 implementation concurrency/visibility
cases. Output: tests_acceptance/content-visibility-independent/results.txt.

Original test_field_rule_content.py from prior roundtrip-independent is copied unchanged
as test_original_blocker.py. The source/restored cases now both report:
- listing hides item, metadata403, export403, original content403;
- no returned synthetic original bytes;
- access audit delta0 and custody Access delta0;
- stored policy unchanged through real export/verify/import into a separate database.
JSONL records actual imported mcis_service path in this isolated tree. Prior failure logs
and the original blocked source tree were neither altered nor deleted.

New independent checks:
- Two cases share EV-001 and identical relative filenames but contain DIFFERENT actual
  bytes. A hidden case returns403/no audit; the other returns its own exact permitted bytes.
- Simulated inconsistent trusted DB embedded caseId points to the other case. Authorization
  still uses request-target case policy and denies; it cannot select the other case's grant.
  This is a trusted-store robustness probe, not a demonstrated remote cross-case exploit.
- Normal evidence remains readable under evidence.restricted Remove, preventing unintended
  blanket denial of nonRestricted items.
- At the actual successful Access append boundary, a second real SQLite connection cannot
  acquire BEGIN IMMEDIATE (SQLITE_BUSY). After read completes, real Lead PUT stores Remove;
  next GET returns403 without another Access. Reservation persists through audit/delivery
  decision rather than ending at file read.

Rerun implementation tests further exercise hidden-item denial before any content read,
revocation that commits before GET reservation, and actual policy PUT contention503 while
read holds the writer followed by denial after committed revocation. Real local SQLite and
ASGI HTTP APIs are used; controlled read hooks only pause execution. No external service,
model, SSO or production identity validation is involved.

## Bounded conclusion and limits

The specific inherited GET inconsistency for evidence.restricted Remove is closed by the
current two-line repair in both source and restored workflows tested here. No remaining
blocker found within this limited scope. This does not certify every policy category,
field rule or other read endpoint. Existing role request headers remain unverified identity;
policy consistency is not production authentication. Trusted DB/process assumptions remain.

Old exported offline snapshots still retain their old policies: revocation on the source
after backup does not propagate to a separate restored store. This repair checks current
policy WHERE the request executes; it introduces no global revocation mechanism. No claim
of provenance or source authenticity follows from byte digest validation.

The independent10-case run is not full-suite, .NET, browser, performance or deployment
acceptance. Broader implementer regression results and existing limitations remain separate
records. This verdict authorizes no remote changes and does not combine the separate
Base64/checksum work with this permission repair.
