# Local acceptance
New isolated Python comparison adapter and contract. No shared router, existing
card schema, OpenAPI, UI or source configuration files touched. Native subagent
implementation; not Codex CLI and not LLM test.

Primary: 33 protocol tests passed locally. Cases cover changed content/locator/
rights/URL, unavailable, candidate version mismatch, missing fields/timestamps,
malformed input, invalid capture dates, no normalization or caller mutation.
No live DeepSeek call was required by this deterministic source comparison;
no real-model capability claim is made. Currentness/authenticity remain unverified.

Independent review result is recorded separately. No merge or deployment.

Combined independent and primary suite: 60 passed locally (33 + 27).
Command: python -m pytest -q service/tests/test_knowledge_source_freshness*.py
Log: logs/knowledge-source-freshness.txt. This is not CI, browser QA, or real LLM testing.
