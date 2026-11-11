using System;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Models
{
    /// <summary>
    /// 航迹离散样本点（已统一转换至局部 ENU 平面与 SI 单位）。
    /// </summary>
    public readonly struct TrackSample
    {
        /// <summary>仿真相对时间。</summary>
        public SimTime Time { get; }

        /// <summary>WGS84 大地坐标。</summary>
        public GeoCoord Geo { get; }

        /// <summary>已做天线偏移修正后的船中心 ENU 位置。</summary>
        public EnuPosition EnuCenter { get; }

        /// <summary>对地速度分量 (Ve, Vn) 单位 m/s。</summary>
        public Double2 VelocityEnuMps { get; }

        /// <summary>对地航速 (m/s)。</summary>
        public float SogMps { get; }

        /// <summary>对地航向 (0..360°)。</summary>
        public float CogDeg { get; }

        /// <summary>船首向 (0..360°)。</summary>
        public float HdgDeg { get; }

        /// <summary>转向率 (°/s)。</summary>
        public float RotDegPerSec { get; }

        /// <summary>数据来源标记。</summary>
        public SampleProvenance Provenance { get; }

        /// <summary>时间戳质量等级。</summary>
        public TimeQuality TimeQuality { get; }

        /// <summary>HDG 缺失时是否由 COG 代替。</summary>
        public bool HeadingFromCog { get; }

        /// <summary>是否处于时间缺口跨越插值区间内。</summary>
        public bool IsInterpolatedAcrossGap
        {
            get { return Provenance == SampleProvenance.LowConfidence || Provenance == SampleProvenance.DeadReckoned; }
        }

        /// <summary>关联原始文件行号（可追溯）。</summary>
        public int? RawSourceLine { get; }

        /// <summary>构造航迹样本点。</summary>
        public TrackSample(
            SimTime time,
            GeoCoord geo,
            EnuPosition enuCenter,
            Double2 velocityEnuMps,
            float sogMps,
            float cogDeg,
            float hdgDeg,
            float rotDegPerSec,
            SampleProvenance provenance,
            TimeQuality timeQuality,
            bool headingFromCog,
            int? rawSourceLine = null)
        {
            Time = time;
            Geo = geo;
            EnuCenter = enuCenter;
            VelocityEnuMps = velocityEnuMps;
            SogMps = sogMps;
            CogDeg = cogDeg;
            HdgDeg = hdgDeg;
            RotDegPerSec = rotDegPerSec;
            Provenance = provenance;
            TimeQuality = timeQuality;
            HeadingFromCog = headingFromCog;
            RawSourceLine = rawSourceLine;
        }
    }

    /// <summary>
    /// 被异常点剔除规则过滤的样本记录（保留原因与参数供审计与人工恢复）。
    /// </summary>
    public readonly struct RejectedSample
    {
        /// <summary>原始文件行号。</summary>
        public int SourceLineNumber { get; }

        /// <summary>仿真相对时间。</summary>
        public SimTime Time { get; }

        /// <summary>原始大地坐标。</summary>
        public GeoCoord Geo { get; }

        /// <summary>原始报告对地航速 (kn)。</summary>
        public float SogKn { get; }

        /// <summary>原始报告对地航向 (°)。</summary>
        public float CogDeg { get; }

        /// <summary>剔除原因代码。</summary>
        public RejectReason Reason { get; }

        /// <summary>诊断说明详情。</summary>
        public string DiagnosticDetail { get; }

        /// <summary>是否已被调查员手动恢复。</summary>
        public bool IsManuallyRestored { get; }

        /// <summary>构造被剔除样本记录。</summary>
        public RejectedSample(
            int sourceLineNumber,
            SimTime time,
            GeoCoord geo,
            float sogKn,
            float cogDeg,
            RejectReason reason,
            string diagnosticDetail,
            bool isManuallyRestored = false)
        {
            SourceLineNumber = sourceLineNumber;
            Time = time;
            Geo = geo;
            SogKn = sogKn;
            CogDeg = cogDeg;
            Reason = reason;
            DiagnosticDetail = diagnosticDetail ?? string.Empty;
            IsManuallyRestored = isManuallyRestored;
        }
    }

    /// <summary>
    /// 航迹中的时间缺口区间。
    /// </summary>
    public readonly struct TimeGapSpan
    {
        /// <summary>缺口起始时间。</summary>
        public SimTime StartTime { get; }

        /// <summary>缺口结束时间。</summary>
        public SimTime EndTime { get; }

        /// <summary>缺口持续时长（秒）。</summary>
        public double DurationSeconds { get; }

        /// <summary>缺口起点 ENU 坐标。</summary>
        public EnuPosition StartEnu { get; }

        /// <summary>缺口终点 ENU 坐标。</summary>
        public EnuPosition EndEnu { get; }

        /// <summary>构造时间缺口区间。</summary>
        public TimeGapSpan(
            SimTime startTime,
            SimTime endTime,
            double durationSeconds,
            EnuPosition startEnu,
            EnuPosition endEnu)
        {
            StartTime = startTime;
            EndTime = endTime;
            DurationSeconds = durationSeconds;
            StartEnu = startEnu;
            EndEnu = endEnu;
        }
    }

    /// <summary>
    /// 两船配对键（本船 Own -> 目标船 Target）。
    /// </summary>
    public readonly struct CpaPairKey : IEquatable<CpaPairKey>
    {
        /// <summary>本船标识。</summary>
        public string OwnVesselId { get; }

        /// <summary>目标船标识。</summary>
        public string TargetVesselId { get; }

        /// <summary>构造两船配对键。</summary>
        public CpaPairKey(string ownVesselId, string targetVesselId)
        {
            OwnVesselId = ownVesselId ?? string.Empty;
            TargetVesselId = targetVesselId ?? string.Empty;
        }

        /// <inheritdoc />
        public bool Equals(CpaPairKey other)
        {
            return string.Equals(OwnVesselId, other.OwnVesselId, StringComparison.Ordinal) &&
                   string.Equals(TargetVesselId, other.TargetVesselId, StringComparison.Ordinal);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is CpaPairKey other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                return ((OwnVesselId != null ? OwnVesselId.GetHashCode() : 0) * 397) ^
                       (TargetVesselId != null ? TargetVesselId.GetHashCode() : 0);
            }
        }
    }

    /// <summary>
    /// DCPA / TCPA 实时计算结果（对应 ARCHITECTURE 4.6 节与 5.2 节）。
    /// </summary>
    public readonly struct CpaResult
    {
        /// <summary>一海里对应的米数（标准值 1852.0）。</summary>
        public const double MetersPerNauticalMile = 1852.0;

        /// <summary>本船-目标船配对键。</summary>
        public CpaPairKey Pair { get; }

        /// <summary>当前仿真时间。</summary>
        public SimTime Time { get; }

        /// <summary>当前船中心间距 (m)。</summary>
        public double CurrentDistanceM { get; }

        /// <summary>当前两船 OBB 最小净距 (m)，&lt;=0 表示接触。</summary>
        public double HullClearanceM { get; }

        /// <summary>目标船相对本船真方位 q (0..360°)。</summary>
        public double TrueBearingDeg { get; }

        /// <summary>相对运动航向 Cr (0..360°)。</summary>
        public double RelativeCourseDeg { get; }

        /// <summary>相对速度大小 |v| (m/s)。</summary>
        public double RelativeSpeedMps { get; }

        /// <summary>最近会遇距离 DCPA (m)。</summary>
        public double DcpaM { get; }

        /// <summary>最近会遇时间 TCPA (s)，&lt;0 表示已过最近点。</summary>
        public double TcpaSec { get; }

        /// <summary>TCPA 时刻本船预测位置。</summary>
        public EnuPosition OwnCpaEnu { get; }

        /// <summary>TCPA 时刻目标船预测位置。</summary>
        public EnuPosition TargetCpaEnu { get; }

        /// <summary>TCPA &lt; 0 正在远离。</summary>
        public bool IsDiverging { get; }

        /// <summary>|v| &lt; 0.01 m/s 相对静止退化。</summary>
        public bool IsDegenerate { get; }

        /// <summary>经滞回判定后的风险等级。</summary>
        public RiskLevel RiskLevel { get; }

        /// <summary>当前船中心间距（海里）。</summary>
        public double CurrentDistanceNm
        {
            get { return CurrentDistanceM / MetersPerNauticalMile; }
        }

        /// <summary>最近会遇距离 DCPA（海里）。</summary>
        public double DcpaNm
        {
            get { return DcpaM / MetersPerNauticalMile; }
        }

        /// <summary>最近会遇时间 TCPA（分钟）。</summary>
        public double TcpaMin
        {
            get { return TcpaSec / 60.0; }
        }

        /// <summary>构造 CPA 计算结果。</summary>
        public CpaResult(
            CpaPairKey pair,
            SimTime time,
            double currentDistanceM,
            double hullClearanceM,
            double trueBearingDeg,
            double relativeCourseDeg,
            double relativeSpeedMps,
            double dcpaM,
            double tcpaSec,
            EnuPosition ownCpaEnu,
            EnuPosition targetCpaEnu,
            bool isDiverging,
            bool isDegenerate,
            RiskLevel riskLevel)
        {
            Pair = pair;
            Time = time;
            CurrentDistanceM = currentDistanceM;
            HullClearanceM = hullClearanceM;
            TrueBearingDeg = trueBearingDeg;
            RelativeCourseDeg = relativeCourseDeg;
            RelativeSpeedMps = relativeSpeedMps;
            DcpaM = dcpaM;
            TcpaSec = tcpaSec;
            OwnCpaEnu = ownCpaEnu;
            TargetCpaEnu = targetCpaEnu;
            IsDiverging = isDiverging;
            IsDegenerate = isDegenerate;
            RiskLevel = riskLevel;
        }

        /// <summary>返回更新了风险等级的副本。</summary>
        public CpaResult WithRiskLevel(RiskLevel newLevel)
        {
            return new CpaResult(
                Pair, Time, CurrentDistanceM, HullClearanceM, TrueBearingDeg,
                RelativeCourseDeg, RelativeSpeedMps, DcpaM, TcpaSec,
                OwnCpaEnu, TargetCpaEnu, IsDiverging, IsDegenerate, newLevel);
        }
    }
}
