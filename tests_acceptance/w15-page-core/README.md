# W15 official-page + original core success gate

Tests only. Combines the already verified web candidate
`912d96a39f1a68e98008a7317a211f5e29ed3845` with the original-core pack
`8d108442f94901bee862ba5f53dd6343350b2718` (product base
`2c72d022f3d3275af637b0cdc6e545735e3200a9`). Service and preview contracts
are unchanged between those sources. This directory is a new acceptance
host: it serves the fixed 912d96a web assets and points the existing
connection at the original core. The existing 503 unavailable-core gate
under `tests_acceptance/w15-source-chromium/` is left unchanged.

A sketch SVG may already render from form input before submit; screenshots
alone do not prove the core ran. The gate requires a live POST 200, core
version `mcis-bowtie/1`, and the page's independent 「核心结构核查结果」
panel in the same session: 5 nodes / 4 edges, structure passed, input
summary matching the response. `EV-001` is registered source metadata for
the whole draft only. The preview must not persist. The same temporary
SQLite is reopened and must keep sources without a stored sketch.

Do not install packages, merge, deploy, change product, permissions, main,
CI, or 3D, disable the Chromium sandbox, or expand into save, export, or
real cases. The test service listens only on 127.0.0.1.

From this candidate checkout, with already-present Linux tools, .NET SDK
8.0.428, service Python, node_modules, and sandboxed Chrome:

```sh
timeout 150 env \
  /existing/python -B tests_acceptance/w15-page-core/run.py \
  --web-source /absolute/912d96a-checkout \
  --core-source /absolute/8d10844-checkout \
  --node-modules /existing/web/node_modules \
  --host-python /existing/service/.venv/bin/python \
  --dotnet /existing/dotnet \
  --browser /existing/google-chrome \
  --evidence /absolute/new-evidence-dir
```
