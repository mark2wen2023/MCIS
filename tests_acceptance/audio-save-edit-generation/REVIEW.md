# 音频本段保存后编辑世代（待独验）

基线 `6aa761c940f98a3c125e379c638206b8a7f234f7`。旧实现等待中本段改过再改回，会因字段重新等于发送值清除 dirtySegments。本轮先运行新测试的文字改回单节点，失败为 dirtySegments.has(s1) 实际 false、预期 true。

产品只作四处局部改动：本段私有 segmentEditVersion 初值；五个本段输入 oninput 增加代次；发送时记代次；清本段 dirty 同时要求代次未变与原字段相等。全局 action 单飞、响应与提交快照/历史校验、切案迟到、412、累计未知和地址控制均未改。逆向移除这四处后整份 HTML 与基线字节一致。别段输入不影响本段代次；等待中改回也保留草稿/离页提醒。

## 本轮开发方实跑

```sh
python tests_acceptance/audio-save-edit-generation/check.py
python tests_acceptance/audio-save-conflict/check.py
node --test tests_acceptance/audio-save-context/page.test.cjs tests_acceptance/audio-reopen-address/page.test.cjs
python tests_acceptance/media-review-capability/check.py
```

新脚本使用实际生产内联代码、json/fetch 包装、受控内存响应和手写 DOM。完整/限定各8场景通过：文字/核对状态/起止/理由改回、别段编辑、无后续编辑、匹配快照保留新稿及旧未知。断言当前 DOM、离页标记、修订与请求数、地址未写。旧头复验命令（先从固定提交准备 audio HTML，再指定 AUDIO_PAGE_SOURCE，不联网）：

```sh
node --test --test-name-pattern='same segment edit and revert remains unsaved: 1' tests_acceptance/audio-save-edit-generation/page.test.cjs
```

相邻冲突完整/限定各17通过；保存上下文4、地址19通过；能力脚本 AST/假挂载、完整/限定动作及限定图片URL9/地址22、音频URL7/地址19通过。不累加重复场景为全量。

`tools/evidence_ui_offline` 及其冻结清单未改。该交付仍应在原 `6aa761c` 检出复跑；本轮音频受测源码变更会被其哈希检查拒绝，不声称冻结入口覆盖新头。新头复跑使用上面的窄命令。

仅离线合成，不证明真实浏览器、HTTP、原音回听、后台保存/权限或完整工作台切案。未运行服务、DB/ORM、模型、暂停测试；未读取真实材料、seed、凭据；未改服务端/契约/默认启动。
