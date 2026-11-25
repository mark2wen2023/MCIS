# From Drawings to Digital Ships — documentary research log

Status: living editorial source, not an engineering acceptance report.
Production target: code-driven Remotion documentary; no video production yet.
Privacy: public repository contains generic methods and synthetic fixtures only. Real vessel drawings, dimensions, CAD derivatives and case-specific statistics require explicit publication clearance.

## Chapter map
1. Four drawings and three-dimensional representation
2. CAD parsing and evidence provenance
3. Conversion success versus integrity
4. Offset tables and coordinate systems
5. Linear, PCHIP and B-spline interpolation
6. Longitudinal lofting and mesh topology
7. Symmetry and orientation
8. Smoothness versus accuracy
9. Residuals, benchmarks and independent acceptance
10. Closed geometry and hydrostatics (future)
11. Investigation simulation (future)
12. Reusable skills and engineering governance

## Evidence ledger
| Item | Source | Status | Visual idea |
|---|---|---|---|
| Bounded linear interpolation | bc96f7a | implementation committed; tests not independently verified here | animate sample points and interpolation brackets |
| PCHIP | e97120e | implementation committed | compare actual evaluated curves |
| Open-side loft | 0d803c2 | implementation committed | animate station grid and triangle connectivity |
| Mesh diagnostics | ecab0f3 | implementation committed | isolate topology defects |
| Reflection | baf601c | implementation committed | reflect vertices and reverse face winding |
| Residual metrics | d827a65 | implementation committed | signed residual plot and tolerance bands |
| B-spline evaluator | 80b0ca2 | implementation committed | evaluated surface sampling |
| Quadratic benchmark | 2138528 | code committed; execution evidence pending | plot held-out points and measured errors |
| Complex benchmarks | e315fb2 | code committed; execution evidence pending | compare nonlinear and chine fixtures |

## Editorial rules
- Separate implemented, executed, independently accepted, and proposed work.
- Record exact commit, fixture, command, environment, units, result and limitations for each experiment.
- Never present a schematic as a measured rendering.
- Do not reuse unverified numerical claims; rerun committed benchmarks and archive machine-readable outputs.
- Preserve failures and corrections, including negative results.
- Real drawing acceptance findings remain in private records until cleared for publication.
- Every chapter should accumulate narration notes, equations, scene ideas, evidence references and unresolved questions.
- Prefer deterministic visualizations generated from actual experiment outputs; use labeled synthetic examples when needed.

## Opening narration draft (Chinese)
一艘船如何存在于几张平面的工程图纸之中？如果我们要让人工智能重建它，真正困难的不是画出一个像船的模型，而是证明每一条曲线、每一个坐标和每一个判断，都有可以追溯的依据。这是一次从工程图纸走向数字船舶的实验，也是一场关于人工智能如何获得可靠工程能力的探索。
