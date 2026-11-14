# Independent timeline migration review

Scoped PASS for the exact local PR79/main combination; no browser or release approval. Read AGENTS.md/handoff, interval contract and changed route/tooltip logic.

Independently checked all22 non-document PR paths byte-for-byte againstb32f4fb. All2371 other tracked files from main25b9df6 are byte-identical, not just the listed recent-main delta. REQUESTS.md and ROADMAP.md equal the full main files plus the exact PR suffix relative to73fc800. Evidence: independent-tree.json. All22 frozen hashes matched (independent-hashes.txt). The first tree-check script encountered Git's quoted non-ASCII filename output; rerun used NUL-delimited paths and completed the full check, without changing files. This establishes local combination preservation, not a remote merge.

Fresh independent backend:

```sh
PYTHONPATH=service service/.venv/bin/python -m pytest -q service/tests/test_timeline_intervals.py service/tests/test_timeline_intervals_independent.py
```

**31 passed in9.24s** (independent-backend.txt). Interval zero endpoints, finite/range validation, negative seconds, source preservation and refusal boundaries are exercised by the two modules. Existing permission checks precede new semantic range validation; malformed ranges fail before writes. No legacy historical-row migration or causal inference is added.

Fresh independent frontend subset (from web): bundled each named test with installed `./node_modules/.bin/esbuild tests/<name>.test.ts --bundle --platform=node --format=cjs --outfile=/tmp/mcis-t25-<name>.cjs --log-level=warning`, then ran node on it. Names: timeline-axis-independent, timeline-domain-independent, timeline-domain-echarts, timeline-tooltip-independent. **30 reported cases passed** (6+8+10+6), independent-frontend.txt. Includes actual ECharts SVG SSR with the production axis, finite/Date boundaries, exact extrema, large arrays, immutable inputs and escaped tooltip text/missing workflow flags. Generated bundles remain in/tmp. No packages installed.

Coordinator backend.txt independently inspected:61 passed/10.51s; this is separate overlapping evidence, not my execution or an additive count. No full service regression was independently run. Real browser interaction remains unverified; SVG SSR does not establish browser rendering, usability or visual clipping behavior. No sandbox workaround/plugin/helper changes attempted.

Tooltip source references are recorded identifiers, not verified evidence; confirmed/presumptive labels remain workflow flags, not facts/confidence. Main research modules are preserved but this migration does not establish new authenticated expert execution or integrate them into the timeline. Known broader environment/core and identity/resource boundaries are not fixed by these focused tests.

Reviewer wrote only acceptance/disposition evidence; no implementation edits, push, merge or deployment. Full browser acceptance remains an outstanding blocker.
