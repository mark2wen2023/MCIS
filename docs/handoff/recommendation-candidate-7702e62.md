# 建议跟踪候选：固定版本合成交接

状态：候选，不是 main 或生产版本。DO NOT MERGE / 不部署。
本指南只整理已有验证记录；编写时未运行测试、安装依赖或请求服务。

## 交付版本

| 用途 | 分支 | 固定完整提交 |
| --- | --- | --- |
| 产品候选 | fix/recommendation-progress-adopt | `7702e62aca3f30a209bb01d76161bc369181af9d` |
| 额外测试修订（产品代码相同） | test/recommendation-adopt-source-guard | `71889d21990b015354ae97b687537a59ad5c7014` |
| 原UI+PR104组合基线 | integration/ui-pr104 | `9cc3ecee7251b6f19a739c14ce316740c048594e` |

额外测试修订是产品候选的后继，修正测试归因；增强snapshot 5场景及flight 7场景已获限定独立复验，不属于原7702e62测试结果。
本指南所在文档分支以7702e62为父基线，不包含71889d2的测试改动。
分支以后可能移动；同事必须核对完整SHA，不将不同头称为同版本。

无需逐个合并下列修复，它们已在产品候选祖先链中：

| 提交 | 有界修复 |
| --- | --- |
| 80b0756 | 报告刷新回调及异步完成后的章节选择 |
| 1a01a49 | 旧建议操作不清除后来打开的待确认项 |
| 2e3f3ad / e8ec0bc | 进度同步锁、unknown及刷新回调异常时保留说明 |
| d7447db | 建议页专用读取控制和加载/旧快照/失败提示；共享hook未修改 |
| a5086d9 | 未编辑进度随快照更新，编辑草稿保留 |
| 717c683 | 案件信息初读失败文案；看板刷新不重读案件信息 |
| ba7e59e | unknown提示不随非Responded状态隐藏 |
| 7702e62 | 已知来源变化阻止进度提交，显式采用已读取值并保留说明 |

服务端回执设计另在 docs/progress-operation-receipts，审查稿头
`08f38ca960c89c85cd321b8f21dd24395ccccd2f`；此产品候选只有更早设计稿，
未包含最新设计修订。设计没有实现或运行，不可视作持久幂等/恢复能力。

## 已测与证据归属

7702e62下列5/7/10/5合成场景及TypeScript/Vite构建，已有开发方记录和限定独立复验通过：

| web目录下命令 | 记录结果 |
| --- | --- |
| node tests/recommendation-progress-snapshot.test.cjs | 5个合成场景 |
| node tests/recommendation-progress-flight.test.cjs | 7个合成场景 |
| node tests/recommendation-form-save.test.cjs | 10个合成场景 |
| node tests/recommendation-read-state.test.cjs | 5个合成场景 |
| npm run build | TypeScript/Vite通过，仍有大包警告 |

这些是实际组件代码与合成hook/API/read快照组合，不是真实浏览器或HTTP。
**7702e62的过期采用回调断言有归因缺口**：没有先渲染ready/source60 Detail，
可能先被此前readReady=false阻断，不能据此证明来源比较生效。

71889d2开发方加强后：先渲染ready/source60，验证当前采用按钮可用，再调用旧
source50采用回调；另检查原本可提交的source25保存回调不再派发。
加强后仍为5场景（不是额外加5）；开发方记录相邻flight7与构建通过。
独立复验通过增强snapshot 5场景及flight 7场景；71889d2仅改测试/文档，
该轮独验未重复构建，沿用7702e62已独验构建，不能称为71889d2本轮新构建。
A→B→A及刷新触发到重渲染窗口仍未覆盖，不代表服务端版本控制。

证据文件：
- 产品：[DEVELOPER.md](../../tests_acceptance/recommendation-progress-adopt/DEVELOPER.md)
- 产品输入：[冻结摘要](../../logs/recommendation-progress-adopt-impl-hashes-frozen.txt)
- 额外测试：在71889d2读取同一DEVELOPER.md的Follow-up，以及
  `logs/recommendation-adopt-source-guard-test-hashes-frozen.txt`。

