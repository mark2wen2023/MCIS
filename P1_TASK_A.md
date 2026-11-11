# P1 任务 A：纯 C# 计算核心 + dotnet 测试

先阅读 ./ARCHITECTURE.md，重点：第 4.2（AIS）、4.3（坐标）、4.4（时间轴）、4.6（CPA）章节，第 5.1–5.3 节（命名空间、数据结构、接口签名：Mcis.Core、Mcis.Domain.Common、Mcis.Domain.Models、Mcis.Domain.Ais、Mcis.Domain.Tracks、Mcis.Domain.Geo、Mcis.Simulation、Mcis.Simulation.Cpa），第 10.1 目录结构、10.2 asmdef 表，第 12 节 P1。再看 ./thesis.txt 3.4 节（DCPA/TCPA 矢量三角形）。

输出根目录：./unity/Assets/_Project/（对应 Unity 工程 Assets/_Project）。严格使用文档中的命名空间、接口名与方法签名、目录与 asmdef 名称。

## 编写范围（本任务只写纯 C#，不得 using UnityEngine）
1. Scripts/Core/Primitives（及 Events 若 P1 需要）：P1 用到的 SimTime、Result<T> 等基础类型。只写纯 C# 文件。
2. Scripts/Domain/Common、Models：GeoCoord、EnuPosition、TrackSample、VesselParticulars、CpaResult、RiskLevel 等 P1 所需类型。
3. Scripts/Domain/Ais：NMEA 0183 !AIVDM/!AIVDO 解码器：校验和验证、多句拼接（按 sequential message id + channel 重组，超时/乱序处理）、6-bit 解装甲、填充位；支持消息类型 1/2/3（Class A 位置报告）、5（静态与航次数据，含多句）、18（Class B 位置）、19（Class B 扩展）、24（Class B 静态 Part A/B）。正确处理不可用值（lon=181、lat=91、SOG=1023、COG=3600、HDG=511）、有符号经纬度（1/600000 度）、ROT。CSV 导入（列名可配置映射：MMSI、时间、纬度、经度、SOG、COG、HDG，兼容常见 UTC 时间格式，CultureInfo.InvariantCulture）。
4. Scripts/Domain/Tracks：TrackCleaner 异常点剔除，每个被剔除点给出原因码枚举（如 DuplicateTimestamp、OutOfRange、SpeedJump、PositionJump/隐含航速超阈、CourseJump、Unavailable、OutOfOrder），输出保留点 + 剔除报告；时间对齐（两船重采样到统一时间轴）；三次 Hermite 插值（切线由 SOG/COG 速度向量提供，缺失时用有限差分/Catmull-Rom），也提供线性；缺口检测（大于阈值的时间间隔输出 Gap 列表，插值器在缺口内标记 IsInterpolatedAcrossGap 或拒绝外推）。
5. Scripts/Domain/Geo：GeoMath，WGS84⇄ECEF（闭式/Bowring 或迭代，双精度）、ECEF⇄ENU（给定原点）、ENU⇄Unity（Unity 左手系：x=East, y=Up, z=North，用纯 C# 结构如 double3 自定义或 (double x,double y,double z) 结构，不引用 Unity.Mathematics）。实现 IGeoConverter（若文档接口引用了 Unity 类型，则纯计算部分放在 Domain，接口签名中的 Unity 类型改由适配器层负责——并在代码注释中说明）。
6. Scripts/Domain/Cpa：CpaCalculator 向量法：r=P_t−P_o，v=V_t−V_o，TCPA=−(r·v)/|v|²，DCPA=|r+v·TCPA|，|v|≈0 时处理；另实现一个按论文 3.4 节矢量三角形/余弦定理的三角函数公式版本（CalculateByTriangle，用 Vo、Co、Vt、Ct、方位 Q、距离 D），用于交叉验证。
7. Scripts/Simulation/Clock：SimClock（播放/暂停/倍速 0.5,1,2,4,8,16/Seek/StepForward/StepBackward/固定步长 Tick(realDeltaSeconds)，确定性：时间用整数 tick（如 1 tick = 1ms 或 long 微秒）累计，Seek 后状态与从头连续播放到同一时刻一致；事件 TimeChanged/StateChanged）。文件中不得 using UnityEngine（该 asmdef 允许引擎，但这些文件保持纯 C# 以便 dotnet 测试）。
8. Scripts/Simulation/Cpa：CpaService：给定两条轨迹（插值器），按固定步长全时段预计算 CPA 序列（时间、距离、DCPA、TCPA、风险等级），提供 O(1)/二分查询 GetAt(time)；三级风险（Safe/Warning/Danger，默认阈值：Danger DCPA<0.3nm 且 0<TCPA<6min；Warning DCPA<1nm 且 0<TCPA<12min）+ 滞回（升级立即、降级需超出阈值一定裕度且保持 N 秒，确保预计算结果与时间方向无关、可确定性重放）；最小距离时刻查询。同样不 using UnityEngine。
9. 每个 asmdef：按 10.2 表创建 .asmdef 文件（Mcis.Core、Mcis.Domain、Mcis.Simulation、Mcis.Tests.EditMode）。注意：Mcis.Domain 为 noEngineReferences:true；为了能在 dotnet 下编译，P1 的 Domain 代码不要使用 Unity.Mathematics（asmdef 引用可保留但代码不用；或删去该引用并在 INTEGRATION 说明里记一句）。

