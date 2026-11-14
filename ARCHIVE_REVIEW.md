# Public evidence archive 独立发布前审查

审查日期2026-11-14。只审本归档选定材料，未执行历史脚本、测试或模型，未访问API、读取环境秘密或修改源目录。本次唯一写入为本报告。

## 裁定与边界

**41项选定附件来源/大小/归档摘要全部匹配；在本次内容审查范围内未发现须拦截的凭据、私案、个人敏感值或实际环境标识。可作为历史证据归档候选继续准备。** 这不是代码功能重新验收、历史模型调用真实性认证或真实执行放行。README/验证器等后续新增文件不包含在本41项裁定，发布前应审查最终完整树并核对清单；任何未在清单或来源无法核对的新内容应停止发布。

审查时HEAD为尚无提交的orphan分支codex/public-evidence-archive-20261114；未携带开发祖先。41附件共102991字节，最大10522字节。全为普通UTF8文本，无符号链接、NUL、可执行位或二进制大文件；evidence实际文件集合等于MANIFEST，未夹入缓存/完整工作树/原始环境元数据。

## 来源与补丁

逐项从指定Git提交git show、本地历史证据目录或精确git diff重新取得源字节，对照sourceSha256，再核对archivedSha256/bytes。Markdown仅前置统一历史HOLD警告，原文逐字保留；其余逐字节相同。41/41通过。来源摘要确认所选快照，不证明原测试或来源声明真实。

source-delta.patch精确等于872815c→43d9f62指定3文件差异（app.ts、README.md、test-provenance.mjs），只显示来源分区与相关测试，无runtime/provider/凭据混入。ui-status-counts.patch精确等于f296f3d到指定UI工作树的两份审查报告差异，仅增加9场景88断言计数说明。未归档大REQUESTS/ROADMAP或整合大patch。

## 安全与历史口径

逐文件阅读并检查credential/token/password/Bearer、环境标识、URL和路径等上下文。出现的是变量名、布尔存在性、null配置ID、Git/文件摘要、测试伪造UUID、公开域名及内部任务路径；未见真实密钥值、代理地址/凭据值、实际环境UUID、邮箱/电话/个人私案内容。日志中的“测试甲/船员”明确虚构，合成img/iframe字符串为安全测试；少量pytest对象内存地址不是凭据或稳定实例标识。公开YANGZE22/JIANGXIN9资料仅路径、摘要和描述，不夹带私人事故数据。

历史readiness曾描述raw-key路径、占位/注入假设和未来步骤；统一页首警告明确旧路径已在498f807禁用、不是当前授权、真实HOLD。不据旧passed日志声称本次重跑；失败/收集错误日志保留。脚本仅归档为文本，不能因保存GitHub就自动执行。

vault READINESS引用的environment-metadata.json、process-presence.json、single-run-plan.json以及其他未选择的disclosure/browser日志不在此归档。应由README明确说明这是有意节选、不能作为完整执行包；缺失附件不能被推定存在或支持当下ready。此限制不要求补入原始环境/进程信息。

## 逐文件核验

所有下列文件均完成来源摘要、归档摘要、大小及内容审查。结论“历史可归档”不等于其脚本可运行或其记录可作当前验收。

