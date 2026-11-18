# Missing recommendation citation — developer synthetic check
Base main: 94d5e38c926fda232bb987b60fa9145e4bcf01a7.
Report sources.py lines 388/407 link recs with case/id. The page preserves that ID but displayed only “选择一张卡片” when absent from a successfully loaded board. The new test failed on this exact missing message before the fix.
Now the details panel says the requested ID is absent from the current case board, preserves no-selection, and allows deliberate card selection. Does not assert deletion, authorization, historical existence or version authenticity. No missing message during initial loading/read error; no changes to API/permissions.

From web: `node tests/recommendation-missing-citation.test.cjs` passed 6 synthetic states / 10 assertions. Actual page evaluation with stub hooks/load states; not React DOM/browser/HTTP. No paused/refusal tests, private records or models. `npm run build` passed (existing >1500kB chunk warning), reused installed dependencies. Real browser/visual/independent verification outstanding.

RecommendationsPage also has unmerged editing candidates such as PR67; this branch does not integrate or replace those. Narrow change needs normal integration review.
