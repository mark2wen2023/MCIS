using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// 反事实仿真中的船舶水平运动学状态（局部 ENU 米制坐标与航海单位混用）。
    /// 本类型为不可变值类型，所有角度按真北顺时针计。
    /// </summary>
    public readonly struct KinematicState : IEquatable<KinematicState>
    {
        /// <summary>仿真相对时间（秒）。</summary>
        public double TimeSeconds { get; }

        /// <summary>东向位置（米）。</summary>
        public double EastM { get; }

        /// <summary>北向位置（米）。</summary>
        public double NorthM { get; }

        /// <summary>船首向（度，真北顺时针，0–360）。</summary>
        public double HeadingDeg { get; }

        /// <summary>对地航速（节）。</summary>
        public double SpeedKn { get; }

        /// <summary>转首率（度/秒，右转为正）。</summary>
        public double RotDegPerSec { get; }

        /// <summary>当前舵角（度，右舵为正）。</summary>
        public double RudderDeg { get; }

        /// <summary>构造运动学状态；航向归一化到 [0, 360)。</summary>
        public KinematicState(
            double timeSeconds,
            double eastM,
            double northM,
            double headingDeg,
            double speedKn,
            double rotDegPerSec = 0.0,
            double rudderDeg = 0.0)
        {
            TimeSeconds = timeSeconds;
            EastM = eastM;
            NorthM = northM;
            HeadingDeg = NormalizeAngleDeg(headingDeg);
            SpeedKn = speedKn;
            RotDegPerSec = rotDegPerSec;
            RudderDeg = rudderDeg;
        }

        /// <summary>返回位置与航向按最短弧插值后的状态副本。</summary>
        public static KinematicState Lerp(KinematicState a, KinematicState b, double t)
        {
            double f = t;
            if (f < 0.0) f = 0.0;
            if (f > 1.0) f = 1.0;
            double delta = NormalizeDeg180(b.HeadingDeg - a.HeadingDeg);
            return new KinematicState(
                a.TimeSeconds + (b.TimeSeconds - a.TimeSeconds) * f,
                a.EastM + (b.EastM - a.EastM) * f,
                a.NorthM + (b.NorthM - a.NorthM) * f,
                a.HeadingDeg + delta * f,
                a.SpeedKn + (b.SpeedKn - a.SpeedKn) * f,
                a.RotDegPerSec + (b.RotDegPerSec - a.RotDegPerSec) * f,
                a.RudderDeg + (b.RudderDeg - a.RudderDeg) * f);
        }

        /// <summary>判断两个状态的全部数值字段是否逐位相等。</summary>
        public bool Equals(KinematicState other)
        {
            return TimeSeconds.Equals(other.TimeSeconds) &&
                   EastM.Equals(other.EastM) &&
                   NorthM.Equals(other.NorthM) &&
                   HeadingDeg.Equals(other.HeadingDeg) &&
                   SpeedKn.Equals(other.SpeedKn) &&
                   RotDegPerSec.Equals(other.RotDegPerSec) &&
                   RudderDeg.Equals(other.RudderDeg);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is KinematicState other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = TimeSeconds.GetHashCode();
                hash = (hash * 397) ^ EastM.GetHashCode();
                hash = (hash * 397) ^ NorthM.GetHashCode();
                hash = (hash * 397) ^ HeadingDeg.GetHashCode();
                hash = (hash * 397) ^ SpeedKn.GetHashCode();
                hash = (hash * 397) ^ RotDegPerSec.GetHashCode();
                hash = (hash * 397) ^ RudderDeg.GetHashCode();
                return hash;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "t={0:F2}s ENU=({1:F1},{2:F1})m HDG={3:F2}° SOG={4:F2}kn ROT={5:F3}°/s δ={6:F2}°",
                TimeSeconds, EastM, NorthM, HeadingDeg, SpeedKn, RotDegPerSec, RudderDeg);
        }

        internal static double NormalizeAngleDeg(double deg)
        {
            double m = deg % 360.0;
            if (m < 0.0) m += 360.0;
            if (m >= 360.0) m -= 360.0;
            return m;
        }

        internal static double NormalizeDeg180(double deg)
        {
            double m = deg % 360.0;
            if (m > 180.0) m -= 360.0;
            if (m < -180.0) m += 360.0;
            return m;
        }
    }

    /// <summary>应急抛锚的舷别（单锚时船首向抛锚舷偏转）。</summary>
    public enum AnchorSide
    {
        /// <summary>左舷锚（船首向左偏转）。</summary>
        Port = 0,
        /// <summary>右舷锚（船首向右偏转）。</summary>
        Starboard = 1,
        /// <summary>双锚（左右偏转相互抵消，不产生附加转首）。</summary>
        Both = 2
    }

    /// <summary>
    /// 应急抛锚的简化模型参数。所有默认值均为估计值：报告未给出锚重、抓力、底质与锚链动力学。
    /// </summary>
    public sealed class AnchorParams
    {
        /// <summary>松锚到锚爪抓底（开始产生有效阻力）的时间（秒，估计）。</summary>
        public double LetGoToBiteSec { get; }

        /// <summary>抓底后对船的附加恒定减速度（节/秒，估计）。</summary>
        public double DecelerationKnPerSec { get; }

        /// <summary>单锚时附加转首率（度/秒，估计；Both 时模型取 0）。</summary>
        public double YawRateDegPerSec { get; }

        /// <summary>锚能有效减速的最大航速（节，估计）；超过后按 MaxEffectiveSpeedKn/u 折减。</summary>
        public double MaxEffectiveSpeedKn { get; }

        /// <summary>
        /// 单锚转首率达到满值所需的最低航速（节，估计）。低于该航速时转首率按
        /// (u − MinSpeed)/(FullYawSpeedKn − MinSpeed) 线性衰减，停船（u ≤ MinSpeed）后为 0。
        /// </summary>
        public double FullYawSpeedKn { get; }

        /// <summary>单锚转首满值航速默认值（节，估计：锚链拖曳产生的转首力矩随对水速度减小，取 2 kn 量级）。</summary>
        public const double DefaultFullYawSpeedKn = 2.0;

        /// <summary>构造锚泊模型参数。</summary>
        public AnchorParams(
            double letGoToBiteSec = 12.0,
            double decelerationKnPerSec = 0.08,
            double yawRateDegPerSec = 0.30,
            double maxEffectiveSpeedKn = 6.0,
            double fullYawSpeedKn = DefaultFullYawSpeedKn)
        {
            FullYawSpeedKn = fullYawSpeedKn;
            LetGoToBiteSec = letGoToBiteSec;
            DecelerationKnPerSec = decelerationKnPerSec;
            YawRateDegPerSec = yawRateDegPerSec;
            MaxEffectiveSpeedKn = maxEffectiveSpeedKn;
        }

        /// <summary>
        /// 按排水量量级生成默认锚参数（估计）：以 70,000 t 船、约 10 kn 为基准，
        /// 减速度按排水量 −1/3 次方缩放（抓力约随排水量 2/3 次方、惯性随排水量一次方）。
        /// 抓底延迟 12 s、单锚偏转 0.30°/s、有效航速上限 6 kn 为同类散货船量级假设。
        /// </summary>
        public static AnchorParams Default(double displacementTons)
        {
            double mass = displacementTons > 0.0 ? displacementTons : 70000.0;
            double decel = 0.08 * Math.Pow(70000.0 / mass, 1.0 / 3.0);
            return new AnchorParams(12.0, decel, 0.30, 6.0, DefaultFullYawSpeedKn);
        }

        /// <summary>校验锚参数；返回中文错误说明列表，空列表表示通过。</summary>
        public IReadOnlyList<string> Validate()
        {
            List<string> errors = new List<string>();
            if (double.IsNaN(LetGoToBiteSec) || double.IsInfinity(LetGoToBiteSec) || LetGoToBiteSec < 0.0)
            {
                errors.Add("松锚到抓底时间必须为非负有限数（s）。");
            }
            if (double.IsNaN(DecelerationKnPerSec) || double.IsInfinity(DecelerationKnPerSec) || DecelerationKnPerSec < 0.0)
            {
                errors.Add("锚附加减速度必须为非负有限数（kn/s）。");
            }
            if (double.IsNaN(YawRateDegPerSec) || double.IsInfinity(YawRateDegPerSec) || YawRateDegPerSec < 0.0)
            {
                errors.Add("锚附加转首率必须为非负有限数（°/s）。");
            }
            if (double.IsNaN(MaxEffectiveSpeedKn) || double.IsInfinity(MaxEffectiveSpeedKn) || MaxEffectiveSpeedKn <= 0.0)
            {
                errors.Add("锚有效航速上限必须为有限正数（kn）。");
            }
            if (double.IsNaN(FullYawSpeedKn) || double.IsInfinity(FullYawSpeedKn) || FullYawSpeedKn <= 0.0)
            {
                errors.Add("锚转首满值航速必须为有限正数（kn）。");
            }
            return new ReadOnlyCollection<string>(errors);
        }
    }

    /// <summary>
    /// 一阶 Nomoto 操纵模型与一阶航速响应参数，按船配置。
    /// </summary>
    public sealed class ManeuverParams
    {
        /// <summary>Nomoto 回转性指数 K（1/s，参考航速下）。</summary>
        public double K { get; }

        /// <summary>Nomoto 追随性指数 T（秒）。</summary>
        public double T { get; }

        /// <summary>K 的参考航速（节）。</summary>
        public double ReferenceSpeedKn { get; }

        /// <summary>最大舵角（度，默认 35）。</summary>
        public double MaxRudderDeg { get; }

        /// <summary>舵机速率限制（度/秒，默认 2.5）。</summary>
        public double RudderRateDegPerSec { get; }

        /// <summary>常规变速一阶时间常数（秒）。</summary>
        public double SpeedTimeConstantSec { get; }

        /// <summary>停车（主机停车）一阶时间常数（秒）。</summary>
        public double StopTimeConstantSec { get; }

        /// <summary>全速后退一阶时间常数（秒，通常更短）。</summary>
        public double AsternTimeConstantSec { get; }

        /// <summary>最低航速（节，默认 0）。</summary>
        public double MinSpeedKn { get; }

        /// <summary>船舶总长 LOA（米）。</summary>
        public double LoaM { get; }

        /// <summary>船舶型宽（米）。</summary>
        public double BeamM { get; }

        /// <summary>排水量（吨）。</summary>
        public double DisplacementTons { get; }

        /// <summary>应急抛锚简化模型参数（默认按排水量量级估计）。</summary>
        public AnchorParams Anchor { get; }

        /// <summary>构造操纵模型参数。</summary>
        public ManeuverParams(
            double k,
            double t,
            double referenceSpeedKn,
            double maxRudderDeg = 35.0,
            double rudderRateDegPerSec = 2.5,
            double speedTimeConstantSec = 90.0,
            double stopTimeConstantSec = 60.0,
            double asternTimeConstantSec = 30.0,
            double minSpeedKn = 0.0,
            double loaM = 100.0,
            double beamM = 15.0,
            double displacementTons = 5000.0,
            AnchorParams anchor = null)
        {
            K = k;
            T = t;
            ReferenceSpeedKn = referenceSpeedKn;
            MaxRudderDeg = maxRudderDeg;
            RudderRateDegPerSec = rudderRateDegPerSec;
            SpeedTimeConstantSec = speedTimeConstantSec;
            StopTimeConstantSec = stopTimeConstantSec;
            AsternTimeConstantSec = asternTimeConstantSec;
            MinSpeedKn = minSpeedKn;
            LoaM = loaM;
            BeamM = beamM;
            DisplacementTons = displacementTons;
            Anchor = anchor ?? AnchorParams.Default(displacementTons);
        }

        /// <summary>
        /// 按船体尺度生成默认操纵参数（K=0.10 1/s、T=60 s、参考航速 12 kn）。
        /// </summary>
        public static ManeuverParams Default(double loaM, double beamM, double displacementTons)
        {
            return new ManeuverParams(
                0.10, 60.0, 12.0,
                35.0, 2.5, 90.0, 60.0, 30.0, 0.0,
                loaM, beamM, displacementTons);
        }

        /// <summary>校验参数；返回中文错误说明列表，空列表表示通过。</summary>
        public IReadOnlyList<string> Validate()
        {
            List<string> errors = new List<string>();
            if (!IsFinitePositive(K)) errors.Add("K 必须为有限正数（1/s）。");
            if (!IsFinitePositive(T)) errors.Add("T 必须为有限正数（s）。");
            if (!IsFinitePositive(ReferenceSpeedKn)) errors.Add("参考航速必须为有限正数（kn）。");
            if (!IsFinitePositive(MaxRudderDeg) || MaxRudderDeg > 90.0) errors.Add("最大舵角必须在 (0, 90] 度内。");
            if (!IsFinitePositive(RudderRateDegPerSec)) errors.Add("舵机速率必须为有限正数（°/s）。");
            if (!IsFinitePositive(SpeedTimeConstantSec)) errors.Add("常规变速时间常数必须为有限正数（s）。");
            if (!IsFinitePositive(StopTimeConstantSec)) errors.Add("停车时间常数必须为有限正数（s）。");
            if (!IsFinitePositive(AsternTimeConstantSec)) errors.Add("全速后退时间常数必须为有限正数（s）。");
            if (double.IsNaN(MinSpeedKn) || double.IsInfinity(MinSpeedKn) || MinSpeedKn < 0.0) errors.Add("最低航速必须为非负有限数（kn）。");
            if (!IsFinitePositive(LoaM)) errors.Add("LOA 必须为有限正数（m）。");
            if (!IsFinitePositive(BeamM)) errors.Add("型宽必须为有限正数（m）。");
            if (!IsFinitePositive(DisplacementTons)) errors.Add("排水量必须为有限正数（t）。");
            if (Anchor == null)
            {
                errors.Add("锚泊参数不能为空。");
            }
            else
            {
                IReadOnlyList<string> anchorErrors = Anchor.Validate();
                for (int i = 0; i < anchorErrors.Count; i++)
                {
                    errors.Add(anchorErrors[i]);
                }
            }
            return new ReadOnlyCollection<string>(errors);
        }

        private static bool IsFinitePositive(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value) && value > 0.0;
        }
    }

    /// <summary>反事实干预类型。</summary>
    public enum InterventionKind
    {
        /// <summary>转向（给定舵角与计划航向改变量）。</summary>
        Turn = 0,
        /// <summary>变速到指定航速。</summary>
        SpeedChange = 1,
        /// <summary>停车（主机停车，较长滑行时间常数）。</summary>
        Stop = 2,
        /// <summary>全速后退（较短时间常数）。</summary>
        FullAstern = 3,
        /// <summary>保持当前航向与航速。</summary>
        HoldCourse = 4,
        /// <summary>应急抛锚（松锚延迟后产生附加减速度与单锚偏转，可与舵令/倒车叠加）。</summary>
        EmergencyAnchor = 5
    }

    /// <summary>
    /// 单船反事实干预指令。执行时刻 = 指令时刻 + 反应延迟。
    /// </summary>
    public sealed class Intervention
    {
        /// <summary>干预类型。</summary>
        public InterventionKind Kind { get; }

        /// <summary>指令时刻（仿真秒）。</summary>
        public double TimeSeconds { get; }

        /// <summary>船员反应延迟（秒，默认 0）。</summary>
        public double ReactionDelaySec { get; }

        /// <summary>指令舵角（度，右舵为正，按最大舵角截断）。</summary>
        public double RudderDeg { get; }

        /// <summary>计划航向改变量（度，带符号，右转为正；达到后用 PD 稳向到目标航向）。</summary>
        public double HeadingChangeDeg { get; }

        /// <summary>目标航速（节，仅变速类使用）。</summary>
        public double TargetSpeedKn { get; }

        /// <summary>抛锚舷别（仅应急抛锚使用，其他类型为 Both）。</summary>
        public AnchorSide AnchorSide { get; }

        /// <summary>中文标签（用于展示）。</summary>
        public string Label { get; }

        /// <summary>实际执行时刻（仿真秒）。</summary>
        public double ExecutionTimeSeconds
        {
            get { return TimeSeconds + ReactionDelaySec; }
        }

        /// <summary>构造干预指令。</summary>
        public Intervention(
            InterventionKind kind,
            double timeSeconds,
            double reactionDelaySec = 0.0,
            double rudderDeg = 0.0,
            double headingChangeDeg = 0.0,
            double targetSpeedKn = 0.0,
            string label = null,
            AnchorSide anchorSide = AnchorSide.Both)
        {
            Kind = kind;
            TimeSeconds = timeSeconds;
            ReactionDelaySec = reactionDelaySec >= 0.0 ? reactionDelaySec : 0.0;
            RudderDeg = rudderDeg;
            HeadingChangeDeg = headingChangeDeg;
            TargetSpeedKn = targetSpeedKn;
            Label = label ?? string.Empty;
            AnchorSide = anchorSide;
        }

        /// <summary>创建右转指令（舵角与航向改变量均取正值）。</summary>
        public static Intervention TurnStarboard(
            double timeSeconds,
            double rudderDeg,
            double headingChangeDeg,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            return new Intervention(
                InterventionKind.Turn, timeSeconds, reactionDelaySec,
                Math.Abs(rudderDeg), Math.Abs(headingChangeDeg), 0.0,
                label ?? "右转");
        }

        /// <summary>创建左转指令（内部舵角与航向改变量取负值）。</summary>
        public static Intervention TurnPort(
            double timeSeconds,
            double rudderDeg,
            double headingChangeDeg,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            return new Intervention(
                InterventionKind.Turn, timeSeconds, reactionDelaySec,
                -Math.Abs(rudderDeg), -Math.Abs(headingChangeDeg), 0.0,
                label ?? "左转");
        }

        /// <summary>创建变速指令。</summary>
        public static Intervention ChangeSpeed(
            double timeSeconds,
            double targetSpeedKn,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            if (double.IsNaN(targetSpeedKn) || targetSpeedKn < 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(targetSpeedKn), "目标航速必须为非负数。");
            }
            return new Intervention(
                InterventionKind.SpeedChange, timeSeconds, reactionDelaySec,
                0.0, 0.0, targetSpeedKn, label ?? "变速");
        }

        /// <summary>创建停车指令。</summary>
        public static Intervention Stop(
            double timeSeconds,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            return new Intervention(
                InterventionKind.Stop, timeSeconds, reactionDelaySec,
                0.0, 0.0, 0.0, label ?? "停车");
        }

        /// <summary>创建全速后退指令。</summary>
        public static Intervention FullAstern(
            double timeSeconds,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            return new Intervention(
                InterventionKind.FullAstern, timeSeconds, reactionDelaySec,
                0.0, 0.0, 0.0, label ?? "全速后退");
        }

        /// <summary>
        /// 创建应急抛锚指令。执行时刻后经过 ManeuverParams.Anchor.LetGoToBiteSec 才产生
        /// 附加减速度与单锚偏转；Both 不产生附加偏转。
        /// </summary>
        public static Intervention EmergencyAnchor(
            double timeSeconds,
            AnchorSide side,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            string text = label ?? (side == AnchorSide.Port
                ? "左舷应急抛锚"
                : side == AnchorSide.Starboard ? "右舷应急抛锚" : "双锚应急抛锚");
            return new Intervention(
                InterventionKind.EmergencyAnchor, timeSeconds, reactionDelaySec,
                0.0, 0.0, 0.0, text, side);
        }

        /// <summary>创建保持航向航速指令。</summary>
        public static Intervention HoldCourse(
            double timeSeconds,
            double reactionDelaySec = 0.0,
            string label = null)
        {
            return new Intervention(
                InterventionKind.HoldCourse, timeSeconds, reactionDelaySec,
                0.0, 0.0, 0.0, label ?? "保向保速");
        }
    }

    /// <summary>单船反事实情景设定。</summary>
    public sealed class VesselScenario
    {
        private readonly ReadOnlyCollection<Intervention> _interventions;

        /// <summary>船舶标识。</summary>
        public string VesselId { get; }

        /// <summary>
        /// 偏离原航迹的时刻（秒）。null 表示取最早干预的执行时刻；
        /// 若早于最早干预执行时刻，则先保持航向航速，可用于表达“推迟转向”。
        /// </summary>
        public double? DivergeTimeSeconds { get; }

        /// <summary>干预列表（按输入顺序保留）。</summary>
        public IReadOnlyList<Intervention> Interventions
        {
            get { return _interventions; }
        }

        /// <summary>构造单船反事实情景。</summary>
        public VesselScenario(
            string vesselId,
            double? divergeTimeSeconds,
            IReadOnlyList<Intervention> interventions)
        {
            if (string.IsNullOrWhiteSpace(vesselId))
            {
                throw new ArgumentException("船舶标识不能为空。", nameof(vesselId));
            }
            VesselId = vesselId;
            DivergeTimeSeconds = divergeTimeSeconds;
            _interventions = new ReadOnlyCollection<Intervention>(
                interventions != null ? new List<Intervention>(interventions) : new List<Intervention>());
        }

        /// <summary>按给定干预创建单船情景（偏离时刻取最早执行时刻）。</summary>
        public static VesselScenario Create(string vesselId, params Intervention[] interventions)
        {
            return new VesselScenario(vesselId, null, interventions);
        }
    }

    /// <summary>
    /// What-if 情景：标识、中文名称、改动摘要与逐船设定；未列出的船沿原航迹。
    /// </summary>
    public sealed class WhatIfScenario
    {
        private readonly ReadOnlyCollection<VesselScenario> _vessels;
        private readonly ReadOnlyCollection<SourcedValue> _inputs;

        /// <summary>情景标识（如 S0、S1）。</summary>
        public string Id { get; }

        /// <summary>情景名称（中文）。</summary>
        public string Name { get; }

        /// <summary>改动摘要（中文）。</summary>
        public string ChangeSummary { get; }

        /// <summary>逐船设定；未列出的船沿原航迹。</summary>
        public IReadOnlyList<VesselScenario> Vessels
        {
            get { return _vessels; }
        }

        /// <summary>本情景特有的输入参数及来源（与 setup 的公共输入合并输出）。</summary>
        public IReadOnlyList<SourcedValue> Inputs
        {
            get { return _inputs; }
        }

        /// <summary>构造 What-if 情景。</summary>
        public WhatIfScenario(
            string id,
            string name,
            string changeSummary,
            IReadOnlyList<VesselScenario> vessels,
            IReadOnlyList<SourcedValue> inputs = null)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                throw new ArgumentException("情景标识不能为空。", nameof(id));
            }
            Id = id;
            Name = name ?? string.Empty;
            ChangeSummary = changeSummary ?? string.Empty;
            _vessels = new ReadOnlyCollection<VesselScenario>(
                vessels != null ? new List<VesselScenario>(vessels) : new List<VesselScenario>());
            _inputs = new ReadOnlyCollection<SourcedValue>(
                inputs != null ? new List<SourcedValue>(inputs) : new List<SourcedValue>());
        }

        /// <summary>创建不改变任何船舶的原始情景。</summary>
        public static WhatIfScenario Original(
            string id = "S0",
            string name = "原始",
            IReadOnlyList<SourcedValue> inputs = null)
        {
            return new WhatIfScenario(id, name, "原始航迹，无改动", Array.Empty<VesselScenario>(), inputs);
        }

        /// <summary>按船舶标识查找设定；未找到返回 null。</summary>
        public VesselScenario FindVessel(string vesselId)
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
    }
}
