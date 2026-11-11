# 任务：补完 prototype/index.html 第三部分 JS

先阅读 ./BRIEF.md（需求）和 ./thesis.txt 的 2.5、3.4、5.3、5.4 节，然后完整阅读 ./prototype/index.html。
文件末尾 IIFE 内有一行占位注释 `// __MCIS_PART3_PLACEHOLDER__`。用第三部分 JS 替换它，不要重写或删除已有代码。

已知事实（已核对）：
- 路由函数 handleRouteChange() 已定义，切屏时会调用（若存在）：resizeSimCanvas()（#sim）、renderEcfcSvg()（#ecfc）、renderAnalysisScreen()（#analysis）。你必须定义这三个函数（同名、IIFE 作用域内）。
- 前两部分定义了 initLobbyScreen、initCaseScreen、initShipsScreen、initEnvScreen、initTrackScreen，但**目前没有任何地方调用它们，也没有 hashchange 监听和启动代码**。第三部分末尾必须加启动代码：调用全部 init 函数（含你新写的 initSimScreen/initEcfcScreen/initAnalysisScreen），window.addEventListener("hashchange", handleRouteChange)，并调用一次 handleRouteChange()（无 hash 时默认 lobby，看 handleRouteChange 实现确定）。
- 复用 APP_STATE（含 APP_STATE.sim.duration=900 秒、APP_STATE.trackEdit.lilyWaypoints/maryWaypoints）、DEFAULT_LILY_WAYPOINTS/DEFAULT_MARY_WAYPOINTS、showToast、cloneJSON。先 grep 这些定义确认字段结构（航点字段名、坐标单位）。
- 先 grep 出 #screen-sim（约 1772–1948 行）、#screen-ecfc（约 1950–1991 行）、#screen-analysis（约 1993 行起）里所有已有元素 id 与按钮，逐一绑定，不要引用不存在的 id（引用前做空值保护）。已有：sim-canvas、sim-ecfc-popups、sim-scrubber、ecfc-svg、ecfc-selected-badge、ecfc-inspector-body、analysis-chart-canvas 等。

需实现：
1. 主仿真（initSimScreen + resizeSimCanvas + requestAnimationFrame 循环）：canvas 动态海面（波纹/高光/网格）、航道与岸线、Lily 与 Mary 沿航点按时间插值运动、尾迹；时间轴播放/暂停、倍速 0.5x–16x、拖动 sim-scrubber、关键事件标记；HUD 每船经纬度、SOG、COG、HDG，风速风向；DCPA/TCPA 真实公式实时计算：r = P_Mary − P_Lily，v = V_Mary − V_Lily（速度由插值轨迹差分得到），TCPA = −(r·v)/|v|²，DCPA = |r + v·TCPA|，单位海里、分钟；风险分级：DCPA<0.3nm 且 0<TCPA<6min 红色危险；DCPA<1nm 且 0<TCPA<12min 琥珀警告；否则青色安全，HUD 变色。小地图画完整航迹与当前位置。ECFC 卡片按时间到达在 sim-ecfc-popups 弹出（动画）。视角切换（驾驶台/跟随/俯视/自由）真实改变渲染（缩放/旋转/跟随中心/驾驶台透视近似）。碰撞时刻显示碰撞特效，之后 Lily 下沉示意。
2. ECFC 编辑器（initEcfcScreen + renderEcfcSvg）：SVG，严格遵守论文 2.5 节：事件=矩形、条件=椭圆、事件间实线箭头、条件→事件虚线箭头、推定项虚线边框、主序列水平居中且箭头加粗、次序列在上下。节点可点选，ecfc-inspector-body 显示并可编辑文字，ecfc-selected-badge 更新；可新增事件/条件（绑定已有按钮）。
3. 分析与导出（initAnalysisScreen + renderAnalysisScreen）：canvas 自绘两船距离、DCPA、TCPA 随时间曲线（坐标轴、网格、碰撞时刻竖线、悬停游标读数）；碰撞瞬间小窗回放（若有对应元素）；PDF 报告预览（若有容器则填充：案件摘要、关键指标、ECFC 缩略、结论）；导出视频/PDF 按钮显示模拟进度与 toast。
所有演示数据标注“示例数据（虚构）”。风格与现有 CSS 一致。

工作方式（重要，避免网络流超时）：分多次小步编辑，每次写入不超过约 250 行。做法：先把占位符替换为“第3部分-A 代码 + 新占位注释 // __PART3_NEXT__”，然后逐步替换 __PART3_NEXT__，最后一步删除它。每步写完立刻继续下一步。
完成后执行：node -e 抽取 <script> 内容写到 /tmp/p3check.js 并运行 node --check /tmp/p3check.js；有错就修到通过。确认文件中不再含 PLACEHOLDER 和 __PART3_NEXT__。
只允许修改 ./prototype/index.html（以及 /tmp 下的检查文件）。不要联网，不要 git 操作。
