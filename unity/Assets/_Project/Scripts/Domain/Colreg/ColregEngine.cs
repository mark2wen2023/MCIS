using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;

namespace Mcis.Domain.Colreg
{
    /// <summary>
    /// 两船会遇及船舶状态的确定性技术核查入口。仅在共同观测区间内插值；
    /// 时间带为左闭右开，末带包含观测终点，终点发生转换时保留零长度末带。
    /// </summary>
    public sealed class ColregEngine
    {
        /// <summary>分析合成或已规范化航迹；输入不合法时返回失败结果。</summary>
        public Result<ColregAnalysisReport> Analyze(ColregAnalysisRequest request)
        {
            string error = Validate(request);
            if (error != null)
                return Result<ColregAnalysisReport>.Fail("COLREG_INVALID_INPUT", error);

            double start = Math.Max(request.OwnSamples[0].Time.Seconds, request.TargetSamples[0].Time.Seconds);
            double end = Math.Min(request.OwnSamples[request.OwnSamples.Count - 1].Time.Seconds,
                request.TargetSamples[request.TargetSamples.Count - 1].Time.Seconds);
            if (start > end)
                return Result<ColregAnalysisReport>.Fail("COLREG_NO_OVERLAP", "两船航迹没有共同观测时间。");
            double count = (end - start) / request.Thresholds.SampleIntervalSeconds;
            if (!Finite(count) || count > 1000000)
                return Result<ColregAnalysisReport>.Fail("COLREG_TOO_MANY_SAMPLES", "采样网格超过一百万点，请增大采样间隔或缩短观测区间。");

            var times = new SortedSet<double> { start, end };
            for (int i = 1; i <= (int)count; i++)
            {
                double time = start + i * request.Thresholds.SampleIntervalSeconds;
                if (time < end) times.Add(time);
            }
            AddTimes(times, request.OwnSamples, start, end);
            AddTimes(times, request.TargetSamples, start, end);
            foreach (var state in request.Environment)
                if (state.Time.Seconds >= start && state.Time.Seconds <= end) times.Add(state.Time.Seconds);
            if (request.InSightSamples != null)
                foreach (var state in request.InSightSamples)
                    if (state.Time.Seconds >= start && state.Time.Seconds <= end) times.Add(state.Time.Seconds);
            if (request.VesselStatusSamples != null)
                foreach (var state in request.VesselStatusSamples)
                    if (state.Time.Seconds >= start && state.Time.Seconds <= end) times.Add(state.Time.Seconds);

            var frames = new List<ColregFrame>();
            var pair = new CpaPairKey(request.OwnVesselId, request.TargetVesselId);
            var encounter = new ColregEncounterState();
            while (times.Count > 0)
            {
                double time = times.Min;
                times.Remove(time);
                var own = SampleAt(request.OwnSamples, time);
                var target = SampleAt(request.TargetSamples, time);
                var cpa = CpaCalculator.CalculateFromSamples(own, target, pair);
                var frame = new ColregFrame(own, target, cpa, VisibilityAt(request, time));
                bool danger = !cpa.IsDegenerate && cpa.TcpaSec > 0 && cpa.TcpaSec <= request.Thresholds.CollisionRiskTcpaSeconds &&
                    (cpa.DcpaNm < request.Thresholds.CollisionRiskDcpaNm || request.Thresholds.IncludeClosingRisk);
                frame.HasCollisionRisk = danger;
                frame.InSight = InSightAt(request, time, frame);
                frame.OwnStatus = StatusAt(request, request.OwnVesselId, time);
                frame.TargetStatus = StatusAt(request, request.TargetVesselId, time);
                frame.DangerStage = ColregEncounterState.DangerStage(frame, request.Thresholds);
                encounter.Apply(frame, request);
                // 最大延后时限即使不落在常规网格上，也必须在准确时刻锁定。
                if (encounter.LockDeadline.HasValue && encounter.LockDeadline.Value > time &&
                    encounter.LockDeadline.Value <= end) times.Add(encounter.LockDeadline.Value);
                frames.Add(frame);
            }

            var spans = new List<ColregSpan>();
            int first = 0;
            for (int i = 1; i <= frames.Count; i++)
            {
                if (i < frames.Count && frames[first].SameClassification(frames[i])) continue;
                int last = i < frames.Count ? i : frames.Count - 1;
                var f = frames[first];
                var maximumStage = f.DangerStage;
                // 转换端点归后一带；报告终点则包含在末带内。
                int exclusive = i < frames.Count ? i : frames.Count;
                for (int j = first + 1; j < exclusive; j++)
                    if (frames[j].DangerStage > maximumStage) maximumStage = frames[j].DangerStage;
                spans.Add(new ColregSpan(first, last, new ColregTimeBand(f.Own.Time,
                    frames[last].Own.Time, f.Situation, f.OwnRole,
                    f.TargetRole, ApplicableRules(f, request.InNarrowChannel),
                    inSight: f.InSight,
                    bandId: ColregIds.Band(request, f.Own.Time, frames[last].Own.Time, f.Situation, f.OwnRole, f.TargetRole),
                    giveWayVesselId: f.OwnRole == TrafficRole.GiveWay ? request.OwnVesselId :
                        f.TargetRole == TrafficRole.GiveWay ? request.TargetVesselId : null,
                    standOnVesselId: f.OwnRole == TrafficRole.StandOn ? request.OwnVesselId :
                        f.TargetRole == TrafficRole.StandOn ? request.TargetVesselId : null,
                    basis: f.Basis, doubt: f.Doubt, dangerStage: maximumStage,
                    doubtReason: f.DoubtReason,
                    vesselStatus: new Dictionary<string, ColregVesselStatus>
                    {
                        { request.OwnVesselId, f.OwnStatus }, { request.TargetVesselId, f.TargetStatus }
                    })));
                first = i;
            }
            var bands = new List<ColregTimeBand>();
            var checks = new List<ColregRuleCheck>();
            foreach (var span in spans)
            {
                bands.Add(span.Band);
                ColregEvaluator.Evaluate(request, frames, span, checks);
            }
            for (int i = 0; i < checks.Count; i++)
            {
                var c = checks[i];
                checks[i] = new ColregRuleCheck(c.StartTime, c.EndTime, c.RuleId, c.VesselId, c.Status,
                    c.Clause, c.ExpectedAction, c.ActualAction, c.Evidence, c.Explanation,
                    checkId: ColregIds.Check(request, c), reviewStatus: ColregReviewStatus.Draft,
                    evidenceIds: request.EvidenceIds, atTimeSec: c.StartTime.Seconds);
            }
            var assumptions = new List<string>
            {
                "未给状态及首个状态样本前采用 Unknown，R13–R17 仍按机动船分析；R18 缺证据时不可评估。NUC/RAM 无直航义务。声号、操纵性能和停船距离须另有证据。",
                "仅在共同观测区间内对ENU位置、速度作线性插值，航向沿最短圆弧插值；保留原始、环境、船舶状态及显式互见变化时刻。",
                "追越扇区包含边界；边界存疑按追越处理。驶过让清的技术代理为已过CPA、正在远离且达到配置让清距离。",
                "安全航速仅输出需研判，5m/s默认值只作提示；及早行动及R17干预/紧迫门限为可配置技术代理，不能证明单凭一船已无法避碰。",
                "交叉角色同时参考双方视角，轴线上优先采用他船明确视角；视角矛盾标存疑，不以船名决定角色。",
                "危险首次形成时检查已有航向历史；转向中延后锁定，稳定或达到最大延后时限才按当时几何锁定，不事后重判推迟期。解除或驶过让清后释放；未互见转互见、船舶状态变化时重新判定。R17阶段在同次危险期单调推进。",
                "R16/R8 及早行动以危险首次形成时刻为起点；锁定后保留同次推迟期内的行动。状态或互见重新判定不承接旧义务的行动。",
                "规则逐带核查，转换点共享观测值；连续避让操纵及安全效果核查延续到危险期结束。危险阶段单独列区间，不拆分会遇类型。合同映射：CollisionRisk→None，Situation 保留会遇类型。"
            };
            assumptions.AddRange(request.Thresholds.DescribeAssumptions());
            assumptions.Add("互见序列按最近过去值阶梯保持，优先于标量；均未给时，能见度达到阈值或两船距离不大于能见距离即推导为互见，距离切换取首个满足的保留采样时刻。未给能见度时视为无限能见度。");
            if (request.VisibilityNm == null && (request.Environment.Count == 0 || request.Environment[0].Time.Seconds > start))
                assumptions.Add("首个环境状态生效前缺少能见度，采用无限能见度；环境状态按最近过去值保持。");
            return Result<ColregAnalysisReport>.Ok(new ColregAnalysisReport(pair, bands, checks,
                request.Thresholds, request.CaseEpochUtc, assumptions, ColregEncounterState.BuildStages(request, frames)));
        }

