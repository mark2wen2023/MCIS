# W8.3 案件包预检 / 导出 UI 验证

基线 main `27f4825fae2d6470ef15b7617e49a089447bd903`。本切片只改变 Web，复用既有服务。

## 依据与交付
- 原型大厅 `.mcase` 入口 + 分析页导出；ARCHITECTURE §11 / R-03 原始证据完整性；contracts §4.1 清单 SHA-256 判定。
- 大厅选择本地文件后主动上传预检；显示清单案件ID、生成器/时间、缺失/哈希不符/额外文件。
- 按每个真实案件卡片下载完整 `.mcase`，不硬编码演示案；API错误/非ZIP/空文件不下载。
- 调查组身份门控、同次请求防重、文件替换/关闭/身份/导航取消、迟到响应隔离、对象URL释放。
- 不新增假数据。独立验收使用已有明确标注的虚构 Lily/Mary 案件，生产UI只显示真实服务响应。

## 实现方验证
- `bash tests/run-package-w83.sh`: 53断言（模型、HTTP适配器、静态渲染，非浏览器）。
- 全部现有前端脚本 + 大厅/上下文/联动脚本: 666旧断言 + 53新断言 = 719通过。日志 `w83-regression.log`。
- `npx tsc -b --force`、`npm run build`: 通过。Vite保留大bundle警告，未放宽阈值。
- `oxlint src`: 退出0；11既有警告 + 1新增有意清洗下载文件名控制字符的no-control-regex警告。日志 `w83-source-lint.log`。
- 最初W12测试因未物化seed及两个历史W14 dump失败；补齐相同基线输入后原断言全部通过，未改测试。
- 8项实现冻结 `w83-impl-hashes-frozen.txt`；旧W8.2的Lobby漂移已在REQUESTS登记，不改旧冻结。

## 范围边界
- 预检不是导入，也不证明数据真实性、JSON语义、审计链完整、导入可成功或事故责任。
- 服务端ZIP资源预算与导入文件非原子回滚问题仍在。界面100MiB限制不是服务端防护，明确只处理可信来源包。
- 服务权限/认证未变，仍仅适合本机单用户演示；不宣称正式部署安全。
- Unity互通、完整W8、全项目/Unity验收、部署未做。

独立验收与最终集成记录见后续追加。

## D01与W9整合返修
- 独立真浏览器发现快速『进入案件→Back』可能在React提交卸载前返回，旧预检结果迟到显示。原失败证据保留，未用等待卸载掩盖。
- 包内新增导航意图捕获（同文档anchor click、popstate/hashchange/pagehide），同步中止请求，折叠预检面板并清导出状态；不patch全局history/router。旧8项v1冻结保留，新9项冻结匹配。
- D01后完整719前端断言、tsc/build/lint退出0。
- W9 PR #10合并后基于 `e8db196982d633579de38bca65ed2cd36d96becc` 整合其caseContext/main/routes/ShipsPage/vessels以及服务cases/router与合同，未覆盖W9改动；W8.3冻结文件不变。
- 整合后803前端断言（原719 + W9现有84）通过，tsc/build/source lint退出0。首次W9脚本误用CJS不支持top-level await，再试ESM内联依赖触发Node动态require限制；最终使用ESM + packages=external跑原测试成功，未修改测试。日志 `w83-w91-integrated-regression.log` + `w83-w91-integrated-final.log`。

## 最终独立验收
`tests_acceptance/W83/REVIEW.md`：真实HTTP14/14；真实Chromium32通过 + 1既有390px共享壳KnownDefect；独立mock生命周期28/28；9项冻结匹配。1440×900和1920×1080通过，390px页面宽732px，隐藏本包元素后仍732，未宣称移动端通过。D01原快速Back、正常Back/Forward及迟到导出测试保留并通过。78个服务Python源文件与整合main逐字节一致；服务无生产改动。没有重跑全量服务/Unity验收。
