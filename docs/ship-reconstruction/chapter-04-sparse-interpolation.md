# Chapter 04 supplement — Evidence-bounded interpolation

Engineering source: sparse_section.py, commit 39790c1. Implementation committed; execution pending.

## Narration draft
插值并不意味着可以任意填补空白。我们只在两个相邻、经过核实的型值之间建立连接。如果中间存在未知数据，曲线就必须暂时中断。数字船体可以不完整，但不能把未经证实的几何伪装成事实。

## Remotion scenes
1. Reveal synthetic height grid and measured half breadths.
2. Draw supported adjacent segments in green.
3. Show null cells as question marks, without numeric coordinates.
4. Show a hypothetical dashed bridge, explicitly label unsupported.
5. Reveal provenance links from interpolated samples to both endpoints.

## Evidence to collect
Exact synthetic fixture, query coordinates, supported/unsupported counts, returned provenance, test results and commit. No actual vessel data in public assets.
