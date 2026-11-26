# W4.1 离线构建后接跑原 ce08e1d 验收报告（Grokbot）

时间：2026-11-26 17:51 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7188428763
已接：#106 comment 7188509565（2026-11-26 17:48 Asia/Shanghai）

本项是临时预览初验，不是正式带锚校时、回写、迟到响应或 W4 整包。不把范围内结果报成整包通过。未改产品、未安装、未联网拉依赖、未合并、未改 CI/main、未部署。未使用来历不明的 `7afd120c…` DLL，也未使用 W15 Bow-tie DLL。

## 第一步：离线确定性构建 — 退出码 0

隔离：`unshare -r -n`，仅 `lo`（UP），无默认路由；`nuget.org` / `api.nuget.org` 均不可解析。HOME=/home/box（已初始化登录 HOME），未虚构 `DOTNET_CLI_HOME`，未跳过 `dotnet nuget locals all --list` 与 `dotnet --version`。干净 Git 导出 `94d5e38c926fda232bb987b60fa9145e4bcf01a7` 到 `/workspace/mcis-w41-src-94d5e38`；空产物目录 `/workspace/mcis-w41-core-out`。导出中无 `tools/mcis-core/bin`。官方 recipe：导出内 `tools/mcis-core/build_reproducible.py`。构建 0 Warning / 0 Error，约 3.62s。

### 构建清单

- SDK：8.0.428（`/home/box/.dotnet/dotnet`）
- recipe SHA-256：`4dbeb66ddb73dead6a91e227a2f88381437beb20d5f4d68719a156bfb584e96b`（与派遣要求全量一致）
- 编译输入：56 个，完整 SHA-256 如下（亦见 `artifacts/build-manifest.json`）：

 1. `48c84a1a6f2ee4f580e04bd9cc59189023b054303e7a2603a41aab0c55d6fa75`  `tools/mcis-core/McisCore.csproj`
 2. `4ce13b7fec0898f01d3157b99278561a1ea391d0f4ce3140c1bc9f79fda99b58`  `tools/mcis-core/src/AlignCommand.cs`
 3. `8f2deb399ef80d42cd7fcc355ea8ec507f417635e43cdb57e41dc3a201ef954a`  `tools/mcis-core/src/ColregCommand.cs`
 4. `54de148e91e27a4ca39c693410722e42caf88fcb58e339dc3907161dc9210d6c`  `tools/mcis-core/src/CpaCommand.cs`
 5. `2b348aee19982b7b6db4556cdd7e4ba311c7d77b3ebfaba9e096e1985b6fab1f`  `tools/mcis-core/src/Program.cs`
 6. `15f9b52af048291c69e4a0ebd9959e679414c9abe67c02daf35ad7b6c9c73145`  `unity/Assets/_Project/Scripts/Core/Primitives/Result.cs`
 7. `b5bad3e00608549ee6a3d99616c32a26e0ae0d7d051c1c76540f7c165e09de3d`  `unity/Assets/_Project/Scripts/Core/Primitives/SimTime.cs`
 8. `e384263c781a33394528de846e3ba225d682488abf3ef559e02afb19643dee40`  `unity/Assets/_Project/Scripts/Data/Vdr/ManualAnchorCsvImporter.cs`
 9. `56714f018e4bb5ded012065a0098de08eb9600fbf58e2f93a4ec19560f409312`  `unity/Assets/_Project/Scripts/Data/Vdr/NmeaParser.cs`
