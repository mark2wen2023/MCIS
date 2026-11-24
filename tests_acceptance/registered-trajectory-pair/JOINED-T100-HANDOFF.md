# Same-DB T100 handoff — test only, ephemeral

Parent: 17247747272fb53623b144e199260f59d6befcbd.
`four_frames_prepare_joined.py` remains byte-for-byte unchanged (SHA256
`a71813661dfdf538ce040f8e1ee83dc0499df15ddf165683eb01f6616c9535d6`).
Existing original-byte registration, permissions, query, prepare and audit checks
are run once, including its three independent baseline tests and one joined test.
This does not combine the baseline tests' separate databases into the joined DB.

```sh
/path/to/existing/python -I -B tests_acceptance/registered-trajectory-pair/joined_t100_handoff.py
```

Use the same existing Python dependencies and fixed Git objects documented in
FOUR-FRAMES-PREPARE-JOINED.md. No fetch, installs, services or default app/seed.
GIT_NO_LAZY_FETCH=1 is set before Git reads. All assertions remain enabled.

Mechanism: a temporary Python return profiler observes the actual
`_query_registered_pair` return, checks its executing file against exact db90fdf
Git bytes, and extracts only the T100 minimum projection. It does not replace
any function, mock a response, call a reader or run a second query. The original
joined test must finish successfully with its expected counts and pins. The
observer is removed in finally; duplicate/missing returns or projection failure
produce only FAILED, not a partial handoff. Captured fixture output stays in
memory and is not emitted or attached. No original bytes or full case document
are included in the handoff.

Output contains only fixed synthetic case/UTC, source fixture commit, actual
registration IDs/request digests/raw hashes, vessel IDs, JSON pointers and one
heading observation per vessel. A: missing/null; B: recorded/270 (strictly below 360, exact fixed-value assertion) in this exact
synthetic input. Recorded here describes fixture quality, not independent truth.
COG is not a heading substitute. Alignment is not human-approved event ordering.
EV-001/EV-002 are this fresh fixture's receipts, not global product constants.

The ephemeral receipt requires queryAccess=8, prepareAccess=1, finalAccess=9,
custodyRows=11, auditRows=12, reportRows=0, one manually supplied snapshot fixture,
no binding table, and denial paths with no extra writes. observerAccess=0 describes
this observer's absence of read calls; it is not a new production audit receipt.
The registered IDs/hashes are internal test handoff fields, NOT browser/model
context, reusable authority, API output or a disclosure grant. Do not persist
or distribute them as real records. No report is generated, saved or exported.

W20 is NOT connected. Its quote/line inputs require a separate typed adapter and
separate authorization; this observation has JSON Pointer and heading semantics,
not report page/line/quote semantics. Do not invent quotes, transfer a pin as a
credential, or infer a maneuver from one point. No model, live account, browser,
3D, common transaction across phases, or end-to-end product claim.

Observed on this task: original fixture exit0 via wrapper; 8+1 Access preserved;
A missing heading and B exact recorded 270 exported. Independent projection
negative checks are pure standard-library and do not run the fixture again.

## 同次登记 pin 的独立观察（后继候选）
在原测试方法 call 事件中先复制已登记 self.pins，且必须早于任何
T100 query 返回；仅附加 expectedRegistrations 最小身份映射。consumer 用它
核对观察结果，不从观察结果反建预期。固定 runner 是信任边界，不是任意
JSON 真伪证明或生产授权。本轮同库重跑仍 8+1 Access，无额外原件读取。
