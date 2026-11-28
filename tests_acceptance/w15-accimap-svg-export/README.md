# W15 AcciMap isolated local SVG export

Isolated acceptance only. Product pin `2447b14076bbf39db014b8bf4a3a3b350cbf0e05`
(`web/src/accimapPreview/Diagram.tsx` SHA-256
`d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f`) is unchanged.
The independent export module serializes the already-rendered six-layer synthetic
sketch and triggers a real browser download. It is not wired into the official
preview route, Bow-tie SVG export, case reads, identity, contracts, or the 3D
repo. This is not a W15 whole-package run and does not rerun the past 9/9 core.

```bash
timeout --signal=TERM --kill-after=10s 150s python run.py \
  --source /existing/mcis-git \
  --node-modules /existing/web/node_modules \
  --chrome /existing/google-chrome \
  --out /new/isolated/results
```
