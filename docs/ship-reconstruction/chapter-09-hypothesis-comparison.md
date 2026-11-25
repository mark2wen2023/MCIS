# Chapter 04 / 09 — Compare like with like

Synthetic experiment only. Source fa88925; tests d09236e. Local Git blob checks matched both remote files and the existing research_baseline module. Python 3.13.5, pytest 9.0.2: 9 passed in 0.06 s. Independent QA and full service suite pending.

| Case | Common x-z footprint | A volume m3 | B volume m3 |
|---|---:|---:|---:|
| full | 1 | 8 | 9.6 |
| one unknown corner in B | 0.5 | 4 | 4.8 |
| no common patch | 0 | null | null |

Fixture: stations [0,2,4] m, heights [0,1] m, symmetric rectangular sections, half breadth A=1 m and B=1.2 m. Both patches explicitly supported. Unknown corner at [0,0] or [1,0] in scenario B, respectively. Integral of 2*y over the common x-z bilinear patches; not displacement, probability or a whole-vessel uncertainty interval.

## Narration and Remotion
1. Show the two equal x-z patches and both half breadths; animate the conditional volumes.
2. Remove one corner from B and exclude its patch from both comparisons.
3. Remove a corner shared by both patches; show coverage zero and volume unknown.
4. Explain: 当资料产生不同解释时，我们不急于选择一个答案。我们把不同假设放在同一个坐标世界、同一片有数据支持的区域内比较。没有共同覆盖区域时，答案不是零，而是未知。

Support mask and symmetry are supplied assumptions, not authenticated facts. Formal authorization remains false. No real vessel data.
