# W15.3 source choice and unavailable Bow-tie core: genuine Chromium gate

Tests only. Product `2c72d022f3d3275af637b0cdc6e545735e3200a9`; 339 exact Git blobs, original production web entry and original FastAPI/SQLite in a synthetic local harness. Existing Python, web dependencies, actual Chrome and Python Playwright with `BrowserContext.route_web_socket` are prerequisites. Do not install anything, use an external service, or disable the Chromium sandbox. The test service listens only on 127.0.0.1 and does not connect outbound.

From the fixed checkout root, use a new absolute evidence directory for each run:

```sh
runner=tests_acceptance/w15-source-chromium/run.py
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules --build-only
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --http-only --evidence /new/w15-http
python3 "$runner" --source "$PWD" --node-modules /existing/web/node_modules \
  --host-python /existing/service/venv/bin/python --browser /existing/google-chrome \
  --evidence /new/w15-browser
```

At 1440×900, open synthetic case A and explicitly select its source. The test points the service at a nonexistent SDK to verify the product's genuine unavailable state: submit one preview, require HTTP 503 `BOWTIE_CORE_UNAVAILABLE`, no cached/fallback diagram or endpoint locator. Switch to the other synthetic case with a different source under the same local evidence ID; the old selection/input must not persist. Restart on the same SQLite and read case A in a fresh 390×844 context; no preview request and no mutation beyond initial setup. A successful true-browser run emits three PNGs and a separate receipt.

Local Linux exact-source build and real loopback HTTP/SQLite checks passed, including 503 and unchanged database dump over restart. Local Chrome startup was blocked by the missing Chromium executable (wrapper exit 127). That is not a browser pass. This intentionally negative gate does not validate real .NET, a successful graph, archival output, any real data, identity, model, or deployment.
