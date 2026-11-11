using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Simulation.Damage;

namespace Mcis.Simulation.WhatIf.Cases
{
    /// <summary>YANGZE 22 案例的船舶强类型输入（由测试从 case.json 读取后传入）。</summary>
    public sealed class Yangze22VesselInput
    {
        /// <summary>船舶标识（yangze22 / vega_dream）。</summary>
        public string VesselId { get; }

        /// <summary>船名。</summary>
        public string Name { get; }

        /// <summary>船长（m，报告直接）。</summary>
        public double LoaM { get; }

        /// <summary>型宽（m，报告直接）。</summary>
        public double BeamM { get; }

        /// <summary>总吨（报告直接）。</summary>
        public double GrossTonnage { get; }

        /// <summary>尺度来源引用（页码/行号/字段）。</summary>
        public string DimensionReference { get; }

        /// <summary>排水量覆盖值（t）；null 表示按总吨估算。</summary>
        public double? DisplacementTonsOverride { get; }

        /// <summary>K 覆盖值（1/s）；null 表示按 K' 估算。</summary>
        public double? KOverride { get; }

        /// <summary>T 覆盖值（s）；null 表示按 T' 估算。</summary>
        public double? TOverride { get; }

        /// <summary>K/T 参考航速覆盖值（kn）；null 表示取 12 kn。</summary>
        public double? ReferenceSpeedKnOverride { get; }

        /// <summary>锚参数覆盖值；null 表示按排水量估计。</summary>
        public AnchorParams AnchorOverride { get; }

        /// <summary>GNSS 天线距船首（m，沿首尾线向后为正）；null 表示报告未给，由案例按【估计】取值。</summary>
        public SourcedValue AntennaFromBowM { get; }

        /// <summary>GNSS 天线距中线（m，右舷为正）；null 表示报告未给，按【估计】取 0（中线上）。</summary>
        public SourcedValue AntennaFromCenterlineM { get; }

        /// <summary>构造船舶输入。</summary>
        public Yangze22VesselInput(
            string vesselId,
            string name,
            double loaM,
            double beamM,
            double grossTonnage,
            string dimensionReference,
            double? displacementTonsOverride = null,
            double? kOverride = null,
            double? tOverride = null,
            double? referenceSpeedKnOverride = null,
            AnchorParams anchorOverride = null,
            SourcedValue antennaFromBowM = null,
            SourcedValue antennaFromCenterlineM = null)
        {
            AntennaFromBowM = antennaFromBowM;
            AntennaFromCenterlineM = antennaFromCenterlineM;
            VesselId = vesselId ?? string.Empty;
            Name = name ?? string.Empty;
            LoaM = loaM;
            BeamM = beamM;
            GrossTonnage = grossTonnage;
            DimensionReference = dimensionReference ?? string.Empty;
            DisplacementTonsOverride = displacementTonsOverride;
            KOverride = kOverride;
            TOverride = tOverride;
            ReferenceSpeedKnOverride = referenceSpeedKnOverride;
            AnchorOverride = anchorOverride;
        }
    }

    /// <summary>表3 的一条操舵记录（强类型输入）。</summary>
    public sealed class Yangze22RudderOrder
    {
        /// <summary>表3 行标识（如 r-220014）。</summary>
        public string Id { get; }

        /// <summary>北京时间。</summary>
        public DateTimeOffset TimeBeijing { get; }

        /// <summary>表3 船首向（度）。</summary>
        public double? HeadingDeg { get; }

        /// <summary>引航员舵令原文。</summary>
        public string PilotOrder { get; }

        /// <summary>舵角指令（度，右舵为正）。</summary>
        public double? RudderCommandDeg { get; }

        /// <summary>舵角实际反馈（度，右舵为正）。</summary>
        public double? RudderFeedbackDeg { get; }

        /// <summary>是否与舵令相反；报告未判定为 null。</summary>
        public bool? ReversedVsOrder { get; }

        /// <summary>来源引用。</summary>
        public string Reference { get; }

        /// <summary>构造表3 行。</summary>
        public Yangze22RudderOrder(
            string id,
            DateTimeOffset timeBeijing,
            double? headingDeg,
            string pilotOrder,
            double? rudderCommandDeg,
            double? rudderFeedbackDeg,
            bool? reversedVsOrder,
            string reference)
        {
            Id = id ?? string.Empty;
            TimeBeijing = timeBeijing;
            HeadingDeg = headingDeg;
            PilotOrder = pilotOrder ?? string.Empty;
            RudderCommandDeg = rudderCommandDeg;
            RudderFeedbackDeg = rudderFeedbackDeg;
            ReversedVsOrder = reversedVsOrder;
            Reference = reference ?? string.Empty;
        }
    }

    /// <summary>YANGZE 22 / VEGA DREAM 案例强类型输入。</summary>
    public sealed class Yangze22Inputs
    {
        private readonly ReadOnlyCollection<Yangze22VesselInput> _vessels;
        private readonly ReadOnlyCollection<Yangze22RudderOrder> _rudderOrders;

        /// <summary>两船输入（须含 yangze22 与 vega_dream）。</summary>
        public IReadOnlyList<Yangze22VesselInput> Vessels
        {
            get { return _vessels; }
        }

        /// <summary>表3 操舵记录。</summary>
        public IReadOnlyList<Yangze22RudderOrder> RudderOrders
        {
            get { return _rudderOrders; }
        }

        /// <summary>碰撞概位（ENU 原点）。</summary>
        public GeoCoord CollisionLocation { get; }

        /// <summary>报告认定的碰撞时刻（北京时间）。</summary>
        public DateTimeOffset CollisionTimeBeijing { get; }

        /// <summary>仿真零点（北京时间，SimTime 0）。</summary>
        public DateTimeOffset SimEpochLocal { get; }

        /// <summary>报告碰撞角（度）。</summary>
        public double ReportCollisionAngleDeg { get; }

        /// <summary>报告接触部位文字。</summary>
        public string ReportContactText { get; }

        /// <summary>碰撞信息引用。</summary>
        public string CollisionReference { get; }

        /// <summary>报告碰撞时 YANGZE 22 船首向（度）。</summary>
        public double? ReportYangze22HeadingDeg { get; }

        /// <summary>报告碰撞时 VEGA DREAM 船首向（度）。</summary>
        public double? ReportVegaDreamHeadingDeg { get; }

        /// <summary>报告碰撞时 YANGZE 22 航速（kn）。</summary>
        public double? ReportYangze22SpeedKn { get; }

        /// <summary>报告碰撞时 VEGA DREAM 航速（kn）。</summary>
        public double? ReportVegaDreamSpeedKn { get; }

        /// <summary>评价结束仿真秒（默认 300 s，即 22:03:30）。</summary>
        public double EndSeconds { get; }

        /// <summary>
        /// 是否截掉报告认定碰撞时刻之后的航迹点（位置、航向、航速样本），默认 true（架构师裁定 A1）。
        /// 截断后末点按最后航向/航速直线延伸；截断点写入每条结果的 Assumptions。
        /// </summary>
        public bool TruncateAfterReportedCollision { get; }

        /// <summary>构造案例输入。</summary>
        public Yangze22Inputs(
            IReadOnlyList<Yangze22VesselInput> vessels,
            IReadOnlyList<Yangze22RudderOrder> rudderOrders,
            GeoCoord collisionLocation,
            DateTimeOffset collisionTimeBeijing,
            DateTimeOffset simEpochLocal,
            double reportCollisionAngleDeg,
            string reportContactText,
            string collisionReference,
            double? reportYangze22HeadingDeg = null,
            double? reportVegaDreamHeadingDeg = null,
            double? reportYangze22SpeedKn = null,
            double? reportVegaDreamSpeedKn = null,
            double endSeconds = 300.0,
            bool truncateAfterReportedCollision = true)
        {
            TruncateAfterReportedCollision = truncateAfterReportedCollision;
            _vessels = new ReadOnlyCollection<Yangze22VesselInput>(
                vessels != null ? new List<Yangze22VesselInput>(vessels) : new List<Yangze22VesselInput>());
            _rudderOrders = new ReadOnlyCollection<Yangze22RudderOrder>(
                rudderOrders != null ? new List<Yangze22RudderOrder>(rudderOrders) : new List<Yangze22RudderOrder>());
            CollisionLocation = collisionLocation;
            CollisionTimeBeijing = collisionTimeBeijing;
            SimEpochLocal = simEpochLocal;
            ReportCollisionAngleDeg = reportCollisionAngleDeg;
            ReportContactText = reportContactText ?? string.Empty;
            CollisionReference = collisionReference ?? string.Empty;
            ReportYangze22HeadingDeg = reportYangze22HeadingDeg;
            ReportVegaDreamHeadingDeg = reportVegaDreamHeadingDeg;
            ReportYangze22SpeedKn = reportYangze22SpeedKn;
            ReportVegaDreamSpeedKn = reportVegaDreamSpeedKn;
            EndSeconds = endSeconds;
        }

        /// <summary>按标识查找船舶输入。</summary>
        public Yangze22VesselInput FindVessel(string vesselId)
        {
            for (int i = 0; i < _vessels.Count; i++)
            {
                if (string.Equals(_vessels[i].VesselId, vesselId, StringComparison.Ordinal))
                {
                    return _vessels[i];
                }
            }
            return null;
        }

        /// <summary>按标识查找表3 行。</summary>
        public Yangze22RudderOrder FindRudderOrder(string id)
        {
            for (int i = 0; i < _rudderOrders.Count; i++)
            {
                if (string.Equals(_rudderOrders[i].Id, id, StringComparison.Ordinal))
                {
                    return _rudderOrders[i];
                }
            }
            return null;
        }
    }

