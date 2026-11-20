# 粤海探析取证工作台：独立视觉候选

基于 `15dd6143377e345bcbd82b1c5751bf7a565f50b7`，独立分支
`candidate/zhihai-evidence-workbench`。不改 local-review-pilot、main 或其他仓库。

## 参考与实际改动

准确参考：用户 2026-11-19 的 `index.html`，经 Library 取回并验得
233421 字节 / SHA-256 `9abd7427923ec3eae5aa231b252c589d3c8778d01896fec8c7ede44adb6fefef`。
只参考 L10–22 色彩、L45–100 布局、L485 右栏、L549–588 壳与 L615–670 取证结构；
没有运行原 JS、加载资产、复制案例内容或提交原附件。不是 Unity 原型或 AI Studio。

- 48px 品牌/面包屑，240px 左队列，46px 编号七阶段，中部独立滚动，380px 右来源/版本/待办。
- 深蓝 `#0c1219/#111a24/#182430`、青 `#4dd0e1`、细边 `#2a3a4d`；系统字体，不请求网络字体。
- 工作台左侧是实际授权案件队列；图片页左侧是当前案与实际核对记录，不伪造第二份案件清单。
- 中部优先显示核对入口/内容；四份 requestDigest 放进图片页明确的折叠导入区。
- 右侧显示实际读取的归属/来源或尚未读取提示。没有 AI 探员、假完成数字、媒体示意播放器或假保存。
- 未接入阶段仅不可操作文字；原图、模型、报告和音频不新增能力。

实际页面塑形在 `local_review_pilot/pages.py`，共享静态壳在 `workbench_skin.py`。
`workbench.html` 内联脚本及塑形后的图片内联脚本与 15dd614 逐字一致，图片功能 ID 集合相同。
原授权、回选、并发响应失效、草稿、返回、导入/保存/重开守门由原脚本维持；没有后端/API 改动。
新增皮肤是后续候选代码，不刷新旧 `6169caf/3a615bf` 镜像源码冻结或允许表，也未包含在旧包。
新冻结见 `logs/zhihai-workbench-impl-hashes-frozen.txt`，尚待独立复核。

## 本轮实际复跑

仅标准库 AST/源码塑形、Node VM/手写 DOM/受控内存响应。已有离线依赖，无安装。

```sh
node tests_acceptance/pilot-workbench/check.cjs
python3 -I tests_acceptance/pilot-pages/check.py
python3 -I tests_acceptance/pilot-factory/check.py
python3 -I tests_acceptance/zhihai-workbench/check.py
python3 -I tools/zhihai_workbench_preview/build.py --output /新建自有父目录/尚不存在的预览目录
```

工作台13组；图片页塑形/返回/草稿检查、限定与普通页各22个相邻重开场景；工厂5组；
新静态结构/脚本等价/制品检查5组。均退出0，不与历史轮次累计。
工厂检查首次因稀疏检出缺少已有相邻测试文件而停止，补齐指定源码后通过，没有安装或扩大测试。

预览生成器复用当前实际 HTML 与纯塑形函数，删除所有 JS 后添加手造静态状态；
输出3份HTML、README、SHA256SUMS及ZIP。所有操作禁用，CSP禁止联网；不含原参考文件或真实资料。
初始/已选案/图片修订1均只是可读的排版状态，不是回执或服务调用。建议在1440×900对照，
再检查980/640px窄屏、长案号/长来源、键盘焦点、区域滚动及折叠导入。

**没有实际像素对照或真实浏览器验收。** 本轮不启动浏览器、服务、HTTP、ORM、容器或模型。
CSS尺寸/颜色与结构断言不证明排版无溢出；真实确认弹窗、焦点行为、响应式和渲染仍待本机检查。
目前只能下载静态预览与审查源码，不应启用实际业务、宣称接入React或合成全链路通过。
