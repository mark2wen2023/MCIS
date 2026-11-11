using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Colreg
{
    /// <summary>按碰撞危险、互见条件与相对几何确定的会遇局面。</summary>
    public enum EncounterSituation
    {
        /// <summary>未达到碰撞危险判据。</summary>
        NoCollisionRisk,
        /// <summary>对遇。</summary>
        HeadOn,
        /// <summary>交叉。</summary>
        Crossing,
        /// <summary>追越。</summary>
        Overtaking,
        /// <summary>能见度不良或未互见。</summary>
        RestrictedVisibility,
        /// <summary>狭水道契约局面；航道侧位由 R9 核查，会遇时间带保留会遇类型。</summary>
        NarrowChannel,
        /// <summary>仅兼容旧合同数据；引擎保留会遇类型，紧迫危险通过 DangerStage 表达。</summary>
        ImmediateDanger,
        /// <summary>碰撞后；保留给适配层和人工研判。</summary>
        PostCollision,
        /// <summary>无法确定。</summary>
        Undetermined
    }

    /// <summary>本次技术分析中的行动角色。</summary>
    public enum TrafficRole
    {
        /// <summary>本时段无让路或直航划分。</summary>
        None,
        /// <summary>让路船。</summary>
        GiveWay,
        /// <summary>直航船。</summary>
        StandOn,
        /// <summary>双方均有行动义务。</summary>
        BothActionRequired,
        /// <summary>角色尚未确定，等待稳定航向或人工研判。</summary>
        Undetermined
    }

    /// <summary>逐条核查状态；合同映射：Satisfied→Complies、NotSatisfied→NotComplied，其余同名。</summary>
    public enum RuleCheckStatus
    {
        /// <summary>满足本项确定性技术判据。</summary>
        Satisfied,
        /// <summary>不满足本项确定性技术判据。</summary>
        NotSatisfied,
        /// <summary>本区段不适用；适用但缺少资料时使用 NotAssessable。</summary>
        NotApplicable,
        /// <summary>仅有部分条件得到满足或证实。</summary>
        Partial,
        /// <summary>需结合补充资料人工研判。</summary>
        NeedsReview,
        /// <summary>现有资料不能评估；核查说明列出所需证据。</summary>
        NotAssessable
    }

    /// <summary>本阶段规则标识。</summary>
    public enum ColregRuleId
    {
        /// <summary>避免碰撞的行动。</summary>
        R8,
        /// <summary>狭水道。</summary>
        R9,
        /// <summary>追越。</summary>
        R13,
        /// <summary>对遇。</summary>
        R14,
        /// <summary>交叉相遇。</summary>
        R15,
        /// <summary>让路船的行动。</summary>
        R16,
        /// <summary>直航船的行动。</summary>
        R17,
        /// <summary>能见度不良时的行动。</summary>
        R19,
        /// <summary>瞭望。</summary>
        R5,
        /// <summary>安全航速。</summary>
        R6,
        /// <summary>碰撞危险判断。</summary>
        R7,
        /// <summary>操纵、警告和能见度不良声号。</summary>
        R34_35,
        /// <summary>船舶之间的责任。</summary>
        R18
    }

    /// <summary>由 CPA 阈值确定的危险阶段；不替代原会遇局面。合同映射：CollisionRisk→None，其余同名。</summary>
    public enum ColregDangerStage
    {
        None,
        CollisionRisk,
        CloseQuarters,
        ImmediateDanger
    }

    /// <summary>核查项人工确认状态；默认值为草稿。</summary>
    public enum ColregReviewStatus
    {
        Draft,
        Confirmed,
        Rejected,
        Modified
    }

    /// <summary>显式互见状态样本；自该时刻起阶梯保持，并保留精确切分时刻。</summary>
    public sealed class ColregInSightSample
    {
        public SimTime Time { get; }
        public bool InSight { get; }

        public ColregInSightSample(SimTime time, bool inSight)
        {
            Time = time;
            InSight = inSight;
        }
    }

    /// <summary>独立危险阶段区间，不据此切分或替换会遇局面；合同映射 CollisionRisk→None。</summary>
    public sealed class ColregStageInterval
    {
        public SimTime StartTime { get; }
        public SimTime EndTime { get; }
        public ColregDangerStage Stage { get; }
        public string StageId { get; }

        public ColregStageInterval(SimTime startTime, SimTime endTime, ColregDangerStage stage,
            string stageId = null)
        {
            StartTime = startTime;
            EndTime = endTime;
            Stage = stage;
            StageId = stageId;
        }
    }

    /// <summary>实际观测到的转向方向；净变化在容差内时保留观察过程中主要曾发生的方向。</summary>
    public enum TurnDirection
    {
        /// <summary>未超过保向容差。</summary>
        None,
        /// <summary>向右转向。</summary>
        Starboard,
        /// <summary>向左转向。</summary>
        Port
    }

    /// <summary>实际观测到的变速类别；净变化在容差内时保留观察过程中主要曾发生的方向。</summary>
    public enum SpeedChange
    {
        /// <summary>未超过保速容差。</summary>
        Steady,
        /// <summary>加速。</summary>
        Accelerating,
        /// <summary>减速。</summary>
        Decelerating
    }

    /// <summary>两船会遇分析请求；输入航迹和环境按时间严格升序，构造时建立集合快照。</summary>
    public sealed class ColregAnalysisRequest
    {
        /// <summary>本船标识。</summary>
        public string OwnVesselId { get; }
        /// <summary>他船标识。</summary>
        public string TargetVesselId { get; }
        /// <summary>本船航迹样本。</summary>
        public IReadOnlyList<TrackSample> OwnSamples { get; }
        /// <summary>他船航迹样本。</summary>
        public IReadOnlyList<TrackSample> TargetSamples { get; }
        /// <summary>本次使用的阈值。</summary>
        public ColregThresholds Thresholds { get; }
        /// <summary>环境状态序列；状态自其时刻起生效。</summary>
        public IReadOnlyList<EnvironmentState> Environment { get; }
        /// <summary>未提供环境状态覆盖时使用的能见度；空值表示未提供。</summary>
        public double? VisibilityNm { get; }
        /// <summary>显式互见条件；空值表示按能见度采用技术假设。</summary>
        public bool? VesselsInSight { get; }
        /// <summary>是否处于狭水道。</summary>
        public bool InNarrowChannel { get; }
        /// <summary>可选案件时间纪元，供展示层格式化钟面时间。</summary>
        public DateTimeOffset? CaseEpochUtc { get; }
        /// <summary>显式互见序列；最近过去样本优先于标量入口。</summary>
        public IReadOnlyList<ColregInSightSample> InSightSamples { get; }
        /// <summary>有序航道中心线，单位为 ENU 米；用于 R9 局部航向侧位核查。</summary>
        public IReadOnlyList<EnuPosition> ChannelCenterline { get; }
        /// <summary>用于派生确定性输出标识的案件标识。</summary>
        public string CaseId { get; }
        /// <summary>传递到每条核查结果的原始证据标识，保留顺序及重复。</summary>
        public IReadOnlyList<string> EvidenceIds { get; }
        /// <summary>可选船舶状态序列；同船时间严格递增并阶梯保持，首个样本前按 Unknown 分析。</summary>
        public IReadOnlyList<ColregVesselStatusSample> VesselStatusSamples { get; }

        /// <summary>构造两船会遇分析请求；无效参数由分析入口返回失败结果。</summary>
        public ColregAnalysisRequest(
            string ownVesselId,
            string targetVesselId,
            IReadOnlyList<TrackSample> ownSamples,
            IReadOnlyList<TrackSample> targetSamples,
            ColregThresholds thresholds = null,
            IReadOnlyList<EnvironmentState> environment = null,
            double? visibilityNm = null,
            bool? vesselsInSight = null,
            bool inNarrowChannel = false,
            DateTimeOffset? caseEpochUtc = null,
            IReadOnlyList<ColregInSightSample> inSightSamples = null,
            IReadOnlyList<EnuPosition> channelCenterline = null,
            string caseId = "case",
            IReadOnlyList<string> evidenceIds = null,
            IReadOnlyList<ColregVesselStatusSample> vesselStatusSamples = null)
        {
            OwnVesselId = ownVesselId;
            TargetVesselId = targetVesselId;
            OwnSamples = ownSamples == null ? null : new List<TrackSample>(ownSamples).AsReadOnly();
            TargetSamples = targetSamples == null ? null : new List<TrackSample>(targetSamples).AsReadOnly();
            Thresholds = thresholds ?? ColregThresholds.Default;
            Environment = new List<EnvironmentState>(environment ?? Array.Empty<EnvironmentState>()).AsReadOnly();
            VisibilityNm = visibilityNm;
            VesselsInSight = vesselsInSight;
            InNarrowChannel = inNarrowChannel;
            CaseEpochUtc = caseEpochUtc;
            InSightSamples = inSightSamples == null ? null : new List<ColregInSightSample>(inSightSamples).AsReadOnly();
            ChannelCenterline = channelCenterline == null ? null : new List<EnuPosition>(channelCenterline).AsReadOnly();
            CaseId = caseId ?? "case";
            EvidenceIds = new List<string>(evidenceIds ?? Array.Empty<string>()).AsReadOnly();
            VesselStatusSamples = vesselStatusSamples == null ? null :
                new List<ColregVesselStatusSample>(vesselStatusSamples).AsReadOnly();
        }
    }

    /// <summary>相邻且局面、适用规则、双方角色一致的合并时间带。</summary>
    public sealed class ColregTimeBand
    {
        /// <summary>起始时刻。</summary>
        public SimTime StartTime { get; }
        /// <summary>结束时刻；除报告末端外，边界时刻归属于后一时间带。</summary>
        public SimTime EndTime { get; }
        /// <summary>会遇局面。</summary>
        public EncounterSituation Situation { get; }
        /// <summary>本船角色。</summary>
        public TrafficRole OwnRole { get; }
        /// <summary>他船角色。</summary>
        public TrafficRole TargetRole { get; }
        /// <summary>适用规则清单。</summary>
        public IReadOnlyList<ColregRuleId> ApplicableRules { get; }
        // 确定性交换元数据；默认参数保留原构造入口兼容。
        public bool? InSight { get; }
        public string BandId { get; }
        public string GiveWayVesselId { get; }
        public string StandOnVesselId { get; }
        public string Basis { get; }
        public bool Doubt { get; }
        /// <summary>带内最高危险阶段；精确阶段区间见报告 DangerStages，合同映射 CollisionRisk→None。</summary>
        public ColregDangerStage DangerStage { get; }
        /// <summary>合同存疑原因；无存疑时为空，取值见 ColregDoubtReasons。</summary>
        public string DoubtReason { get; }
        /// <summary>按船号索引的状态快照；引擎输出包含两船，未给状态时为 Unknown。</summary>
        public IReadOnlyDictionary<string, ColregVesselStatus> VesselStatus { get; }

        /// <summary>构造会遇时间带。</summary>
        public ColregTimeBand(SimTime startTime, SimTime endTime, EncounterSituation situation,
            TrafficRole ownRole, TrafficRole targetRole, IReadOnlyList<ColregRuleId> applicableRules,
            bool? inSight = null, string bandId = null, string giveWayVesselId = null,
            string standOnVesselId = null, string basis = null, bool doubt = false,
            ColregDangerStage dangerStage = ColregDangerStage.None,
            string doubtReason = null,
            IReadOnlyDictionary<string, ColregVesselStatus> vesselStatus = null)
        {
            StartTime = startTime;
            EndTime = endTime;
            Situation = situation;
            OwnRole = ownRole;
            TargetRole = targetRole;
            ApplicableRules = new List<ColregRuleId>(applicableRules ?? Array.Empty<ColregRuleId>()).AsReadOnly();
            InSight = inSight;
            BandId = bandId;
            GiveWayVesselId = giveWayVesselId;
            StandOnVesselId = standOnVesselId;
            Basis = basis;
            Doubt = doubt;
            DangerStage = dangerStage;
            DoubtReason = doubtReason;
            var statusSnapshot = new Dictionary<string, ColregVesselStatus>();
            if (vesselStatus != null)
                foreach (var status in vesselStatus) statusSnapshot.Add(status.Key, status.Value);
            VesselStatus = new ReadOnlyDictionary<string, ColregVesselStatus>(statusSnapshot);
        }
    }

    /// <summary>同一核查时段内的实际操纵，包括净变化和中途最大偏移，避免往返操纵相互抵消。</summary>
    public readonly struct ObservedManeuver
    {
        /// <summary>累计净航向变化，向右为正。</summary>
        public double HeadingChangeDeg { get; }
        /// <summary>净航速变化，增加为正。</summary>
        public double SpeedChangeMps { get; }
        /// <summary>转向方向；净变化在保向容差内时采用观察过程中主要曾发生的转向方向。</summary>
        public TurnDirection Turn { get; }
        /// <summary>变速类别；净变化在保速容差内时采用观察过程中主要曾发生的变速方向。</summary>
        public SpeedChange Speed { get; }
        /// <summary>观察过程中相对此前最小展开航向的最大向右转幅，可捕获折返操纵。</summary>
        public double MaxStarboardTurnDeg { get; }
        /// <summary>观察过程中相对此前最大展开航向的最大向左转幅，采用非负值，可捕获折返操纵。</summary>
        public double MaxPortTurnDeg { get; }
        /// <summary>相对时段起点的最大航速增加。</summary>
        public double MaxSpeedIncreaseMps { get; }
        /// <summary>相对时段起点的最大航速降低，采用非负值。</summary>
        public double MaxSpeedDecreaseMps { get; }
        /// <summary>首次达到明显操纵阈值的时刻；未达到时为空。</summary>
        public SimTime? FirstSubstantialActionTime { get; }
        /// <summary>实际观察时长；零时长不能证实已经采取操纵。</summary>
        public double ObservedDurationSeconds { get; }

        /// <summary>构造实际操纵的不可变摘要。</summary>
        public ObservedManeuver(double headingChangeDeg, double speedChangeMps, TurnDirection turn,
            SpeedChange speed, double maxStarboardTurnDeg, double maxPortTurnDeg,
            double maxSpeedIncreaseMps, double maxSpeedDecreaseMps,
            SimTime? firstSubstantialActionTime, double observedDurationSeconds)
        {
            HeadingChangeDeg = headingChangeDeg;
            SpeedChangeMps = speedChangeMps;
            Turn = turn;
            Speed = speed;
            MaxStarboardTurnDeg = maxStarboardTurnDeg;
            MaxPortTurnDeg = maxPortTurnDeg;
            MaxSpeedIncreaseMps = maxSpeedIncreaseMps;
            MaxSpeedDecreaseMps = maxSpeedDecreaseMps;
            FirstSubstantialActionTime = firstSubstantialActionTime;
            ObservedDurationSeconds = observedDurationSeconds;
        }
    }

    /// <summary>规则核查使用的数值依据；距离采用米，时间采用秒，航向角采用度。</summary>
    public sealed class ColregEvidence
    {
        /// <summary>他船相对受核查船船首的方位，右舷方向为正，范围为零至三百六十度。</summary>
        public double RelativeBearingDeg { get; }
        /// <summary>双方船首向最小夹角。</summary>
        public double HeadingDifferenceDeg { get; }
        /// <summary>时段开始时的 DCPA。</summary>
        public double DcpaM { get; }
        /// <summary>时段开始时的 TCPA。</summary>
        public double TcpaSeconds { get; }
        /// <summary>时段内净航向变化，向右为正。</summary>
        public double HeadingChangeDeg { get; }
        /// <summary>时段内净航速变化，增加为正。</summary>
        public double SpeedChangeMps { get; }
        /// <summary>能见度，单位为海里；正无穷表示没有提供资料。</summary>
        public double VisibilityNm { get; }
        /// <summary>时段开始时的两船距离。</summary>
        public double DistanceM { get; }
        /// <summary>时段结束时的 DCPA。</summary>
        public double EndDcpaM { get; }
        /// <summary>时段内观测轨迹的最小船中心距离，单位为米；不是船体净距，未提供时为非数值。</summary>
        public double MinimumObservedDistanceM { get; }
        /// <summary>时段结束时的 TCPA，单位为秒；未提供时为非数值。</summary>
        public double EndTcpaSeconds { get; }
        /// <summary>时段结束时的船中心距离，单位为米；未提供时为非数值。</summary>
        public double EndDistanceM { get; }
        /// <summary>首次达到明显操纵阈值时的剩余 TCPA，单位为秒；无明显动作或未提供时为非数值。</summary>
        public double EarlyActionRemainingTcpaSeconds { get; }
        /// <summary>首次达到明显操纵阈值时的船中心距离，单位为米；无明显动作或未提供时为非数值。</summary>
        public double EarlyActionDistanceM { get; }

        /// <summary>构造核查依据快照；可选审计字段在未提供时保留为非数值。</summary>
        public ColregEvidence(double relativeBearingDeg, double headingDifferenceDeg, double dcpaM,
            double tcpaSeconds, double headingChangeDeg, double speedChangeMps, double visibilityNm,
            double distanceM, double endDcpaM, double minimumObservedDistanceM = double.NaN,
            double endTcpaSeconds = double.NaN, double endDistanceM = double.NaN,
            double earlyActionRemainingTcpaSeconds = double.NaN, double earlyActionDistanceM = double.NaN)
        {
            RelativeBearingDeg = relativeBearingDeg;
            HeadingDifferenceDeg = headingDifferenceDeg;
            DcpaM = dcpaM;
            TcpaSeconds = tcpaSeconds;
            HeadingChangeDeg = headingChangeDeg;
            SpeedChangeMps = speedChangeMps;
            VisibilityNm = visibilityNm;
            DistanceM = distanceM;
            EndDcpaM = endDcpaM;
            MinimumObservedDistanceM = minimumObservedDistanceM;
            EndTcpaSeconds = endTcpaSeconds;
            EndDistanceM = endDistanceM;
            EarlyActionRemainingTcpaSeconds = earlyActionRemainingTcpaSeconds;
            EarlyActionDistanceM = earlyActionDistanceM;
        }
    }

    /// <summary>针对一船的一项规则核查，应采取行动与实际操纵对应相同起止时段。</summary>
    public sealed class ColregRuleCheck
    {
        /// <summary>核查起始时刻。</summary>
        public SimTime StartTime { get; }
        /// <summary>核查结束时刻。</summary>
        public SimTime EndTime { get; }
        /// <summary>规则标识。</summary>
        public ColregRuleId RuleId { get; }
        /// <summary>受核查船标识。</summary>
        public string VesselId { get; }
        /// <summary>核查状态。</summary>
        public RuleCheckStatus Status { get; }
        /// <summary>条款或技术核查子项标识。</summary>
        public string Clause { get; }
        /// <summary>应采取的行动。</summary>
        public string ExpectedAction { get; }
        /// <summary>同一时段内的实际操纵。</summary>
        public ObservedManeuver ActualAction { get; }
        /// <summary>数值依据。</summary>
        public ColregEvidence Evidence { get; }
        /// <summary>状态理由及资料限制。</summary>
        public string Explanation { get; }
        // 引擎输出恒为草稿，证据标识保留请求中的原始值。
        public string CheckId { get; }
        public ColregReviewStatus ReviewStatus { get; }
        public IReadOnlyList<string> EvidenceIds { get; }
        public double? AtTimeSec { get; }

        /// <summary>构造逐条规则核查结果。</summary>
        public ColregRuleCheck(SimTime startTime, SimTime endTime, ColregRuleId ruleId, string vesselId,
            RuleCheckStatus status, string clause, string expectedAction, ObservedManeuver actualAction,
            ColregEvidence evidence, string explanation, string checkId = null,
            ColregReviewStatus reviewStatus = ColregReviewStatus.Draft,
            IReadOnlyList<string> evidenceIds = null, double? atTimeSec = null)
        {
            StartTime = startTime;
            EndTime = endTime;
            RuleId = ruleId;
            VesselId = vesselId;
            Status = status;
            Clause = clause;
            ExpectedAction = expectedAction;
            ActualAction = actualAction;
            Evidence = evidence;
            Explanation = explanation;
            CheckId = checkId;
            ReviewStatus = reviewStatus;
            EvidenceIds = new List<string>(evidenceIds ?? Array.Empty<string>()).AsReadOnly();
            AtTimeSec = atTimeSec;
        }
    }

    /// <summary>可审计的会遇技术分析报告，包含阈值快照、时间带和逐条行动对照。</summary>
    public sealed class ColregAnalysisReport
    {
        /// <summary>固定免责声明原文。</summary>
        public const string RequiredDisclaimer = "仅作安全调查技术分析，不作责任认定。";
        /// <summary>分析的两船配对。</summary>
        public CpaPairKey Pair { get; }
        /// <summary>合并的局面时间带。</summary>
        public IReadOnlyList<ColregTimeBand> TimeBands { get; }
        /// <summary>逐条核查结果，保留不适用项。</summary>
        public IReadOnlyList<ColregRuleCheck> RuleChecks { get; }
        /// <summary>适用条目的应采取与实际行动对照。</summary>
        public IReadOnlyList<ColregRuleCheck> ActionComparisons { get; }
        /// <summary>报告固定显示的免责声明。</summary>
        public string Disclaimer { get { return RequiredDisclaimer; } }
        /// <summary>本次实际使用的全部阈值。</summary>
        public ColregThresholds Thresholds { get; }
        /// <summary>可选案件时间纪元。</summary>
        public DateTimeOffset? CaseEpochUtc { get; }
        /// <summary>本次分析采用的技术假设和资料限制。</summary>
        public IReadOnlyList<string> Assumptions { get; }
        /// <summary>独立于会遇时间带的危险阶段区间，含确定性标识。</summary>
        public IReadOnlyList<ColregStageInterval> DangerStages { get; }

        /// <summary>构造报告并建立只读集合快照。</summary>
        public ColregAnalysisReport(CpaPairKey pair, IReadOnlyList<ColregTimeBand> timeBands,
            IReadOnlyList<ColregRuleCheck> ruleChecks, ColregThresholds thresholds,
            DateTimeOffset? caseEpochUtc = null, IReadOnlyList<string> assumptions = null,
            IReadOnlyList<ColregStageInterval> dangerStages = null)
        {
            Pair = pair;
            TimeBands = new List<ColregTimeBand>(timeBands ?? Array.Empty<ColregTimeBand>()).AsReadOnly();
            RuleChecks = new List<ColregRuleCheck>(ruleChecks ?? Array.Empty<ColregRuleCheck>()).AsReadOnly();
            var comparisons = new List<ColregRuleCheck>();
            for (int i = 0; i < RuleChecks.Count; i++)
            {
                if (RuleChecks[i].Status != RuleCheckStatus.NotApplicable) comparisons.Add(RuleChecks[i]);
            }
            ActionComparisons = comparisons.AsReadOnly();
            Thresholds = thresholds ?? ColregThresholds.Default;
            CaseEpochUtc = caseEpochUtc;
            Assumptions = new List<string>(assumptions ?? Array.Empty<string>()).AsReadOnly();
            DangerStages = new List<ColregStageInterval>(dangerStages ?? Array.Empty<ColregStageInterval>()).AsReadOnly();
        }
    }
}
