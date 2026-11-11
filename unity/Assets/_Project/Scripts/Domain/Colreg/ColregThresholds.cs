using System;
using System.Collections.Generic;

namespace Mcis.Domain.Colreg
{
    /// <summary>COLREG 技术分析阈值快照；距离采用海里，速度采用米每秒，时间采用秒，角度采用度。</summary>
    public sealed class ColregThresholds
    {
        /// <summary>默认技术分析阈值。</summary>
        public static readonly ColregThresholds Default = new ColregThresholds();

        /// <summary>接近相反航向的对遇半角。</summary>
        public double HeadOnHalfAngleDeg { get; }
        /// <summary>追越扇区边界距正横向后的角度。</summary>
        public double OvertakingAbaftBeamAngleDeg { get; }
        /// <summary>追越扇区下边界；上下边界均包含。</summary>
        public double OvertakingBoundaryDeg { get { return 90.0 + OvertakingAbaftBeamAngleDeg; } }
        /// <summary>能见度不良阈值。</summary>
        public double RestrictedVisibilityNm { get; }
        /// <summary>碰撞危险的最近会遇距离阈值。</summary>
        public double CollisionRiskDcpaNm { get; }
        /// <summary>安全驶过的最近会遇距离阈值。</summary>
        public double SafePassingDcpaNm { get; }
        /// <summary>明显转向角度阈值。</summary>
        public double SubstantialTurnDeg { get; }
        /// <summary>附加绝对明显变速阈值；零表示禁用，大于零时与相对初速判据取或。</summary>
        public double SubstantialSpeedChangeMps { get; }
        /// <summary>保向容差。</summary>
        public double MaintainHeadingToleranceDeg { get; }
        /// <summary>保速容差。</summary>
        public double MaintainSpeedToleranceMps { get; }
        /// <summary>规则判定的最大采样步长；原始样本和环境切换时刻仍保留。</summary>
        public double SampleIntervalSeconds { get; }
        /// <summary>及早行动的剩余 TCPA 门限。</summary>
        public double EarlyActionTcpaSeconds { get; }
        /// <summary>及早行动的距离门限。</summary>
        public double EarlyActionDistanceNm { get; }
        /// <summary>安全航速提示值；仅在人工研判说明中提示，不作为满足或不满足判据。</summary>
        public double SafeSpeedMps { get; }
        /// <summary>对遇时他船位于船首附近的半角。</summary>
        public double HeadOnForwardHalfAngleDeg { get; }
        /// <summary>紧迫阶段的 TCPA 技术代理门限；不足以证明单凭让路船已无法避碰。</summary>
        public double StandOnEmergencyTcpaSeconds { get; }
        /// <summary>允许直航船介入分析的 TCPA 技术代理门限。</summary>
        public double StandOnInterventionTcpaSeconds { get; }
        /// <summary>是否在 DCPA 判据之外将正在接近也视为碰撞危险。</summary>
        public bool IncludeClosingRisk { get; }
        /// <summary>驶过让清后解除追越保持所需的距离。</summary>
        public double ClearDistanceNm { get; }
        /// <summary>碰撞危险的未来 TCPA 上限，含边界。</summary>
        public double CollisionRiskTcpaSeconds { get; }
        /// <summary>紧迫局面的严格 DCPA 上限。</summary>
        public double CloseQuartersDcpaNm { get; }
        /// <summary>紧迫局面的未来 TCPA 上限，含边界。</summary>
        public double CloseQuartersTcpaSeconds { get; }
        /// <summary>相对行动前航速的明显变速比例；绝对变速判据启用时两者取或。</summary>
        public double SubstantialSpeedChangeFraction { get; }
        /// <summary>判定同向明显转向的滑动观察窗口。</summary>
        public double SubstantialTurnWindowSeconds { get; }
        /// <summary>R14(c) 对遇存疑扇区的船首方位半角。</summary>
        public double HeadOnDoubtBearingDeg { get; }
        /// <summary>延后锁定所用稳定航向窗口；历史不足窗口时使用已有历史。</summary>
        public double LockHeadingStableWindowSeconds { get; }
        /// <summary>稳定窗口内允许的最大航向变化。</summary>
        public double LockHeadingStableMaxChangeDeg { get; }
        /// <summary>风险形成后最多延后锁定的时长。</summary>
        public double LockMaxDeferSeconds { get; }

