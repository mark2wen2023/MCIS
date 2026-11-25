# Chapter 06 — A surface with evidence

Engineering references: sparse_loft.py (9a337dd), geometry_provenance.py (ef8dd13). Implementations committed; tests pending.

## Narration
一块数字船体表面，不仅有顶点和三角面，还应该有自己的证据来源。我们尝试把每个局部网格与支持它的型值和审核记录关联起来。没有证据支持的区域保持空缺。模型不再只是形状，也是对当前知识边界的表达。

## Remotion scene plan
1. Reveal a synthetic sparse offset grid.
2. Build only explicitly supported cells; preserve holes.
3. Select one computed face and highlight its four supporting cell corners.
4. Animate links from corner samples to synthetic document references.
5. Distinguish direct observations from interpolated samples and computed surfaces.
6. Display pending review and no production authorization.

## Limitations and data requirements
The initial binder trusts mesh cell mappings and sample arrays supplied by the caller; it does not yet verify coordinate equality, triangle membership, source hashes or cryptographic signatures. Archive executable synthetic outputs and tests before presenting results. Real vessel assets require publication clearance.
