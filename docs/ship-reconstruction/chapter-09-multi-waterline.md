# Chapter 09 — Multi-waterline reconstruction: model error versus missing evidence

Synthetic experiment only. Source 09d1542, tests f61ca1c. Local pytest: 36 passed in 0.10 s (14 new, 22 previous). Both new source and test blob hashes match remote.

Analytic model y=1+x*z/2, x in [0,4], z in [0,1] m. Two boundary waterlines have zero reference residual. On each shared affine x interval the maximum same-(x,z) half-breadth error between the bilinear band and its triangular approximation is abs(cross term)/4 in exact arithmetic. Actual diagonal-midpoint measurements:
| Budget mm | Stations | Faces | Error mm |
|---:|---:|---:|---:|
| 510 | 2 | 2 | 500 |
| 250 | 3 | 4 | 250 |
| 100 | 9 | 16 | 62.5 |
| 20 | 33 | 64 | 15.625 |
| 5 | 129 | 256 | 3.90625 |
| 1 | 513 | 1024 | 0.9765625 |

A separate three-waterline experiment preserves five original mandatory/common stations, refines to 33, produces 99 vertices and 128 faces, and shares the middle boundary. The 64-face and 128-face synthetic GLBs were written and reread by trimesh, with identical face indices and zero readback coordinate error for these samples. Not the MCIS exporter.

Counterexample y=1+x*z/2+1.2*z*(1-z): identical boundary waterlines, yet 300 mm different half breadth at z=0.5. Refinement cannot resolve that ambiguity. Require independent geometric constraints. Remotion: show two boundary lines, the triangular diagonal midpoint residual, six measured refinement levels, and the indistinguishable second surface; then reveal the third waterline. The bound is a model discretization error, not physical hull accuracy.

Limits: shared longitudinal extent and contiguous reviewed waterlines required, no unsupported band bridging, no closed hull, no full geometry topology or source authenticity validation, no runtime integration, no formal authorization. Actual ship data remain private.
