# Case read failure label — developer evidence

Base a5086d9cd60643841ff1030655b4a305f1d149f6; independent
fix/recommendation-case-read-label. Inherits earlier candidates pending their own
acceptance; this change does not validate their full behavior.

New synthetic page test on parent failed: expected 案件信息读取失败, actual
案件信息加载中. Minimal label now distinguishes initial loading, error and unavailable
from loaded metadata. Error text explicitly states the board/audit refresh button does
not reread case metadata. Request handlers, permissions and retries are unchanged.

Reviewed commands from web, existing dependencies:
- node tests/recommendation-case-read-label.test.cjs: 3 synthetic states passed
  (ordinary connection failure/loading/ready). Actual parent/button callbacks with
  mocked hooks; each click counts case/board/audit reloads as [0,1,1]. No HTTP.
- node tests/recommendation-read-state.test.cjs: 5 adjacent states passed.
- npm run build: TypeScript/Vite passed, 768 modules, JS1865.95kB/gzip603.02kB;
  existing large-chunk warning remains.

No denied/refusal/paused tests, real requests/data, seed reads, models or browser.
No backend test or real visual verification; independent review pending. No merge/deploy.