10. `fbdcec3c8956d7d55b13f99c6ec5c0227aa87c23272df6176c9ca6a95ccbb4ce`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrCsvImporter.cs`
11. `6846eb8bec94833ad2fc0d567e2358b20dee76a5965bf1e60b5b15e5d84acb08`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrCsvMapping.cs`
12. `9942716682b86f9ad34fd2c9a22c0fa17f319c99b64fc48855411cf829761cf4`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrImporter.cs`
13. `626508816982baea3792147fb40f7ebb6212248f3ae83386ebc17dc9200a8b40`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrMediaManifestImporter.cs`
14. `2b08c83fe0f633887dd4adf5494af77e194aa49a72608fceee6a8dd06c2d5742`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrNmeaImporter.cs`
15. `7704ec0c1b5e17343fedf067f422390b21d7371de1805e95a6cdffe5f9d6d01c`  `unity/Assets/_Project/Scripts/Data/Vdr/VdrOptions.cs`
16. `63cc794942033c6aba76bb5b5196682dcfe5c92443e19504adf43d1645ddf30a`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregEncounterState.cs`
17. `50a9f68cd654d06d3e76e32ad5320736d8060b2ab4613d4edc5b346275504df3`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregEngine.cs`
18. `cd0ee6c4a0ded2e974ca4998264c149c77a430a958a51447c4b6e02c945b9e53`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregEvaluator.cs`
19. `847b6c70a64eb7dd58f378fc2abb62c5cefdfd7694aaa99fc4e7ad8148e04c2e`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregIds.cs`
20. `2adaedf93969718e549d7f9f09af6e89654fa6dd8693e57910dba59a6a7bad2c`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregModels.cs`
21. `654b424b5d6325ae3f5f75191a6647e4ca1f4f87ef6d50306784d42ee058df65`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregRules.cs`
22. `456665831ad4c3fd73129867ca8e52c234870da9433d5d00110a2be17a935b83`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregThresholds.cs`
23. `4a2d8ae9fc968c1f4004528cb1a26cf8225e8e2d91ac1385a64f4d108a588c32`  `unity/Assets/_Project/Scripts/Domain/Colreg/ColregW11Api.cs`
24. `648c7fb959dd442345925e2bdee153766b8227485aac5fd9b48db8271164deb8`  `unity/Assets/_Project/Scripts/Domain/Common/EcfcAndDamageEnums.cs`
25. `150ac2f316e4b27270cccdf35d6787fd7ed948503710e1e89cbea5bafb2122f2`  `unity/Assets/_Project/Scripts/Domain/Common/EnuAndEnums.cs`
26. `dc2c117170a16df866fb5b372a89cbac2d528edbd5587dfff1e9b34ce7b1e204`  `unity/Assets/_Project/Scripts/Domain/Common/GeoPrimitives.cs`
27. `25dafae8117a8ba092166187ca8b49b3573103746529bb5000f33815173ed2ce`  `unity/Assets/_Project/Scripts/Domain/Cpa/CpaCalculator.cs`
28. `efea454b7ef27bcb4c16f802088ece4eb07d482077a7abc294e19e651703da2d`  `unity/Assets/_Project/Scripts/Domain/Cpa/CpaCalculatorTriangle.cs`
29. `293e4c38d4c6edfe1a130b58a45cc849f633aae22c7f0a74ffa94f6346e03192`  `unity/Assets/_Project/Scripts/Domain/Cpa/CpaModels.cs`
30. `ffe7a06d86ec2d698cf23e61484d1e0117eebdaea9fc41a3cc9ea4fc585b7f26`  `unity/Assets/_Project/Scripts/Domain/Evidence/CustodyEvent.cs`
31. `618af0e414ed0a70e52a712d9702249512922d3ce08528530927d7020ae837d8`  `unity/Assets/_Project/Scripts/Domain/Evidence/CustodyLedger.cs`
32. `9116d127128155f5d1ebd0491e66a95042989bdbf97c9b687f2577c024813a5c`  `unity/Assets/_Project/Scripts/Domain/Evidence/EvidenceItem.cs`
33. `07aa67c779169490de2697569519b25fc122bc2473b4a0e31660c1b4c5026d2a`  `unity/Assets/_Project/Scripts/Domain/Evidence/InvestigationAudit.cs`
34. `ad9478e84a7b947a16145cfc9407f21aaf14a62b3e99379ae729829015bd93be`  `unity/Assets/_Project/Scripts/Domain/Evidence/Sha256Hex.cs`
35. `de24d691cb1f451f861ffb7846a66c83b3da5e696a5e237ee4a629951c4d8932`  `unity/Assets/_Project/Scripts/Domain/Geo/GeoMath.cs`
36. `12a69085704ebafe67c26fd8500a9253e914f28f24ad1a30bd09afe9e216ccc1`  `unity/Assets/_Project/Scripts/Domain/Geo/IGeoConverter.cs`
37. `823763ae8d7bcbe14509ed712388d3b3938d31765e3a242a60c330d6d5f08839`  `unity/Assets/_Project/Scripts/Domain/Models/CaseMetadata.cs`
38. `36343c3df71fa5086faf386e60f3d1ff9ca5c2b2496c74327957b271745e7703`  `unity/Assets/_Project/Scripts/Domain/Models/CollisionModels.cs`
39. `cfcc4a65e2747f3ab87c988d06eccbd4a1a41c61b4ee22804008bc911194437c`  `unity/Assets/_Project/Scripts/Domain/Models/EcfcModels.cs`
40. `43ff94c07281553876d2a293f2404a27258d1f7b261a3ac2e856a740ddcf50e8`  `unity/Assets/_Project/Scripts/Domain/Models/EnvironmentModels.cs`
41. `4d5b71c59c54e3274a1b898bb52fbdf0422a94b4c6aa2e99246e47986982c501`  `unity/Assets/_Project/Scripts/Domain/Models/TrackAndCpaModels.cs`
42. `31063f18913c178667cfbc55935465b4d2feba1674c5b23925111ae221ca2f89`  `unity/Assets/_Project/Scripts/Domain/Models/VesselAndAisModels.cs`
43. `ef08f8b8f003807976bcb012abdc25af9cd90b4e0a1f4279fac58aa1bab584a8`  `unity/Assets/_Project/Scripts/Domain/Timeline/AngleMath.cs`
44. `bf74750f4b18c08ece4aa292009d6ed7b38762b5793f080ab57d09dea84ec7de`  `unity/Assets/_Project/Scripts/Domain/Timeline/BearingReference.cs`
45. `46b0aae77adf2b429bc1f9025af0072c7002ef3e94d1d55804304aae42fafaf6`  `unity/Assets/_Project/Scripts/Domain/Timeline/Calibration.cs`
46. `706284407173eb98a81efad7d16ee1d5ba0ff7faba3730860ad6b2bdd4ccccc6`  `unity/Assets/_Project/Scripts/Domain/Timeline/ClockOffsets.cs`
47. `40cee8fbbbeabdee09a44ecafe6550f4e97b308cf5069aa22fe53de0eebb9d04`  `unity/Assets/_Project/Scripts/Domain/Timeline/ConflictDetection.cs`
48. `7836036d51e46a17c3213b8bb55f08b1bbbd1e99d6c9d2a1f0037ee524966286`  `unity/Assets/_Project/Scripts/Domain/Timeline/ConflictJson.cs`
49. `6cc0341f0c71077d9313da1ab9838a73333156eaf98675ceb928b4e6cc6ec768`  `unity/Assets/_Project/Scripts/Domain/Timeline/EventMarker.cs`
50. `57c97d05d17887377f1e66c00dece9aecfa5a7b07758a05f7cf0730447691dcc`  `unity/Assets/_Project/Scripts/Domain/Timeline/ManualAnchors.cs`
51. `709660343cbd03fd25484c64e19239b5331b4475a8f93c62a17894377bb48e2c`  `unity/Assets/_Project/Scripts/Domain/Timeline/MediaItem.cs`
52. `10c58629533a3172b1ca910bf39e36cbcd5c5741072ab4a1f175a9bcb07dc0ac`  `unity/Assets/_Project/Scripts/Domain/Timeline/MultiTrackTimeline.cs`
53. `c3938896e99545686aeeaaeb52a4c6ce2c63b2a17de25db195e8723c8bd8979d`  `unity/Assets/_Project/Scripts/Domain/Timeline/TimeRange.cs`
54. `5e63d30e821b21db493a134744174f4375d2edf88a4dfd521d4f997332b3c882`  `unity/Assets/_Project/Scripts/Domain/Timeline/TimelineSample.cs`
55. `89e8607600df698b889b1b0ade6489b4b2be76f39828337a4d65379c2566de4c`  `unity/Assets/_Project/Scripts/Domain/Timeline/Track.cs`
56. `659e989aa9fd4ab1a1ab919fbe854430e20aecc6fa66775628aac72fc93fc8be`  `unity/Assets/_Project/Scripts/Domain/Timeline/TrackKind.cs`

