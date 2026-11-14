# W7.5 independent acceptance — 2026-11-14

Separate native reviewer; no changes to implementation/frozen files. Tests use fictional Lily/Mary temporary SQLite and a separate HappyDOM interaction harness. No real model, production identity, browser-engine, deployment or merge claim.

The reviewer found W75-D01: malformed recent full-body history was incompletely validated, returning200 or serialization500. Initial run was4 failed/5 passed. The implementation owner fixed strict parsing, text/Unicode/budget/digest/association checks. The original assertions remain, now with current-token PUT rejection and unchanged body/audit checks. See DEFECTS/W75.md.

Independent API coverage (17 cases): malformed history across four data constraints; strict duplicate/nonfinite/oversize parser rejection; complete21-version audit with newest20 view; read/write permission revocation and no-store; post-audit response preparation failure rolls back everything; revoked no-op denied; unrelated audit does not stale the document token; all five non-Draft states reject editing with a current token.

Independent UI coverage:20 assertions pass. Late GET responses are isolated after same-role operator change or selected recommendation change. Cancel/continue sends no PUT. Body-mismatched, malformed, unchanged-version or missing-new-history successful responses become unknown outcomes, keep the draft and block further writes. Reread alone does not silently adopt a new baseline; explicit rebase is required. Discard after an unknown outcome still requires reread before editing. A404 hides the existing body/draft; no successful-save callback fires.

**Final result:118/118 combined API/contract regressions passed, zero skips (17 independent +101 related);20 independent UI assertions passed. Revised freeze `logs/w75-r1-impl-hashes-frozen.txt` matches10/10. The original freeze is superseded after W75-D01 repair and retained as historical evidence.**

Reproduce:

```sh
service/.venv/bin/pytest -q tests_acceptance/W75/test_independent.py service/tests/test_recommendation_body_edit.py service/tests/test_recommendations.py service/tests/test_recommendation_content_access.py service/tests/test_recommendation_review_w74.py service/tests/test_contracts.py
NODE_PATH="$PWD/web/node_modules" web/node_modules/.bin/esbuild tests_acceptance/W75/ui_independent.test.tsx --bundle --platform=node --format=cjs --outfile=web/tests/.tmp-w75-independent.cjs --jsx=automatic --loader:.css=empty --log-level=warning
MCIS_HAPPY_DOM=/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js node web/tests/.tmp-w75-independent.cjs
```

Limits: API adapter plus DOM assertions are not browser visual/mobile/native behavior acceptance. No browser launch attempted by this reviewer; the previously reported SUID sandbox blocker remains. No full-system or CI claim. Permission roles remain the existing local header mechanism; restored history remains an editable local record, not authenticated provenance. The append-only audit retains full bodies but only latest20 body versions are parsed for this view.
