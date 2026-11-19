# 取证阶段图音缺项说明（开发侧限定验证）

基线55ae5677ce75ee7611d2dc7d1c7f7dde38dc803f。当前Git树没有service/mcis_service/image_review、audio_review及media_review_demo；web EvidencePage使用EvidenceIntakePanel，其API只有原件预览/登记/回执/下载，不是图音机器结果导入或人工修订。只读参考独立媒体76d6c22页面，它们未解析URLSearchParams的case/run，不能靠拼URL接成本工作台入口；未合入该候选。

用户在取证阶段看到明确“图音核对尚未接入本工作台”，说明文件登记不等于核对修订、如何选择证据后进入现有“查看登记原件”，并保留权限、策略、完整性及报告未闭环边界。无新按钮、链接、API、保存动作或完成标记。无明确案号及其他阶段不显示此提示，避免旧案残留。

先追加合成SSR断言运行旧组件，因缺少该提示失败；最小5行组件修改后通过。新增测试覆盖四个取证子页、空/重复案号、切案、非取证路径、不产生虚构图音链接。下列命令本轮通过（web目录，复用现有离线依赖，无安装）：

```bash
node tests/run-case-workspace-flow.cjs
node tests/report-explicit-case.test.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

Vite8.3.8，774模块，原>1500kB警告保留。SSR/内存hooks不是浏览器或真实React并发；未调用HTTP、App、DB、ORM、模型、权限实测或暂停测试。未读取媒体/案例/seed/凭据；原件回执与错误逻辑未改亦未实跑。图音结果导入→保存修订→重开仍需受控后端与同案/运行绑定接线，不因文案完成而成为可用能力。无合并或部署。