        private static IReadOnlyList<ColregRuleId> ApplicableRules(ColregFrame f, bool narrow)
        {
            var rules = new List<ColregRuleId>();
            if (f.Situation != EncounterSituation.NoCollisionRisk)
            {
                rules.Add(ColregRuleId.R5);
                rules.Add(ColregRuleId.R6);
                rules.Add(ColregRuleId.R7);
                rules.Add(ColregRuleId.R8);
                rules.Add(ColregRuleId.R34_35);
                rules.Add(ColregRuleId.R18);
                if (f.Situation == EncounterSituation.RestrictedVisibility) rules.Add(ColregRuleId.R19);
                else if (f.Situation == EncounterSituation.Undetermined)
                {
                    rules.AddRange(new[] { ColregRuleId.R13, ColregRuleId.R14, ColregRuleId.R15,
                        ColregRuleId.R16, ColregRuleId.R17 });
                }
                else if (f.Situation == EncounterSituation.HeadOn) rules.Add(ColregRuleId.R14);
                else
                {
                    rules.Add(f.Situation == EncounterSituation.Overtaking ? ColregRuleId.R13 : ColregRuleId.R15);
                    rules.Add(ColregRuleId.R16);
                    rules.Add(ColregRuleId.R17);
                }
                if (f.OwnRole == TrafficRole.GiveWay || f.TargetRole == TrafficRole.GiveWay)
                    if (!rules.Contains(ColregRuleId.R16)) rules.Add(ColregRuleId.R16);
            }
            if (narrow) rules.Add(ColregRuleId.R9);
            return rules;
        }