        /// <summary>构造阈值快照；参数合法性由分析入口验证，不静默替换用户输入。</summary>
        public ColregThresholds(
            double headOnHalfAngleDeg = 6.0,
            double overtakingAbaftBeamAngleDeg = 22.5,
            double restrictedVisibilityNm = 2.0,
            double collisionRiskDcpaNm = 1.0,
            double safePassingDcpaNm = 0.5,
            double substantialTurnDeg = 30.0,
            double substantialSpeedChangeMps = 0.0,
            double maintainHeadingToleranceDeg = 3.0,
            double maintainSpeedToleranceMps = 0.5,
            double sampleIntervalSeconds = 10.0,
            double earlyActionTcpaSeconds = 120.0,
            double earlyActionDistanceNm = 1.0,
            double safeSpeedMps = 5.0,
            double headOnForwardHalfAngleDeg = 15.0,
            double standOnEmergencyTcpaSeconds = 60.0,
            double standOnInterventionTcpaSeconds = 180.0,
            bool includeClosingRisk = false,
            double clearDistanceNm = 0.5,
            double collisionRiskTcpaSeconds = 720.0,
            double closeQuartersDcpaNm = 0.3,
            double closeQuartersTcpaSeconds = 360.0,
            double substantialSpeedChangeFraction = 0.3,
            double substantialTurnWindowSeconds = 60.0,
            double headOnDoubtBearingDeg = 22.5,
            double lockHeadingStableWindowSeconds = 60.0,
            double lockHeadingStableMaxChangeDeg = 5.0,
            double lockMaxDeferSeconds = 120.0)
        {
            HeadOnHalfAngleDeg = headOnHalfAngleDeg;
            OvertakingAbaftBeamAngleDeg = overtakingAbaftBeamAngleDeg;
            RestrictedVisibilityNm = restrictedVisibilityNm;
            CollisionRiskDcpaNm = collisionRiskDcpaNm;
            SafePassingDcpaNm = safePassingDcpaNm;
            SubstantialTurnDeg = substantialTurnDeg;
            SubstantialSpeedChangeMps = substantialSpeedChangeMps;
            MaintainHeadingToleranceDeg = maintainHeadingToleranceDeg;
            MaintainSpeedToleranceMps = maintainSpeedToleranceMps;
            SampleIntervalSeconds = sampleIntervalSeconds;
            EarlyActionTcpaSeconds = earlyActionTcpaSeconds;
            EarlyActionDistanceNm = earlyActionDistanceNm;
            SafeSpeedMps = safeSpeedMps;
            HeadOnForwardHalfAngleDeg = headOnForwardHalfAngleDeg;
            StandOnEmergencyTcpaSeconds = standOnEmergencyTcpaSeconds;
            StandOnInterventionTcpaSeconds = standOnInterventionTcpaSeconds;
            IncludeClosingRisk = includeClosingRisk;
            ClearDistanceNm = clearDistanceNm;
            CollisionRiskTcpaSeconds = collisionRiskTcpaSeconds;
            CloseQuartersDcpaNm = closeQuartersDcpaNm;
            CloseQuartersTcpaSeconds = closeQuartersTcpaSeconds;
            SubstantialSpeedChangeFraction = substantialSpeedChangeFraction;
            SubstantialTurnWindowSeconds = substantialTurnWindowSeconds;
            HeadOnDoubtBearingDeg = headOnDoubtBearingDeg;
            LockHeadingStableWindowSeconds = lockHeadingStableWindowSeconds;
            LockHeadingStableMaxChangeDeg = lockHeadingStableMaxChangeDeg;
            LockMaxDeferSeconds = lockMaxDeferSeconds;
        }

