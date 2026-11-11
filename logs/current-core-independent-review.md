# Independent provenance tooling review

- Reviewed build_reproducible.py, mcis-core.sh, generate_seed_candidate.py and current tests without changing implementation.
- SDK selection checks 8.0.428, temporary build global.json disables roll-forward. This identifies SDK version, not an independently verified SDK binary supply-chain hash.
- Recipe SHA, deterministic and apphost settings now participate in cache identity. Artifact digest mismatch invalidates cache.
- Current manifest enumerates 55 C# Compile inputs plus csproj. Independently compared all 55 with actual MSBuild -getItem:Compile output: exact equality. This is validation for the current restricted project format, not a general MSBuild dependency enumerator.
- Existing 4 tool tests passed. Independently verified 7 unsupported project-element rejections (Import, ProjectReference, PackageReference, EmbeddedResource, Resource, Analyzer, Target).
- Independently ran the real build_seed generator twice through the candidate tool, before and after recipe-cache hardening. Both generated DLL SHA f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf.
- Latest independently generated isolated candidate: 14539 numeric leaves strictly identical, fingerprint b1d98497ef4c5cf7181557d0481f49d484d56242b9198a5b12ae67dec723fd0e. Only generatedAt and coreDll.sha256 changed. W14 cross-check 52 values, maxAbsDiff 0.
- SHA checks before/after both runs confirmed original seed JSON, sidecar and production DLL unchanged. No candidate installed. Existing frozen assertions not relaxed.
- Wrapper now intentionally uses content-verified isolated builds on invocation and would replace its configured production out artifacts then. Our review only invoked wrapper inside isolated generator copies, not production wrapper.
- No blocking issue found in this scope. This does not prove application end-to-end acceptance or production readiness.


## Subsequent installed-baseline W12 retest

After the implementation agent installed the reviewed candidate baseline, the independent reviewer reran all W12 acceptance tests: **21 passed (8.15 seconds)**. The old Layout substring test was adapted following REQUESTS registration to execute real Layout loading effects under deterministic mocked hooks/router/fetch: 7 routes × successful/failed case lookup, 14 scenarios. Only analysis may fall back to `/analysis/cases`; successful analysis lookups and all other routes must not. All original numerical checks and the original test identity are retained. This is unit/acceptance coverage, not a new browser or mobile run.
