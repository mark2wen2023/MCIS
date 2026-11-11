# GISIS 本地字段对照表（W16.1）

依据：IMO **MSC-MEPC.3/Circ.4/Rev.1**《Revised harmonized reporting procedures – Reports required under SOLAS regulations I/21 and XI-1/6, and MARPOL, articles 8 and 12》，GISIS 海上事故与事件（MCI）模块的填报备忘录。
来源：<https://wwwcdn.imo.org/localresources/en/OurWork/IIIS/Documents/Casualty%20documents/4-Rev-1.pdf>（2026-11-11 下载副本 `logs/w16.1-MSC-MEPC.3-Circ.4-Rev.1.pdf`，sha256 `a0b9ff9dcf855cc453117535d8b6f85a5ca79c3b02c156e8755f16660b338c24`；文本 `logs/w16.1-MSC-MEPC.3-Circ.4-Rev.1.txt`）。

## 约定
- **条目写法**：通函附件按附录编号。附录 1 分三组，每组各自从 .1 编号，所以写成“附录1·一般信息 .1”“附录1·一般事故数据 .2”；附录 2 用分组号加条目号，写成“附录2 1.1”（1 船舶资料 / 2 航次数据 / 3 事故数据 / 4 后果）。
- **必填**：以通函条目号后的星号（*）为准。通函第 7 段：初期至少填完附录 1、2 的星号字段，附录 3 的后果数据尽量填。
- **对应程度**：完全对应 / 部分对应（含义或取值形式不同，表中写明差异）/ 无对应（本地字段，通函没有）/ **待核**（不能从通函原文确认，不得自拟）。
- 本系统只做本地准备，**不提交 IMO GISIS**；缺值导出为 null 并标“缺数据”。

## 一、本地字段逐条对照