- 产物哈希（文件字节与清单一致）：
  - `mcis-core.dll`：`f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`
  - `mcis-core.runtimeconfig.json`：`3d25821758613e4cd940d143ccb03c93704140077e69104996832510f38f6598`
  - `mcis-core.deps.json`：`fda133109cf9fc926cbda09598ad344f75dc57ec02e345b6923ec5fe2dff9d12`
- 历史交叉参照（完整哈希，非短 SHA）：本次 DLL 与 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf` **完全一致**。
- 箱上来历不明的 `bin/Release/net8.0/mcis-core.dll` 仍为 `7afd120cb343a4459b1f012ea96c5ab8df53c04a4ba58b916dcc20f3d1d88337`，mtime 未变，未读取、未复用。产品树 `tools/mcis-core/out/` 仍不存在。

## 第二步：原 ce08e1d 真 Chrome 合成验收 — 退出码 1

命令：`timeout --signal=TERM --kill-after=10s 150s run.py`（正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；`--core-dll` 为上一步新编 DLL，`--core-sha256` 为上列完整哈希）。Vite 构建成功（2.10s）。服务绑 127.0.0.1。`receipt.json`：`coreDllSha256` 已核对，`sandboxRequested=true`，`passed=false`，范围声明为 synthetic unanchored COG preview only; not W4 whole package。未手发信号。

**第一处失败（即停止）：** 1440 视口、首次 `preview(SYN-W41-X-A)`。`show(A)` 与添加 CSV 源、填写 CSV / UTC时间列名 / 值列名之后，在

`panel.get_by_label("数据类型", exact=True).nth(0).select_option("CourseOverGround")`

处 Playwright `TimeoutError`（30s）：`waiting for locator(".w4-preview").get_by_label("数据类型", exact=True).first`。产品 `AlignPreviewPanel.tsx` 中该控件为 `<label>数据类型<select …>`，选项展示文案为「对地航向（度）」等，value 为 `CourseOverGround`。未改 runner、未改产品、未重试放宽选择器。

因此以下均为 **未验**：390 视口；两视口 Evidence 面板 COG 差值（脚本期望 A=5 deg、B=11 deg，但未读到结果区）；未校准/不入库正文；A→B→A 隔离；SQLite 重开；截图（失败发生在首次截图之前，`accept-out` 无 png）。`sqliteLogicalSha256` 未写出。

## 约束

服务只监听 127.0.0.1；合成案件仅脚本创建路径（本失败发生在创建之后的 UI 步骤，seed 函数只建 SYN-W41-X-A/B，`MCIS_SEED_DEMO=0`）。未打包 NetLog。
