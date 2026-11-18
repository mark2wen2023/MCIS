# Audio fragment playback late status

Base: 8222050597b19f1d4b3800b3f718fc036556ffb9, candidate/media-demo-launcher.
Developer-only pure Node verification; pending independent review.

The actual inline page script runs in node:vm with synthetic DOM/media objects and a manually
settled play Promise. fetch throws if called; all scenarios assert zero fetch calls. No audio
bytes, Python application imports, model calls, server, browser, dependency install or backend tests.

Initial harness setup assigned the synthetic URL before render, which calls clearAudio; all
8 cases therefore failed before reaching play. This was a fixture error, not product evidence.
After assigning the synthetic URL after render, the unmodified product had 6 failed late-status
cases and 2 passed current-context controls. Late success overwrote 'original not loaded'; late
failure overwrote the new general status. Inputs were synthetic text only.

The handler now captures audio generation, case/run, selection version and object URL, checking
these before publishing play success or forwarding a failure to the existing action error display.
Current-context validation/errors still display normally. Existing pause, clear, URL revocation,
busy behavior and playback permission behavior are unchanged. This does not cancel a play Promise,
prove that audio stopped, or establish that the user heard anything.

Exact command from repository root:
```
node --test tests_acceptance/audio-playback-late-status/page.test.cjs
```
Final result: 8 passed, 0 failed/skipped. Case/run/clear x success/failure, plus normal success/failure.
Current DOM input is re-read after settlement; retained draft and cleared stopAt are checked.
Only this new script ran. No paused/refusal/security tests, real data or seed reads. git diff --check
passed. No web build: changed surface is the standalone HTML inline script, not the Vite application.
No browser/media decoding/real playback acceptance. Application startup and archive tests stay paused.
No merge/deploy, no permissions or safety settings changed.