| 归档路径 | 字节 | 结论 |
|---|---:|---|
| `evidence/provenance/DEFECTS/EXPERTWORKBENCH_PROVENANCE.md` | 1220 | 来源匹配；历史可归档 |
| `evidence/provenance/logs/EXPERTWORKBENCH-PROVENANCE-IMPLEMENTATION.md` | 1402 | 来源匹配；历史可归档 |
| `evidence/provenance/logs/EXPERTWORKBENCH-PROVENANCE-impl-hashes-frozen.txt` | 1127 | 来源匹配；历史可归档 |
| `evidence/provenance/logs/EXPERTWORKBENCH-PROVENANCE-selftest.txt` | 137 | 来源匹配；历史可归档 |
| `evidence/provenance/tests_acceptance/EXPERTWORKBENCH_PROVENANCE/REPORT.md` | 3457 | 来源匹配；历史可归档 |
| `evidence/provenance/tests_acceptance/EXPERTWORKBENCH_PROVENANCE/hashes.txt` | 445 | 来源匹配；历史可归档 |
| `evidence/provenance/tests_acceptance/EXPERTWORKBENCH_PROVENANCE/independent.mjs` | 9384 | 来源匹配；历史可归档 |
| `evidence/provenance/tests_acceptance/EXPERTWORKBENCH_PROVENANCE/results.txt` | 1166 | 来源匹配；历史可归档 |
| `evidence/provenance/source-delta.patch` | 8993 | 来源匹配；历史可归档 |
| `evidence/report-addenda/ui-status-counts.patch` | 1866 | 来源匹配；历史可归档 |
| `evidence/gap/REVIEW_AND_PLAN.md` | 10522 | 来源匹配；历史可归档 |
| `evidence/gap/PLANNED_RUN_SPEC.json` | 887 | 来源匹配；历史可归档 |
| `evidence/gap/no_egress.py` | 711 | 来源匹配；历史可归档 |
| `evidence/gap/offline-tests.txt` | 2579 | 来源匹配；历史可归档 |
| `evidence/readiness/single-role-pair/READINESS.md` | 3468 | 来源匹配；历史可归档 |
| `evidence/readiness/single-role-pair/input-freeze.json` | 504 | 来源匹配；历史可归档 |
| `evidence/readiness/multiround/READINESS.md` | 5608 | 来源匹配；历史可归档 |
| `evidence/readiness/multiround/HOLD-OWNERSHIP.md` | 579 | 来源匹配；历史可归档 |
| `evidence/readiness/multiround/readiness.json` | 437 | 来源匹配；历史可归档 |
| `evidence/readiness/vault/READINESS.md` | 6665 | 来源匹配；历史可归档 |
| `evidence/integration/REPORT.md` | 7840 | 来源匹配；历史可归档 |
| `evidence/integration/heads.json` | 370 | 来源匹配；历史可归档 |
| `evidence/integration/integration-apply.json` | 3925 | 来源匹配；历史可归档 |
| `evidence/integration/integrated-diff-numstat.txt` | 3392 | 来源匹配；历史可归档 |
| `evidence/integration/cross-regressions-final.txt` | 443 | 来源匹配；历史可归档 |
| `evidence/integration/integrated-service-final.txt` | 261 | 来源匹配；历史可归档 |
| `evidence/integration/integrated-targeted-final.txt` | 341 | 来源匹配；历史可归档 |
| `evidence/integration/main-only-non57.txt` | 261 | 来源匹配；历史可归档 |
| `evidence/integration/main-only-targeted-final.txt` | 2386 | 来源匹配；历史可归档 |
| `evidence/integration/pr56-baseline-build-final.txt` | 691 | 来源匹配；历史可归档 |
| `evidence/integration/filename-independent-ui.txt` | 71 | 来源匹配；历史可归档 |
| `evidence/integration/recommendation-independent-ui.txt` | 50 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/REPORT.md` | 7428 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/dependency-manifest.json` | 5668 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/pr57-manifest.json` | 3729 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/runtime-dependencies.json` | 141 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/reproduce.py` | 1423 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/seven-file-smoke.json` | 252 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/runtime-only-test.txt` | 2802 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/extracted-tests.txt` | 180 | 来源匹配；历史可归档 |
| `evidence/semantic-extraction/reproduced-tests.txt` | 180 | 来源匹配；历史可归档 |

审查绑定MANIFEST原字节SHA256：`f3c4612221fb06e62d4375c2b8172e7c76f40108c28c66535dfd5c074284d202`。文件/清单变更后须重新核对；本报告无远端提交或推送操作。

## 追加根文件审查

已只读审查后补README.md、OMITTED.md、verify_archive.py。两文档明确选择性归档、缺失附件、不重跑历史、旧raw-key禁用/占位假设作废、当前真实HOLD，不把历史成功当新验收；未见敏感值。README所引远端提交未在本审查联网核对，不扩大为远端已保存证明。

verify_archive.py仅本地读取清单与文件、校验归档摘要/大小/历史标记和evidence精确文件集合，并拒绝链接/缓存；未执行归档脚本或调用网络。它不重取原始来源、不是签名认证或敌对工作区沙箱，也不校验顶层任意新增文件；使用assert，应按普通Python（不可-O）运行。当前源摘要核验由本独审另行完成。此工具可作为可信归档树普通完整性检查，不应声称全目录独立来源认证。

三新增文件在此用途下无发布阻断。尚未生成的SHA256SUMS须由父协调者在本报告停止改动后覆盖最终文件（清单本身通常除外），并在提交前再核一次；本审查未推送或执行历史测试。

## 验证器最终修正复核

父协调者随后将全部assert检查替换为显式require(ok)，失败抛出ValueError('archive_integrity_invalid')。独立只读复核确认检查条件与原逻辑一致，无剩余assert，因此上节“必须普通Python、不可-O”的限制已撤销；优化模式不会移除这些完整性检查。父协调者报告普通与-O各41项通过，本补充只做代码复核，未执行历史脚本。其余审查范围、非签名/非顶层精确清单限制不变。本报告至此停止修改，可生成最终SHA256SUMS。
