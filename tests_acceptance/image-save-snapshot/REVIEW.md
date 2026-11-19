# 图片保存提交快照（待独验）

基线：561892c0e38053d66b3b3eabb0e8c1f4fcb9700f。

现有 action 同步 busy 单飞门控保留。发送时固定原 state 身份/修订、initial 与完整历史序列化快照及 Object.freeze 的原始提交字段。返回逐项比较原请求而不是等待后 live input；仍须同案同运行、当前选择世代、同一 state/版本、initial、完整历史前缀、仅追加一条及预期修订，正文/行号/理由/decision 完整匹配。不减少原成功条件，新增当前基线检查；JSON 键序仍保守比较。

行内 oninput 单调代次区分提交之后的编辑（包括改后改回）。确认仅更新已保存 state/历史/修订，不重绘输入。仅无随后本行编辑时清本行 dirty，其他行 dirty 不动；有草稿不更新 URL，旧 unknown 不清。412 精确冲突仍仅当前请求明确未保存，其余保守未知且不污染新目标。无自动重读/重试。

## 开发方实跑

```sh
python tests_acceptance/image-save-snapshot/check.py
python tests_acceptance/image-save-conflict/check.py
node --test tests_acceptance/image-save-context/page.test.cjs tests_acceptance/image-reopen-address/page.test.cjs
python tests_acceptance/media-review-capability/check.py
```

- 新快照测试完整/限定各22场景通过；生产内联脚本和 json 包装、合成 DOM/受控 fetch Promise。覆盖三类本行编辑、改回、另行编辑、错字段/身份/版本/initial/历史、丢响应、冲突、状态替换、切案/运行、单飞及旧未知。
- 基线先跑 `node --test --test-name-pattern='matching submitted response preserves subsequent text' tests_acceptance/image-save-snapshot/page.test.cjs`：实际修订2而预期3，确证原提交匹配仍被标未知。此前一次夹具未提供 URLSearchParams 的测试装配错误已修正，不作为产品反例。
- 原冲突20场景在完整/限定均通过。相邻保存上下文4、重开地址22通过；能力脚本 AST/假挂载及四模式通过，并运行限定图片 URL9/地址22、音频 URL7/地址19。不同模式重复不累计为全量。
- 修订旧地址测试“等待编辑必为未知”的断言：该旧绿测刻画的是本轮确证问题；改为原请求匹配时确认修订、保留新草稿、不写地址。未删错响应、迟到或未知检查。新增模拟刷新断言：重开读已提交值，非尚未保存的新草稿。

仅前端内存模拟；不证明真实 React/浏览器、HTTP、后端提交/权限或持久一致性。不运行应用、DB/ORM、模型、暂停测试，不读真实资料/seed/凭据。未改服务器/接口/原件保护；仍未具备安全隔离联调入口。上一项请求摘要指引中“完整 JS 与其基线逐字相同”为该固定提交的证据，本轮有意修改保存代码，不将该冻结断言当当前回归。
