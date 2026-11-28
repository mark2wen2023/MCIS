# W11 ECFC 自动布局：混合时间排序修正（承 Dot 7237794872）

- 候选：`candidate/w11-ecfc-auto-layout` @ `94cc3a33fbc521041a71b7a251b17d5e4bda973f`（父提交 `49bf8a5`）
- 改动 2 个文件：
  - `web/src/ecfcDrafts/layout.ts`（SHA-256 8078a120181d5154e6c8b855803cf4a8dbb9b0b9cfb09a2303c2d5c45b833017）
  - `web/tests/ecfc-auto-layout.test.tsx`（SHA-256 ee14811f3ed4247d8a9c4cd577e5eb8e4cccf32ab4b0aec7b77ff859d869f128）
  - Graph.tsx 未变（6cf912d8…）；其他文件都没动。
- 根因：可同时排的事件之间，原比较函数“两者都有时间就比时间，否则比输入序”不传递。输入 A(30s), U(未知), B(10s) 时会得到 A < U < B，于是 30s 排到了 10s 前。
- 修正：先按输入序给同批可排节点占位；有时间的节点在它们自己占的位置里按时间→ID 重排，未定时节点留在原位。这个排列稳定、确定，而且不比较未定时节点的时间，也就不猜时间。拓扑约束（Kahn 入度）不变；未定时节点在多节点并列时仍列为待核。

## 命令与原始退出码
1. `sh web/tests/run-ecfc-auto-layout.sh`（在 94cc3a33fbc521041a71b7a251b17d5e4bda973f，工作树干净）：exit 0。27 条通过（原 22 条加新 5 条），既有 ecfc-model 82 条也通过。
2. `tsc -b --force`：exit 0。
3. 修正前复现：用新测试跑旧的 49bf8a5 layout.ts（临时目录），exit 1，报 `FAIL: mixed A,U,B: 10s B before 30s A`。
4. 原 22 条检查没有放宽：49bf8a5 测试文件的每一行都原样保留在 HEAD（见 00-head.txt）。

## 新增的 5 条检查
1. 输入 A,U,B 时 B 在 A 前。
2. U 列为待核，时间仍为 null。
3. 6 种输入顺序下都是 B 在 A 前、U 待核。
4. 同一输入重复运行，结果逐字节一致。
5. 有 A(30s)→B(10s) 连线时，A 仍在 B 前，拓扑优先。

按要求没有重跑 Chrome，没接服务，没改契约或试用版。不安装、不合并、不部署。这只是一个子项，不等于 W11 整包。
