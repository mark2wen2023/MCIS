# Explicit local-model verification readiness

Current environment inspection found no configured or identified usable local inference provider. No unknown listener was probed; no model/runtime was installed, downloaded or deployed. Therefore this work does NOT claim genuine LLM inference validation. Separately authorized external-provider integration is outside this local-only slice.

Implemented a reproducible one-shot CLI that accepts only an explicit existing loopback HTTP /v1 endpoint and model, uses a fixed fictional interview and short-lived temporary authorized database, and returns sanitized validation summaries. No key input, implicit environment selection, arbitrary file/case input, saved proposal, real source material or fixture fallback. Default returns not_connected without a request; invalid remote configuration is rejected before transport. These two CLI paths were actually executed. Successful-response tests use mocked transport only.

Independent inspection also identified and fixed a low-level bypass: callers could construct ModelConfig directly and call complete() without the environment validator. A shared validator now runs at the actual transport entry and LocalProvider. Empty userinfo/query/fragment delimiters, whitespace/control/backslash, nonliteral/nonloopback hosts and invalid model settings are rejected before httpx creation. Existing no-proxy/no-redirect and bounded single-response behavior remains.

Final local verification: **604/604** related Python regression, zero skipped, 359.16 seconds; focused combined **99/99**, including independent security **38/38**. One existing Starlette/httpx deprecation warning. No real model/API/production login/CI acceptance, merge or deployment is implied. A validated response only establishes configured-endpoint output structure and exact-quote matching, not authentic model identity, expert quality or fact truth.

Changed existing modules are model_client.py and host_extraction.py; local_extraction_probe.py is new. Local-only safety is intentional and should not be weakened to add external providers; use an explicitly separately authorized adapter.
