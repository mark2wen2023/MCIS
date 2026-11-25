# Chapter 09 — Signed deviation fields

Synthetic experiment only. Algorithm b1945ff; tests 921c6cf. Local pytest: 27 passed in 0.09 s (11 new, 16 existing). Independent QA pending.

| Case | Common projected area m2 | Mean B-A m | RMSE m |
|---|---:|---:|---:|
| Gradient | 4 | 0.1 | 0.11547005383792518 |
| Signed | 4 | 0 | 0.11547005383792512 |
| Gap | 2 | 0.15 | 0.1527525231651947 |
| Empty | 0 | null | null |

Synthetic x=[0,2,4] m, z=[0,1] m, reference half breadth 1 m. Gradient candidate [1,1.1,1.2] m; signed candidate [0.8,1,1.2] m. Gap removes B corner [0,0]; empty removes B corner [1,0], both using gradient. Explicit support of both patches. Colors use fixed ±0.25 m. Statistics integrate linear signed differences on projected x-z triangles, not shell area or closest spatial distance. Color clipping does not alter statistics. Independent Trimesh export and reload of signed scenario preserved 6 vertices, 4 faces and all vertex RGB values. Not MCIS exporter validation.

Remotion: reveal matching grid, animate -200/0/+200 mm, map blue/gray/red, compare mean 0 versus RMS 115.47 mm, remove unsupported patch, show null on empty domain. Narration: 向内和向外的偏差可以相互抵消，平均值为零不代表几何相同。让差异在空间里可见，保留未知，而不是把未知画成零。

No private data or production authorization.