    /// <summary>YANGZE 22 案例构建结果：评价设定、情景、输入来源与航迹诊断。</summary>
    public sealed class Yangze22Study
    {
        private readonly ReadOnlyCollection<WhatIfScenario> _scenarios;
        private readonly ReadOnlyCollection<SourcedValue> _inputs;
        private readonly ReadOnlyCollection<ReportTrackRow> _trackRows;
        private readonly ReadOnlyCollection<Yangze22RudderOrder> _rudderOrders;
        private readonly ReadOnlyCollection<string> _notes;

        /// <summary>反事实评价设定。</summary>
        public WhatIfSetup Setup { get; }

        /// <summary>情景列表（S0、Y1、Y5、Y1+Y5、Y4）。</summary>
        public IReadOnlyList<WhatIfScenario> Scenarios
        {
            get { return _scenarios; }
        }

        /// <summary>全案例输入参数及来源。</summary>
        public IReadOnlyList<SourcedValue> Inputs
        {
            get { return _inputs; }
        }

        /// <summary>解析后的报告航迹行。</summary>
        public IReadOnlyList<ReportTrackRow> TrackRows
        {
            get { return _trackRows; }
        }

        /// <summary>表3 操舵记录（强类型）。</summary>
        public IReadOnlyList<Yangze22RudderOrder> RudderOrders
        {
            get { return _rudderOrders; }
        }

        /// <summary>航迹取舍、插值与 S0 偏差诊断说明。</summary>
        public IReadOnlyList<string> Notes
        {
            get { return _notes; }
        }

        /// <summary>构造案例构建结果。</summary>
        public Yangze22Study(
            WhatIfSetup setup,
            IReadOnlyList<WhatIfScenario> scenarios,
            IReadOnlyList<SourcedValue> inputs,
            IReadOnlyList<ReportTrackRow> trackRows,
            IReadOnlyList<Yangze22RudderOrder> rudderOrders,
            IReadOnlyList<string> notes)
        {
            Setup = setup;
            _scenarios = new ReadOnlyCollection<WhatIfScenario>(
                scenarios != null ? new List<WhatIfScenario>(scenarios) : new List<WhatIfScenario>());
            _inputs = new ReadOnlyCollection<SourcedValue>(
                inputs != null ? new List<SourcedValue>(inputs) : new List<SourcedValue>());
            _trackRows = new ReadOnlyCollection<ReportTrackRow>(
                trackRows != null ? new List<ReportTrackRow>(trackRows) : new List<ReportTrackRow>());
            _rudderOrders = new ReadOnlyCollection<Yangze22RudderOrder>(
                rudderOrders != null ? new List<Yangze22RudderOrder>(rudderOrders) : new List<Yangze22RudderOrder>());
            _notes = new ReadOnlyCollection<string>(
                notes != null ? new List<string>(notes) : new List<string>());
        }

        /// <summary>按顺序评价全部情景。</summary>
        public IReadOnlyList<ScenarioResult> EvaluateAll()
        {
            return ScenarioEvaluator.EvaluateAll(Setup, Scenarios);
        }
    }

    /// <summary>YANGZE 22 案例运行结果：各情景结果、对比表与 S0 对报告的偏差。</summary>
    public sealed class Yangze22Result
    {
        private readonly ReadOnlyCollection<ScenarioResult> _results;

        /// <summary>各情景评价结果。</summary>
        public IReadOnlyList<ScenarioResult> Results
        {
            get { return _results; }
        }

        /// <summary>对比表。</summary>
        public ComparisonTable Comparison { get; }

        /// <summary>S0 原始情景。</summary>
        public ScenarioResult Original { get; }

        /// <summary>S0 对报告（22:01:54、约 70°、右舷5舱）的量化偏差说明。</summary>
        public string OriginalDeviation { get; }

        /// <summary>Y1+Y5 组合情景相对单干预的说明（组合最小距离可能非单调）。</summary>
        public string CombinedScenarioNote { get; }

        /// <summary>S0 对 GNSS 天线位置的敏感性（不改正、VEGA DREAM 中点后 0.35L / 0.375L / 0.40L）。</summary>
        public IReadOnlyList<AntennaSensitivityRow> AntennaSensitivity { get; }

        /// <summary>构造案例运行结果。</summary>
        public Yangze22Result(
            IReadOnlyList<ScenarioResult> results,
            ComparisonTable comparison,
            ScenarioResult original,
            string originalDeviation,
            string combinedScenarioNote = null,
            IReadOnlyList<AntennaSensitivityRow> antennaSensitivity = null)
        {
            AntennaSensitivity = new ReadOnlyCollection<AntennaSensitivityRow>(
                antennaSensitivity != null
                    ? new List<AntennaSensitivityRow>(antennaSensitivity)
                    : new List<AntennaSensitivityRow>());
            _results = new ReadOnlyCollection<ScenarioResult>(
                results != null ? new List<ScenarioResult>(results) : new List<ScenarioResult>());
            Comparison = comparison;
            Original = original;
            OriginalDeviation = originalDeviation ?? string.Empty;
            CombinedScenarioNote = combinedScenarioNote ?? string.Empty;
        }

        /// <summary>按情景标识查找结果。</summary>
        public ScenarioResult Find(string scenarioId)
        {
            for (int i = 0; i < _results.Count; i++)
            {
                if (string.Equals(_results[i].ScenarioId, scenarioId, StringComparison.Ordinal))
                {
                    return _results[i];
                }
            }
            return null;
        }
    }

    /// <summary>S0 天线位置敏感性的一行（天线位置均为【估计】）。</summary>
    public sealed class AntennaSensitivityRow
    {
        /// <summary>行标签（如“VEGA 中点后 0.40L”）。</summary>
        public string Label { get; }

        /// <summary>YANGZE 22 天线在船中点之后的比例（L 的倍数，0=船中）。</summary>
        public double YangzeAftOfMidshipRatio { get; }

        /// <summary>VEGA DREAM 天线在船中点之后的比例（L 的倍数，0=船中）。</summary>
        public double VegaAftOfMidshipRatio { get; }

        /// <summary>是否接触。</summary>
        public bool Collision { get; }

        /// <summary>首次接触时刻（仿真秒）；未接触为 null。</summary>
        public double? TcSeconds { get; }

        /// <summary>首次接触北京时间文字；未接触为“—”。</summary>
        public string TcLocalText { get; }

        /// <summary>接触时刻相对报告 22:01:54 的偏差（秒，正=晚）；未接触为 null。</summary>
        public double? DelayVsReportSec { get; }

        /// <summary>碰撞角（度）；未接触为 null。</summary>
        public double? CollisionAngleDeg { get; }

        /// <summary>报告时刻（t=204 s）的 OBB 真实净距（米，负值为穿透）。</summary>
        public double ClearanceAtReportTimeM { get; }

        /// <summary>接触部位文字；未接触为“—”。</summary>
        public string ContactText { get; }

        /// <summary>同一天线设定下各情景的结论与最小净距摘要（键为情景标识，如 “Y1” → “险情 184.4 m”）。</summary>
        public IReadOnlyDictionary<string, string> ScenarioSummaries { get; }

        /// <summary>同一天线设定下各情景的数值结果（键为情景标识），供对比表敏感性区间与临界判定。</summary>
        public IReadOnlyDictionary<string, SensitivityOutcome> ScenarioOutcomes { get; private set; }

        /// <summary>是否属于裁定 A2 的天线估计区间（YANGZE 0.20L + VEGA 0.35–0.40L）；“不改正”行为对照，不计入临界区间。</summary>
        public bool InEstimateRange { get; private set; }

        /// <summary>对比表中使用的短标签（如“VEGA 0.35L”）。</summary>
        public string ShortLabel { get; private set; }

        internal void SetOutcomes(IDictionary<string, SensitivityOutcome> outcomes, bool inEstimateRange, string shortLabel)
        {
            ScenarioOutcomes = new ReadOnlyDictionary<string, SensitivityOutcome>(
                outcomes != null
                    ? new Dictionary<string, SensitivityOutcome>(outcomes, StringComparer.Ordinal)
                    : new Dictionary<string, SensitivityOutcome>(StringComparer.Ordinal));
            InEstimateRange = inEstimateRange;
            ShortLabel = shortLabel ?? Label;
        }

