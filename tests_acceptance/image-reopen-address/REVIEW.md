# 图片当前运行地址同步 — 开发检查

基线 `3d5b09d9d01c9f736afbf7e56829456c0e58b3f0`，候选 `candidate/media-demo-lazy-factory`。本轮仅图片页面，音频及服务端未改。

在导入、读取、人工修订响应通过原有校验并被当前 UI 接纳后，且没有残留草稿或页面累计未知保存，使用同源相对 query 的 `history.replaceState(null, '', search)` 更新 case/run。无 revision、角色、操作者、凭据或摘要，不 push、不导航、不增加请求。无参数手工流程在成功后获得合法重开地址；刷新仍是当前运行，不是报告固定历史版本。

按图片真实逻辑保留：保存响应与当前行输入比较；等待中编辑导致不符时继续未知，不改成音频的提交快照接受策略。本行保存确认但其他行仍脏时不更新地址；读取不能核实旧未知保存，因此仍阻止地址更新。History 缺失或抛错只写独立提示，不抛进保存 catch，不把已确认保存记为未知。原 reset 确认、edit/selection/createForm 代次、响应身份/版本/原始与历史比较均不变。原件和 task binding 守门未动。

实际执行：

```
node --test tests_acceptance/image-reopen-address/page.test.cjs
node --test tests_acceptance/image-url-reopen/page.test.cjs tests_acceptance/image-loaded-context/page.test.cjs
```

新增21个命名场景通过；相邻URL重开9个、归属/草稿5个分别通过。实际内联脚本在 Node VM 中运行，DOM、History、请求均为手写替身；真实 fetch、解码和原件加载禁止。合成导入/保存响应不是实际服务或权限验收。以新 VM 和同步后的 query 模拟刷新，核对重新请求和显示的修订文字；不是浏览器端到端。

旧头反例：将 `git show 3d5b09d9d01c9f736afbf7e56829456c0e58b3f0:service/mcis_service/image_review/review.html` 保存为 `/tmp/image-address-baseline.html`：

```
IMAGE_PAGE_SOURCE=/tmp/image-address-baseline.html node --test --test-name-pattern='manual new import' tests_acceptance/image-reopen-address/page.test.cjs
```

旧头实际失败：地址写入数组为空，候选相同场景通过。无关React构建未重复；无真实浏览器、HTTP、应用、DB/ORM、权限、模型、原件、归档或暂停验收。真实 History/刷新及受控同源身份仍待隔离环境验收，启动暂停未解除。未接工作台，未合并部署。