| 本地字段 id | 中文 / English | 通函条目 | 通函原文 | 通函必填 | 本地必填 | 对应程度与差异 |
|---|---|---|---|---|---|---|
| `investigatingState` | 调查国 / Marine safety investigating State | 附录1·一般信息 .1* | Marine safety investigating State（See table 1） | 是 | 是 | 部分对应：通函取值为 Table 1“As per GISIS nomenclatures”，本地为自由文本；与 GISIS 名录的对照**待核** |
| `numberOfShips`（W16.1 新增） | 涉事船舶数 / Number of ships involved | 附录1·一般信息 .2* | Number of ships involved（Number） | 是 | 是 | 完全对应：取案件船舶登记数，没有船舶资料时为缺数据 |
| `incidentTimeUtc` | 事故日期时间（UTC）/ Occurrence date and time (UTC) | 附录1·一般事故数据 .2* / .3* | Date / Time of initial marine casualty or marine incident (local) | 是 | 是 | 部分对应：通函要求**当地**日期和时间分两栏，本地为一个 UTC 时间；换算成当地时间所需的时区来源**待核** |
| `latitude` | 纬度 / Latitude | 附录1·一般事故数据 .4* | Position … – latitude（Numbers） | 是 | 是 | 完全对应（十进制度；GISIS 录入格式**待核**） |
| `longitude` | 经度 / Longitude | 附录1·一般事故数据 .5* | Position … – longitude（Numbers） | 是 | 是 | 完全对应（同上，录入格式**待核**） |
| `locationCategory`（W16.1 新增） | 事发水域类型 / Location of initial casualty | 附录1·一般事故数据 .6* | Location of initial marine casualty or marine incident（See table 3） | 是 | 是 | 完全对应：取值按 Table 3（At berth … Offshore installation）；案件没有该字段时显示缺数据，不从文字描述推断 |
| `eventType` | 事件类型 / Occurrence type | 附录1·一般事故数据 .7*（总体）；附录2 3.1（每船，非必填） | Overall occurrence designated casualty event（See table 4） | 是（附录1） | 是 | 部分对应：Table 4 为两级取值（如 Collision → with other ship / with multiple ships / own ship not under way），本地只有一级；二级取值**待核** |
| `severity` | 事故严重程度 / Casualty severity | 附录1·一般事故数据 .8*；附录2 3.2* | Overall occurrence severity / Casualty event severity（See table 5） | 是 | 是 | 部分对应：Table 5 只有三档 Very serious marine casualty / Marine casualty / Marine incident。W16.1 起按 Table 5 取值：VerySerious→.1，MarineIncident→.3；本地 Serious / LessSerious 对应哪一档**待核**，遇到时输出缺数据，不自动归档 |
| `imoNumber` | IMO 船舶识别号 / IMO number | 附录2 1.1* | IMO number（Number/Auto） | 是 | 是 | 完全对应 |
| `name` | 船名 / Name of ship | 附录2 1.2* | Name of ship（Text/Auto） | 是 | 是 | 完全对应 |
| `flagState` | 船旗国 / Flag State | 附录2 1.5* | Flag State（Auto） | 是 | 是 | 完全对应（GISIS 自动带出；本地取船舶资料） |
| `vesselType` | 船舶类型 / Type of ship | 附录2 1.6* | Type of ship（drop list to include high speed craft）（Auto） | 是 | 是 | 部分对应：本地是船型代码，与 GISIS 下拉表的对照**待核** |
| `grossTonnage` | 总吨 / Gross tonnage | 附录2 1.7 | Gross tonnage（Auto） | 否 | 否（W16.1 起） | 完全对应；不得用排水量代替 |
| `deaths` | 死亡人数 / Fatalities | 附录2 4.1–4.3 | Number of dead or missing crew / passengers / other persons | 否 | 否（W16.1 起） | 部分对应：通函把死亡和失踪合在一栏、按船员/旅客/其他分三栏，本地只分死亡、失踪两个合计数 |
| `missingPersons` | 失踪人数 / Missing persons | 附录2 4.1–4.3 | 同上 | 否 | 否（W16.1 起） | 部分对应：同上 |
| `injuries` | 受伤人数 / Injured persons | 附录2 4.4–4.6 | Number of crew / passengers / other persons seriously injured | 否 | 否（W16.1 起） | 部分对应：通函只计**重伤**并分三栏；本地“受伤”是否等同重伤**待核** |
| `shipLoss` | 船舶灭失 / Total loss of ship | 附录2 4.7 | Total loss of ship（Y/N/U） | 否 | 否（W16.1 起） | 部分对应：通函为 是/否/不明 三值，本地为布尔，缺值时输出 null |
| `pollution` | 是否污染 / Pollution occurred | 附录2 4.12–4.15 | Ship pollution – oil cargo / oil bunkers / chemicals in bulk / packaged DG（Table 13/15/14，类型与数量） | 否 | 否（W16.1 起） | 部分对应：通函按污染物种类填类型和数量，没有“是否污染”这一栏；本地布尔仅作摘要 |
| `pollutionDetails` | 污染说明 / Pollution details | 附录2 4.11–4.15 | Third party damage（Text）及上述污染条目 | 否 | 否 | 部分对应：自由文本，不能代替按表填报 |
| `reportStatus` | 报告状态 / Report status | — | — | — | 否（W16.1 起） | 无对应：本地字段，用来标注草稿、初步、最终 |

## 二、通函星号字段中本地仍未覆盖的
| 通函条目 | 原文 | 说明 |
|---|---|---|
| 附录2 3.2* 的每船取值 | Casualty event severity（每船） | 本地 `severity` 只按案件取一个值，每船分别取值**待核** |
| 附录 3 / 附录 4 | Casualty analysis data / Supplementary information | 通函第 7 段只要求“尽量填”，本包不做 |

## 三、不确定事项（待核，交架构师）
1. Table 1 国家名录、Table 4 二级取值、船型下拉表：需要 GISIS 平台的实际取值表，通函本身只写 “As per GISIS nomenclatures” 或 “Auto”。
2. 本地严重程度 Serious / LessSerious 与 Table 5 的对应。
3. 当地时间换算用的时区来源（案件字段还是事发位置）。
4. “受伤”与 “seriously injured” 是否一致。
