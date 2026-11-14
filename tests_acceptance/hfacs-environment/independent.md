# Independent HFACS environment diagnostic review

Verdict: limited diagnostic acceptance PASS; real HFACS/core and the two dependent archive workflows remain BLOCKED by the missing SDK. No product fallback or test suppression is introduced.

Read AGENTS.md and the handoff, frozen checker/tests/README, and existing build.py. Independently ran:

```sh
service/.venv/bin/python -m pytest -q tools/mcis-hfacs/test_environment.py
sha256sum -c logs/hfacs-environment-impl-hashes-frozen.txt
python3 tools/mcis-hfacs/check_environment.py
```

Results: **11 passed in 0.02s** (`independent-tests.txt`); **3/3 frozen hashes OK** (`independent-hashes.txt`); actual checker **exit1 / SDK_MISSING**, selection HOME_DEFAULT, expectedSdk8.0.428, coreValidated=false, dllPresent=false, manifestPresent=false (`independent-environment.json`). Unit cases use explicitly declared subprocess doubles; they are not C# execution or model capability evidence. Actual diagnostic execution did not build or validate the core.

The checker and build.py select the same executable expression: MCIS_DOTNET if present, otherwise ~/.dotnet/dotnet. A configured bare name uses subprocess PATH resolution; there is no silent PATH fallback for the home default. The checker imports build.py's SDK pin and input list without invoking build(), checks source presence first and only requests --version with a five-second timeout. SDK readiness is explicitly separate from build/artifact/core validity. Status output excludes configured paths and captured process output. The chosen executable is a trusted environment prerequisite, not a sandbox; README explicitly allows its own normal initialization.

Existing build.py and the two actual service tests are unchanged in the working diff. No fake DLL, taxonomy, model result, skipped assertion or automatic skip was added. build.py retains its genuine source/artifact receipt and build path. The diagnostic's DLL/manifest booleans are presence checks only; its result always keeps coreValidated=false.

The coordinator's retained main-two.txt records **2 failed in1.54s**, specifically test_real_hfacs_and_report_optional_extension_three_generations and test_report_versions_full_review_gisis_and_hfacs_coexist. I inspected that log but did not rerun those two tests; my own fresh SDK_MISSING check agrees with the stated environment blocker. These failures must remain visible, and this result does not classify unrelated suite failures as environmental.

Genuine SDK8.0.428 provisioning and subsequent real adapter/core plus both archive tests are still required. No SDK installation, binary substitution, product/test implementation change, push, merge or deployment was performed in this review. This is local diagnostic evidence, not production/core readiness.

Also inspected coordinator wrapper.json: returncode1, stdoutBytes0, missingExecutable=true, mentionsDefaultDotnet=true, coreOutputProduced=false. This is a recorded genuine-wrapper failure, not successful core JSON; this reviewer did not rerun the wrapper.
