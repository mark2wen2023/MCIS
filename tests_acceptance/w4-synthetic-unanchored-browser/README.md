# W4.1 synthetic unanchored preview candidate

No product modifications or new dependencies. Run this outside the repository only from Linux, using already-present dependencies and an independently verified, prebuilt MCIS core from the fixed product source. Python ≥ 3.12 and Playwright with sandbox and WebSocket routing support required.

```bash
timeout --signal=TERM --kill-after=10s 360s python run.py \
  --source /existing/mcis-git \
  --node-modules /existing/web/node_modules \
  --chrome /existing/google-chrome \
  --host-python /existing/service/.venv/bin/python \
  --dotnet /existing/dotnet \
  --core-dll /existing/prebuilt/mcis-core.dll \
  --core-sha256 VERIFIED_64_HEX \
  --out /new/isolated/results
```

The fixed Git commit is 94d5e38c926fda232bb987b60fa9145e4bcf01a7. Record the actual build provenance of the supplied DLL separately; this runner pins the supplied DLL bytes but does not attest how it was built. It has no fallback output and does not build/install dependencies. The fixed product is served via real loopback FastAPI/uvicorn; demo seeds are disabled and only cases SYN-W41-X-A/B are explicitly created. No real case is loaded. Via the visible Evidence panel, Chrome checks distinct 5°/11° COG differences, unanchored status, A→B→A isolated state, temporary-only requests, desktop and 390px layout, repeat idle reopening at 390, and unchanged real SQLite content after preview and after genuine backend restart. The browser denies non-origin requests and WebSockets; no replay or mock is used. Browser capture has no positive proof of late responses arriving after a switch; do not extend the credit to that race. Opting out of the sandbox is not supported.

Not anchored calibration, persistence/writeback, complete W4, production, Unity, or a substitute for validation. This checkout compiled the Python harness and showed help only. Browser E2E and actual core run are **not tested** here; the local chromium wrapper points to a missing binary and dotnet is absent from PATH.
