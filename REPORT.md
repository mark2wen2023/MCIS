# W12 已登记可见性与来源（独立小候选）

- 底版：`4f7940e28989fb48d617cc9319b7232ff4959635`（不重跑 3287d0e 数值接线与前两轮）
- 独立小候选 `candidate/w12-registered-visibility`：`c150548c16516f5ad7319e3a00213e5fbe448497`
- 只修可见性与来源，未改核心、契约、存储、换版或 W21
- 官方：2026-11-27 15:01:35–15:01:39 CST，`timeout 150s`，127.0.0.1:18781，正常沙箱 Chrome，退出 0
- 既有回归：31 项、96 项通过
- 不是 W12 整包

## 已验

已登记模式：三条曲线 `showSymbol=true`、`connectNulls=false`、`symbol=circle`、`symbolSize=10`。Chrome 截图可见 T+10 / T+20 孤立点，T+15 无点，线不穿越 null。

默认可读两行表（带单位，`tabIndex=0`，键盘 focus 成功）：
- T+10（08:00:10）：2.578139 nm / 1.822610 nm / 7.736156 min
- T+20（08:00:20）：2.147531 nm / 1.881462 nm / 4.392701 min
- 表内无 T+15，共 2 行

登记视图来源：去掉占位种子自检、种子生成时间和「装配占位」提示；只报两份真实登记回执与官方 mcis-core（DLL SHA-256 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`）。缺回执检查保持：`missing-receipt:SYN-TGT`，无当前分析、无核心数值、无离线种子 9.999 泄漏、无画布。

测试制品 `echarts-getoption.json` 只导出所需字段，ECharts 自带 Infinity 转为 null，JSON 严格可读；未改运行时 option。

## 未验

正式分析入口接到已登记输入；同案换版；W21；真实案；授权缺口元数据下的断段；W12 整包。离线种子模式本轮只确认既有 96 项回归通过，未再单独截图。
