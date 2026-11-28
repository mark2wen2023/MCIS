# W11 ECFC 本地自动布局候选（Grokbot）

- 基线：`875ccc50b049fb24b82f6b0663f3f9476db1880e`（既有候选编辑器）
- 候选分支：`candidate/w11-ecfc-auto-layout` @ `49bf8a5094e36bce121031070e734e20257d52a4`
- 等价候选：全仓 `git log --all` 未找到 web 端 ECFC 布局实现，新写。
- 依据：ARCHITECTURE §4.9.2；定时规则沿用 `EcfcLayout.cs` 的时间→ID。

## 改动的文件（只此 5 个）
| 文件 | SHA-256 |
|---|---|
| web/src/ecfcDrafts/layout.ts（新，布局模块） | bb0f8c1b8dc5fe52b59f57a3f26bb634a002a84263b5d4df2c31d313fa56201b |
| web/src/ecfcDrafts/Graph.tsx（既有候选界面，加显式按钮） | 6cf912d852e3d8b94271e349618040cf25e688b12f2783a729c3d16651985ba6 |
| web/tests/ecfc-auto-layout.test.tsx（新） | 7934ac9fd8075057a1e80e183438ee38a29f83682e7588a80f0257e1ba3ee2e9 |
| web/tests/run-ecfc-auto-layout.sh（新） | 642a8bbfe9a04769c32562626ba28303825be4ad776696c447ed92d41e7e58a2 |
| web/tests/ecfc-auto-layout.browser.py（新） | ac0b5be1bdd3bce353ede07cd27c5702f87d8f1fb623e1dee4e2b3ddc9e776dc |

未改：Panel.tsx（d41e296a…，同基线）、model.ts、api.ts、main.tsx（主入口不接）、服务、契约、CI、main、三维仓。

## 规则
- 主序列（泳道 0 事件）：全部有时间按时间→ID；否则按序列连线拓扑序，并列时两者都有时间才按时间，否则按输入顺序暂排，并把并列的未定时节点列为“待核”。时间不猜，仍为 null。
- 次序列事件：x 对齐它指向的主事件；没有主目标或对齐位被占，则列为待核。
- 条件：在自身泳道行、离所指节点最近的空位（贪心避让）；没有可定位目标就列为待核。
- 手工位置：模块接受只用于显示的手工坐标表，给定的节点原样保留，不覆写。注意：现有草稿契约没有 manualPosition 字段，本单不改契约，所以界面上没有手工拖动入口；此项只在模块级回归里验证。
- 循环或不合法输入（复用 validateDraft）：返回 invalid，界面显示 alert，保留原示意布局，不算完成。
- 默认仍是原来按输入顺序的示意布局；只有点「自动布局（仅调整显示坐标）」才切换，可点「恢复输入顺序示意布局」切回。

## 命令与实际退出码（在 49bf8a5094e36bce121031070e734e20257d52a4，工作树干净）
1. `sh web/tests/run-ecfc-auto-layout.sh`：exit 0。新增确定性断言 22 条；既有 ecfc-model 82 条照跑，也通过。
2. `web/node_modules/.bin/tsc -b --force`：exit 0。
3. `MCIS_EVIDENCE_DIR=… python web/tests/ecfc-auto-layout.browser.py`（Chrome 156.0.8078.47，chromium_sandbox=True，未用 --no-sandbox）：exit 0。
   - 流程：既有 ecfc-harness 里的真实 EcfcPanel 加载合成已存草稿（API 替身，127.0.0.1），点预览（persisted:false），再点一次自动布局按钮。
   - 请求只有 GET context、GET draft、POST preview 各一次；保存 POST 0 次；外部请求拦截 0 个；页面错误 0 个。
   - 结果：布局前按输入顺序 A,M,Z；布局后按拓扑 Z(160) → M(450) → A(740) 同一行。S 的 x 与 A 相同（740，在下一行）；C1 在 M 上方（450）；节点标题（id、文字、泳道、时间）布局前后完全一致；没有待核项。
   - 截图 01/01b 是布局前，02/02b 是布局后；另有 receipt.json 和 browser.log。
   - 说明：Vite 的 HMR WebSocket 连在同源 127.0.0.1 上，没有外部连接。
4. 另跑了一次 `vite build --outDir /tmp/…`：exit 0（大包体积提示是旧的，产物不入库）。

## 范围声明
数据全部是合成的，零写回，不安装、不合并、不部署，不接真实案卷或 4A。这只是一个子项，不等于 W11 整包。只验证了显示坐标，不涉及因果、专业或法律核验。
