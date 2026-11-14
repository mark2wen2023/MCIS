# Real DeepSeek / Pi semantic-support blind run

## Pre-registered scope
One authorized run only, on the fixed public-report corpus. No automatic retry after failure or unknown outcome. Corpus SHA256 `77cdbdf3f2656aa57b0772fadc909671bf5bbfbd7c480a3fcbb1cc79460ad19b`; projected model-input digest `b8d5ae6ea1e6afbdf72c4dbfb0ccb99de03a518dae78b1c592e91c9833db4d85`; manifest digest `5a553a8dca41f1cbd1242f261d535aa66e19070c09f3b11abea5ec53c889bc9a`. Full projection and methods are in blind-input.json. Reference labels were frozen before the run and are never supplied to the model.

Opaque case IDs hide the original IDs' semantic hints. Source text, claim and citation are unchanged; schema validation reveals no answer labels or correctness. The system does provide general method guidance (qualifiers, attribution, absence versus negation, signal versus action, causation limits), so this is answer-hidden assessment with methodological guidance, not a zero-shot benchmark. The task uses a purpose-built research Pi harness, not the production extraction Skill/profile or an expert panel.

Configured endpoint is official DeepSeek HTTPS, configured model deepseek-v4-pro; underlying model identity is not independently attested. Official Pi Agent1.5.2 runs the loop with two read/schema-only tools. Credential remains only in the Python parent process and request header, not Node input, model input, environment, argv, files or logs. Each attempt is recorded and fsynced before dispatch; completion additionally requires trusted-host accepted candidate, close acknowledgement and child exit0. Receipts are operational records, not signed audit.

Safety/unit fixture tests do not count as model capability tests. Model capability observations below must come only from the actual public-source API run. The provisional reference set is not expert-certified, so no authoritative accuracy, factual approval or expert consensus is computed. Labels and brief explanations are unreviewed model proposals.

## Actual result
Completed once after independent safety review. Run `36c8d113-e34c-458f-bb89-2cf66abe1486`: **3 actual DeepSeek requests completed, 2 tools, 11 unreviewed predictions**, realPi=true, realModel=true, transportMocked=false. Trusted host completion/close, Node exit and observed Python process exit0 verified. No retry. No facts activated.

Artifacts: blind-real-run.json (accepted host result), blind-real-receipt.jsonl (no-content request/close record), blind-real-predictions.json (model labels and explanations mapped back to original cases), blind-real-comparison.json (post-run provisional reference comparison). The comparison tool itself never calls a model: its realModelCalled=false describes the offline comparator, not the upstream run, which is verified separately by the run record.

Two labeled cases differ from the provisional suggestions: the model calls the unsupported precision claim and the assertion of a new command from a blank cell `conflicted`, while provisional suggestions say `insufficient`. This is a support-versus-contradiction distinction requiring expert review, not an automatically certified error count. For the deliberately unlabelled omission of “approximately”, the model says `supported`, which may fail to preserve an important qualifier and remains for expert adjudication. The altered quote is independently not_exact even though the model detects numerical conflict. No authoritative accuracy or expert consensus is reported.

Safety verification: Python main13 plus independent19 =32/32; independent input-projection2; Node runner6 scenarios and CLI coordination passed. These offline mocked tests validate engineering boundaries only. The capability observations above are solely from the actual public-source run. No production mount, deployment or merge.

Final combined offline regression after real-result capture:78/78 Python tests, zero skips,1.26s; Node2 test files passed (including6 runner scenarios). These are regression/safety checks, not additional real-model evaluations. Only the one real run above contributes model observations.