        private static void AddTimes(SortedSet<double> times, IReadOnlyList<TrackSample> samples, double start, double end)
        {
            foreach (var sample in samples)
                if (sample.Time.Seconds >= start && sample.Time.Seconds <= end) times.Add(sample.Time.Seconds);
        }

        internal static TrackSample SampleAt(IReadOnlyList<TrackSample> samples, double time)
        {
            int lo = 0, hi = samples.Count - 1;
            while (lo < hi)
            {
                int middle = lo + (hi - lo) / 2;
                if (samples[middle].Time.Seconds < time) lo = middle + 1;
                else hi = middle;
            }
            if (samples[lo].Time.Seconds == time || lo == 0) return samples[lo];
            var a = samples[lo - 1];
            var b = samples[lo];
            double fraction = (time - a.Time.Seconds) / (b.Time - a.Time);
            return new TrackSample(new SimTime(time), a.Geo,
                new EnuPosition(Lerp(a.EnuCenter.EastM, b.EnuCenter.EastM, fraction),
                    Lerp(a.EnuCenter.NorthM, b.EnuCenter.NorthM, fraction)),
                new Double2(Lerp(a.VelocityEnuMps.X, b.VelocityEnuMps.X, fraction),
                    Lerp(a.VelocityEnuMps.Y, b.VelocityEnuMps.Y, fraction)),
                (float)Lerp(a.SogMps, b.SogMps, fraction),
                (float)Normalize(Course(a) + Delta(Course(a), Course(b)) * fraction),
                (float)Normalize(Heading(a) + Delta(Heading(a), Heading(b)) * fraction),
                0, SampleProvenance.Interpolated, a.TimeQuality, false);
        }

        private static double VisibilityAt(ColregAnalysisRequest request, double time)
        {
            double visibility = request.VisibilityNm ?? double.PositiveInfinity;
            int lo = 0, hi = request.Environment.Count;
            while (lo < hi)
            {
                int mid = lo + (hi - lo) / 2;
                if (request.Environment[mid].Time.Seconds <= time) lo = mid + 1;
                else hi = mid;
            }
            if (lo > 0) visibility = request.Environment[lo - 1].VisibilityNm;
            return visibility;
        }

        private static bool InSightAt(ColregAnalysisRequest request, double time, ColregFrame frame)
        {
            var samples = request.InSightSamples;
            if (samples != null)
            {
                int lo = 0, hi = samples.Count;
                while (lo < hi)
                {
                    int mid = lo + (hi - lo) / 2;
                    if (samples[mid].Time.Seconds <= time) lo = mid + 1;
                    else hi = mid;
                }
                if (lo > 0) return samples[lo - 1].InSight;
            }
            if (request.VesselsInSight.HasValue) return request.VesselsInSight.Value;
            return frame.VisibilityNm >= request.Thresholds.RestrictedVisibilityNm ||
                frame.Cpa.CurrentDistanceNm <= frame.VisibilityNm;
        }

        private static ColregVesselStatus StatusAt(ColregAnalysisRequest request, string vessel, double time)
        {
            var status = ColregVesselStatus.Unknown;
            if (request.VesselStatusSamples != null)
                foreach (var sample in request.VesselStatusSamples)
                    if (sample.VesselId == vessel && sample.Time.Seconds <= time) status = sample.Status;
            return status;
        }

