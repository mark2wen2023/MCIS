# Offline worksheet candidate on main

This is a research-only local tool, not a mounted production page. See
../../contracts/semantic-offline-main-candidate.md for scope and limits.
Seven runtime files need only Python standard library. Existing Node/pytest tests
are validation dependencies. No service needs to start.

Generate a new local review page from retained historical sample snapshots:

```sh
python research/semantic_support/render_restore_review.py \
  --corpus research/semantic_support/jiangxin9-provisional.json \
  --predictions research/semantic_support/jiangxin9-real-predictions.json \
  --output /tmp/my-new-review.html
```

Output must not already exist. The sample is not a new model acceptance run. Keep
original corpus/prediction bytes. Open the HTML locally; edits are ephemeral until
explicit JSON export. Imported notes require validation and explicit confirmation;
notes and flags never confirm facts, authorship or source authenticity. Native
browser behavior is still awaiting sandbox-supported acceptance.

Reproduce offline engineering tests:

```sh
PYTHONPATH=research/semantic_support service/.venv/bin/pytest --import-mode=importlib -q \
  research/semantic_support tests_acceptance/SEMANTIC_BROWSER_EXPORT \
  tests_acceptance/SEMANTIC_MAIN_CANDIDATE
sha256sum -c logs/semantic-main-candidate-impl-hashes-frozen.txt
```

Historical source/run documents are retained for context. The extraction neither
executes the original Pi/DeepSeek harness nor certifies its recorded provenance.
