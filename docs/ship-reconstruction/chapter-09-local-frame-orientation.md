# Chapter 09 supplement — Nondegenerate geometry can still be wrong

Independent QA reference: 07aac678f056433aebfc33f0e21f5cc16635aab6 (synthetic coordinate experiment and tests). No private ship data.

## Reproduced scalar and orientation calculations
Python standard library struct.pack/unpack '<f' (binary32), using invented coordinates. For x=16384 m, x+0.001 m rounds to a separation of 1.953125 mm. Subtracting the 32768 m origin before float32 conversion preserves 1.0000000474974513 mm.
For triangle [(8388608,8388608),(8388609.49,8388608.49),(8388610.49,8388608.51)], float32 yields [(8388608,8388608),(8388609,8388608),(8388610,8388609)]. The signed doubled planar area changes from -0.4602000008851289 to +1.0 square metres: three distinct vertices remain, yet orientation reverses.
These numerical results were actually reproduced, not an execution of the full revised exporter.

## Engineering changes
f096d50: explicit origin, optional vertex/edge/area error budgets, orientation and evidence checks.
30849a7: require research flags and origin agreement between GLB and sidecar.
430a3a6: new regression tests; execution pending.
Research budgets are caller supplied; formal engineering tolerances require authorization. Existing default export remains compatible and does not impose distortion budgets. Do not reassemble large global coordinates into float32. Translation cannot recover precision already lost at input.

## Remotion scenes
1. Animate the same one-millimetre edge at increasing coordinate offsets using measured synthetic distances.
2. Draw the three vertices above on a local grid; show rounding arrows and signed cross-product inversion.
3. Separate local geometry from origin metadata, show the proper axis transform.
4. Distinguish format validation, geometric tolerances, and provenance checks.
5. Show independent QA feedback and the new regression, explicitly label verification status.

Narration: 几何没有消失，不代表几何没有失真。三个顶点仍然存在，但它们围成的方向已经翻转。可靠的工程系统必须验证最终写入的几何，并保留独立的误差预算。
