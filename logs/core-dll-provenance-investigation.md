# 历史 mcis-core DLL 来源差异：精确重建已完成

## 结论
成功在**隔离临时副本**中重建出与 W12 seed 记录完全相同的 DLL：
`b0e507b80b41f2d3a5de0dd73adac2b070dd7310e2f9c52b65a6ab44b9b652f3`。
这不是下载到原开发机器上的旧文件，而是基于已记录源码哈希、SDK及路径条件实现的**字节级精确重现**。

**不能把之前失败说成“仅构建元信息误报”。** 已证实有两个因素：
1. W5.1 修改了 CLI glob 编译范围内的 `Domain/Evidence/InvestigationAudit.cs`（新增可选 BatchId、构造器与序列化键）。当前源码不是历史生成工件的源码。
2. 同源构建的 Git revision 信息和绝对编译路径也会改变 DLL 字节。控制实验已验证。

因此 `test_seed_sources_not_stale` 在当前新版 DLL 下失败，是正确检测到生成输入与历史记录不同。测试断言、当前生产源码、当前 `tools/mcis-core/out`、seed/旁注均保持不变；不通过回退当前审计修复来追求全绿。

## 原始证据（固定 c6113bee85d25bf97d805fb2d264fb6ab138b2e2）
- `logs/w3.2-retest-impl-hashes-start.txt` 与 `...-end.txt` 的 Git blob 都是 `1b2f3a3330bdfc2a3c694421a9f49549e24ba399`。记载旧 InvestigationAudit.cs SHA256：
  `ec56cbfe1ae6c81be28e31844fd77462d60c3a67d42d13e68416b7b8e65bbf75`。
- `logs/w5.1-impl-hashes-frozen.txt` blob `e6d62a42e04b5a6ef4f0f6b6e0c0256ebf9c4cdb` 与当前文件相同：
  `07aa67c779169490de2697569519b25fc122bc2473b4a0e31660c1b4c5026d2a`。
- 对当前文件只撤回上述 W5.1 新增块并恢复原 ToJsonLine 注释，旧源码**精确命中** W3.2 已记录 SHA256，不凭近似推断其原貌。
- `tools/mcis-core/McisCore.csproj` 明确 glob 包含 `Domain/Evidence/**/*.cs`。`logs/mcis-core-hashes-2106.txt` 仅冻结 CLI 4个入口、csproj、wrapper，并未覆盖这些被 glob 引入的领域文件。
- 从初始导入 `ddb9dffaa7e2d0e2c7ee82ff28b95c45cd4224d8` 至 c6113bee 的7次后续提交中，未见该 CLI 编译输入变化；初始导入已经包含新审计源码。因此不能仅靠当前Git历史取回旧正文，旧验收哈希是关键证据。

## 控制构建与精确重现
使用真实 SDK **8.0.428**，无 Git 元数据的临时目录，生产文件不变。
- 同一目录、同一56项编译输入，只改 SourceRevisionId：两次 DLL SHA 不同，AssemblyInformationalVersion分别带不同revision。
- 同源无revision，两个不同临时路径：DLL SHA不同。
- 两目录均设置 `PathMap=<临时根>=/workspace/maritime-sim-design`：两次当前源码 DLL 完全相同，SHA为 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`，仍不是历史DLL。
- 仅在临时副本换回已精确核验的旧 InvestigationAudit.cs，并保留原根PathMap、禁用revision后缀：输出**精确命中历史 b0e507…**。
- 最小复现脚本在另一个全新临时目录独立重跑也命中相同历史 SHA，输出验证JSON确认生产 DLL 未变。

完整矩阵见 `core-dll-provenance-evidence.json`；56项当前输入指纹见 `core-dll-provenance-inputs.json`。

## 重现方式
```bash
python tools/provenance/reproduce_historical_core.py \
  --dotnet /path/to/dotnet-8.0.428 \
  --output-dir /tmp/new-mcis-historical-verification
```
输出目录必须是新建、位于仓库外的目录。脚本严格检查 SDK、56项当前编译输入总摘要、当前审计文件SHA、重建旧源SHA及最终DLL SHA；任何条件不符即失败。它不替换仓库运行工件，也不生成或更改分析seed。额外校验已证明篡改当前源码时脚本拒绝恢复。

## 原工件可得性检索
GitHub releases返回空列表；Actions runs返回0；`tools/mcis-core/out/mcis-core.dll` 路径提交历史为空，且`.gitignore`明确忽略core/out。全仓Actions artifacts接口不在当前连接器允许读取列表，不能声称该接口已完整查询；无workflow run可逐次查询工件。未找到已上传原DLL，但上述精确重建已恢复对应字节。

## 后续建议（本调查未实施）
- 将“历史生成工件身份核验”与“当前源码重新生成后的新来源链”明确区分，避免把二者互换。
- 如继续采用当前审计源码生成新的分析seed，应先制定可重现核心构建约定，再正规运行生成器、对全部数值和来源复验并另行冻结。不能只改seed中的hash、删断言或把旧DLL覆盖到新版运行路径。
- 现有2348点独立数值重算全相同是数值证据，不应代替上述来源身份区分。
