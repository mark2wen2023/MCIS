# Audio reread selection epoch
Base: 0779feb8c9808a11854e1af67e13bfb0b47508c7.
New ordinary synthetic node statically reviewed; deferred successful HTTP/DOM doubles only. Before fix: 1 failed (old response re-rendered after selection away/back). After fix: `node --test tests_acceptance/audio-read-selection/page.test.cjs` 1 passed. Adjacent `node --test --test-name-pattern="^(edit during pending reread|unchanged reread)" tests_acceptance/audio-read-race/page.test.cjs` 2 passed.
No browser/backend/model/data verification, independent acceptance or paused/security/write-refusal tests. Selection epoch prevents stale reread acceptance even if displayed IDs return to original values.