        /// <summary>以固定文化格式列出本次全部阈值及明显行动判据，供报告审计。</summary>
        internal IReadOnlyList<string> DescribeAssumptions()
        {
            return Array.AsReadOnly(new[]
            {
                FormattableString.Invariant($"碰撞危险：DCPA < {CollisionRiskDcpaNm:R} nm 且 0 < TCPA ≤ {CollisionRiskTcpaSeconds:R} s；IncludeClosingRisk={IncludeClosingRisk}（启用时在 TCPA 窗口内另含正在接近的目标）。"),
                FormattableString.Invariant($"紧迫局面：DCPA < {CloseQuartersDcpaNm:R} nm 且 0 < TCPA ≤ {CloseQuartersTcpaSeconds:R} s；紧迫危险另需 TCPA ≤ {StandOnEmergencyTcpaSeconds:R} s。"),
                FormattableString.Invariant($"明显转向：{SubstantialTurnWindowSeconds:R} s 滑窗内同向转幅 ≥ {SubstantialTurnDeg:R}°；跨窗口的小幅行动不累计。明显变速：|Δv| ≥ {SubstantialSpeedChangeFraction:R} × 行动前航速；SubstantialSpeedChangeMps={SubstantialSpeedChangeMps:R} m/s，0 禁用绝对判据，>0 时作为附加取或判据。"),
                FormattableString.Invariant($"对遇航向半角 HeadOnHalfAngleDeg={HeadOnHalfAngleDeg:R}°；正前方半角 HeadOnForwardHalfAngleDeg={HeadOnForwardHalfAngleDeg:R}°；对遇存疑方位 HeadOnDoubtBearingDeg={HeadOnDoubtBearingDeg:R}°；追越正横后角 OvertakingAbaftBeamAngleDeg={OvertakingAbaftBeamAngleDeg:R}°，闭区间边界 OvertakingBoundaryDeg={OvertakingBoundaryDeg:R}°。"),
                FormattableString.Invariant($"延后锁定：回看 LockHeadingStableWindowSeconds={LockHeadingStableWindowSeconds:R} s，双方航向变化均 ≤ LockHeadingStableMaxChangeDeg={LockHeadingStableMaxChangeDeg:R}° 时锁定；风险形成后 LockMaxDeferSeconds={LockMaxDeferSeconds:R} s 仍不稳定则按当时几何锁定并标存疑。"),
                FormattableString.Invariant($"能见度不良采用 VisibilityNm < RestrictedVisibilityNm={RestrictedVisibilityNm:R} nm（相等不算不良）；SafeSpeedMps={SafeSpeedMps:R} m/s 仅为提示，R6/R19(b) 需人工研判。"),
                FormattableString.Invariant($"安全驶过 SafePassingDcpaNm={SafePassingDcpaNm:R} nm；追越让清 ClearDistanceNm={ClearDistanceNm:R} nm；保向容差 MaintainHeadingToleranceDeg={MaintainHeadingToleranceDeg:R}°；保速容差 MaintainSpeedToleranceMps={MaintainSpeedToleranceMps:R} m/s。"),
                FormattableString.Invariant($"采样最大步长 SampleIntervalSeconds={SampleIntervalSeconds:R} s；及早行动 EarlyActionTcpaSeconds={EarlyActionTcpaSeconds:R} s 或 EarlyActionDistanceNm={EarlyActionDistanceNm:R} nm；直航介入 StandOnInterventionTcpaSeconds={StandOnInterventionTcpaSeconds:R} s；紧迫行动 StandOnEmergencyTcpaSeconds={StandOnEmergencyTcpaSeconds:R} s。")
            });
        }
    }
}
