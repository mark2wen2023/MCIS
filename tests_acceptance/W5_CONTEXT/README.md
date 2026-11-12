# Independent W5 case-context acceptance

All test records and people are synthetic. Tests start the real app/service only on temporary `127.0.0.1` ports and an ephemeral database via the existing W82 harness. No deployment or persistent user data writes.

```bash
# From repository root, using the service environment for HTTP tests:
service/.venv/bin/pytest -q tests_acceptance/W5_CONTEXT/test_http.py
# System Python with Playwright, Chromium headless shell at the path in browser.py:
python tests_acceptance/W5_CONTEXT/browser.py
```

`test_http.py` covers real TCP case scoping, four mutation types with identical record/statement identifiers in a peer case, provenance labels, role permissions/redaction, and demo compatibility.

`browser.py` uses the actual React app and actual HTTP API. Scenario names beginning `fault-` explicitly inject delayed responses or wrong response identifiers through Playwright routes. Their data is fetched from the real service before withholding delivery, except the deliberate synthetic HTTP 500. Other scenarios have no response mocks, including creating an empty case from the lobby and navigating to W5, all four actions, special statement ID encoding, and external-role denial.

Artifacts and scope limits: `logs/w5-context-independent-review.md`. This is a targeted context-isolation acceptance, not complete W5/production-security/Unity certification. Time formatting remains the existing UTC+8 behavior by the recorded scope decision.
