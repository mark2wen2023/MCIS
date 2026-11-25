# Chapter 09 — A valid file can contain collapsed geometry

## Evidence
Independent QA reported float32 collapse after export (operator-relayed report; exact private fixture not inspected). Corrective commits: 1ed3fa8, 5514ed7, 8f5f1c1, 9d2d16e; synthetic regression tests c14bf27 (execution pending).

## Independent synthetic numerical experiment
Python struct.pack/unpack with IEEE 754 binary32. Compare x and x+0.001 metres and the spacing to the next representable value. All inputs below are invented, not ship coordinates.
| x (m) | next representable spacing (m) | stored separation (m) |
|---:|---:|---:|
| 1 | 0.00000011920928955078125 | 0.001000046730041504 |
| 1000 | 0.00006103515625 | 0.0009765625 |
| 10000 | 0.0009765625 | 0.0009765625 |
| 100000 | 0.0078125 | 0 |
| 1000000 | 0.0625 | 0 |

Reproduce with Python: import struct; f=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]; print(f(100000+.001)-f(100000)).
This experiment checks scalar quantization, not execution of the repaired GLB exporter.

## Remotion storyboard
1. Draw a synthetic thin rectangle at its local origin.
2. Show the same rectangle with a large coordinate offset; geometry unchanged in double precision.
3. Display the increasing spacing between adjacent binary32 values.
4. Round both x coordinates to the same value; collapse the rectangle into a line.
5. Contrast format validity with geometric validity.
6. Show the corrective post-serialization check and explicit rejection; label integration tests pending.

## Narration
文件格式正确，并不等于几何正确。计算机用有限的二进制位表达空间坐标。当坐标绝对值增大，相邻可表达数字的间距也可能增大。一毫米的距离，在某些坐标下可能完全消失。因此，我们必须检查最终写入文件的几何，而不能只检查写入之前的数学模型。

No real ship data; no production authorization.
