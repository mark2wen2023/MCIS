# 校验清单

- [x] 仅新增 tests_acceptance/w4-manual-anchor-sample-clock/
- [x] 未改 CLI/产品/核心；相对钉 94d5e38 仅上述目录
- [x] 未改 candidate/w4-manual-anchor-core @ 3c40859
- [x] 夹具自 3c40859 复制且字节哈希一致
- [x] SDK 8.0.428 预检；nuget locals 预检；unshare -r -n 离线
- [x] 无 PackageReference；离线 restore（源已 clear）+ build --no-restore；未安装、未接外部源
- [x] 官方外层 150s 有界超时，退出 0
- [x] 直接读核心校准后时间线，cliUsed=false，未以三组 CLI 替代
- [x] 有锚：基准不移，快源 -12 s，数量/顺序/来源/观测值未改
- [x] 去锚：原时刻不动，状态 Uncalibrated，timeline_no_reference
- [x] 保留原始逐点 JSON、退出码、工具版本、可复跑命令、源码/二进制指纹、SHA256SUMS
- [x] 只合成；不接服务/浏览器、不写回、不碰其他分支/真实案卷/CI/合并/部署
- [x] 不把本子项通过说成 W4 整包通过
- [ ] 令牌扫描、候选与证据分支推送、#106 待复核、表第 41 行：打包时补记
