# W15 AcciMap synthetic sketch component (isolated)

Isolated acceptance only. The product component at
`2447b14076bbf39db014b8bf4a3a3b350cbf0e05` is mounted on a synthetic test page.
The product source is not modified, and the component is not wired into the
main entry. This is not a W15 or W4 whole-package run, and it does not rerun
W4.1, anchored calibration, or writeback.

Desktop (1440×900) and 390×844 are checked in real sandboxed Chrome with real
keyboard input: Tab into the named diagram region, ArrowRight when the diagram
is wider than its frame, then keyboard-expand the text list. Playwright is not
used to set focus or `scrollLeft` in place of those keys.

```bash
timeout --signal=TERM --kill-after=10s 150s python run.py \
  --source /existing/mcis-git \
  --node-modules /existing/web/node_modules \
  --chrome /existing/google-chrome \
  --out /new/isolated/results
```
