# Audit test policy alignment

Fetched latest main: 73fc8002868d9c6894b5fce6d03f7db690291bf6.
Remote saved archive candidate remains 7aa9b9fb657ee118eddba0d278b94c9c2f589aaa;
remote HFACS diagnostic remains 1a9c802a59503bda5ce4e6c9c78a93e58d3aea26.
Both have that exact main as direct parent, not merged into main. See ancestry.json.
Neither candidate changes service/tests/test_audit.py relative to main, so this
isolated test-only fix has no file overlap with their implementation changes.
No combined branch was created or represented as independently validated.

Fresh unmodified main test_audit.py: 1 failed, 7 passed in1.95s (baseline.txt).
The chain-format test requested complete seeded audit using Investigator. Current
service protects recommendation/consultation originals, returns403; the test
then iterated the error dictionary as events and raised TypeError before reaching
chain assertions. This is test role/response handling drift, not missing SDK or
proof of a product permission defect. Existing seeded roles are self-reported
test inputs, not trustworthy SSO.

Candidate changes only this test module: retain Investigator audit verification,
assert HTTP200 before parsing, request complete audit with LeadInvestigator,
and preserve every original sequence/hash/time/key-order assertion. A new actual
TestClient regression requires Investigator full-list403/FORBIDDEN/no-store,
no event envelope and unchanged valid verification summary before/after denial.
ExternalExpert denial remains. No global fixture, source, policy, SDK, archive
format or core computation changes. No skip or mock is added.

Self-tests: 9 passed in2.16s (after.txt). Related actual local HTTP/policy suites:
recommendation_content_access, interview_access_w52a, reports_w162_access:
186 passed in34.73s (related.txt). These are synthetic temporary DB tests with
existing policy and declared local role headers, not authenticated production
traffic. Independent acceptance is recorded separately.

No SDK installed; no HFACS outcome fabricated. Its known two workflow failures
remain blocked and were not rerun here (see saved1a9c802 evidence). The saved
archive candidate's real browser gate remains unverified. No claim of a green
full suite, safe production authentication, performance, reduced lock duration
or bounded aggregate memory. No remote push, PR, merge or deployment in this task.
