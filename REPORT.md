# W12 首次登记接线（隔离宿主）

- 产品底版：`34d6acf1a64fb22d651e3de00fc851952488285e`（再源 309b0cc）
- 复用 8266aba 同一只读事务捕获与同刻核心调用
- 官方：2026-11-27 13:54:34–13:54:39 CST，`timeout 150s`，127.0.0.1:18777，正常沙箱 Chrome，退出 0
- 既有回归：31 项、96 项通过
- 不重跑 34d6acf 曲线隔离包。不是 W12 整包，不是同案换版，不是 W21。

## 已验

修正：图区按 `metricProvenance` 区分真实核心与装配占位，占位不得自称核心；公共 `EChart` 不再默认挂出 `data-testid` / `__echartsOption` / `__echartsInstance`。隔离装配用 `echarts.getInstanceByDom` 读 option。

隔离宿主：现有 track-imports 首次保存两艘合成船；`WRITE_LOCK`+`BEGIN IMMEDIATE` 同一事务读回两份回执与点数组；仅同刻有出处样本调用官方 mcis-core（DLL SHA-256 `f94197777acc45d7ff4e84f265ded9d43c32e773c17cac462d952574d77ac9cf`，两次一致，coreVersion=mcis-core/0.1.0）：
- T+10：distanceNm=2.578139，dcpaNm=1.82261，tcpaMin=7.736156，Safe
- T+20：distanceNm=2.147531，dcpaNm=1.881462，tcpaMin=4.392701，Safe
- T+0/15/30/40：无同刻样本，图上为 null，不回填

图上数值与读回回执/指纹一致；缺回执视图显示 `missing-receipt:SYN-TGT`，无核心数值，无离线种子 9.999 泄漏，无画布。缺口元数据未接（登记 CSV 无授权显式缺口字段，不从步长猜）。

正式 `GET /analysis` 仍读离线种子，本轮未改正式存储、写入或契约，不绕过 W10.2。

## 未验

正式分析入口接到已登记输入；同案换版；W21；真实案；授权缺口元数据下的断段；W12 整包。