        internal static double Heading(TrackSample sample)
        {
            return !sample.HeadingFromCog && Finite(sample.HdgDeg) && sample.HdgDeg >= 0 && sample.HdgDeg <= 360
                ? Normalize(sample.HdgDeg) : sample.CogDeg;
        }

        private static double Course(TrackSample sample)
        {
            return Finite(sample.CogDeg) && sample.CogDeg >= 0 && sample.CogDeg <= 360 ? Normalize(sample.CogDeg) :
                Normalize(Math.Atan2(sample.VelocityEnuMps.X, sample.VelocityEnuMps.Y) * 180 / Math.PI);
        }

        internal static double Normalize(double angle) { return (angle % 360 + 360) % 360; }
        internal static double Delta(double from, double to) { return Normalize(to - from + 180) - 180; }
        internal static bool Finite(double value) { return !double.IsNaN(value) && !double.IsInfinity(value); }
        private static double Lerp(double a, double b, double f) { return a + (b - a) * f; }

        private static string Validate(ColregAnalysisRequest r)
        {
            if (r == null) return "请求不能为空。";
            if (string.IsNullOrWhiteSpace(r.OwnVesselId) || string.IsNullOrWhiteSpace(r.TargetVesselId) ||
                r.OwnVesselId == r.TargetVesselId) return "需要两个不同且非空的船舶标识。";
            var t = r.Thresholds;
            var positive = new[] { t.RestrictedVisibilityNm, t.CollisionRiskDcpaNm, t.SafePassingDcpaNm,
                t.SubstantialTurnDeg, t.SampleIntervalSeconds,
                t.EarlyActionTcpaSeconds, t.EarlyActionDistanceNm, t.SafeSpeedMps, t.ClearDistanceNm,
                t.StandOnEmergencyTcpaSeconds, t.StandOnInterventionTcpaSeconds,
                t.CollisionRiskTcpaSeconds, t.CloseQuartersDcpaNm, t.CloseQuartersTcpaSeconds,
                t.SubstantialSpeedChangeFraction, t.SubstantialTurnWindowSeconds,
                t.LockHeadingStableWindowSeconds, t.LockMaxDeferSeconds };
            foreach (double value in positive) if (!Finite(value) || value <= 0) return "阈值必须为有限正数。";
            var nonnegative = new[] { t.HeadOnHalfAngleDeg, t.OvertakingAbaftBeamAngleDeg,
                t.MaintainHeadingToleranceDeg, t.MaintainSpeedToleranceMps, t.HeadOnForwardHalfAngleDeg,
                t.SubstantialSpeedChangeMps, t.HeadOnDoubtBearingDeg, t.LockHeadingStableMaxChangeDeg };
            foreach (double value in nonnegative) if (!Finite(value) || value < 0) return "角度/保持容差必须为有限非负数。";
            if (t.HeadOnHalfAngleDeg >= 90 || t.HeadOnForwardHalfAngleDeg >= 90 ||
                t.OvertakingAbaftBeamAngleDeg >= 90 || t.HeadOnDoubtBearingDeg >= 90 || t.SubstantialTurnDeg > 180 ||
                t.MaintainHeadingToleranceDeg >= t.SubstantialTurnDeg ||
                (t.SubstantialSpeedChangeMps > 0 && t.MaintainSpeedToleranceMps >= t.SubstantialSpeedChangeMps) ||
                t.StandOnEmergencyTcpaSeconds > t.StandOnInterventionTcpaSeconds)
                return "角度、明显行动/保持容差或R17阶段阈值的关系不合法。";
            string error = ValidateSamples(r.OwnSamples) ?? ValidateSamples(r.TargetSamples);
            if (error != null) return error;
            if (r.VisibilityNm.HasValue && (double.IsNaN(r.VisibilityNm.Value) || r.VisibilityNm.Value < 0))
                return "能见度必须为非负数。";
            double previous = double.NegativeInfinity;
            foreach (var state in r.Environment)
            {
                if (!Finite(state.Time.Seconds) || state.Time.Seconds <= previous ||
                    !Finite(state.VisibilityNm) || state.VisibilityNm < 0)
                    return "环境状态时间必须严格递增且能见度为有限非负数。";
                previous = state.Time.Seconds;
            }
            previous = double.NegativeInfinity;
            if (r.InSightSamples != null)
                foreach (var sample in r.InSightSamples)
                {
                    if (sample == null || !Finite(sample.Time.Seconds) || sample.Time.Seconds <= previous)
                        return "互见序列时间必须为有限值且严格递增。";
                    previous = sample.Time.Seconds;
                }
            if (r.ChannelCenterline != null)
                foreach (var point in r.ChannelCenterline)
                    if (!Finite(point.EastM) || !Finite(point.NorthM) || !Finite(point.UpM))
                        return "航道中心线坐标必须有效。";
            var statusTimes = new Dictionary<string, double>();
            if (r.VesselStatusSamples != null)
                foreach (var sample in r.VesselStatusSamples)
                {
                    double last;
                    if (sample == null || (sample.VesselId != r.OwnVesselId && sample.VesselId != r.TargetVesselId) ||
                        !Finite(sample.Time.Seconds) || !Enum.IsDefined(typeof(ColregVesselStatus), sample.Status) ||
                        (statusTimes.TryGetValue(sample.VesselId, out last) && sample.Time.Seconds <= last))
                        return "船舶状态必须属于请求船舶，状态有效且同船时间为有限值并严格递增。";
                    statusTimes[sample.VesselId] = sample.Time.Seconds;
                }
            return null;
        }

