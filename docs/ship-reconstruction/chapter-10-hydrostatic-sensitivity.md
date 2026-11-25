# Chapter 10 — From geometry to conditional hydrostatics

Synthetic inputs only. Algorithm e5fb95a; tests be6887c. Local Python 3.13.5 / pytest 9.0.2: 40 passed in 0.14s, including 13 new cases. Full service and independent QA pending.

| Experiment | Common submerged projected coverage | A volume m3 | B volume m3 |
|---|---:|---:|---:|
| Box at Z=1 m | 100% | 8 | 9.6 |
| Box at Z=0.5 m | 100% | 4 | 4.8 |
| Wedge at Z=1 m | 100% | 4 | 4.8 |
| Missing submerged patch | 50% | 4 (partial) | 4.8 (partial) |
| Empty | 0% | null | null |

Coordinates x=[0,2,4] m, z=[0,1,2] m; half breadth A=1 and B=1.2 m for boxes. Wedge half breadth A=z and B=1.2*z. Explicit symmetry and support assumptions. At Z=1 m the box waterplane areas are 8 and 9.6 m2; transverse inertia about longitudinal centerline 2.6666666667 and 4.608 m4; transverse BM 0.3333333333 and 0.48 m. A 20% breadth increase gives 72.8% inertia and 44% BM increase in this specific model.

Remotion: reveal boxes, clip by waterline, integrate submerged volume, sweep waterplane, animate cubic inertia relation, then remove one patch and show full-domain fields null. Narration: 船体宽度只变化百分之二十，水线面的横向惯性矩却增加了百分之七十二点八。几何不确定性会通过数学关系传递到物理参数。

The model is a symmetric upright bilinear rectangular domain, not a certified hull. It does not solve equilibrium, loading, density, KG, GM or actual envelope closure. Raw grids are supplied, not yet tied to candidate provenance. No formal authorization. Local experiment package retains exact JSON and reproduction script.
