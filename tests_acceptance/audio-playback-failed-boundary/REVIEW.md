# 失败片段停止点清理（待独验）

基线 `a962092bd130ced9a0c61a7d71c98e3f2d3b7667`。旧头实际内联脚本设置 stopAt=2.5 后，play Promise 拒绝未清理；随后手写播放器 timeupdate=3 会多暂停一次（计数2而预期1，初始render清理已有一次pause）。这不是实际播放验收。

只增加本次 attemptStop 标记；在原 current() 保护下，失败且全局 stopAt 仍等于本次设置值才清零。原保护包含音频 generation、case/run、选择代次与 URL。现有 action 单飞不变。同步 seek/play 抛错同样清理；赋值前校验失败不清已有边界；更晚上下文的边界不清，原提示处理不变。逆向移除三处变化后整个HTML逐字等于基线。

## 开发方实跑

```sh
python tests_acceptance/audio-playback-failed-boundary/check.py
node --test tests_acceptance/audio-playback-late-status/page.test.cjs tests_acceptance/audio-playback-serialization/page.test.cjs tests_acceptance/audio-playback-waiting/page.test.cjs
python tests_acceptance/media-review-capability/check.py
```

完整/限定 HTML 各8新场景通过：异步拒绝、seek同步失败、play同步失败；成功片段2.50秒到点仅停一次；清空/切案/切运行后迟到拒绝不清更晚的合成音频边界或提示；未知时间赋值前失败不清原边界。检查草稿仍保留、无fetch。更晚音频是内存状态夹具，不声称实际加载。

旧头先跑本测试 `node --test --test-name-pattern='failed segment leaves no stop point for ordinary playback: pending' tests_acceptance/audio-playback-failed-boundary/page.test.cjs` 得到上述暂停计数反例。相邻三个播放脚本共18节点通过；能力AST/替身及限定重开回归通过。不同模式不累加成全量。

只用合成DOM/播放器/Promise和生产内联源码，不读取音频字节，不启动浏览器、实际播放器、服务、HTTP、DB/ORM、权限或模型，不读真实案件/seed/凭据。未验证真实seek/暂停时刻；未改默认启动或服务端。冻结双检出入口6aa761c与清单未修改，仍仅在其固定交付复跑，本轮使用上述窄命令。
