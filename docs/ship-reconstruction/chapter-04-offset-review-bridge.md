# Chapter 04 / 06 — A source change requires a fresh review

Synthetic local experiment at source commit 6ecb403 and tests 2e2faf3. Local blob hashes match remote: offset_bridge e1d040a7ee7e64ceb519ad4d409b3a0f471fb8a8; sparse_section 67d2f3ce9a7531f23b09812e486dc5dc3507409b; test 8bb813cb3e1e5deb5a9ed4e213deea0296552cd1. Isolated pytest: 14 passed in 0.05 s. Independent QA pending.

| Step | Source value (m) | Research sample (m) | Result |
|---|---:|---:|---|
| Original | 1 | 1 | matching review |
| Change without fresh review | 1.125 | null | rejected |
| Update review to match new observation | 1.125 | 1.125 | accepted |
| Replace observation by null | null | null | unsupported |

Actual observed half-breadth sample change: 0.125 m. Axes [0,2,4] and [0,1] m; no second unit conversion. Null source observation remains in audit record. No mesh or GLB produced by this isolated test. The adapter rejects absent grid records and extraction issues; fixing whole empty CAD rows is separate. Frame identity and review labels are externally supplied and not authenticated.

## Narration
一个原始型值发生了变化，几何数据也应当发生相应变化。但审核不能随着数字自动更新。我们故意修改一个数据，旧审核立即失效；重新核对后，新的数值才允许进入横剖面计算。最后，我们把它变成空白，系统保留未知。可靠的数据链条，不只是传递数字，也是传递数字的依据与审核状态。

## Remotion
Animate source cell 1.000 to 1.125 m, review rejected, new synthetic review, sample updated by 125 mm. Replace cell with null and show unsupported. Read machine-readable output from the local experiment package. Research only; no design approval, no real vessel data.
