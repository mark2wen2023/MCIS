# W7 截止时间未知提示

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`，独立候选，不修改W3/W7合同或截止业务边界。只修改 closeHint 一处普通显示逻辑：无有效 deadlineUtc 或有限本机时间，不再称“未到期限”，改为无法判断；最终由服务决定。已关闭/各方已回复优先语义不变；精确截止相等仍为本机已到。

源码核对：consultation-round.schema.json 要求 deadlineUtc，daysRemaining是服务只读推导字段；RecommendationsPage显示服务截止和剩余天数。W7.2生命周期以deadline而非daysRemaining=0判断关闭提示，现有30项涵盖边界但对无效日期只断言“可能拒绝”，遗漏同时错误称“未到”。本轮不增加倒计时、不从打开时间加30天推导权威期限，不改变服务判断或发送/通知/权限/保存。

重要差异：当前源码 newRoundPayload 已硬编码 days:30，RoundLifecycle 显示固定默认30天；ROADMAP W7.2也记录该既有裁定。用户本轮要求不可当法定期限；本候选不作法律判断、不另造期限，也不擅改已裁定的新建行为。合同中的规范性说明未经本轮外部核实；要改变既有30天产品默认须另行确认。无轮次时仍是新建草稿表单，不显示本候选的到期提示；关闭状态不伪装征求中。RecommendationsPage服务剩余天数的实时更新不在本轮验收内。

## 实跑（复用已安装离线依赖）

```bash
web/node_modules/.bin/esbuild web/tests/consultation-deadline-hint.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/w7-hint.cjs --jsx=automatic --log-level=warning
node /tmp/w7-hint.cjs
bash web/tests/run-consultation-w72.sh
```

旧固定头同一新测试退出1，首个未知期限断言失败。候选24项纯函数/实际RoundLifecycle SSR断言通过（退出0），原W7.2 30项通过（退出0），不累计为浏览器覆盖。覆盖空串/空白/null/缺值/无法解析日期、NaN/正负Infinity本机时钟、deadline±1ms及相等、epoch合法0、已关闭/各方回复状态优先。SSR不执行事件/网络；mutate替身不被调用。

未跑浏览器、HTTP、发送、保存、真实服务权限或全量TS/Vite；没有安装依赖/使用真实资料/模型。主题和原页面结构不变。冻结见 logs/w7-unknown-deadline-impl-hashes-frozen.txt，旧冻结保留。
