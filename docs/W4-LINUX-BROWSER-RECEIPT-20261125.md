# W4 合成 PDF 预览：Linux 实跑与独立复核

**结论：W4 的合成 PDF 预览浏览器子关口通过。整个 W4 不销项，甘特图整体验收仍 10/22。**

- Grokbot 实跑：[验收脚本固定提交 `3ae5166b7522f63bf39827a02341c856e394a0c9`](https://github.com/mark2wen2023/MCIS/blob/3ae5166b7522f63bf39827a02341c856e394a0c9/tests_acceptance/w4-synthetic-pdf-live/README.md)，固定产品 `67654fd9801735dfe81361caf5e6f0148ab5e7da`。Linux 非 root，Google Chrome 156.0.8078.47，沙箱开启；脚本基础 HTTP/浏览器退出 0，额外重复实跑 3 次各退出 0。仅合成数据，真实回环服务、Poppler、临时 SQLite。
- 1440×900 与 390×844 各自扩展实跑退出 0。红派生页、蓝登记页显示正确；服务端延后真实响应，切案／切轮 A→B→A、延迟旧 PNG 与清除预览都没有让旧回调覆盖当前结果。各有 10 条 Access（PDF 6、PNG 4），对应各自 10 次受控读取；迟到但真正读过的请求照样留 Access。外网请求和 OCR 写入均为 0。
- Dot 复核的是 Grokbot 的原始附件，不是再宣称自己跑了一次浏览器：包 `mcis-w4-report.tar.gz` 87909 字节，SHA-256 `1622ed848e5f66ad34e9e98e71764e092fc5291a343a9c10a880e40caba508bb`；核对运行日志、逐行审计及两视口共 14 张画布截图的中心像素，并目视抽看两张视口截图。原包留在授权附件，不复制到仓库。
- 剩余：两视口各一条未追源的控制台 404，不称零控制台报错；窄屏长摘要在截图边缘截断，属界面待修；未验真触屏、Firefox/WebKit、真实案卷、正式身份、归档与工作台集成。示例路径 `/usr/bin/chromium` 在该机器不存在，实际成功用 `/opt/google/chrome/google-chrome`；不将这台机器的路径问题归因到其他环境。

W17 与 W4 独立：浏览器从 `29cbfe255967fc6814abafd919ed9a7485ef8710`，真实 HTTP/SQLite 登记收据验收从 `a80226d7e32d79ce8ab7a035a16e5089bfbac377`。不能沿用 W4 `3ae5166` 的提交。见[三方交接书](./HANDOFF-THREE-AGENTS-20261125.md)。
