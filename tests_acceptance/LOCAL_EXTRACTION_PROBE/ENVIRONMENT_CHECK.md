# Current cloud environment check

Checked on 2026-11-14 by the coordinating implementation thread, without reading credentials or probing unidentified local services.

Observed:
- `MCIS_AGENT_BASE_URL` and `MCIS_AGENT_MODEL` are not configured.
- `ollama`, `llama-server`, `vllm` and `nvidia-smi` were not found on PATH; targeted standard binary locations did not locate a supported inference executable.
- Neither the general Python environment nor the service virtual environment lists ollama, llama-cpp-python, vllm, transformers, torch, mlx or mlx-lm distributions.
- No model directory was located in the targeted conventional model locations. This is not an exhaustive filesystem search.

Conclusion: no configured or identified usable local provider was available to run a genuine LLM acceptance test. Unidentified platform listeners were not queried. No model was downloaded, launched, installed or deployed, and no external API or user key was used.

Actual CLI smoke checks (not mocked):
- `PYTHONPATH=service python -m mcis_service.agents.local_extraction_probe` returned `not_connected`, `requestAttempted:false`, `fixtureFallback:false`, exit 0.
- The same CLI with `--base-url https://example.invalid/v1 --model fictional-check` returned `invalid_configuration`, `requestAttempted:false`, exit 2. This deliberately invalid non-loopback configuration is rejected before transport; it is not an external request.

Successful-response unit tests elsewhere use mocked local transport and are contract tests, not proof of real inference. When an operator supplies an existing permitted local endpoint and model, the runner can execute the fixed fictional interview and check returned structure/exact quotations. Even a successful response does not authenticate the model identity or prove expert accuracy/facts. No production login or stored result is produced.