历史测试、独立审查和当前开发自测必须分别归属其精确头；不累计轮次、场景和断言
为全量通过。上述独验仅覆盖列明的合成场景及对应构建，不是完整交互验收。

## 合成验证操作

仅在自己控制的新工作目录中检出。普通git clone不证明仓库资料已净化；
不得加入或打开真实案件资料、种子、数据库或凭据。执行范围仅限下列已审阅前端脚本
及构建，不因取得完整仓库而扩大到数据读取或后端测试。
以下Git命令是交接步骤，本次文档工作未重新执行克隆：

```bash
git clone --branch fix/recommendation-progress-adopt https://github.com/mark2wen2023/MCIS.git mcis-recommendation-review
cd mcis-recommendation-review
git checkout --detach 7702e62aca3f30a209bb01d76161bc369181af9d
git rev-parse HEAD
cd web
```

输出必须等于上述完整SHA。若远端变化或对象无法取得，停止核对，不换版本冒充。
开发方复用了现有Node/npm依赖（记录Node24.22.1、Vite8.3.8），没有验证新机器安装。
`web/package.json`及`web/package-lock.json`存在；按组织正常授权方式准备锁定依赖。
**全新依赖安装未验证**，本指南不提供已保证可用的安装命令，不复制开发机绝对路径
或缓存软链。依赖缺失、网络或权限阻碍时停止，不绕过、不下载模型。

依赖齐备后，仅运行已审阅选择：

```bash
node tests/recommendation-progress-snapshot.test.cjs
node tests/recommendation-progress-flight.test.cjs
node tests/recommendation-form-save.test.cjs
node tests/recommendation-read-state.test.cjs
npm run build
```

命令对应实际文件；build脚本是 `tsc -b && vite build`。不要改成全仓测试或npm test，
不要运行baseline模式（它用于历史缺陷复现，并非候选通过检查）。这些脚本无需后端。

若专门复核额外测试，在另一个新目录重复克隆步骤，将分支换成
`test/recommendation-adopt-source-guard`，detach固定到
`71889d21990b015354ae97b687537a59ad5c7014`，核对HEAD后在web运行：

```bash
node tests/recommendation-progress-snapshot.test.cjs
node tests/recommendation-progress-flight.test.cjs
npm run build
```

记录本机版本、精确SHA、每条命令退出码和未验内容。不要把文档里的旧结果当本机执行。
禁止运行此前暂停节点、拒写/安全探测、恢复、真实案例生成、HFACS或模型。

## 不能用于生产的原因与下一步

- 全新依赖安装、真实浏览器/视觉、真实HTTP联动、可信身份及生产验收均未验证；
  不是完整CI，不能用SSR/合成hooks代替浏览器。
- 身份仍为现有自报角色机制，不是生产认证；权限策略未改，不得注入高权限绕过。
- 草稿、锁与通知在内存，离开/重挂载可能丢失。unknown无原地解锁；先复制草稿，
  人工核对记录/审计。刷新或重新打开不证明旧请求未提交，不能自动重发。
- 来源比较仅使用已观察字段，不是CAS、不可变版本或人已读证明。多用户可在读取后改动。
- 采用当前值只改本地；同百分比不能单独保存说明，不能为保存说明而改变实际进度。
- 看板/审计分别读取，不是同一快照；读取失败不能当作没有记录。
- 此交付不新增归档恢复能力，不表示复杂案件可完整备份，不改变现有防丢保护。

下一步是同事在自身环境按固定头复现上述限定检查，并记录环境差异；
浏览器验收须另在正常沙箱可用环境中经授权安排，现有合成独验不能替代。
遇阻停止报告，不改变安全设置、不以替换工具规避限制；不合并、不部署。
