# Independent review: internal knowledge worksheet

Reviewed `review_worksheet.py`, its contract, and reused `router.validate_content`/digest. Added independent synthetic safety/protocol tests only; no implementation modifications, model calls, network, database access, publishing or deployment.

## Result

**42 local tests passed: primary 22 + independent 20.** Command:

```
PYTHONPATH=/workspace/scratch/d5cd4f6afdb1/line-dataset-1615/repo/service ../line-dataset-1615/repo/service/.venv/bin/python -m pytest -q service/tests/test_knowledge_review_worksheet*.py
```

Reviewed implementation SHA256: `e2f5a05a42539a9a5b75d09d1b39f85c2a37402b2b71a7dca7fb43c3f182abe7`.

Coverage: rejects card ID, database, role/operator and approval inputs; blocks SQLAlchemy execute/get and socket/DNS during a successful Public-source invocation; source-field omissions; bad JSON and size budget; exact rights-change version conflict; returned nested content/checklists are isolated copies; all six checks and three release approvals start pending; HTML remains data; JSON export escapes HTML metacharacters and roundtrips script-terminator/Unicode text; export also rejects stale digest.

No blocking defect found within the stated standalone scope. This is NOT an authorization boundary: the caller supplies the full content, and the utility returns it. It cannot retrieve another card or confer access, but integration must authorize the caller before supplying/exporting content. No route, session, persistence, actual review decision, production-auth or browser behavior was tested or implemented.

`build()` intentionally contains raw original strings. `export_json()` escapes `<`, `>` and `&`, but parsing restores them. Any future UI must use text rendering, never trust these as HTML; JSON escaping is not a substitute for UI XSS testing. Pending items do not certify truth, rights or expert approval. No real-model quality claim and no CI claim is made.
