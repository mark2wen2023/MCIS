# MCIS 阶段交接与剩余验收

2026-11-25（UTC+8）。[当前甘特图](https://chatgpt.com/space/page_d59ce90cb8ac81918005a5642f50e655)按原工作包计数：限定范围整体验收 **10/22**。本交接目录、候选分支和局部实跑不是发布、合并或新增验收勾选。不要把各分叉的候选一次性合并，也不要用新版提交替代旧版通过回执。

## 可拉取的最近候选

| 包 | 分支或固定提交 | 实跑边界 |
| --- | --- | --- |
| W3 | [`9a72cf3`](https://github.com/mark2wen2023/MCIS/commit/9a72cf3edaf420eddce393ce31d60d9c6b5fba34) · `candidate/w3-pr56-source-version-status-20261124` | 合成案来源和版本对照、复核，React 与 API/SQLite；实际浏览器待验。 |
| W4 | [`67654fd`](https://github.com/mark2wen2023/MCIS/commit/67654fd9801735dfe81361caf5e6f0148ab5e7da) · `candidate/w4-synthetic-pdf-preview-20261124` | 默认关闭的单案单页入口，FastAPI/SQLite/Poppler 16 项；实际浏览器待验。 |
| W7 | [`7dfb326`](https://github.com/mark2wen2023/MCIS/commit/7dfb3261522ff6241b9f5b44f809dd405b28ffde) · `candidate/w7-agreed-deadline-20261124` | 商定期限、重开、版本关联为合成验证；完整轮次与正式流程待验。 |
| W9 | [`de058c65`](https://github.com/mark2wen2023/MCIS/commit/de058c65edb59b4069865de49fca06349e32793f) · `candidate/w9-zero-span-geometry-20261124`；[`a928e5e`](https://github.com/mark2wen2023/MCIS/commit/a928e5e4db6d0bd669a41b80a8f5d39a707cab98) · `candidate/w9-environment-replay-status-20261124` | [二维固定页 Chrome 任务](https://github.com/mark2wen2023/MCIS/actions/runs/45352023199) 桌面与窄屏各 9/9，仅该二维运行；人工视觉及新版环境页实际浏览器未验。 |
| W11 | [`d9187fe`](https://github.com/mark2wen2023/MCIS/commit/d9187fef1f979866ac4d8ce2064d1ac92f34bb36) · `candidate/ecfc-graph-edge-selection` | 合成关联读与版本边界；本分支附 [W7/W11 独立联验](../tests_acceptance/w7-ecfc-sqlite/README.md)，不代替 .NET 生成、正式持久化或实际浏览器。 |
| W15 | [`597a7d5`](https://github.com/mark2wen2023/MCIS/commit/597a7d5e42dbbee55f7a75ead629c0a89669cc15) · `candidate/w15-accimap-empty-endpoints-20261125`；[`2c72d02`](https://github.com/mark2wen2023/MCIS/commit/2c72d022f3d3275af637b0cdc6e545735e3200a9) · `candidate/w15-bowtie-path-navigation-20261124` | React DOM / 静态渲染、TypeScript；正式接线、审核/保存及浏览器待验。 |
| W16 | [`67299ce`](https://github.com/mark2wen2023/MCIS/commit/67299ce6a03edae1cb74be4a4993b54c2110127f) · `candidate/w16-reference-locators-20261125` | 真合成生成、编辑、导出、重开，6 项引用回归。原仓字体重新取样目视正常；Microsoft Word 客户端未验。 |
| W17 | [`29cbfe2`](https://github.com/mark2wen2023/MCIS/commit/29cbfe255967fc6814abafd919ed9a7485ef8710) · `candidate/w17-explicit-evidence-selection-20261124` | 合成切案选证与访问审计已复跑；新候选实机浏览器和正式身份未验。 |
| W19 | [`7ba7970`](https://github.com/mark2wen2023/MCIS/commit/7ba7970ba4f77ebce11463d663e0f02a6c3f7928) · `candidate/w19-read-lifecycle-20261124` | 知识卡合成读取、撤回、过期响应，React 和 SQLite；实机浏览器待验。 |
| W20 | [`58fc144`](https://github.com/mark2wen2023/MCIS/commit/58fc144ca99e91b42037bcab75ea94772bbad888) · `candidate/w20-typed-t100-seat-20261124`；[`39d8f53`](https://github.com/mark2wen2023/MCIS/commit/39d8f530e6011a54a130c58f687b3695b9112b8e) · `candidate/w20-four-review-questions-20261124`；[`e419ffe`](https://github.com/mark2wen2023/MCIS/commit/e419ffe66c8418261e2a6af163debaaee2721128) · `candidate/synthetic-report-draft-local` | 单席与四席待审源绑定合成测试，非正式宿主/真实推理，不自动出调查结论。 |
| W21 | [`1724774`](https://github.com/mark2wen2023/MCIS/commit/17247747272fb53623b144e199260f59d6befcbd) · `candidate/four-frames-prepare-joined`；[`8d68f6f`](https://github.com/mark2wen2023/MCIS/commit/8d68f6fa076b7acad90fab10e95ab88c6945a018) · `candidate/mcis-cross-repo-clock-receipt` | GitHub 可拉取；需要有两条完整历史的 MCIS 工作副本复验。三份固定合成样例已对字节，无须重交。真三维与 SQLite 四时点尚未联验。 |

## 闭环顺序

1. W4、W3、W9、W15、W17、W19 在各自固定版本运行真实浏览器，分别保留桌面/移动、选证/撤权、切案清旧、控制台及下载回执。W9 已跑过的旧二维入口不再重复冒充新版全验。
2. W7、W11 合并验收证据，不合并代码分支：完成建议全轮次、指定图版本/端点及已登记原片段联结、撤销、真实 .NET 与持久化。W12 保持冻结，不能用旁路推演替代原计算验收。
3. W20 先验证同案带来源的正式读入口再开多席。保留事实、分歧、不足与人工决定；合成或替身测试不能代表真实模型、4A 或生产身份。
4. W13、W21 分开验 Web 与 Unity。四时点固定 T+100／121／124.250／127.500：浏览器回执应带两仓提交、三份样例哈希、实际命令退出码及首导航起的网络范围，再查同案关联、访问审计、草稿写入和重开。正式集成还需 Unity、串流回退及 Windows 交付。
5. 正式发布、签发或部署均未执行。本交接只纳入可验证候选和合成测试，不含环境配置、附件原件、账号、运行数据库或证据包。
