# Chapter 08 — 光滑不代表准确

## Engineering evidence
- geometry_features.py, commit b71d52e: adjacent secant turning-angle candidates; implementation committed, execution pending.
- A large turning angle is a review candidate, not proof of a physical chine.
- Threshold is a caller-supplied research parameter, not a shipbuilding standard.
- Sampling density and measurement uncertainty can change the result.

## Narration draft
一条更光滑的曲线，真的更接近真实的船体吗？如果船体本身存在折角，过度追求光滑反而可能抹去真实结构。我们先计算相邻线段的方向变化，将异常转折标记为待核实的几何特征，再回到图纸寻找证据。

## Remotion scene notes
1. Draw synthetic section samples on equally scaled metric axes.
2. Reveal adjacent secants and their direction vectors.
3. Animate theta = abs(atan2(delta_y2,delta_z2)-atan2(delta_y1,delta_z1)).
4. Sweep a labeled illustrative threshold; highlight candidates.
5. Contrast a genuine chine with a smooth sparsely sampled curve.
6. End with review pending, not automatic classification.

## Data requirements
Export exact fixture coordinates, threshold, angles, candidate flags, commit and runtime versions after actual execution. Do not present unexecuted examples as measured results.