        private static string ValidateSamples(IReadOnlyList<TrackSample> samples)
        {
            if (samples == null || samples.Count == 0) return "航迹不能为空。";
            double previous = double.NegativeInfinity;
            foreach (var s in samples)
            {
                if (!Finite(s.Time.Seconds) || s.Time.Seconds <= previous || !Finite(s.EnuCenter.EastM) ||
                    !Finite(s.EnuCenter.NorthM) || !Finite(s.VelocityEnuMps.X) || !Finite(s.VelocityEnuMps.Y) ||
                    !Finite(s.SogMps) || s.SogMps < 0 || !Finite(Heading(s)) || Heading(s) < 0 || Heading(s) > 360)
                    return "航迹时间必须严格递增，ENU、速度与有效船首向（或替代COG）必须有效。";
                previous = s.Time.Seconds;
            }
            return null;
        }
    }

    /// <summary>内部单时刻状态；CPA由既有解算器提供。</summary>
    internal sealed class ColregFrame
    {
        internal TrackSample Own { get; }
        internal TrackSample Target { get; }
        internal CpaResult Cpa { get; }
        internal double VisibilityNm { get; }
        internal double OwnBearingDeg { get; }
        internal double TargetBearingDeg { get; }
        internal double HeadingDifferenceDeg { get; }
        internal bool HasCollisionRisk { get; set; }
        internal bool InSight { get; set; }
        internal ColregDangerStage DangerStage { get; set; }
        internal int EncounterId { get; set; }
        internal bool Doubt { get; set; }
        internal string DoubtReason { get; set; }
        internal ColregVesselStatus OwnStatus { get; set; }
        internal ColregVesselStatus TargetStatus { get; set; }
        internal double? RiskStartTime { get; set; }
        internal string Basis { get; set; }
        internal bool CrossingGeometryAmbiguous { get; set; }
        internal int Overtaker { get; set; }
        internal EncounterSituation Situation { get; set; }
        internal TrafficRole OwnRole { get; set; }
        internal TrafficRole TargetRole { get; set; }

        internal ColregFrame(TrackSample own, TrackSample target, CpaResult cpa, double visibilityNm)
        {
            Own = own; Target = target; Cpa = cpa; VisibilityNm = visibilityNm;
            OwnBearingDeg = ColregEngine.Normalize(cpa.TrueBearingDeg - ColregEngine.Heading(own));
            TargetBearingDeg = ColregEngine.Normalize(cpa.TrueBearingDeg + 180 - ColregEngine.Heading(target));
            HeadingDifferenceDeg = Math.Abs(ColregEngine.Delta(ColregEngine.Heading(own), ColregEngine.Heading(target)));
        }

        internal bool SameClassification(ColregFrame other)
        {
            return Situation == other.Situation && OwnRole == other.OwnRole && TargetRole == other.TargetRole &&
                InSight == other.InSight && Doubt == other.Doubt && DoubtReason == other.DoubtReason &&
                OwnStatus == other.OwnStatus && TargetStatus == other.TargetStatus;
        }
    }

    /// <summary>内部时间带与对应观测端点索引。</summary>
    internal sealed class ColregSpan
    {
        internal int First { get; }
        internal int Last { get; }
        internal ColregTimeBand Band { get; }
        internal ColregSpan(int first, int last, ColregTimeBand band)
        {
            First = first; Last = last; Band = band;
        }
    }
}
