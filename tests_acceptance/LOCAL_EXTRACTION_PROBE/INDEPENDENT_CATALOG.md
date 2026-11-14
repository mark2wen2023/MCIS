# Independent local model transport / fictional probe review

Independent reviewer: catalog_review. No product edits, service discovery, real inference, push or deployment.

## Final result

38 local tests passed in 0.30 seconds, one dependency deprecation warning.

```
PYTHONPATH=issue-journal/service mcis-work/service/.venv/bin/pytest -q issue-journal/service/tests/test_local_model_catalog_review.py
```

All transport in this suite is mocked. The successful fictional extraction test proves contract/citation processing with a test double, not genuine model inference or model quality.

## Findings resolved

1. Direct `complete(cfg)` previously bypassed configuration validation and constructed a transport even for an arbitrary config object. Independently reproduced without network by replacing the HTTP client constructor. Shared configuration validation is now called at the transport entry and by the host.
2. Empty userinfo (`@`), query (`?`) and fragment (`#`) delimiters were still accepted because parsed values were empty. Query/fragment suffixes changed the meaning of appended `/chat/completions`. They now reject before transport; all three regression tests pass.

## Coverage

- Exact configuration type and explicit HTTP loopback literals, IPv4/IPv6, explicit valid port and /v1 path.
- Remote/HTTPS/localhost/missing or invalid port, credentials, query/fragment, wrong path, whitespace/control characters, blank/oversized/nonstring model, and fake config object rejected before any client construction.
- Correct model and URL; environment proxies and API keys are not sent; redirects disabled.
- Redirect, incomplete generation, tool/function calls, nonstring content, oversized/malformed response and empty choices reject without retry/fallback.
- Probe default ignores configured environment and performs no request; incomplete/remote explicit configuration rejects.
- Fixed fictional contract test yields unreviewed summary only, configured model remains unverified; no saved/fact-verified/full-case-validation claim.
- Transport exception is sanitized; no fixture fallback is invoked.

## Limits

No real model endpoint was supplied or contacted. This does not establish actual local model availability, inference performance, factual accuracy, production authentication or real-case readiness. The runner is fixed fictional, one-shot and temporary. `validated_response` means protected extraction accepted response shape/citations, not that the configured model's identity is authenticated.

## Frozen SHA-256

- model_client.py: `81718af99f5424c86bd43daed40131a39318b3decab36e0427eee54b0219e63b`
- host_extraction.py: `561ccd86e0681b5d4a0cdb766808f9cbdd070ebe89e0adeecf35a0d9255f1178`
- local_extraction_probe.py: `76631dd58139841bd7a59de11512a51f87c314fd72f4ce166385af37a0c8b0cd`
- test_local_model_catalog_review.py: `6936f462ad444bac3a1701c2ac112f280bfdfa9444306a2e64d0c1b11064fce7`

No remaining blocking finding in this bounded transport/probe slice.
