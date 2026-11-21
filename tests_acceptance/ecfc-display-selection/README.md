# W11 节点与边独立出处：只读展示选择工装

基于 2a1af988df07ebde97336829fe361188b05c9146，固定原节点 check/display 文件逐字节核对。只新增 tests_acceptance 文件，不改 ECFC V1、任何研究源码、产品、权限、存储、路由或三维。

## 本轮新增范围

`selection.py` 是手写的纯内存展示选择实验，不是正式关联合同、输入安全解析器或授权服务。宿主供应经原 parseEnvelope 验证的合成图，关联也由工装显式构造。边选择绑定 caseId、revision、digest、edge ID 和 from/to；generation 仅是本地失效序号，不是凭据。选择变化立即清空，旧成功/失败完成不更新当前值，删边不给展示。

节点正例调用原 `display()`，输入来自原工装真实临时 SQLite 登记/Access/精确原字节投影；再仅投影允许的展示字段。保留17秒手工节点时间，原件来源UTC另列，不推导事件UTC。原标签“原始位置记录，非事件发生证据”、推定状态不变。

边另用独立纯合成片段定位 `/fragments/0`，源记载UTC为 `2026-02-01T12:00:37.000Z`。该片段和映射没有经过登记、权限或持久化，不能冒称可信原件。只演练选择展示；不把节点 `/points/7` 或其UTC借给连线。边保持待审、证据方向未判定，replayUtc=null、seekAvailable=false。两种展示的不确定度都为null，不造精度或审核；不输出内部pin/摘要。

## 复跑（既有依赖，不安装）

在候选根目录：

```sh
MCIS_ESBUILD=/absolute/existing/web/node_modules/.bin/esbuild \
  /absolute/existing/service/.venv/bin/python -I -B tests_acceptance/ecfc-display-selection/check.py
MCIS_ESBUILD=/absolute/existing/web/node_modules/.bin/esbuild \
  /absolute/existing/service/.venv/bin/python -I -B research/ecfc_associated_position/check.py
```

缺固定Git对象/依赖即失败，不自动获取。沿原工装的固定生产源码和2048c60合成JSON。临时库/文件自动清理；Ctx、案件行和ECFC保存标记仍是原合成工装，不是真实登录或ECFC保存。

新入口6项通过：3既有业务+3新增选择检查；原入口另6项通过（重叠不累计）。新增节点正例恰好一次双船读，2 Register+2 Access；边投影/选择零读写，两项生命周期检查仅原准备的2 Register，无Access。检查包含不同图版本同edge ID、迟到成功/失败、删边、端点变化、片段版本/案件/定位不符；原入口继续验证缺轨/无点、错案/原字节失配及拒绝读取。未构造新增权限。

没有浏览器、Promise调度/React生命周期或真实UI；迟到由手动完成顺序演练，不冒称实机异步。没有服务、模型、报告或归档。首个产品前置仍为可信边关联来源及其读取/失效合同，本工装不补足它，不接线、不开放、不部署。
