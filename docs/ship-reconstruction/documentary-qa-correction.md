# Independent QA and scientific correction — editorial checkpoint

Source: operator-relayed independent QA report, local QA commit c56099f (not remotely verified at recording). Public publication of case-specific data requires clearance.

## Generic engineering lessons
- Missing JSON Schema identifiers can disrupt shared registry initialization; both identifiers were repaired in a513e72 and b198607.
- Compare frozen feature and main revisions under identical environments before attributing failures to a change.
- Distinguish environment failures, shared baseline failures, and feature regressions. Do not weaken authorization to satisfy outdated tests.
- A converter exit code is not proof of valid geometry or even a valid output file.
- A minimal synthetic fixture and single-variable intervention can isolate duplicate traversal of an entity ownership graph.
- Independent CAD kernels may represent equivalent curves differently; entity identity and geometric equivalence are separate checks.
- Document revision, units, coordinate axes, and missing-cell semantics require authoritative confirmation.

## Documentary scenes
Chapter 03: animate two ownership paths reaching the same synthetic vertex, then demonstrate deduplicated traversal.
Chapter 09: animate a baseline/feature test matrix, isolate environment and shared permission failures, and show why a zero-regression result does not mean all tests pass.
Chapter 04: show two hypothetical document revisions with conflicting station spacing; leave the authoritative revision unresolved.
Chapter 12: illustrate controlled experiments, independent replication, correction, and explicit approval gates.

## Evidence policy
Do not publish case-specific counts, drawings, private paths or design parameters without clearance. Obtain actual machine-readable synthetic results and independently verified commit references before final rendering. No production lofting authorization.
