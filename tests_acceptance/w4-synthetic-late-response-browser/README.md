# W4.1 synthetic late-response candidate

Isolated acceptance only. No product modifications, no new dependencies, and no rebuild of the already verified core DLL. This does **not** rerun the passed unanchored preview baseline (two viewports, A→B→A, SQLite reopen). It only checks a real late preview response.

The test host wraps the real loopback FastAPI/uvicorn app with an ASGI send gate. After the genuine core has computed the SYN-W41-X-A align-preview body, the host holds `http.response.start` and the unmodified body until the runner releases the gate. SYN-W41-X-B is never held. Playwright is not used to fulfill or invent a response body.

```bash
timeout --signal=TERM --kill-after=10s 150s python run.py \
  --source /existing/mcis-git \
  --node-modules /existing/web/node_modules \
  --chrome /existing/google-chrome \
  --host-python /existing/service/.venv/bin/python \
  --dotnet /existing/dotnet \
  --core-dll /existing/prebuilt/mcis-core.dll \
  --core-sha256 VERIFIED_64_HEX \
  --out /new/isolated/results \
  --viewport-width 390 --viewport-height 844
```

The gate mechanism is unchanged. Pass `--viewport-width` / `--viewport-height` to run at 390×844 (or another requested size) without rerunning the desktop late-response or the unanchored preview baseline. Timeouts stay the same. After the original late-response assertions, the runner also checks that the preview result (receipt) panel is readable and that the document does not overflow the viewport horizontally.


The fixed product commit is 94d5e38c926fda232bb987b60fa9145e4bcf01a7. Demo seeds stay disabled; only SYN-W41-X-A/B are created. After B's 11° result is visible, the original A response is released. The A browser request must actually finish, and that finish must be after B. A cancelled or never-arrived A request is a failure. B's case id, sources and 11° result must not be replaced by A's 5°. SQLite is compared before the late sequence, after it, and after a genuine service reopen.

Not anchored calibration, persistence/writeback, complete W4, production, or a substitute for the already-passed preview baseline. Opting out of the sandbox is not supported.