        /// <summary>构造敏感性行。</summary>
        public AntennaSensitivityRow(
            string label,
            double yangzeAftOfMidshipRatio,
            double vegaAftOfMidshipRatio,
            bool collision,
            double? tcSeconds,
            string tcLocalText,
            double? delayVsReportSec,
            double? collisionAngleDeg,
            double clearanceAtReportTimeM,
            string contactText,
            IReadOnlyDictionary<string, string> scenarioSummaries = null)
        {
            ScenarioSummaries = new ReadOnlyDictionary<string, string>(
                scenarioSummaries != null
                    ? new Dictionary<string, string>(scenarioSummaries, StringComparer.Ordinal)
                    : new Dictionary<string, string>(StringComparer.Ordinal));
            Label = label ?? string.Empty;
            YangzeAftOfMidshipRatio = yangzeAftOfMidshipRatio;
            VegaAftOfMidshipRatio = vegaAftOfMidshipRatio;
            Collision = collision;
            TcSeconds = tcSeconds;
            TcLocalText = string.IsNullOrEmpty(tcLocalText) ? "—" : tcLocalText;
            DelayVsReportSec = delayVsReportSec;
            CollisionAngleDeg = collisionAngleDeg;
            ClearanceAtReportTimeM = clearanceAtReportTimeM;
            ContactText = string.IsNullOrEmpty(contactText) ? "—" : contactText;
            ScenarioOutcomes = new ReadOnlyDictionary<string, SensitivityOutcome>(
                new Dictionary<string, SensitivityOutcome>(StringComparer.Ordinal));
            InEstimateRange = false;
            ShortLabel = Label;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}：tc={1}（{2}），碰撞角 {3}，报告时刻净距 {4:F1} m，{5}",
                Label,
                TcLocalText,
                DelayVsReportSec.HasValue
                    ? DelayVsReportSec.Value.ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) + " s"
                    : "—",
                CollisionAngleDeg.HasValue
                    ? CollisionAngleDeg.Value.ToString("F1", CultureInfo.InvariantCulture) + "°"
                    : "—",
                ClearanceAtReportTimeM,
                ContactText);
        }
    }

    /// <summary>
    /// YANGZE 22 / VEGA DREAM（长江口“12·30”）案例构建器。
    /// 核心库只接收强类型输入与 CSV 行；case.json 由测试用 System.Text.Json 读取后传入。
    /// SimTime 0 = 2024-12-30T21:58:30+08:00（北京时间），ENU 原点取报告碰撞概位。
    /// </summary>
    public static class Yangze22Case
    {
        /// <summary>YANGZE 22 标识。</summary>
        public const string Yangze22Id = "yangze22";

        /// <summary>VEGA DREAM 标识。</summary>
        public const string VegaDreamId = "vega_dream";

        /// <summary>K' 估计值（无因次，取同类散货船量级 1.0）。</summary>
        public const double EstimatedKPrime = 1.0;

        /// <summary>T' 估计值（无因次，取同类散货船量级 1.6）。</summary>
        public const double EstimatedTPrime = 1.6;

        /// <summary>K/T 参考航速估计（kn）。</summary>
        public const double EstimatedReferenceSpeedKn = 12.0;

        /// <summary>排水量/总吨比估计（同类散货船约 1.55）。</summary>
        public const double EstimatedDisplacementPerGrossTon = 1.55;

        /// <summary>舵速推算值（°/s，表3 22:01:21–22:01:30 反馈 −35°→+4°）。</summary>
        public const double DerivedRudderRateDegPerSec = 4.0;

        /// <summary>Y1 干预时刻（22:00:14 相对 21:58:30 = 104 s）。</summary>
        public const double Y1TimeSeconds = 104.0;

        /// <summary>Y5 干预时刻（22:00:42 相对 21:58:30 = 132 s）。</summary>
        public const double Y5TimeSeconds = 132.0;

        /// <summary>Y4 干预时刻（22:00:45 相对 21:58:30 = 135 s）。</summary>
        public const double Y4TimeSeconds = 135.0;

        /// <summary>YANGZE 22 GNSS 天线在船中点之后的比例【估计】（居住舱常见位置，约 45 m）。</summary>
        public const double EstimatedYangzeAntennaAftRatio = 0.20;

        /// <summary>VEGA DREAM GNSS 天线在船中点之后的比例下限【估计】。</summary>
        public const double EstimatedVegaAntennaAftRatioLow = 0.35;

        /// <summary>VEGA DREAM GNSS 天线在船中点之后的比例上限【估计】。</summary>
        public const double EstimatedVegaAntennaAftRatioHigh = 0.40;

        /// <summary>VEGA DREAM GNSS 天线名义取值（区间中值 0.375L）【估计】；不为对齐报告调整。</summary>
        public const double EstimatedVegaAntennaAftRatio = 0.375;

        /// <summary>构建案例（不评价）。天线位置未给时按【估计】名义值改正到船中心。</summary>
        public static Yangze22Study Build(IEnumerable<string> csvLines, Yangze22Inputs inputs)
        {
            return Build(csvLines, inputs, null, null);
        }

        /// <summary>
        /// 构建案例（不评价），可覆盖两船天线在船中点之后的比例（L 的倍数；0 表示不改正、天线视为船中）。
        /// 覆盖值优先于输入中的天线 SourcedValue，用于敏感性扫描。
        /// </summary>
        public static Yangze22Study Build(
            IEnumerable<string> csvLines,
            Yangze22Inputs inputs,
            double? yangzeAntennaAftRatioOverride,
            double? vegaAntennaAftRatioOverride)
        {
            if (csvLines == null)
            {
                throw new ArgumentNullException(nameof(csvLines));
            }
            if (inputs == null)
            {
                throw new ArgumentNullException(nameof(inputs));
            }

            IReadOnlyList<ReportTrackRow> rows = ReportTrackCsv.Parse(csvLines);
            Yangze22VesselInput yangze = inputs.FindVessel(Yangze22Id);
            Yangze22VesselInput vega = inputs.FindVessel(VegaDreamId);
            if (yangze == null || vega == null)
            {
                throw new ArgumentException("输入必须同时包含 yangze22 与 vega_dream 两船。", nameof(inputs));
            }
            ValidateVessel(yangze);
            ValidateVessel(vega);

            double endSeconds = inputs.EndSeconds > 0.0
                ? inputs.EndSeconds
                : (inputs.CollisionTimeBeijing - inputs.SimEpochLocal).TotalSeconds + 60.0;

            List<string> notes = new List<string>();
            List<SourcedValue> globalInputs = new List<SourcedValue>();
            AddCollisionInputs(globalInputs, inputs, notes);

            ManeuverParams yangzeParams = BuildParams(yangze, globalInputs, notes);
            ManeuverParams vegaParams = BuildParams(vega, globalInputs, notes);

            double reportTc = (inputs.CollisionTimeBeijing - inputs.SimEpochLocal).TotalSeconds;
            double? cutoff = inputs.TruncateAfterReportedCollision ? (double?)reportTc : null;
            List<string> caseAssumptions = new List<string>();
            int yangzeRemoved;
            int vegaRemoved;
            IReadOnlyList<KinematicState> yangzeStates = BuildYangzeTrack(
                rows, inputs, yangzeParams, endSeconds, notes, cutoff, out yangzeRemoved);
            IReadOnlyList<KinematicState> vegaStates = BuildVegaTrack(
                rows, inputs, vegaParams, endSeconds, notes, cutoff, out vegaRemoved);
            string cutoffText = inputs.SimEpochLocal.AddSeconds(reportTc).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
            if (cutoff.HasValue)
            {
                caseAssumptions.Add(string.Format(
                    CultureInfo.InvariantCulture,
                    "真实案例航迹截断：只用报告认定碰撞时刻 {0}（t={1:F0} s）及以前的航迹行；去掉其后的 YANGZE 22 行 {2} 条、VEGA DREAM 行 {3} 条（含位置、航向、航速样本），截断点之后按最后航向/航速直线延伸（可通过 Yangze22Inputs.TruncateAfterReportedCollision 关闭）。",
                    cutoffText, reportTc, yangzeRemoved, vegaRemoved));
            }
            else
            {
                caseAssumptions.Add(string.Format(
                    CultureInfo.InvariantCulture,
                    "真实案例航迹未截断（配置关闭）：报告认定碰撞时刻 {0}（t={1:F0} s）之后记录的航迹点也参与插值，碰撞后船位会影响回放的接触时刻与碰撞角。",
                    cutoffText, reportTc));
            }

            double yangzeFromBow, yangzeFromCl, vegaFromBow, vegaFromCl;
            ResolveAntenna(yangze, yangzeAntennaAftRatioOverride, EstimatedYangzeAntennaAftRatio,
                "估计依据：报告未给天线位置（case.json 第4897行“天线位置未给”）；取居住舱常见位置，中点后 0.20L（约 45 m），见 logs/w14-independent-check.md 天线扫描。",
                globalInputs, out yangzeFromBow, out yangzeFromCl);
            ResolveAntenna(vega, vegaAntennaAftRatioOverride, EstimatedVegaAntennaAftRatio,
                "估计依据：报告未给天线位置；架构师裁定 A2 取中点后 0.35–0.40L，名义值取区间中值 0.375L，结果附 0.35L/0.40L 敏感性。",
                globalInputs, out vegaFromBow, out vegaFromCl);
            yangzeStates = AntennaToCenter(yangzeStates, yangze.LoaM, yangzeFromBow, yangzeFromCl);
            vegaStates = AntennaToCenter(vegaStates, vega.LoaM, vegaFromBow, vegaFromCl);
            caseAssumptions.Add(string.Format(
                CultureInfo.InvariantCulture,
                "船位改正：报告 VDR/AIS 船位为 GNSS 天线位置，已沿船首向换算到船中心（OBB 中心）。YANGZE 22 天线距船首 {0:F1} m（中点后 {1:F3}L）、距中线 {2:F1} m；VEGA DREAM 天线距船首 {3:F1} m（中点后 {4:F3}L）、距中线 {5:F1} m。报告未给的取值均为【估计】，偏差照实列出，不为对齐报告调参。",
                yangzeFromBow, (yangzeFromBow - 0.5 * yangze.LoaM) / yangze.LoaM, yangzeFromCl,
                vegaFromBow, (vegaFromBow - 0.5 * vega.LoaM) / vega.LoaM, vegaFromCl));

            WhatIfVessel yangzeVessel = WhatIfVessel.FromStates(
                Yangze22Id, yangzeParams, yangzeStates, yangze.Name);
            WhatIfVessel vegaVessel = WhatIfVessel.FromStates(
                VegaDreamId, vegaParams, vegaStates, vega.Name);

            globalInputs.Add(new SourcedValue(
                "CSV 数据行数", rows.Count, "行", ValueSource.ReportDerived,
                "reports/yangze22/tracks_from_report.csv；REAL_CASES.md §8（54 行）",
                "跳过 # 注释与表头后的数据行数，用于校验读取完整性。"));

            DateTimeOffset epoch = inputs.SimEpochLocal;
            WhatIfSetup setup = new WhatIfSetup(
                new[] { yangzeVessel, vegaVessel },
                Yangze22Id,
                VegaDreamId,
                0.0,
                endSeconds,
                1.0,
                0.05,
                0.5,
                0.1,
                null,
                epoch,
                inputs.CollisionLocation,
                new ReadOnlyCollection<SourcedValue>(new List<SourcedValue>(globalInputs)),
                caseAssumptions);

            List<WhatIfScenario> scenarios = BuildScenarios(inputs);
            notes.Add("SimTime 0 = " + epoch.ToString("yyyy-MM-dd'T'HH:mm:sszzz", CultureInfo.InvariantCulture) +
                      "（北京时间），取 tracks_from_report.csv 首个 VDR 点；EndSeconds=" +
                      endSeconds.ToString("F0", CultureInfo.InvariantCulture) + " s。");
            notes.Add("YANGZE 22 位置取舍：同一时刻按 ReportFigure-VDR > ReportFigure-AIS > ReportNarrative 取一条；无位置行用于航向/航速插值。");
            notes.Add("VEGA DREAM 仅有 3 个带位置点；22:00:38→22:00:42 的 AIS 位移约 55 m/4 s（约 27 kn）与 10.6 kn 矛盾（case.json X10 与 CSV note），故以 22:01:54 AIS 船位为锚点、按航向/航速积分反推与延伸，标为推算/插值。");
            notes.Add("S0 为报告航迹回放、不施加任何干预；Y1/Y5/Y4 自干预时刻偏离原航迹按 Nomoto 模型积分。");
            notes.AddRange(caseAssumptions);

            return new Yangze22Study(
                setup, scenarios, globalInputs, rows, inputs.RudderOrders, notes);
        }

        /// <summary>构建、评价并生成对比表与 S0 偏差说明。</summary>
        public static Yangze22Result Run(IEnumerable<string> csvLines, Yangze22Inputs inputs)
        {
            if (csvLines == null)
            {
                throw new ArgumentNullException(nameof(csvLines));
            }
            List<string> lines = new List<string>(csvLines);
            Yangze22Study study = Build(lines, inputs);
            IReadOnlyList<ScenarioResult> results = study.EvaluateAll();
            IReadOnlyList<AntennaSensitivityRow> sensitivity = RunAntennaSensitivity(lines, inputs);
            ComparisonTable comparison = ScenarioComparison.Build(results, ToComparisonSensitivity(sensitivity));
            ScenarioResult original = null;
            for (int i = 0; i < results.Count; i++)
            {
                if (string.Equals(results[i].ScenarioId, "S0", StringComparison.Ordinal))
                {
                    original = results[i];
                    break;
                }
            }
            if (original == null)
            {
                throw new InvalidOperationException("案例结果缺少 S0。");
            }
            string deviation = DescribeDeviation(inputs, original, study.Setup);
            string combinedNote = DescribeCombined(results);
            return new Yangze22Result(results, comparison, original, deviation, combinedNote, sensitivity);
        }

        /// <summary>
        /// 把天线敏感性行转为对比表的敏感性输入：只取裁定 A2 估计区间内的行（VEGA 0.35L / 0.375L / 0.40L），
        /// “不改正”行是对照，不参与临界判定。
        /// </summary>
        public static IReadOnlyDictionary<string, IReadOnlyList<SensitivityOutcome>> ToComparisonSensitivity(
            IReadOnlyList<AntennaSensitivityRow> rows)
        {
            Dictionary<string, List<SensitivityOutcome>> map =
                new Dictionary<string, List<SensitivityOutcome>>(StringComparer.Ordinal);
            if (rows != null)
            {
                for (int i = 0; i < rows.Count; i++)
                {
                    AntennaSensitivityRow row = rows[i];
                    if (row == null || !row.InEstimateRange)
                    {
                        continue;
                    }
                    foreach (KeyValuePair<string, SensitivityOutcome> pair in row.ScenarioOutcomes)
                    {
                        List<SensitivityOutcome> list;
                        if (!map.TryGetValue(pair.Key, out list))
                        {
                            list = new List<SensitivityOutcome>();
                            map[pair.Key] = list;
                        }
                        list.Add(pair.Value);
                    }
                }
            }
            Dictionary<string, IReadOnlyList<SensitivityOutcome>> result =
                new Dictionary<string, IReadOnlyList<SensitivityOutcome>>(StringComparer.Ordinal);
            foreach (KeyValuePair<string, List<SensitivityOutcome>> pair in map)
            {
                result[pair.Key] = new ReadOnlyCollection<SensitivityOutcome>(pair.Value);
            }
            return new ReadOnlyDictionary<string, IReadOnlyList<SensitivityOutcome>>(result);
        }

        /// <summary>
        /// S0 对天线位置的敏感性：不改正（两船天线视为船中）、YANGZE 0.20L 配 VEGA 0.35L / 0.375L / 0.40L。
        /// 天线位置均为【估计】；截断设置沿用输入。
        /// </summary>
        public static IReadOnlyList<AntennaSensitivityRow> RunAntennaSensitivity(
            IEnumerable<string> csvLines,
            Yangze22Inputs inputs)
        {
            if (csvLines == null)
            {
                throw new ArgumentNullException(nameof(csvLines));
            }
            if (inputs == null)
            {
                throw new ArgumentNullException(nameof(inputs));
            }
            List<string> lines = new List<string>(csvLines);
            double[][] grid =
            {
                new[] { 0.0, 0.0 },
                new[] { EstimatedYangzeAntennaAftRatio, EstimatedVegaAntennaAftRatioLow },
                new[] { EstimatedYangzeAntennaAftRatio, EstimatedVegaAntennaAftRatio },
                new[] { EstimatedYangzeAntennaAftRatio, EstimatedVegaAntennaAftRatioHigh }
            };
            string[] labels =
            {
                "不改正天线（天线视为船中）",
                "YANGZE 中点后 0.20L + VEGA 中点后 0.35L",
                "YANGZE 中点后 0.20L + VEGA 中点后 0.375L（名义）",
                "YANGZE 中点后 0.20L + VEGA 中点后 0.40L"
            };
            string[] shortLabels = { "天线不改正", "VEGA 0.35L", "VEGA 0.375L", "VEGA 0.40L" };
            double reportTc = (inputs.CollisionTimeBeijing - inputs.SimEpochLocal).TotalSeconds;
            List<AntennaSensitivityRow> rows = new List<AntennaSensitivityRow>(grid.Length);
            for (int i = 0; i < grid.Length; i++)
            {
                Yangze22Study study = Build(lines, inputs, grid[i][0], grid[i][1]);
                IReadOnlyList<ScenarioResult> all = study.EvaluateAll();
                ScenarioResult s0 = all[0];
                Dictionary<string, string> summaries = new Dictionary<string, string>(StringComparer.Ordinal);
                Dictionary<string, SensitivityOutcome> outcomes =
                    new Dictionary<string, SensitivityOutcome>(StringComparer.Ordinal);
                for (int k = 0; k < all.Count; k++)
                {
                    outcomes[all[k].ScenarioId] = SensitivityOutcome.From(shortLabels[i], all[k]);
                    summaries[all[k].ScenarioId] = all[k].Collision
                        ? all[k].VerdictText + " " + all[k].TcLocalText
                        : all[k].VerdictText + " " + all[k].MinClearanceM.ToString("F1", CultureInfo.InvariantCulture) + " m";
                }
                double clearanceAtReport = OrientedBoundingBox.Clearance(
                    s0.Tracks[study.Setup.OwnVesselId].ToBodyState(reportTc).Obb,
                    s0.Tracks[study.Setup.TargetVesselId].ToBodyState(reportTc).Obb);
                string contact = s0.Geometry != null && s0.Geometry.IsBowToBow
                    ? ScenarioComparison.ContactPartText(s0.Geometry)
                    : s0.Geometry != null
                    ? s0.Geometry.StruckSide + " 距船首 " +
                      s0.Geometry.ContactFromStruckBowM.ToString("F0", CultureInfo.InvariantCulture) + " m（" +
                      s0.Geometry.ContactFromStruckBowRatio.ToString("F2", CultureInfo.InvariantCulture) + " L）"
                    : "—";
                AntennaSensitivityRow sensitivityRow = new AntennaSensitivityRow(
                    labels[i],
                    grid[i][0],
                    grid[i][1],
                    s0.Collision,
                    s0.TcSeconds,
                    s0.TcLocalText,
                    s0.TcSeconds.HasValue ? (double?)(s0.TcSeconds.Value - reportTc) : null,
                    s0.Geometry != null ? (double?)s0.Geometry.CollisionAngleDeg : null,
                    clearanceAtReport,
                    contact,
                    summaries);
                sensitivityRow.SetOutcomes(outcomes, i > 0, shortLabels[i]);
                rows.Add(sensitivityRow);
            }
            return new ReadOnlyCollection<AntennaSensitivityRow>(rows);
        }

        private static void ResolveAntenna(
            Yangze22VesselInput vessel,
            double? aftRatioOverride,
            double defaultAftRatio,
            string estimateNote,
            List<SourcedValue> inputs,
            out double fromBowM,
            out double fromCenterlineM)
        {
            SourcedValue fromBow;
            if (aftRatioOverride.HasValue)
            {
                double ratio = aftRatioOverride.Value;
                fromBow = new SourcedValue(
                    vessel.Name + " GNSS 天线距船首", vessel.LoaM * (0.5 + ratio), "m", ValueSource.Estimated,
                    "敏感性扫描覆盖值（报告未给天线位置）",
                    "【估计】敏感性：中点后 " + ratio.ToString("F3", CultureInfo.InvariantCulture) + "L" +
                    (Math.Abs(ratio) < 1e-12 ? "（不改正，天线视为船中）" : string.Empty) + "。");
            }
            else if (vessel.AntennaFromBowM != null)
            {
                fromBow = vessel.AntennaFromBowM;
            }
            else
            {
                fromBow = new SourcedValue(
                    vessel.Name + " GNSS 天线距船首", vessel.LoaM * (0.5 + defaultAftRatio), "m", ValueSource.Estimated,
                    "REAL_CASES.md §9；case.json（报告未给天线位置）；DEFECTS/W14.md 架构师裁定 A2",
                    "【估计】中点后 " + defaultAftRatio.ToString("F3", CultureInfo.InvariantCulture) + "L。" + estimateNote);
            }
            SourcedValue fromCl = vessel.AntennaFromCenterlineM ?? new SourcedValue(
                vessel.Name + " GNSS 天线距中线（右舷为正）", 0.0, "m", ValueSource.Estimated,
                "REAL_CASES.md §9；case.json（报告未给天线位置）",
                "【估计】报告未给横向位置，取中线上（0 m）。");
            if (fromBow.Value < 0.0 || fromBow.Value > vessel.LoaM)
            {
                throw new ArgumentOutOfRangeException(nameof(vessel), "天线距船首必须位于 0…船长 之间：" + vessel.VesselId);
            }
            if (Math.Abs(fromCl.Value) > 0.5 * vessel.BeamM + 1e-9)
            {
                throw new ArgumentOutOfRangeException(nameof(vessel), "天线距中线不得超过半宽：" + vessel.VesselId);
            }
            inputs.Add(fromBow);
            inputs.Add(fromCl);
            fromBowM = fromBow.Value;
            fromCenterlineM = fromCl.Value;
        }

        /// <summary>
        /// 把天线位置序列换算为船中心序列：center = antenna − f·(L/2 − 距船首) − s·距中线，
        /// f/s 为该时刻船首向的前向/右舷单位向量。
        /// </summary>
        public static IReadOnlyList<KinematicState> AntennaToCenter(
            IReadOnlyList<KinematicState> antennaStates,
            double loaM,
            double antennaFromBowM,
            double antennaFromCenterlineM)
        {
            double forwardOffset = 0.5 * loaM - antennaFromBowM;
            List<KinematicState> result = new List<KinematicState>(antennaStates.Count);
            for (int i = 0; i < antennaStates.Count; i++)
            {
                KinematicState s = antennaStates[i];
                double rad = s.HeadingDeg * Math.PI / 180.0;
                double fe = Math.Sin(rad);
                double fn = Math.Cos(rad);
                double se = Math.Cos(rad);
                double sn = -Math.Sin(rad);
                result.Add(new KinematicState(
                    s.TimeSeconds,
                    s.EastM - fe * forwardOffset - se * antennaFromCenterlineM,
                    s.NorthM - fn * forwardOffset - sn * antennaFromCenterlineM,
                    s.HeadingDeg,
                    s.SpeedKn,
                    s.RotDegPerSec,
                    s.RudderDeg));
            }
            return new ReadOnlyCollection<KinematicState>(result);
        }

        private static List<ReportTrackRow> TruncateRows(
            List<ReportTrackRow> rows,
            double? cutoffSeconds,
            DateTimeOffset epoch,
            out int removed)
        {
            removed = 0;
            if (!cutoffSeconds.HasValue)
            {
                return rows;
            }
            List<ReportTrackRow> kept = new List<ReportTrackRow>(rows.Count);
            for (int i = 0; i < rows.Count; i++)
            {
                if ((rows[i].TimeBeijing - epoch).TotalSeconds <= cutoffSeconds.Value + 1e-9)
                {
                    kept.Add(rows[i]);
                }
                else
                {
                    removed++;
                }
            }
            return kept;
        }

        private static void ValidateVessel(Yangze22VesselInput vessel)
        {
            if (vessel.LoaM <= 0.0 || vessel.BeamM <= 0.0 || vessel.GrossTonnage <= 0.0)
            {
                throw new ArgumentException("船舶尺度与总吨必须为正数：" + vessel.VesselId, nameof(vessel));
            }
            if (string.IsNullOrWhiteSpace(vessel.DimensionReference))
            {
                throw new ArgumentException("船舶尺度来源引用不能为空：" + vessel.VesselId, nameof(vessel));
            }
        }

        private static ManeuverParams BuildParams(
            Yangze22VesselInput vessel,
            List<SourcedValue> inputs,
            List<string> notes)
        {
            double displacement = vessel.DisplacementTonsOverride.HasValue
                ? vessel.DisplacementTonsOverride.Value
                : EstimatedDisplacementPerGrossTon * vessel.GrossTonnage;
            double referenceSpeed = vessel.ReferenceSpeedKnOverride.HasValue
                ? vessel.ReferenceSpeedKnOverride.Value
                : EstimatedReferenceSpeedKn;
            double referenceMps = referenceSpeed * VesselMotionState.MpsPerKnot;
            double k = vessel.KOverride.HasValue
                ? vessel.KOverride.Value
                : EstimatedKPrime * referenceMps / vessel.LoaM;
            double t = vessel.TOverride.HasValue
                ? vessel.TOverride.Value
                : EstimatedTPrime * vessel.LoaM / referenceMps;

            string vesselName = vessel.Name;
            inputs.Add(new SourcedValue(
                vesselName + " 船长", vessel.LoaM, "m", ValueSource.ReportDirect,
                vessel.DimensionReference,
                "报告直接给出；case.json vessels[].loaM。"));
            inputs.Add(new SourcedValue(
                vesselName + " 型宽", vessel.BeamM, "m", ValueSource.ReportDirect,
                vessel.DimensionReference,
                "报告直接给出；case.json vessels[].beamM。"));
            inputs.Add(new SourcedValue(
                vesselName + " 总吨", vessel.GrossTonnage, "GT", ValueSource.ReportDirect,
                vessel.DimensionReference,
                "报告直接给出；case.json vessels[].grossTonnage。"));
            inputs.Add(new SourcedValue(
                vesselName + " 排水量", displacement, "t", ValueSource.Estimated,
                "REAL_CASES.md §9（报告未给排水量）；case.json vessels[].grossTonnage 为报告直接",
                "估计依据：同类散货船排水量≈1.55×总吨；" + displacement.ToString("F0", CultureInfo.InvariantCulture) +
                " t = 1.55 × " + vessel.GrossTonnage.ToString("F0", CultureInfo.InvariantCulture) + " GT。"));
            inputs.Add(new SourcedValue(
                vesselName + " K", k, "1/s", ValueSource.Estimated,
                "REAL_CASES.md §4.1/§9（报告未给 K）；K'=" + EstimatedKPrime.ToString("F1", CultureInfo.InvariantCulture) +
                "，参考航速 " + referenceSpeed.ToString("F0", CultureInfo.InvariantCulture) + " kn",
                "估计依据：K = K'·u_ref/L，K'=1.0 取同类散货船量级；u_ref=" +
                referenceSpeed.ToString("F1", CultureInfo.InvariantCulture) + " kn，L=" +
                vessel.LoaM.ToString("F2", CultureInfo.InvariantCulture) + " m。"));
            inputs.Add(new SourcedValue(
                vesselName + " T", t, "s", ValueSource.Estimated,
                "REAL_CASES.md §4.1/§9（报告未给 T）；T'=" + EstimatedTPrime.ToString("F1", CultureInfo.InvariantCulture) +
                "，参考航速 " + referenceSpeed.ToString("F0", CultureInfo.InvariantCulture) + " kn",
                "估计依据：T = T'·L/u_ref，T'=1.6 取同类散货船量级。"));
            inputs.Add(new SourcedValue(
                vesselName + " 参考航速", referenceSpeed, "kn", ValueSource.Estimated,
                "REAL_CASES.md §4.1（报告未给操纵参考航速）",
                "估计依据：取同类散货船服务航速量级 12 kn；报告实际航速约 8–10.6 kn。"));
            inputs.Add(new SourcedValue(
                vesselName + " 常规变速时间常数", 120.0, "s", ValueSource.Estimated,
                "REAL_CASES.md §9（报告未给主机响应参数）",
                "估计依据：大型散货船速降惯性大，取 120 s 量级。"));
            inputs.Add(new SourcedValue(
                vesselName + " 停车时间常数", 90.0, "s", ValueSource.Estimated,
                "REAL_CASES.md §9（报告未给主机响应参数）",
                "估计依据：停车滑行时间常数取 90 s 量级。"));
            inputs.Add(new SourcedValue(
                vesselName + " 后退时间常数", 45.0, "s", ValueSource.Estimated,
                "REAL_CASES.md §9（报告未给主机响应参数）",
                "估计依据：后退响应快于停车，取 45 s 量级。"));
            inputs.Add(new SourcedValue(
                vesselName + " 最大舵角", 35.0, "°", ValueSource.ReportDirect,
                "case.json vessels[].steeringGear.maxRudderDegFromTable=35；报告表3（p25）满舵 35°",
                "报告直接给出满舵 35°。"));
            inputs.Add(new SourcedValue(
                vesselName + " 舵速", DerivedRudderRateDegPerSec, "°/s", ValueSource.ReportDerived,
                "REAL_CASES.md §4.1；case.json 表3 r-220121/r-220130（p25，PDF p27，line 617/619）",
                "推算：22:01:21 反馈左 35°→22:01:30 反馈右 4°，9 s 转 39°，约 4.3°/s，取 4.0°/s。"));

            AnchorParams anchor = vessel.AnchorOverride ?? AnchorParams.Default(displacement);
            inputs.Add(new SourcedValue(
                vesselName + " 锚抓底延迟", anchor.LetGoToBiteSec, "s", ValueSource.Estimated,
                "REAL_CASES.md §4.1 Y5/§9（报告未给锚设备、底质与抓力）",
                "估计依据：浅水 12.5 m 航道松锚至锚爪抓底约 12 s；未计锚链动力学。"));
            inputs.Add(new SourcedValue(
                vesselName + " 锚附加减速度", anchor.DecelerationKnPerSec, "kn/s", ValueSource.Estimated,
                "REAL_CASES.md §4.1 Y5/§9（报告未给锚抓力）",
                "估计依据：以 70,000 t 船约 0.08 kn/s 为基准，按排水量 −1/3 次方缩放（抓力约随排水量 2/3 次方、惯性随排水量一次方）。"));
            inputs.Add(new SourcedValue(
                vesselName + " 锚附加转首率", anchor.YawRateDegPerSec, "°/s", ValueSource.Estimated,
                "REAL_CASES.md §4.1 Y5/§9（报告未给单锚偏转）",
                "估计依据：单锚在航速数节时对船首的附加偏转取 0.30°/s 量级；双锚取 0。"));
            inputs.Add(new SourcedValue(
                vesselName + " 锚有效航速上限", anchor.MaxEffectiveSpeedKn, "kn", ValueSource.Estimated,
                "REAL_CASES.md §4.1 Y5/§9（报告未给锚链破断/拖锚临界速度）",
                "估计依据：超过 6 kn 锚链易断或仅拖动，减速度按 6/u 折减。"));

            notes.Add(vesselName + "：K=" + k.ToString("F5", CultureInfo.InvariantCulture) +
                      " 1/s、T=" + t.ToString("F1", CultureInfo.InvariantCulture) +
                      " s、排水量=" + displacement.ToString("F0", CultureInfo.InvariantCulture) +
                      " t 均为估计；K'=" + EstimatedKPrime.ToString("F1", CultureInfo.InvariantCulture) +
                      "、T'=" + EstimatedTPrime.ToString("F1", CultureInfo.InvariantCulture) +
                      " 按 u_ref=" + referenceSpeed.ToString("F1", CultureInfo.InvariantCulture) + " kn 换算。");

            return new ManeuverParams(
                k, t, referenceSpeed,
                35.0, DerivedRudderRateDegPerSec,
                120.0, 90.0, 45.0, 0.0,
                vessel.LoaM, vessel.BeamM, displacement,
                anchor);
        }

        private static void AddCollisionInputs(
            List<SourcedValue> inputs,
            Yangze22Inputs source,
            List<string> notes)
        {
            double reportTc = (source.CollisionTimeBeijing - source.SimEpochLocal).TotalSeconds;
            inputs.Add(new SourcedValue(
                "报告碰撞角", source.ReportCollisionAngleDeg, "°", ValueSource.ReportDirect,
                "case.json collision.collisionAngleDeg；" + source.CollisionReference,
                "报告原文：VEGA DREAM 艏向约297°、YANGZE 22 艏向约047°，取锐角约70°（报告第15页，PDF 第17页，line 407-409）。"));
            inputs.Add(new SourcedValue(
                "报告碰撞时刻（相对 SimTime 0）", reportTc, "s", ValueSource.ReportDerived,
                "case.json collision.time.beijing（2024-12-30T22:01:54+08:00）与 SimEpochLocal（21:58:30）",
                "推算：22:01:54 − 21:58:30 = 204 s；报告第14页（PDF 第16页，line 387-389）。"));
            inputs.Add(new SourcedValue(
                "报告接触货舱号", 5.0, "号舱", ValueSource.ReportDirect,
                "case.json collision.contact：" + source.ReportContactText,
                "报告第15页（PDF 第17页，line 406-407）：VEGA DREAM 船首撞 YANGZE 22 右舷中部第5号货舱。"));
            if (source.ReportYangze22HeadingDeg.HasValue)
            {
                inputs.Add(new SourcedValue(
                    "报告 YANGZE 22 碰撞船首向", source.ReportYangze22HeadingDeg.Value, "°",
                    ValueSource.ReportDirect,
                    "case.json collision.yangze22HeadingDeg（报告第15页，PDF 第17页，line 404）",
                    "图6 AIS 船首向 47.0°。"));
            }
            if (source.ReportVegaDreamHeadingDeg.HasValue)
            {
                inputs.Add(new SourcedValue(
                    "报告 VEGA DREAM 碰撞船首向", source.ReportVegaDreamHeadingDeg.Value, "°",
                    ValueSource.ReportDirect,
                    "case.json collision.vegaDreamHeadingDeg（报告第15页，PDF 第17页，line 404）",
                    "图6 AIS 船首向 297.0°。"));
            }
            if (source.ReportYangze22SpeedKn.HasValue)
            {
                inputs.Add(new SourcedValue(
                    "报告 YANGZE 22 碰撞航速", source.ReportYangze22SpeedKn.Value, "kn",
                    ValueSource.ReportDirect,
                    "case.json collision.yangze22SpeedKn（报告第38页，PDF 第40页，line 827）",
                    "正文约 8.0 kn。"));
            }
            if (source.ReportVegaDreamSpeedKn.HasValue)
            {
                inputs.Add(new SourcedValue(
                    "报告 VEGA DREAM 碰撞航速", source.ReportVegaDreamSpeedKn.Value, "kn",
                    ValueSource.ReportDirect,
                    "case.json collision.vegaDreamSpeedKn（报告图6 AIS，第15页，PDF 第17页，line 404）",
                    "图6 AIS 船速 10.2 kn。"));
            }
            notes.Add("报告认定：22:01:54（t=204 s）、碰撞角约 " +
                      source.ReportCollisionAngleDeg.ToString("F0", CultureInfo.InvariantCulture) +
                      "°、VEGA DREAM 船首撞 YANGZE 22 右舷5舱（" + source.CollisionReference + "）。");
        }

        private static List<WhatIfScenario> BuildScenarios(Yangze22Inputs inputs)
        {
            List<WhatIfScenario> scenarios = new List<WhatIfScenario>();
            scenarios.Add(WhatIfScenario.Original("S0", "原始航迹回放（不干预）"));

            List<SourcedValue> y1Inputs = new List<SourcedValue>
            {
                new SourcedValue(
                    "Y1 干预时刻", Y1TimeSeconds, "s", ValueSource.ReportDerived,
                    "case.json timeline e-y-220014（22:00:14）与 SimEpochLocal（21:58:30）",
                    "推算：22:00:14 − 21:58:30 = 104 s。"),
                new SourcedValue(
                    "Y1 舵角", 35.0, "°", ValueSource.ReportDirect,
                    "case.json rudderOrders r-220014（pilotOrder=右满舵；表3 p25，PDF p27，line 614）",
                    "反事实为正确执行右满舵 +35°；原报告实际执行左舵29°/反馈左舵30°。"),
                new SourcedValue(
                    "Y1 舵速", DerivedRudderRateDegPerSec, "°/s", ValueSource.ReportDerived,
                    "REAL_CASES.md §4.1；表3 r-220121/r-220130",
                    "由表3 22:01:21–22:01:30 反馈变化推算约 4.3°/s，取 4.0°/s。")
            };
            VesselScenario y1Vessel = new VesselScenario(
                Yangze22Id,
                Y1TimeSeconds,
                new[]
                {
                    Intervention.TurnStarboard(
                        Y1TimeSeconds, 35.0, 0.0, 0.0, "正确执行右满舵 +35°")
                });
            scenarios.Add(new WhatIfScenario(
                "Y1", "YANGZE 22 正确执行右满舵",
                "YANGZE 22 于 t=104 s（22:00:14）偏离原航迹，右满舵 +35°，舵速 4°/s",
                new[] { y1Vessel }, y1Inputs));

            List<SourcedValue> y5Inputs = new List<SourcedValue>
            {
                new SourcedValue(
                    "Y5 干预时刻", Y5TimeSeconds, "s", ValueSource.ReportDerived,
                    "case.json timeline e-v-220042-orders（22:00:42）与 SimEpochLocal（21:58:30）",
                    "推算：22:00:42 − 21:58:30 = 132 s。"),
                new SourcedValue(
                    "Y5 抛锚舷别（1=右舷）", 1.0, "1=右舷", ValueSource.Estimated,
                    "REAL_CASES.md §4.1 Y5；case.json timeline e-v-220042-orders（报告未给锚别）",
                    "估计依据：YANGZE 22 位于 VEGA DREAM 左舷船首方向（图29 相对方位约 −11.9°），选右舷锚使船首向右偏转、背离来船，并与报告右满舵意图一致；报告未给锚设备状态。"),
                new SourcedValue(
                    "Y5 实际右满舵", 35.0, "°", ValueSource.ReportDirect,
                    "case.json timeline e-v-220042-orders：引航员令右满舵",
                    "保留报告实际操作：22:00:42 右满舵。"),
                new SourcedValue(
                    "Y5 实际后退三", 3.0, "档（后退三）", ValueSource.ReportDirect,
                    "case.json timeline e-v-220042-orders：随即连续令…停车、正舵、后退三",
                    "保留报告实际操作：后退三按同一时刻近似（报告未给逐条车钟时刻）；模型以全速后退处理。")
            };
            VesselScenario y5Vessel = new VesselScenario(
                VegaDreamId,
                Y5TimeSeconds,
                new[]
                {
                    Intervention.EmergencyAnchor(
                        Y5TimeSeconds, AnchorSide.Starboard, 0.0, "右舷应急抛锚（假设舷别）"),
                    Intervention.TurnStarboard(
                        Y5TimeSeconds, 35.0, 0.0, 0.0, "保留实际右满舵"),
                    Intervention.FullAstern(
                        Y5TimeSeconds, 0.0, "保留实际后退三（近似）")
                });
            scenarios.Add(new WhatIfScenario(
                "Y5", "VEGA DREAM 应急抛锚",
                "VEGA DREAM 于 t=132 s（22:00:42）向右舷应急抛锚，并保留实际右满舵 + 后退三",
                new[] { y5Vessel }, y5Inputs));

            List<SourcedValue> combinedInputs = new List<SourcedValue>(y1Inputs);
            combinedInputs.AddRange(y5Inputs);
            VesselScenario combinedYangze = new VesselScenario(
                Yangze22Id,
                Y1TimeSeconds,
                new[]
                {
                    Intervention.TurnStarboard(
                        Y1TimeSeconds, 35.0, 0.0, 0.0, "正确执行右满舵 +35°")
                });
            VesselScenario combinedVega = new VesselScenario(
                VegaDreamId,
                Y5TimeSeconds,
                new[]
                {
                    Intervention.EmergencyAnchor(
                        Y5TimeSeconds, AnchorSide.Starboard, 0.0, "右舷应急抛锚（假设舷别）"),
                    Intervention.TurnStarboard(
                        Y5TimeSeconds, 35.0, 0.0, 0.0, "保留实际右满舵"),
                    Intervention.FullAstern(
                        Y5TimeSeconds, 0.0, "保留实际后退三（近似）")
                });
            scenarios.Add(new WhatIfScenario(
                "Y1+Y5", "YANGZE 22 右满舵 + VEGA DREAM 应急抛锚",
                "YANGZE 22 于 t=104 s 正确右满舵；VEGA DREAM 于 t=132 s 向右舷应急抛锚并保留实际右满舵/后退三",
                new[] { combinedYangze, combinedVega }, combinedInputs));

            List<SourcedValue> y4Inputs = new List<SourcedValue>
            {
                new SourcedValue(
                    "Y4 干预时刻", Y4TimeSeconds, "s", ValueSource.ReportDerived,
                    "case.json timeline e-y-220045（22:00:45）与 SimEpochLocal（21:58:30）",
                    "推算：22:00:45 − 21:58:30 = 135 s。"),
                new SourcedValue(
                    "Y4 全速后退", 3.0, "档（后退三）", ValueSource.Estimated,
                    "REAL_CASES.md §4.1 Y4；case.json timeline e-y-220045 仅有船首越线记录",
                    "反事实动作：报告未下令全速倒车，按 R8(e) 建议设为后退三；时刻取 22:00:45。")
            };
            VesselScenario y4Vessel = new VesselScenario(
                Yangze22Id,
                Y4TimeSeconds,
                new[] { Intervention.FullAstern(Y4TimeSeconds, 0.0, "全速倒车") });
            scenarios.Add(new WhatIfScenario(
                "Y4", "YANGZE 22 全速倒车（可选）",
                "YANGZE 22 于 t=135 s（22:00:45）偏离原航迹并全速倒车",
                new[] { y4Vessel }, y4Inputs));

            return scenarios;
        }

        private static IReadOnlyList<KinematicState> BuildYangzeTrack(
            IReadOnlyList<ReportTrackRow> rows,
            Yangze22Inputs inputs,
            ManeuverParams parameters,
            double endSeconds,
            List<string> notes,
            double? cutoffSeconds,
            out int removed)
        {
            List<ReportTrackRow> vesselRows = TruncateRows(
                FilterRows(rows, Yangze22Id), cutoffSeconds, inputs.SimEpochLocal, out removed);
            List<ReportTrackRow> positionRows = SelectPositionRows(vesselRows);
            if (positionRows.Count < 2)
            {
                throw new ArgumentException("YANGZE 22 带经纬度的航迹点不足 2 个。", nameof(rows));
            }
            List<TimeValue> headings = BuildSeries(vesselRows, true, inputs.SimEpochLocal);
            List<TimeValue> speeds = BuildSeries(vesselRows, false, inputs.SimEpochLocal);

            List<KinematicState> states = new List<KinematicState>();
            for (int i = 0; i < positionRows.Count; i++)
            {
                ReportTrackRow row = positionRows[i];
                double t = (row.TimeBeijing - inputs.SimEpochLocal).TotalSeconds;
                double heading = InterpolateAngle(headings, t);
                double speed = InterpolateLinear(speeds, t);
                EnuPosition enu = GeoMath.Wgs84ToEnu(
                    new GeoCoord(row.LonDeg.Value, row.LatDeg.Value, 0.0),
                    inputs.CollisionLocation);
                states.Add(new KinematicState(t, enu.EastM, enu.NorthM, heading, speed, 0.0, 0.0));
            }

            states = TrimToEnd(states, endSeconds);
            AppendExtension(states, endSeconds);
            notes.Add("YANGZE 22：采用 " + positionRows.Count + " 个带位置点（VDR/AIS/正文按优先级去重），" +
                      "航向/航速由 " + headings.Count + " 个航向样本、" + speeds.Count + " 个航速样本插值；" +
                      "末点后按最后航向/航速直线延伸至评价结束。");
            return states;
        }

        private static IReadOnlyList<KinematicState> BuildVegaTrack(
            IReadOnlyList<ReportTrackRow> rows,
            Yangze22Inputs inputs,
            ManeuverParams parameters,
            double endSeconds,
            List<string> notes,
            double? cutoffSeconds,
            out int removed)
        {
            List<ReportTrackRow> vesselRows = TruncateRows(
                FilterRows(rows, VegaDreamId), cutoffSeconds, inputs.SimEpochLocal, out removed);
            List<ReportTrackRow> positionRows = SelectPositionRows(vesselRows);
            if (positionRows.Count < 1)
            {
                throw new ArgumentException("VEGA DREAM 缺少带经纬度的航迹点。", nameof(rows));
            }
            List<TimeValue> headings = BuildSeries(vesselRows, true, inputs.SimEpochLocal);
            List<TimeValue> speeds = BuildSeries(vesselRows, false, inputs.SimEpochLocal);
            if (headings.Count == 0 || speeds.Count == 0)
            {
                throw new ArgumentException("VEGA DREAM 缺少航向或航速样本。", nameof(rows));
            }

            // 以最后一个 AIS 位置为锚点，按航向/航速积分反推与延伸，避免 22:00:38→42 的
            // 55 m/4 s 不一致点被线性插值放大（case.json X10）。
            ReportTrackRow anchorRow = positionRows[positionRows.Count - 1];
            double anchorTime = (anchorRow.TimeBeijing - inputs.SimEpochLocal).TotalSeconds;
            EnuPosition anchorEnu = GeoMath.Wgs84ToEnu(
                new GeoCoord(anchorRow.LonDeg.Value, anchorRow.LatDeg.Value, 0.0),
                inputs.CollisionLocation);

            List<KinematicState> states = new List<KinematicState>();
            double anchorHeading = InterpolateAngle(headings, anchorTime);
            double anchorSpeed = InterpolateLinear(speeds, anchorTime);
            states.Add(new KinematicState(anchorTime, anchorEnu.EastM, anchorEnu.NorthM, anchorHeading, anchorSpeed, 0.0, 0.0));

            double east = anchorEnu.EastM;
            double north = anchorEnu.NorthM;
            double previous = anchorTime;
            for (double t = anchorTime - 1.0; t >= 0.0 - 1e-9; t -= 1.0)
            {
                double heading = InterpolateAngle(headings, t);
                double speed = InterpolateLinear(speeds, t);
                double dt = previous - t;
                double rad = heading * Math.PI / 180.0;
                double distance = speed * VesselMotionState.MpsPerKnot * dt;
                east -= Math.Sin(rad) * distance;
                north -= Math.Cos(rad) * distance;
                states.Add(new KinematicState(t, east, north, heading, speed, 0.0, 0.0));
                previous = t;
            }

            east = anchorEnu.EastM;
            north = anchorEnu.NorthM;
            previous = anchorTime;
            for (double t = anchorTime + 1.0; t <= endSeconds + 1e-9; t += 1.0)
            {
                double heading = InterpolateAngle(headings, t);
                double speed = InterpolateLinear(speeds, t);
                double dt = t - previous;
                double rad = heading * Math.PI / 180.0;
                double distance = speed * VesselMotionState.MpsPerKnot * dt;
                east += Math.Sin(rad) * distance;
                north += Math.Cos(rad) * distance;
                states.Add(new KinematicState(t, east, north, heading, speed, 0.0, 0.0));
                previous = t;
            }

            states.Sort((a, b) => a.TimeSeconds.CompareTo(b.TimeSeconds));
            states = TrimToEnd(states, endSeconds);
            AppendExtension(states, endSeconds);

            notes.Add("VEGA DREAM：" + positionRows.Count + " 个带位置点；以 " +
                      inputs.SimEpochLocal.AddSeconds(anchorTime)
                          .ToString("HH:mm:ss", CultureInfo.InvariantCulture) +
                      " AIS 船位为锚点，按航向/航速积分补全为 1 s 序列，标为 Interpolated/推算。");
            return states;
        }

        private static List<ReportTrackRow> FilterRows(IReadOnlyList<ReportTrackRow> rows, string vesselId)
        {
            List<ReportTrackRow> result = new List<ReportTrackRow>();
            for (int i = 0; i < rows.Count; i++)
            {
                if (string.Equals(rows[i].VesselId, vesselId, StringComparison.Ordinal))
                {
                    result.Add(rows[i]);
                }
            }
            return result;
        }

        private static List<ReportTrackRow> SelectPositionRows(List<ReportTrackRow> rows)
        {
            Dictionary<DateTimeOffset, ReportTrackRow> best =
                new Dictionary<DateTimeOffset, ReportTrackRow>();
            Dictionary<DateTimeOffset, int> bestIndex = new Dictionary<DateTimeOffset, int>();
            for (int i = 0; i < rows.Count; i++)
            {
                ReportTrackRow row = rows[i];
                if (!row.HasPosition)
                {
                    continue;
                }
                ReportTrackRow existing;
                if (!best.TryGetValue(row.TimeBeijing, out existing))
                {
                    best.Add(row.TimeBeijing, row);
                    bestIndex.Add(row.TimeBeijing, i);
                    continue;
                }
                int existingIndex = bestIndex[row.TimeBeijing];
                if (row.ProvenancePriority < existing.ProvenancePriority ||
                    (row.ProvenancePriority == existing.ProvenancePriority && i < existingIndex))
                {
                    best[row.TimeBeijing] = row;
                    bestIndex[row.TimeBeijing] = i;
                }
            }

            List<DateTimeOffset> keys = new List<DateTimeOffset>(best.Keys);
            keys.Sort();
            List<ReportTrackRow> result = new List<ReportTrackRow>(keys.Count);
            for (int i = 0; i < keys.Count; i++)
            {
                result.Add(best[keys[i]]);
            }
            return result;
        }

        private static List<TimeValue> BuildSeries(List<ReportTrackRow> rows, bool heading, DateTimeOffset epoch)
        {
            Dictionary<DateTimeOffset, TimeValue> best = new Dictionary<DateTimeOffset, TimeValue>();
            Dictionary<DateTimeOffset, int> priority = new Dictionary<DateTimeOffset, int>();
            Dictionary<DateTimeOffset, int> index = new Dictionary<DateTimeOffset, int>();
            for (int i = 0; i < rows.Count; i++)
            {
                ReportTrackRow row = rows[i];
                double? value = heading ? (row.HdgDeg ?? row.CogDeg) : (row.SogKn ?? row.StwKn);
                if (!value.HasValue)
                {
                    continue;
                }
                int p = row.ProvenancePriority;
                TimeValue existing;
                if (!best.TryGetValue(row.TimeBeijing, out existing))
                {
                    best.Add(row.TimeBeijing, new TimeValue((row.TimeBeijing - epoch).TotalSeconds, value.Value));
                    priority.Add(row.TimeBeijing, p);
                    index.Add(row.TimeBeijing, i);
                    continue;
                }
                if (p < priority[row.TimeBeijing] ||
                    (p == priority[row.TimeBeijing] && i < index[row.TimeBeijing]))
                {
                    best[row.TimeBeijing] = new TimeValue((row.TimeBeijing - epoch).TotalSeconds, value.Value);
                    priority[row.TimeBeijing] = p;
                    index[row.TimeBeijing] = i;
                }
            }

            List<TimeValue> result = new List<TimeValue>(best.Values);
            result.Sort((a, b) => a.TimeSeconds.CompareTo(b.TimeSeconds));
            return result;
        }

        private static List<KinematicState> TrimToEnd(List<KinematicState> states, double endSeconds)
        {
            List<KinematicState> trimmed = new List<KinematicState>();
            for (int i = 0; i < states.Count; i++)
            {
                if (states[i].TimeSeconds <= endSeconds + 1e-9)
                {
                    trimmed.Add(states[i]);
                }
            }
            return trimmed;
        }

        private static void AppendExtension(List<KinematicState> states, double endSeconds)
        {
            KinematicState last = states[states.Count - 1];
            double t = last.TimeSeconds;
            double east = last.EastM;
            double north = last.NorthM;
            while (t < endSeconds - 1e-9)
            {
                double dt = Math.Min(1.0, endSeconds - t);
                double rad = last.HeadingDeg * Math.PI / 180.0;
                double distance = last.SpeedKn * VesselMotionState.MpsPerKnot * dt;
                east += Math.Sin(rad) * distance;
                north += Math.Cos(rad) * distance;
                t += dt;
                states.Add(new KinematicState(t, east, north, last.HeadingDeg, last.SpeedKn, 0.0, 0.0));
            }
        }

        private static double InterpolateLinear(List<TimeValue> series, double timeSeconds)
        {
            if (series.Count == 0)
            {
                return 0.0;
            }
            if (timeSeconds <= series[0].TimeSeconds)
            {
                return series[0].Value;
            }
            if (timeSeconds >= series[series.Count - 1].TimeSeconds)
            {
                return series[series.Count - 1].Value;
            }
            int lo = FindBracket(series, timeSeconds);
            TimeValue a = series[lo];
            TimeValue b = series[lo + 1];
            double span = b.TimeSeconds - a.TimeSeconds;
            double f = span > 1e-12 ? (timeSeconds - a.TimeSeconds) / span : 0.0;
            return a.Value + (b.Value - a.Value) * f;
        }

        private static double InterpolateAngle(List<TimeValue> series, double timeSeconds)
        {
            if (series.Count == 0)
            {
                return 0.0;
            }
            if (timeSeconds <= series[0].TimeSeconds)
            {
                return series[0].Value;
            }
            if (timeSeconds >= series[series.Count - 1].TimeSeconds)
            {
                return series[series.Count - 1].Value;
            }
            int lo = FindBracket(series, timeSeconds);
            TimeValue a = series[lo];
            TimeValue b = series[lo + 1];
            double span = b.TimeSeconds - a.TimeSeconds;
            double f = span > 1e-12 ? (timeSeconds - a.TimeSeconds) / span : 0.0;
            double delta = KinematicState.NormalizeDeg180(b.Value - a.Value);
            return KinematicState.NormalizeAngleDeg(a.Value + delta * f);
        }

        private static int FindBracket(List<TimeValue> series, double timeSeconds)
        {
            int lo = 0;
            int hi = series.Count - 2;
            while (lo <= hi)
            {
                int mid = lo + ((hi - lo) >> 1);
                if (timeSeconds < series[mid].TimeSeconds)
                {
                    hi = mid - 1;
                }
                else if (timeSeconds > series[mid + 1].TimeSeconds)
                {
                    lo = mid + 1;
                }
                else
                {
                    return mid;
                }
            }
            return Math.Max(0, Math.Min(series.Count - 2, lo));
        }

        private static string DescribeCombined(IReadOnlyList<ScenarioResult> results)
        {
            ScenarioResult y1 = null;
            ScenarioResult y5 = null;
            ScenarioResult combined = null;
            for (int i = 0; i < results.Count; i++)
            {
                if (results[i].ScenarioId == "Y1") y1 = results[i];
                else if (results[i].ScenarioId == "Y5") y5 = results[i];
                else if (results[i].ScenarioId == "Y1+Y5") combined = results[i];
            }
            if (y1 == null || y5 == null || combined == null)
            {
                return string.Empty;
            }

            double maximum = Math.Max(y1.MinDistanceNm, y5.MinDistanceNm);
            if (combined.MinDistanceNm >= maximum - 1e-9)
            {
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "Y1+Y5 最小距离 {0:F3} nm ≥ max(Y1,Y5)={1:F3} nm，组合不劣于任一单干预。",
                    combined.MinDistanceNm, maximum);
            }

            return string.Format(
                CultureInfo.InvariantCulture,
                "Y1+Y5 最小距离 {0:F3} nm 小于 max(Y1,Y5)={1:F3} nm，组合效应非单调：" +
                "两船同时改变航迹后，最近会遇点的几何关系不是单干预最近点的简单叠加；" +
                "但组合情景的 OBB 最小净距 {2:F1} m 仍远大于 S0，且未发生碰撞。",
                combined.MinDistanceNm, maximum, combined.MinClearanceM);
        }

        private static string DescribeDeviation(
            Yangze22Inputs inputs,
            ScenarioResult original,
            WhatIfSetup setup)
        {
            double reportTc = (inputs.CollisionTimeBeijing - inputs.SimEpochLocal).TotalSeconds;
            if (original.Collision && original.TcSeconds.HasValue)
            {
                string angleText = original.Geometry != null
                    ? original.Geometry.CollisionAngleDeg.ToString("F1", CultureInfo.InvariantCulture) + "°"
                    : "—";
                string angleDiff = original.Geometry != null
                    ? (original.Geometry.CollisionAngleDeg - inputs.ReportCollisionAngleDeg)
                        .ToString("+0.0;-0.0;0.0", CultureInfo.InvariantCulture) + "°"
                    : "—";
                string side = original.Geometry != null && original.Geometry.IsBowToBow
                    ? ScenarioComparison.ContactPartText(original.Geometry)
                    : original.Geometry != null
                    ? original.Geometry.StruckSide + "，距船首约 " +
                      original.Geometry.ContactFromStruckBowM.ToString("F0", CultureInfo.InvariantCulture) +
                      " m（" + original.Geometry.ContactFromStruckBowRatio.ToString("F2", CultureInfo.InvariantCulture) + " L）"
                    : "—";
                double reportClearance = OrientedBoundingBox.Clearance(
                    original.Tracks[setup.OwnVesselId].ToBodyState(reportTc).Obb,
                    original.Tracks[setup.TargetVesselId].ToBodyState(reportTc).Obb);
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "S0 复现接触：tc={0:F1} s（{1}），与报告 {2:F1} s 偏差 {3:+0.0;-0.0;0.0} s；" +
                    "报告时刻 t={2:F1} s 的 OBB 真实净距为 {9:F1} m（{10}）；" +
                    "计算碰撞角 {4}，与报告 {5:F1}° 偏差 {6}；接触部位 {7}，报告为“{8}”" +
                    "（报告未给第5舱的纵向位置，接触部位只能定性比对）。{11}未为对齐报告调整任何模型参数。",
                    original.TcSeconds.Value,
                    setup.FormatLocalTime(original.TcSeconds.Value),
                    reportTc,
                    original.TcSeconds.Value - reportTc,
                    angleText,
                    inputs.ReportCollisionAngleDeg,
                    angleDiff,
                    side,
                    inputs.ReportContactText,
                    reportClearance,
                    reportClearance > 0.0 ? "未接触" : "已接触",
                    (inputs.TruncateAfterReportedCollision
                        ? "已截掉报告碰撞时刻之后的航迹点，"
                        : "未截断碰撞后航迹点，") +
                    "船位已按【估计】天线位置换算到船中心；");
            }

            double minDistanceM = original.MinDistanceNm * 1852.0;
            return string.Format(
                CultureInfo.InvariantCulture,
                "S0 未复现接触：最小船中心距 {0:F3} nm（{1:F0} m），最近时刻 t={2:F1} s（{3}），" +
                "OBB 最小净距 {4:F1} m；报告认定 t={5:F1} s（{6}）发生接触、碰撞角约 {7:F1}°、" +
                "“{8}”。偏差：最小中心距 {1:F0} m > 0，接触时刻与碰撞角因无接触不可比；" +
                "原因包括 VDR/AIS 船位为天线位置、两船天线偏移未给、航迹点稀疏（YANGZE 22 约 9–12 个位置点，" +
                "VEGA DREAM 仅 3 个）以及报告 §8/X10 已指出 AIS 船位间距大于报告船体距离；" +
                "未为迎合报告而修改或加密报告数据。",
                original.MinDistanceNm,
                minDistanceM,
                original.MinDistanceTimeSeconds,
                setup.FormatLocalTime(original.MinDistanceTimeSeconds),
                original.MinClearanceM,
                reportTc,
                setup.FormatLocalTime(reportTc),
                inputs.ReportCollisionAngleDeg,
                inputs.ReportContactText);
        }

        private readonly struct TimeValue
        {
            public readonly double TimeSeconds;
            public readonly double Value;

            public TimeValue(double timeSeconds, double value)
            {
                TimeSeconds = timeSeconds;
                Value = value;
            }
        }
    }
}
