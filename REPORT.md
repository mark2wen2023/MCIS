# W15 AcciMap 隔离本地 SVG 导出报告（Grokbot）

时间：2026-11-28 16:51 Asia/Shanghai（CST, UTC+8）
派遣：#106 comment 7236486490
已接：#106 comment 7236805539（2026-11-28 16:46 Asia/Shanghai）

先搜现成 AcciMap SVG 实现或回执：没有可复用的正式导出。已过的 Bow-tie SVG / 网页预览与 9/9 核心不在本项范围，未重跑。现有六层合成草图组件（产品钉 `2447b14`）能渲染内嵌 SVG 并保留「待核验／证据状态未知／均非已证实因果」，但组件本身无下载。本项只在独立候选上新增隔离工具与独立导出模块，用该草图做一次本地真下载，未把预览接口改成正式导出，未接病例读取、身份、契约或外网。

## 验收候选与产品核对

- 候选分支：`candidate/w15-accimap-svg-export` @ `0a9707f312b348aa81a911bd7536534ed2d09e4a`（2026-11-28 16:51:01 +0800）。基于产品 `2447b14076bbf39db014b8bf4a3a3b350cbf0e05`，仅新增 `tests_acceptance/w15-accimap-svg-export/`。
- 产品组件 `web/src/accimapPreview/Diagram.tsx` SHA-256 `d6f67ba6d80b19b7a1c212a02ee6ac0bfc7903f6d067affd2acba4e6210c875f`，与既有草图钉一致；跑后摘要未变，未改 main、CI、服务权限、试用版或三维仓。
- 独立导出模块：`tests_acceptance/w15-accimap-svg-export/svgExport.ts` SHA-256 `f2c219c36f1e2daf0c9ac816378dbee2d4128140162af72c78345ebc4576540c`。

## 官方运行结果

命令：

```
timeout --signal=TERM --kill-after=10s 150s /workspace/w17-pyplaywright-venv/bin/python \
  tests_acceptance/w15-accimap-svg-export/run.py \
  --source /workspace/mcis-w15-accimap-svg-cand \
  --node-modules /workspace/mcis-w17-871db66/web/node_modules \
  --chrome /opt/google/chrome/google-chrome \
  --out /workspace/mcis-w15-accimap-svg-report/accept-out
```

正常沙箱 Chrome 156.0.8078.47，`chromium_sandbox=True`，未用 `--no-sandbox`；页面只走 127.0.0.1。未安装、未手发信号。退出码 **0**。`receipt.passed=true`。无 pageerror，无外网请求。

- 真浏览器点击「下载 SVG」，下载名为 `accimap-synthetic-draft.svg`（8393 bytes）。
- 制品 SHA-256 `9b358a77003e4cf4bda2ab61c34df0a319c5b8f9624faae3dcc9b6c8ecf57f4b`。
- 文件可独立打开（根元素 `svg`，命名空间 `http://www.w3.org/2000/svg`）。
- 中文六层均可核对：政府与法规、监管、公司、船舶管理、船员行为、设备与环境。
- 标识保留：待核验、证据状态未知、均非已证实因果（沿用现有草图用语；未改组件文案）。
- 完整节点 ID 与中文长名称均在制品中可核对（含节点标题，不截断丢失）。
- 边类型未混：实线输入关系 2 条，虚线输入信息流 1 条。

截图：

- `w15-accimap-svg-page.png` 1440×1106（全页，含下载按钮与草图），147072 bytes，SHA-256 `49bc5deeea2179fa6e93984754eb0d59b35fa9c88b3aea69dbb94ab0f207e524`
- `w15-accimap-svg-opened.png` 1440×900（浏览器直接打开已下载 SVG），91688 bytes，SHA-256 `084997bc1f3af10cbd89559199e31ab3aadae93c6f55444d508ced9b36db5290`

已验：隔离合成草图的一次本地真下载、文件可打开、中文标签与六层、信息流与关系边不混、未核标识保留。未验：W15 整包、主入口接入、把预览变成正式导出、9/9 核心、Bow-tie 导出、真案及 4A。
