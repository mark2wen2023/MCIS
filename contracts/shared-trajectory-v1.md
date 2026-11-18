# MCIS-SHARED-TRAJECTORY-1：二维／未来三维共享轨迹输入（独立候选）

## 范围与接线
JSON Schema：`schemas/shared-trajectory-v1.schema.json`；参考语义校验器：`service/mcis_service/trajectory_exchange/validation.py`。这是新、未接生产的交换契约，不替换既有 `track-point.schema.json`、W10.2 CSV输入、C# TrackSample 或数据库。没有API、Unity实现、网页适配、3D Tiles、动力学、服务端渲染或真实AIS/LLM验收。JSON可供不同语言实现消费；未来适配器必须显式映射并复验，不能把当前简化航迹字段机械套入本合同。现有权限检查不变；读取来源/构建输入仍须通过原有服务端权限，校验器不提供授权或身份认证。

一个文档对应一个案件、一艘船、多条来源记录；多船复盘在外层逐船校验后按对齐UTC组合。caseId/vesselId是调用者提供的稳定关联键，不自动由船名猜身份。identityStatus仅`unresolved`或`operator_asserted`，后者也只是操作者声明，非已认证身份。IMO/MMSI仅检查数字长度，不验证登记、校验位、重复使用或真实归属；保留identityBasis和每个标识来源，不覆盖冲突身份。

## 坐标与角度／单位
固定WGS84 geographic经纬度，十进制度，纬度[-90,90]、经度[-180,180]，非有限数/布尔数拒绝；不得把度当米。无高程/水深/投影/ENU原点/Unity轴定义，本轮不转换坐标。跨日期变更线、极区、地形与局部投影处理留给显式适配器，不能直线连经纬度暗示实际航迹。
速度knots，真实尺寸metres；艏向headingDeg与航迹向courseDeg分别取真北顺时针[0,360)，不能互相回填。AIS不可用码511/360等不能进入有效角度，必须保留原件，在本合同以missing/null与basis说明。缺艏向时orientation.headingAvailable=false，可保留位置点，但消费者不得把COG当船体艏向；不替代人工判断。

## 原记录时间、校时和冲突
每点保留sourceRecordTime原始文字（设备时间／时区声明可原样保留），sourceUtc是来源时间显式转换后的UTC或null；不能猜时区、日期、接收时刻等于定位生成时刻。时间来源以sourceIds和basis说明。标准时间仅接受完整UTC Z、秒精度至微秒，不接受无时区或非Z偏移；显式时区转换在适配器完成并保留依据。非法日期/闰秒拒绝，本版本不支持闰秒。
- unresolved/conflict：alignedUtc、correctionSeconds必须null；保留原时间/冲突依据，阻断同步复盘。
- referenced：显式声明来源UTC可作为复盘参考，sourceUtc与alignedUtc相同，correctionSeconds=0，basis非空。语法通过不证明时钟已校准。
- corrected：两时间都存在、correctionSeconds有限；alignedUtc=sourceUtc+correctionSeconds，数值验证容差1e-6秒。basis记录比较时钟、依据/方法；校正符号正表示向后移动UTC。本版本仅逐点常量偏移结果，不计算漂移或拟合。
输入顺序保留，重复或倒序对齐时间返回TIME_NOT_INCREASING并阻断同步；不排序、不删除、不猜哪条更可信。同一时刻不同来源冲突需操作者先决定/分支，不能自动平均。原件来源仍应保留。

## 值来源与空缺
position作为成对经纬度测量；heading、course、speed、length、beam各自为`{value,kind,sourceIds,basis}`。五类非空值必须区分：recorded（输入声明为记录值，不等于实测真实）、calculated、interpolated、manual_assumption、schematic。计算/插值方法、输入引用及人工假设理由写basis；本校验器不复算这些值。missing必须value=null、basis解释缺失；null不能标为recorded。经纬度任一缺失时整对missing，不拼接成虚假位置。所有sourceIds必须指向本文件sources；recordLocator是行/页/记录定位，不被自动打开或下载。

sources的AIS/VDR/public_report/manual/simulation/other只是材料类型声明，与值的kind分离；报告中的值可以为calculated，AIS材料也不天然可信。不推断不同来源已互证，不把任何来源名当认证。

## 采样与断段
expectedIntervalSeconds可null（采样未知）；gapThresholdSeconds是本次显式连续显示工程阈值，不是海事标准，basis须说明。相邻可对齐点间隔超过阈值返回gaps和interpolate=false。已知缺失区间另存missingIntervals（有序UTC端点+来源+原因），存在则continuousReplayAllowed=false；不填补数据、不补零、不默默插值。消费者应断线/停止连续动画并提示未知区间。canReplaySynchronously仅表示声明的身份、位置及时间条件足够排列点；不等于continuousReplayAllowed，也不保证真实性。位置缺失、身份未决、时间未决/冲突/倒序均阻断同步。插值点只有输入明确标记interpolated才可保留，并须持续显示其性质。

## 船体尺寸与视觉比例
lengthM/beamM为真实尺寸候选值及来源（也可missing），不得由画面宽高或默认模型反推。display.scaleMultiplier是纯显示倍率，purpose=true_scale时必须为1，其他倍率必须visibility_only；比例不得写回尺寸、碰撞包围盒、CPA或运动计算。消费者须显示“示意放大”，尺寸/艏向不足时不得绘制声称精确的船体占地。视觉重叠永不构成碰撞结论，返回visualOverlapIsCollisionEvidence=false；几何、时间、艏向、尺寸和独立证据仍需人工复核。

## 校验与边界
结构/取值错误抛TrajectoryError；未决业务状态以diagnostics返回，原输入不变。requiresHumanReview始终true，authenticityVerified始终false。没有I/O数据采集、网络、数据库或权限修改；只读取仓库固定schema。JSON解码/文件大小/深度预算由未来边界适配器负责，不能直接把此函数暴露为无预算HTTP服务。结构预算100来源、10000点、1000缺失区间是工程范围，不是实际系统吞吐承诺。JSON Schema只能表达结构；时间算术、引用一致性、显示比例和断段需运行语义校验器（未来其他语言须实现同等规则）。

示例：`service/tests/fixtures/shared_trajectory_synthetic.json`，完全构造，非真实AIS、OCR、模型或事故实测。运行：
```bash
cd service
.venv/bin/pytest -q tests/test_shared_trajectory.py
```
待独立审查：契约/语义、跨语言一致性、真实来源适配、身份授权、浏览器/Unity表现、坐标转换和大数据预算。未经审查不能将本候选接生产或宣称三维完成。
