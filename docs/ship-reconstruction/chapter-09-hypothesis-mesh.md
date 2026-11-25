# Chapter 09 — Same position, different hypotheses

Synthetic data only. Implementation 0bd6e59; tests ec23683. Local joint pytest: 16 passed in 0.07 s, including 7 new cases. No full-service or independent QA claim.

| Case | Common domain | Vertices per model | Triangles per model | Maximum B-A breadth difference |
|---|---:|---:|---:|---:|
| Full | 100% | 6 | 4 | 0.2 m |
| One unknown corner | 50% | 4 | 2 | 0.2 m |
| No overlap | 0% | 0 | 0 | null |

Synthetic rectangular half widths A=1 m, B=1.2 m, x=[0,2,4] m, z=[0,1] m. Independent visualization export with trimesh (not the MCIS exporter): both GLBs read back with 6 vertices and 4 faces; max coordinate round-trip error A=0, B=4.768371586472142e-8 m. Both open meshes.

Remotion: reveal shared grid, overlay A and B, highlight signed breadth differences, remove one corner then the shared corner, display null rather than zero, reveal vertex candidate provenance. Narration: 我们把不同答案放进同一个坐标世界，只有双方都有依据的位置才允许比较。没有共同证据的地方，不是没有差异，而是我们还不知道差异有多大。

Signed breadth at common x-z is not shortest spatial distance or a probability interval. Piecewise linear mesh and bilinear volume integration are different representations in general. No production authorization. Actual experiment assets retained in local synthetic package.
