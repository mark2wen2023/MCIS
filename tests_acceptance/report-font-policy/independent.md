# Independent report font policy test review

Verdict: PASS for test-only alignment on main73fc800. Read AGENTS.md/handoff, full test diff, shared fixture, report export route and font selection. Product service/contracts/web files are unchanged. No font strategy, production policy or renderer was modified.

Fresh independent commands:

```sh
service/.venv/bin/python -m pytest -q service/tests/test_reports_font_coverage.py
sha256sum -c logs/report-font-policy-impl-hashes-frozen.txt
```

**4 passed in2.90s**, independent-tests.txt; frozen test hash1/1 matches, independent-hashes.txt. Coordinator baseline.txt retains the original two403-related failures (2 failed/0.82s); inspected but not rerun by this reviewer.

The original two case parameterizations and all substantive assertions remain: Draft and authorized-public status, actual Chinese source characters, YangZe maritime terms, font charToGlyph coverage, original Chinese set included in pdftotext output, multiple nonempty pages, DRAFT and 不作责任认定 on every extracted page, and 需复核/缺数据 text. Only authorized requests now use synthetic LeadInvestigator and failed export assertions include response detail.

These are real local service/TestClient and SQLite cases with the normal renderer. Existing _font() registers project fonts/NotoSansSC-Regular.ttf; the route calls the genuine exporter after existing policy checks. Tests write returned PDF bytes to a temporary file and invoke the actual pdftotext subprocess. There is no replacement font, fake PDF body, monkeypatch, skip or mocked extraction. Passing text/glyph checks is not visual layout or browser acceptance, and the public-report records are not freshly independently fact-verified by this test.

Two added Investigator cases require denied creation and PDF export403/FORBIDDEN/no-store, unchanged valid audit verification summary, JSON rather than PDF response, and unchanged report after denied export. This preserves the restricted path while letting the font regression reach its intended authorized renderer. Matching audit summary/report does not prove every database table unchanged; no broad rollback guarantee is claimed. Header roles are synthetic policy inputs, not authenticated SSO.

No original assertions removed; no product/frozen test edits by reviewer. No commit, push, merge or deployment. Missing .NET/HFACS functionality and broader suite failures are not hidden or resolved by this focused pass.
