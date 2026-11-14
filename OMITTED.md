# 选择性归档：仍保留本地的内容

本次没有删除或覆盖任何源目录。未上传项不被视为已经保全。

- mcis-personal-vault-readiness-20261114/environment-metadata.json、process-presence.json：属于运行环境快照，排除；公开结论仅在历史报告中保留，没有环境实例标识或变量值。
- 各readiness目录的disclosure.json、较大input-freeze.json、single-run-plan.json及旧SHA256SUMS：旧版本的重复配置/冻结材料，不是可执行批准。保留代表性准备/HOLD报告及单次简要冻结，其他原件仍在云端。旧报告对未选文件的引用仅说明原目录，不保证归档包含它们。
- mcis-integration-evidence/REQUESTS.md.*、ROADMAP.md.*：重复大快照与共享历史；pr57/58/61/64/67.patch：完整增量已关联远端提交，归档保留heads.json和审查/测试，不重复上传全部应用代码。
- integration原始浏览器启动命令/诊断、安装/克隆日志及早期重复测试输出：避免不必要运行环境细节；保留审查报告的沙箱失败说明、关键基线失败和最终结果，不伪称浏览器通过。
- mcis-semantic-extraction-evidence/runtime-seven/、seven-file-review.html、pr57.patch：生成/重复源码，既有远端eb65de4候选及归档清单可定位；不携带缓存或生成页。
- mcis-integration-audit-20261114、mcis-main-patch-probe-20261114、mcis-semantic-extraction-probe-20261114及reproduce/build-baseline目录中的混合未提交试验文件：没有把这些工作树当完整验收候选上传；相关结论、精确来源清单和选定日志已归档。
- 所有__pycache__、.venv、node_modules、构建输出、/tmp临时页面/回执及本机依赖：不归档；必要依赖应按原项目版本另行准备。
- 43d9f629原提交对象及共同REQUESTS/ROADMAP历史未直接推送。其独审附件与三文件来源展示增量已选择性保存；原提交hash不会成为本单提交归档的祖先。

未发现选中文件含真实密钥、私案材料或个人敏感内容。没有因无法判断而擅自上传的文件；未选项的完整性/安全性不由此次归档保证。