## 代码约束
- 必须兼容 Unity 2022.3/Unity 6 的 C# 9：不要用 file-scoped namespace、不要用 record（用 readonly struct / sealed class）、不要用 required/init-only（init 需 IsExternalInit，避免）、不要用全局 using、不要用 C# 10+ 特性。可空引用注解不用。
- 所有数值格式化/解析用 InvariantCulture。双精度。
- 每个公共类型有中文 XML 注释（简洁）。

## dotnet 测试工程
- dotnet 在 ~/.dotnet/dotnet（export PATH=$HOME/.dotnet:$PATH; export DOTNET_CLI_TELEMETRY_OPTOUT=1）。
- 在 ./unity/DotnetTests/ 下建：Mcis.Pure.csproj（netstandard2.1，LangVersion 9，通过 <Compile Include> glob 引入 ../Assets/_Project/Scripts/Core/Primitives/**、Domain/**、Simulation/Clock/**、Simulation/Cpa/** 的 .cs，不复制源码）和 Mcis.Pure.Tests.csproj（net8.0，xUnit 或 NUnit，LangVersion 9）。可选 Mcis.sln。
- 测试至少覆盖：
  * 真实 NMEA 样例句解码，至少用这些公认样例并断言字段：
    - `!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C`（类型1）应得 MMSI 366053209 ... 若自行验证发现期望值不同，以正确解码结果为准并在测试注释说明来源；
    - `!AIVDM,1,1,,A,13aEOK?P00PD2wVMdLDRhgvL289?,0*26`（类型1）；
    - 类型5 两句：`!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C` 与 `!AIVDM,2,2,1,A,88888888880,2*25`；
    - 类型18：`!AIVDM,1,1,,B,B52K>;h00Fc>jpUlNV@ikwpUoP06,0*4C`；
    - 类型24：`!AIVDM,1,1,,A,H42O55i18tMET00000000000000,2*6D`；
    - 另外自行构造（用你自己的编码器生成后解码往返）类型19 与类型 24 Part B 的样例；
    - 校验和错误句被拒绝。
  * 坐标往返误差：多个点（含肇庆/珠江口附近、赤道、高纬度、高程）WGS84→ECEF→WGS84 误差 <1e-9 度 / <1mm；WGS84→ENU→WGS84 与 ENU→Unity→ENU 往返。
  * 插值：Hermite 在节点处精确通过；匀速直线航迹上插值误差极小；缺口检测。
  * TrackCleaner 原因码。
  * CPA：已知解析解（对遇、交叉、追越、平行等速 |v|=0）；向量法与论文三角公式版本在大量随机场景下 DCPA/TCPA 一致（容差 1e-6）。
  * SimClock：Seek(t) 后的 Time/状态 与 从0连续 Tick 到 t 完全一致；倍速；步进；暂停时 Tick 不前进。
  * CpaService：预计算结果正向/反向查询一致，滞回行为。
- 运行 dotnet build 与 dotnet test，修到全部通过。最后把 `dotnet test` 结果摘要写到 ./unity/DotnetTests/TEST_RESULTS.txt。

## 工作方式
分多次小步写文件（每次写入 ≤ 250 行），避免长时间无输出。只允许在 /workspace/maritime-sim-design/unity 内写文件（以及 dotnet/NuGet 自身缓存）。允许 dotnet restore 访问 NuGet。不要 git 操作，不要读写其他目录。
