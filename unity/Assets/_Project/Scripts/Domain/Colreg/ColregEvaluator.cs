using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Cpa;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Colreg
{
    /// <summary>逐时间带对照应采取行动与观测操纵；所有CPA均复用既有解算器。</summary>
    internal static class ColregEvaluator
    {
        internal static void Evaluate(ColregAnalysisRequest request, List<ColregFrame> frames,
            ColregSpan span, List<ColregRuleCheck> checks)
        {
            var own = Observe(frames, span, true, request.Thresholds);
            var target = Observe(frames, span, false, request.Thresholds);
            EvaluateVessel(request, frames, span, true, own, checks);
            EvaluateVessel(request, frames, span, false, target, checks);
        }

        private static void EvaluateVessel(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, ObservedManeuver action,
            List<ColregRuleCheck> checks)
        {
            var first = frames[span.First];
            var last = frames[span.Last];
            var t = r.Thresholds;
            var role = own ? first.OwnRole : first.TargetRole;
            var vesselStatus = own ? first.OwnStatus : first.TargetStatus;
            bool privileged = Privileged(vesselStatus);
            bool statusRelationship = StatusRelationship(first);
            bool pending = first.DoubtReason == ColregDoubtReasons.PendingStableHeading;
            bool reviewRoles = role == TrafficRole.Undetermined;
            double bearing = own ? first.OwnBearingDeg : first.TargetBearingDeg;
            string vessel = own ? r.OwnVesselId : r.TargetVesselId;
            bool observed = action.ObservedDurationSeconds > 0;
            bool substantial = Substantial(action, t);
            bool early = Early(r, action, first);
            double minimumDistance = MinimumObservedDistance(frames, span);
            bool safe = SafePassing(last.Cpa, t) && minimumDistance >= t.SafePassingDcpaNm * VesselMotionState.MetersPerNm;
            bool holding = Holding(frames, span, own, t);
            double earlyTcpa, earlyDistance;
            ActionEvidence(r, action, first, out earlyTcpa, out earlyDistance);
            var evidence = new ColregEvidence(bearing, first.HeadingDifferenceDeg, first.Cpa.DcpaM,
                first.Cpa.TcpaSec, action.HeadingChangeDeg, action.SpeedChangeMps,
                first.VisibilityNm, first.Cpa.CurrentDistanceM, last.Cpa.DcpaM,
                minimumDistance, last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM, earlyTcpa, earlyDistance);
            string numbers = string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "及早={0}；明显行动={1}；安全驶过代理={2}；终点DCPA={3:F3}m，TCPA={4:F3}s，间距={5:F3}m；观测最小中心间距={6:F3}m。",
                early, substantial, safe, last.Cpa.DcpaM, last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM, minimumDistance);

            Action<ColregRuleId, RuleCheckStatus, string, string, string> add = (id, status, clause, expected, explanation) =>
                checks.Add(new ColregRuleCheck(span.Band.StartTime, span.Band.EndTime, id, vessel,
                    status, clause, expected, action, evidence, explanation));
            Action<ColregRuleId> na = id => add(id, RuleCheckStatus.NotApplicable, id.ToString(),
                ColregRules.Get(id).Summary, privileged && id >= ColregRuleId.R14 && id <= ColregRuleId.R17 ?
                "船舶状态为" + (vesselStatus == ColregVesselStatus.NotUnderCommand ? "失控" : "操限") + "，R18 适用；本船无直航义务。" :
                "本时间带的会遇局面或船舶角色不适用该项。");
            Action<ColregRuleId> review = id => add(id, RuleCheckStatus.NeedsReview, id.ToString(),
                ColregRules.Get(id).Summary, pending ? "转向中，延后判定；稳定航向或达到最大延后时长前不确定会遇角色。" :
                "让路/直航角色需研判；" + first.Basis);

            AddAvoidanceChecks(r, frames, span, own, checks);

            AddGeneralChecks(r, frames, span, own, checks);
            RuleCheckStatus channelStatus = !r.InNarrowChannel ? RuleCheckStatus.NotApplicable :
                r.ChannelCenterline == null || r.ChannelCenterline.Count < 2 ? RuleCheckStatus.NotAssessable :
                ChannelRightSide(r.ChannelCenterline, frames, span, own);
            add(ColregRuleId.R9, channelStatus, "R9(a)", "在狭水道尽量靠本船右舷一侧的航道外缘行驶。",
                !r.InNarrowChannel ? "请求未标记狭水道。" : channelStatus == RuleCheckStatus.NotAssessable ?
                "已标记狭水道；需要有效航道中心线、外缘和船位记录，才能核查靠右外缘的几何项。" :
                "按最近的航道中心线段及本船沿该段的航行方向核查右侧；未提供外缘，结论仅核查中线右侧。");

            AddResponsibilityChecks(r, frames, span, own, checks);

            if (pending || (reviewRoles && ComplexStatuses(first))) review(ColregRuleId.R13);
            else if (first.Situation == EncounterSituation.Overtaking && role != TrafficRole.None)
                add(ColregRuleId.R13, !observed ? RuleCheckStatus.Partial :
                    (role == TrafficRole.GiveWay ? safe : holding) ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied,
                    "R13", role == TrafficRole.GiveWay ? "追越船应让清，驶过让清前持续履行让路义务。" : "被追越船按直航船规则核查保向保速。",
                    "闭边界追越判据；追越身份持续至驶过、达到让清距离且正在远离。" + numbers + ObservationNote(observed));
            else na(ColregRuleId.R13);

            if (privileged) na(ColregRuleId.R14);
            else if (pending || (reviewRoles && ComplexStatuses(first))) review(ColregRuleId.R14);
            else if (first.Situation == EncounterSituation.HeadOn && !statusRelationship)
                add(ColregRuleId.R14, !observed ? RuleCheckStatus.Partial :
                    action.MaxPortTurnDeg > t.MaintainHeadingToleranceDeg || action.MaxStarboardTurnDeg <= t.MaintainHeadingToleranceDeg
                        ? RuleCheckStatus.NotSatisfied : RuleCheckStatus.Satisfied,
                    "R14", "双方均应向右转向，以便从他船左舷驶过。",
                    "按船首向差和双方前方扇区识别；任何超出噪声容差的左转均不满足。" + ObservationNote(observed));
            else na(ColregRuleId.R14);

            if (privileged) na(ColregRuleId.R15);
            else if (reviewRoles) review(ColregRuleId.R15);
            else if (first.Situation == EncounterSituation.Crossing && !statusRelationship)
            {
                bool astern = PassesAstern(last, own);
                add(ColregRuleId.R15, role == TrafficRole.StandOn ? RuleCheckStatus.NotApplicable :
                    !observed || first.CrossingGeometryAmbiguous ? RuleCheckStatus.Partial :
                    safe && substantial && astern ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied,
                    "R15", role == TrafficRole.GiveWay ? "他船在本船右舷，应给他船让路并避免横越其前方。" : "他船在本船左舷，按R17核查直航行动。",
                    "采用终点CPA预测相对位置沿直航船船首方向的投影核查前后关系；双方同侧或轴线几何疑义=" + first.CrossingGeometryAmbiguous + "。" +
                    "预测从后方驶过=" + astern + "；" + numbers + ObservationNote(observed));
            }
            else na(ColregRuleId.R15);

            if (privileged) na(ColregRuleId.R16);
            else if (reviewRoles) review(ColregRuleId.R16);
            else if (role == TrafficRole.GiveWay)
            {
                // 延后期的操纵属于同次风险，锁定后仍须保留；不跨状态变化或互见重判的会遇边界。
                var actionSpan = PendingActionSpan(frames, span);
                var giveWayAction = Observe(frames, actionSpan, own, t);
                // 行动与安全效果使用同一观察范围，不能漏掉延后期已经发生的过近驶过。
                double giveWayMinimumDistance = MinimumObservedDistance(frames, actionSpan);
                bool giveWaySafe = SafePassing(last.Cpa, t) &&
                    giveWayMinimumDistance >= t.SafePassingDcpaNm * VesselMotionState.MetersPerNm;
                double giveWayTcpa, giveWayDistance;
                ActionEvidence(r, giveWayAction, first, out giveWayTcpa, out giveWayDistance);
                bool giveWayAdequate = Early(r, giveWayAction, first) && Substantial(giveWayAction, t) && giveWaySafe &&
                    !(first.Situation == EncounterSituation.HeadOn && !statusRelationship &&
                        giveWayAction.MaxPortTurnDeg > t.MaintainHeadingToleranceDeg);
                checks.Add(new ColregRuleCheck(span.Band.StartTime, span.Band.EndTime, ColregRuleId.R16,
                    vessel, giveWayAction.ObservedDurationSeconds <= 0 ? RuleCheckStatus.Partial :
                    giveWayAdequate ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied,
                    "R16", "让路船应及早采取大幅度行动，以便明确让清他船。", giveWayAction,
                    new ColregEvidence(bearing, first.HeadingDifferenceDeg, first.Cpa.DcpaM, first.Cpa.TcpaSec,
                        giveWayAction.HeadingChangeDeg, giveWayAction.SpeedChangeMps, first.VisibilityNm,
                        first.Cpa.CurrentDistanceM, last.Cpa.DcpaM, giveWayMinimumDistance, last.Cpa.TcpaSec,
                        last.Cpa.CurrentDistanceM, giveWayTcpa, giveWayDistance),
                    "及早=" + Early(r, giveWayAction, first) + "；明显行动=" + Substantial(giveWayAction, t) +
                    "；安全驶过代理=" + giveWaySafe + "；保留同次风险延后判定期间的行动和最小间距。" + ObservationNote(giveWayAction.ObservedDurationSeconds > 0)));
            }
            else na(ColregRuleId.R16);

            if (privileged) na(ColregRuleId.R17);
            else if (reviewRoles) review(ColregRuleId.R17);
            else if (role == TrafficRole.StandOn) AddStandOnChecks(r, frames, span, own, checks);
            else na(ColregRuleId.R17);

            if (first.Situation == EncounterSituation.RestrictedVisibility)
            {
                foreach (var phase in RiskSpans(frames, span, t))
                {
                    bool active = frames[phase.First].HasCollisionRisk || CloseQuarters(frames[phase.First], t);
                    AddPhaseCheck(r, frames, phase, own, checks, ColregRuleId.R19,
                        active ? RuleCheckStatus.NeedsReview : RuleCheckStatus.NotApplicable, "R19(b)",
                        "以适合能见度不良环境的安全航速行驶。", active ? SpeedReview(frames, phase, own, t) : "本区段无碰撞危险或紧迫局面。");
                }
                bool foreApplicable, aftApplicable;
                bool foreViolation, aftViolation;
                RestrictedTurns(frames, span, own, action, t, out foreApplicable, out aftApplicable,
                    out foreViolation, out aftViolation);
                add(ColregRuleId.R19, !foreApplicable ? RuleCheckStatus.NotApplicable : !observed ? RuleCheckStatus.Partial :
                    foreViolation ? RuleCheckStatus.NotSatisfied : RuleCheckStatus.Satisfied,
                    "R19(d)(i)", "对正横以前他船避免向左转向，正在被本船追越的目标除外。",
                    "以各观测段起点相对方位核查；追越例外依据保留的追越身份。" + ObservationNote(observed));
                add(ColregRuleId.R19, !aftApplicable ? RuleCheckStatus.NotApplicable : !observed ? RuleCheckStatus.Partial :
                    aftViolation ? RuleCheckStatus.NotSatisfied : RuleCheckStatus.Satisfied,
                    "R19(d)(ii)", "对正横或正横以后他船避免朝其转向。",
                    "右舷正横至船尾禁右转，左舷船尾至正横禁左转；正后方任一明显转向保守列为不满足。" + ObservationNote(observed));
            }
            else na(ColregRuleId.R19);
        }

        private static bool Privileged(ColregVesselStatus status)
        {
            return status == ColregVesselStatus.NotUnderCommand || status == ColregVesselStatus.RestrictedManoeuvrability;
        }

        private static bool Ordinary(ColregVesselStatus status)
        {
            return status == ColregVesselStatus.PowerDriven || status == ColregVesselStatus.Unknown;
        }

        private static bool StatusRelationship(ColregFrame frame)
        {
            return Privileged(frame.OwnStatus) && Ordinary(frame.TargetStatus) ||
                Privileged(frame.TargetStatus) && Ordinary(frame.OwnStatus);
        }

        private static bool ComplexStatuses(ColregFrame frame)
        {
            return !StatusRelationship(frame) && !(Ordinary(frame.OwnStatus) && Ordinary(frame.TargetStatus));
        }

        private static void AddResponsibilityChecks(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, List<ColregRuleCheck> checks)
        {
            foreach (var phase in RiskSpans(frames, span, r.Thresholds))
            {
                var first = frames[phase.First];
                var last = frames[phase.Last];
                bool active = first.HasCollisionRisk || first.Overtaker != 0;
                RuleCheckStatus verdict;
                string clause = "R18", explanation;
                var actionSpan = PendingActionSpan(frames, phase);
                var action = Observe(frames, actionSpan, own, r.Thresholds);
                var role = own ? first.OwnRole : first.TargetRole;
                if (!active)
                {
                    verdict = RuleCheckStatus.NotApplicable;
                    explanation = "本区段无碰撞危险或持续追越义务。";
                }
                else if (ComplexStatuses(first))
                {
                    verdict = RuleCheckStatus.NeedsReview;
                    explanation = "船舶状态组合为" + first.OwnStatus + " / " + first.TargetStatus +
                        "，涉及双方失控/操限、限于吃水、捕鱼或帆船；需结合号灯号型、VHF通报、VDR音频、轮机日志及水域条件研判R18，不确定让路/直航角色。";
                }
                else if (StatusRelationship(first))
                {
                    clause = "R18(a)";
                    bool safe = SafePassing(last.Cpa, r.Thresholds) &&
                        MinimumObservedDistance(frames, actionSpan) >= r.Thresholds.SafePassingDcpaNm * VesselMotionState.MetersPerNm;
                    verdict = role != TrafficRole.GiveWay ? RuleCheckStatus.NotApplicable :
                        action.ObservedDurationSeconds <= 0 ? RuleCheckStatus.Partial :
                        Early(r, action, first) && Substantial(action, r.Thresholds) && safe
                            ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied;
                    explanation = role == TrafficRole.GiveWay ?
                        "R18(a)：本船应让清失控/操限船；R13追越义务优先；及早=" + Early(r, action, first) +
                        "；明显行动=" + Substantial(action, r.Thresholds) + "；安全驶过代理=" + safe + "。" :
                        "本船为失控/操限船，由他船按R18(a)让路；本船无直航义务，R5/R7/R8/R19仍独立核查。";
                }
                else if (first.OwnStatus == ColregVesselStatus.Unknown || first.TargetStatus == ColregVesselStatus.Unknown)
                {
                    verdict = RuleCheckStatus.NotAssessable;
                    explanation = "缺少船舶状态证据：需要号灯、号型、VHF通报、VDR音频和轮机日志，才能核查R18船舶之间的责任；Unknown暂按机动船进行R13–R17几何核查。";
                }
                else
                {
                    verdict = RuleCheckStatus.NotApplicable;
                    explanation = "双方均明确为机动船，无R18特殊状态关系；按会遇局面核查R13–R17。";
                }
                double earlyTcpa, earlyDistance;
                ActionEvidence(r, action, first, out earlyTcpa, out earlyDistance);
                var evidence = new ColregEvidence(own ? first.OwnBearingDeg : first.TargetBearingDeg,
                    first.HeadingDifferenceDeg, first.Cpa.DcpaM, first.Cpa.TcpaSec, action.HeadingChangeDeg,
                    action.SpeedChangeMps, first.VisibilityNm, first.Cpa.CurrentDistanceM, last.Cpa.DcpaM,
                    MinimumObservedDistance(frames, actionSpan), last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM,
                    earlyTcpa, earlyDistance);
                checks.Add(new ColregRuleCheck(first.Own.Time, last.Own.Time, ColregRuleId.R18,
                    own ? r.OwnVesselId : r.TargetVesselId, verdict, clause,
                    "按经确认的船舶状态及R13追越优先条款确定让清义务。", action, evidence, explanation));
            }
        }

        private static ColregSpan PendingActionSpan(List<ColregFrame> frames, ColregSpan span)
        {
            int first = span.First;
            int encounterId = frames[first].EncounterId;
            if (encounterId == 0) return span;
            int encounterFirst = first;
            while (encounterFirst > 0 && frames[encounterFirst - 1].EncounterId == encounterId)
                encounterFirst--;
            // 只继承延后判定的前缀；正常带切分、状态变化和新会遇不借用早先操纵。
            if (encounterFirst < first && frames[encounterFirst].DoubtReason == ColregDoubtReasons.PendingStableHeading)
                first = encounterFirst;
            return new ColregSpan(first, span.Last, span.Band);
        }

        private static ObservedManeuver Observe(List<ColregFrame> frames, ColregSpan span, bool own, ColregThresholds t)
        {
            var first = own ? frames[span.First].Own : frames[span.First].Target;
            var previous = first;
            double cumulative = 0, minimum = 0, maximum = 0, port = 0, starboard = 0;
            double speedUp = 0, speedDown = 0;
            SimTime? actionTime = null;
            var times = new List<double> { first.Time.Seconds };
            var headings = new List<double> { 0 };
            int direction = 0, runFirst = 0, windowFirst = 0;
            double speedBaseline = first.SogMps;
            int speedDirection = 0;
            for (int i = span.First + 1; i <= span.Last; i++)
            {
                var current = own ? frames[i].Own : frames[i].Target;
                double change = ColregEngine.Delta(ColregEngine.Heading(previous), ColregEngine.Heading(current));
                cumulative += change;
                starboard = Math.Max(starboard, cumulative - minimum);
                port = Math.Max(port, maximum - cumulative);
                maximum = Math.Max(maximum, cumulative);
                minimum = Math.Min(minimum, cumulative);
                speedUp = Math.Max(speedUp, current.SogMps - first.SogMps);
                speedDown = Math.Max(speedDown, first.SogMps - current.SogMps);
                int index = times.Count;
                times.Add(current.Time.Seconds);
                headings.Add(cumulative);
                int nextDirection = Math.Abs(change) <= 1e-7 ? 0 : Math.Sign(change);
                if (nextDirection != 0 && nextDirection != direction)
                {
                    direction = nextDirection;
                    runFirst = index - 1;
                }
                SimTime? turnTime = null;
                if (!actionTime.HasValue && direction != 0)
                    turnTime = FirstWindowTurn(times, headings, runFirst, index, direction,
                        t.SubstantialTurnWindowSeconds, t.SubstantialTurnDeg, ref windowFirst);
                if (turnTime.HasValue) actionTime = turnTime;
                double speedDelta = current.SogMps - previous.SogMps;
                int nextSpeedDirection = Math.Abs(speedDelta) <= 1e-7 ? 0 : Math.Sign(speedDelta);
                if (nextSpeedDirection != 0 && nextSpeedDirection != speedDirection)
                {
                    speedDirection = nextSpeedDirection;
                    speedBaseline = previous.SogMps;
                }
                double threshold = double.PositiveInfinity;
                if (t.SubstantialSpeedChangeFraction > 0 && speedBaseline > 0)
                    threshold = t.SubstantialSpeedChangeFraction * speedBaseline;
                if (t.SubstantialSpeedChangeMps > 0) threshold = Math.Min(threshold, t.SubstantialSpeedChangeMps);
                if ((!actionTime.HasValue || turnTime.HasValue) && nextSpeedDirection != 0)
                {
                    double fraction = CrossingFraction(Math.Abs(previous.SogMps - speedBaseline),
                        Math.Abs(current.SogMps - speedBaseline), threshold);
                    if (fraction <= 1)
                    {
                        var speedTime = new SimTime(previous.Time.Seconds + fraction * (current.Time - previous.Time));
                        if (!actionTime.HasValue || speedTime < actionTime.Value) actionTime = speedTime;
                    }
                }
                previous = current;
            }
            TurnDirection turn = Math.Abs(cumulative) > t.MaintainHeadingToleranceDeg
                ? cumulative > 0 ? TurnDirection.Starboard : TurnDirection.Port
                : Math.Max(starboard, port) <= t.MaintainHeadingToleranceDeg ? TurnDirection.None
                : starboard >= port ? TurnDirection.Starboard : TurnDirection.Port;
            double speedChange = previous.SogMps - first.SogMps;
            SpeedChange speed = Math.Abs(speedChange) > t.MaintainSpeedToleranceMps
                ? speedChange > 0 ? SpeedChange.Accelerating : SpeedChange.Decelerating
                : Math.Max(speedUp, speedDown) <= t.MaintainSpeedToleranceMps ? SpeedChange.Steady
                : speedUp >= speedDown ? SpeedChange.Accelerating : SpeedChange.Decelerating;
            return new ObservedManeuver(cumulative, speedChange, turn, speed, starboard, port,
                speedUp, speedDown, actionTime, previous.Time - first.Time);
        }

        private static SimTime? FirstWindowTurn(List<double> times, List<double> headings,
            int runFirst, int index, int direction, double window, double threshold, ref int windowFirst)
        {
            double previousTime = times[index - 1], currentTime = times[index];
            windowFirst = Math.Max(windowFirst, runFirst);
            while (windowFirst < index && times[windowFirst] + window <= previousTime) windowFirst++;
            double left = previousTime;
            double before = WindowAmount(times, headings, runFirst, index, direction, window, left);
            int shifted = windowFirst;
            while (true)
            {
                double right = shifted < index ? Math.Min(currentTime, times[shifted] + window) : currentTime;
                double after = WindowAmount(times, headings, runFirst, index, direction, window, right);
                double fraction = CrossingFraction(before, after, threshold);
                if (fraction <= 1) return new SimTime(left + fraction * (right - left));
                if (right >= currentTime) break;
                left = right;
                before = after;
                shifted++;
            }
            windowFirst = shifted;
            return null;
        }

        private static double WindowAmount(List<double> times, List<double> headings,
            int runFirst, int index, int direction, double window, double time)
        {
            // F(t) 的折点同时包括船首向样本与样本+窗口；在折点间作线性求交可精确给首次行动时刻。
            double start = Math.Max(times[runFirst], time - window);
            int lo = runFirst, hi = index - 1;
            while (lo < hi)
            {
                int middle = lo + (hi - lo + 1) / 2;
                if (times[middle] <= start) lo = middle;
                else hi = middle - 1;
            }
            double startHeading = headings[lo];
            if (times[lo] < start)
                startHeading += (headings[lo + 1] - startHeading) * (start - times[lo]) / (times[lo + 1] - times[lo]);
            double endHeading = headings[index - 1] + (headings[index] - headings[index - 1]) *
                (time - times[index - 1]) / (times[index] - times[index - 1]);
            return direction * (endHeading - startHeading);
        }

        private static double CrossingFraction(double before, double after, double threshold)
        {
            const double tolerance = 1e-7;
            if (before >= threshold - tolerance) return 0;
            return after >= threshold - tolerance && after > before ?
                Math.Min(1, (threshold - before) / (after - before)) : 2;
        }

        private static bool Substantial(ObservedManeuver a, ColregThresholds t)
        {
            // Max* 保留完整观测幅值；资格由滑窗/行动前初速判据的首次触发时刻决定。
            return a.FirstSubstantialActionTime.HasValue;
        }

        private static bool Early(ColregAnalysisRequest r, ObservedManeuver a, ColregFrame first)
        {
            double tcpa, distance;
            ActionEvidence(r, a, first, out tcpa, out distance);
            return tcpa >= r.Thresholds.EarlyActionTcpaSeconds || distance / VesselMotionState.MetersPerNm >= r.Thresholds.EarlyActionDistanceNm;
        }

        private static void ActionEvidence(ColregAnalysisRequest r, ObservedManeuver a, ColregFrame first,
            out double remainingTcpa, out double distanceM)
        {
            remainingTcpa = distanceM = double.NaN;
            if (!a.FirstSubstantialActionTime.HasValue) return;
            double time = a.FirstSubstantialActionTime.Value.Seconds;
            var own = ColregEngine.SampleAt(r.OwnSamples, time);
            var target = ColregEngine.SampleAt(r.TargetSamples, time);
            var atAction = CpaCalculator.CalculateFromSamples(own, target);
            double riskStart = first.RiskStartTime ?? first.Own.Time.Seconds;
            var origin = CpaCalculator.CalculateFromSamples(ColregEngine.SampleAt(r.OwnSamples, riskStart),
                ColregEngine.SampleAt(r.TargetSamples, riskStart));
            remainingTcpa = origin.TcpaSec - (time - riskStart);
            distanceM = atAction.CurrentDistanceM;
        }

        private static double MinimumObservedDistance(List<ColregFrame> frames, ColregSpan span)
        {
            double minimum = frames[span.First].Cpa.CurrentDistanceM;
            for (int i = span.First; i < span.Last; i++)
            {
                var a = frames[i];
                var b = frames[i + 1];
                double seconds = b.Own.Time - a.Own.Time;
                var ownVelocity = (b.Own.EnuCenter.Horizontal - a.Own.EnuCenter.Horizontal) * (1 / seconds);
                var targetVelocity = (b.Target.EnuCenter.Horizontal - a.Target.EnuCenter.Horizontal) * (1 / seconds);
                var cpa = CpaCalculator.CalculateFromStates(
                    VesselMotionState.FromEnuMeters(a.Own.EnuCenter, ownVelocity),
                    VesselMotionState.FromEnuMeters(a.Target.EnuCenter, targetVelocity));
                // 按段内TCPA限制既有解算器结果，避免将观测区间外的CPA当成实际经过距离。
                if (!cpa.IsDegenerate && cpa.TcpaSec >= 0 && cpa.TcpaSec <= seconds)
                    minimum = Math.Min(minimum, cpa.DcpaM);
                minimum = Math.Min(minimum, Math.Min(cpa.CurrentDistanceM, b.Cpa.CurrentDistanceM));
            }
            return minimum;
        }

        private static bool SafePassing(CpaResult cpa, ColregThresholds t)
        {
            if (cpa.IsDegenerate) return cpa.CurrentDistanceNm >= t.SafePassingDcpaNm;
            return cpa.TcpaSec > 0 ? cpa.DcpaNm >= t.SafePassingDcpaNm :
                cpa.IsDiverging && cpa.CurrentDistanceNm >= t.SafePassingDcpaNm;
        }

        private static bool Holding(List<ColregFrame> frames, ColregSpan span, bool own, ColregThresholds t)
        {
            var first = own ? frames[span.First].Own : frames[span.First].Target;
            double accumulated = 0;
            var previous = first;
            for (int i = span.First; i <= span.Last; i++)
            {
                var sample = own ? frames[i].Own : frames[i].Target;
                accumulated += ColregEngine.Delta(ColregEngine.Heading(previous), ColregEngine.Heading(sample));
                if (Math.Abs(accumulated) > t.MaintainHeadingToleranceDeg ||
                    Math.Abs(sample.SogMps - first.SogMps) > t.MaintainSpeedToleranceMps) return false;
                previous = sample;
            }
            return true;
        }

        private static void AddAvoidanceChecks(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, List<ColregRuleCheck> checks)
        {
            int first = span.First;
            bool active = frames[first].HasCollisionRisk || frames[first].Overtaker != 0;
            for (int i = span.First + 1; i < span.Last; i++)
            {
                // 右端点只用作上一阶段的效果证据，不另造归属下一带的零长核查。
                bool next = frames[i].HasCollisionRisk || frames[i].Overtaker != 0;
                if (next == active) continue;
                AddAvoidancePhase(r, frames, new ColregSpan(first, i, span.Band), own, active, checks);
                first = i;
                active = next;
            }
            AddAvoidancePhase(r, frames, new ColregSpan(first, span.Last, span.Band), own, active, checks);
        }

        private static void AddAvoidancePhase(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, bool active, List<ColregRuleCheck> checks)
        {
            var t = r.Thresholds;
            var first = frames[span.First];
            var last = frames[span.Last];
            var actionSpan = PendingActionSpan(frames, span);
            var action = Observe(frames, actionSpan, own, t);
            var role = own ? first.OwnRole : first.TargetRole;
            bool holding = Holding(frames, span, own, t);
            double minimumDistance = MinimumObservedDistance(frames, actionSpan);
            bool safe = SafePassing(last.Cpa, t) && minimumDistance >= t.SafePassingDcpaNm * VesselMotionState.MetersPerNm;
            bool allowed = first.Situation != EncounterSituation.HeadOn || StatusRelationship(first) ||
                action.MaxPortTurnDeg <= t.MaintainHeadingToleranceDeg;
            bool early = Early(r, action, first);
            bool substantial = Substantial(action, t);
            RuleCheckStatus status = !active || (role == TrafficRole.StandOn && holding && !Emergency(frames, span, t))
                ? RuleCheckStatus.NotApplicable : action.ObservedDurationSeconds <= 0 ? RuleCheckStatus.Partial :
                early && substantial && safe && allowed ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied;
            double earlyTcpa, earlyDistance;
            ActionEvidence(r, action, first, out earlyTcpa, out earlyDistance);
            var evidence = new ColregEvidence(own ? first.OwnBearingDeg : first.TargetBearingDeg,
                first.HeadingDifferenceDeg, first.Cpa.DcpaM, first.Cpa.TcpaSec, action.HeadingChangeDeg,
                action.SpeedChangeMps, first.VisibilityNm, first.Cpa.CurrentDistanceM, last.Cpa.DcpaM,
                minimumDistance, last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM, earlyTcpa, earlyDistance);
            checks.Add(new ColregRuleCheck(first.Own.Time, last.Own.Time, ColregRuleId.R8,
                own ? r.OwnVesselId : r.TargetVesselId, status, "R8",
                "及早采取明显的避碰行动，并核查能否在安全距离驶过。", action, evidence,
                status == RuleCheckStatus.NotApplicable ? "本阶段无碰撞危险，或直航船在正常保向保速阶段。" :
                "及早=" + early + "；明显行动=" + substantial + "；安全驶过代理=" + safe +
                "；按本阶段及继承的延后期全部观测段的CPA核查最小实际中心间距。" + ObservationNote(action.ObservedDurationSeconds > 0)));
        }

        private static void AddStandOnChecks(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, List<ColregRuleCheck> checks)
        {
            var t = r.Thresholds;
            int encounterFirst = span.First;
            int encounterId = frames[span.First].EncounterId;
            while (encounterFirst > 0 && encounterId != 0 && frames[encounterFirst - 1].EncounterId == encounterId)
                encounterFirst--;
            int encounterLast = EncounterLast(frames, span.Last, encounterId);
            var otherAction = Observe(frames, new ColregSpan(encounterFirst, encounterLast, span.Band), !own, t);
            int stage = 0;
            for (int i = encounterFirst; i <= span.First; i++)
                stage = Math.Max(stage, StandOnStage(frames[i], otherAction.FirstSubstantialActionTime.HasValue &&
                    otherAction.FirstSubstantialActionTime.Value <= frames[i].Own.Time, t));
            int first = span.First;
            for (int i = span.First + 1; i < span.Last; i++)
            {
                // 本次危险期内只推进；自己的操纵引起 TCPA 回升或退化不重置已进入的阶段。
                int nextStage = Math.Max(stage, StandOnStage(frames[i], otherAction.FirstSubstantialActionTime.HasValue &&
                    otherAction.FirstSubstantialActionTime.Value <= frames[i].Own.Time, t));
                if (nextStage == stage) continue;
                AddStandOnPhase(r, frames, new ColregSpan(first, i, span.Band), encounterFirst, own, stage, checks);
                first = i;
                stage = nextStage;
            }
            AddStandOnPhase(r, frames, new ColregSpan(first, span.Last, span.Band), encounterFirst, own, stage, checks);
        }

        private static int StandOnStage(ColregFrame frame, bool otherSubstantial, ColregThresholds t)
        {
            if (!frame.HasCollisionRisk || (otherSubstantial && SafePassing(frame.Cpa, t))) return 0;
            if (frame.Cpa.TcpaSec <= t.StandOnEmergencyTcpaSeconds + 1e-7) return 2;
            return frame.Cpa.TcpaSec <= t.StandOnInterventionTcpaSeconds + 1e-7 ? 1 : 0;
        }

        private static void AddStandOnPhase(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, int encounterFirst, bool own, int stage, List<ColregRuleCheck> checks)
        {
            var t = r.Thresholds;
            var first = frames[span.First];
            var last = frames[span.Last];
            var action = Observe(frames, span, own, t);
            bool observed = action.ObservedDurationSeconds > 0;
            bool holding = Holding(frames, span, own, t);
            var continuousSpan = ContinuousActionSpan(frames, span, encounterFirst, own);
            var continuousAction = Observe(frames, continuousSpan, own, t);
            bool substantial = Substantial(action, t) || Substantial(continuousAction, t);
            bool continuing = ContinuingManeuver(frames, span, encounterFirst, own, action, t) ||
                PriorPermittedAction(frames, span, encounterFirst, own, t);
            // 安全效果在整个锁定危险期的结束帧核查，不用操纵中途的阶段切分点作最终结论。
            int encounterLast = EncounterLast(frames, span.Last, frames[encounterFirst].EncounterId);
            var outcome = frames[encounterLast];
            double minimumDistance = MinimumObservedDistance(frames, new ColregSpan(encounterFirst, encounterLast, span.Band));
            bool safe = SafePassing(outcome.Cpa, t) && minimumDistance >= t.SafePassingDcpaNm * VesselMotionState.MetersPerNm;
            bool forbiddenPort = first.Situation == EncounterSituation.Crossing && PortTowardPortVessel(frames, span, own, action, t);
            RuleCheckStatus status;
            if (!observed) status = RuleCheckStatus.Partial;
            else if (forbiddenPort) status = RuleCheckStatus.NotSatisfied;
            else if (stage == 2) status = (substantial || continuing) && safe ? RuleCheckStatus.Partial : RuleCheckStatus.NotSatisfied;
            else if (holding) status = RuleCheckStatus.Satisfied;
            else if (stage == 1) status = (substantial || continuing) && safe ? RuleCheckStatus.Satisfied : RuleCheckStatus.NotSatisfied;
            else status = RuleCheckStatus.NotSatisfied;
            double earlyTcpa, earlyDistance;
            ActionEvidence(r, action, first, out earlyTcpa, out earlyDistance);
            var evidence = new ColregEvidence(own ? first.OwnBearingDeg : first.TargetBearingDeg,
                first.HeadingDifferenceDeg, first.Cpa.DcpaM, first.Cpa.TcpaSec, action.HeadingChangeDeg,
                action.SpeedChangeMps, first.VisibilityNm, first.Cpa.CurrentDistanceM, last.Cpa.DcpaM,
                minimumDistance, last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM, earlyTcpa, earlyDistance);
            checks.Add(new ColregRuleCheck(first.Own.Time, last.Own.Time, ColregRuleId.R17,
                own ? r.OwnVesselId : r.TargetVesselId, status,
                stage == 2 ? "R17(b)" : stage == 1 ? "R17(a)(ii)" : "R17(a)(i)",
                stage == 2 ? "紧迫阶段应采取最有助于避碰的行动；交叉局面避免向左舷来船左转。" :
                stage == 1 ? "他船明显未适当行动时可采取避碰行动；避免向左舷来船左转。" : "直航船应保向保速，并持续观察让路船行动。",
                action, evidence,
                "本次危险期内R17阶段单调推进；安全效果按整个危险期结束核查；保向保速=" + holding + "；安全驶过代理=" + safe + "；连续操纵=" + continuing +
                "；朝左舷来船左转=" + forbiddenPort + "。" +
                (stage == 2 ? "缺少操纵性能与停船距离，无法证实单凭让路船已不能避碰；即使动作有效亦仅部分核查。" : "") +
                "R17不解除让路船义务。" + ObservationNote(observed)));
        }

        private static ColregSpan ContinuousActionSpan(List<ColregFrame> frames, ColregSpan phase,
            int encounterFirst, bool own)
        {
            int first = phase.First, last = phase.Last;
            // 仅当阶段边界落在操纵中才向两边补全；在操纵开始前的保向阶段不能借未来行动免责。
            if (first < last && Moving(frames, first, first + 1, own))
                while (first > encounterFirst && Moving(frames, first - 1, first, own)) first--;
            if (last > first && Moving(frames, last - 1, last, own))
                while (last + 1 < frames.Count && Moving(frames, last, last + 1, own)) last++;
            return new ColregSpan(first, last, phase.Band);
        }

        private static bool Moving(List<ColregFrame> frames, int first, int last, bool own)
        {
            var before = own ? frames[first].Own : frames[first].Target;
            var after = own ? frames[last].Own : frames[last].Target;
            return Math.Abs(ColregEngine.Delta(ColregEngine.Heading(before), ColregEngine.Heading(after))) > 1e-7 ||
                Math.Abs(after.SogMps - before.SogMps) > 1e-7;
        }

        private static int EncounterLast(List<ColregFrame> frames, int from, int encounterId)
        {
            int last = from;
            // 包含危险释放的首帧；该帧提供最终效果，而不改变核查的会遇身份。
            while (last + 1 < frames.Count && encounterId != 0 && frames[last].EncounterId == encounterId) last++;
            return last;
        }

        private static bool PriorPermittedAction(List<ColregFrame> frames, ColregSpan span,
            int encounterFirst, bool own, ColregThresholds t)
        {
            var prior = Observe(frames, new ColregSpan(encounterFirst, span.Last, span.Band), own, t);
            if (!prior.FirstSubstantialActionTime.HasValue) return false;
            // 先前已经在允许介入阶段采取的有效操纵，在紧迫阶段可继续发挥作用；无需每阶段重新转向。
            for (int i = encounterFirst; i <= span.Last && frames[i].Own.Time <= prior.FirstSubstantialActionTime.Value; i++)
                if (frames[i].HasCollisionRisk && frames[i].Cpa.TcpaSec <= t.StandOnInterventionTcpaSeconds + 1e-7)
                    return true;
            return false;
        }

        private static bool ContinuingManeuver(List<ColregFrame> frames, ColregSpan span, int encounterFirst,
            bool own, ObservedManeuver action, ColregThresholds t)
        {
            if (span.First <= encounterFirst || action.ObservedDurationSeconds <= 0) return false;
            var before = own ? frames[span.First - 1].Own : frames[span.First - 1].Target;
            var after = own ? frames[span.First].Own : frames[span.First].Target;
            double turn = ColregEngine.Delta(ColregEngine.Heading(before), ColregEngine.Heading(after));
            double speed = after.SogMps - before.SogMps;
            bool sameTurn = (turn > 0 && action.HeadingChangeDeg > t.MaintainHeadingToleranceDeg) ||
                (turn < 0 && action.HeadingChangeDeg < -t.MaintainHeadingToleranceDeg);
            bool sameSpeed = (speed > 0 && action.SpeedChangeMps > t.MaintainSpeedToleranceMps) ||
                (speed < 0 && action.SpeedChangeMps < -t.MaintainSpeedToleranceMps);
            if (!sameTurn && !sameSpeed) return false;
            return Substantial(Observe(frames, new ColregSpan(encounterFirst, span.Last, span.Band), own, t), t);
        }

        private static bool Emergency(List<ColregFrame> frames, ColregSpan span, ColregThresholds t)
        {
            // 不将下一局面端点的危险归到上一局面；单点带仍可显示阶段，但证据不足。
            for (int i = span.First; i < span.Last || i == span.First; i++)
                if (frames[i].HasCollisionRisk && frames[i].Cpa.TcpaSec <= t.StandOnEmergencyTcpaSeconds) return true;
            return false;
        }

        private static bool PassesAstern(ColregFrame f, bool own)
        {
            var standOn = own ? f.Target : f.Own;
            var giveWayCpa = own ? f.Cpa.OwnCpaEnu : f.Cpa.TargetCpaEnu;
            var standOnCpa = own ? f.Cpa.TargetCpaEnu : f.Cpa.OwnCpaEnu;
            double rad = ColregEngine.Heading(standOn) * Math.PI / 180;
            return (giveWayCpa.EastM - standOnCpa.EastM) * Math.Sin(rad) +
                (giveWayCpa.NorthM - standOnCpa.NorthM) * Math.Cos(rad) <= 0;
        }

        private static bool PortTowardPortVessel(List<ColregFrame> frames, ColregSpan span, bool own,
            ObservedManeuver action, ColregThresholds t)
        {
            if (action.MaxPortTurnDeg <= t.MaintainHeadingToleranceDeg) return false;
            for (int i = span.First; i < span.Last; i++)
            {
                double bearing = own ? frames[i].OwnBearingDeg : frames[i].TargetBearingDeg;
                var before = own ? frames[i].Own : frames[i].Target;
                var after = own ? frames[i + 1].Own : frames[i + 1].Target;
                if (bearing > 180 && ColregEngine.Delta(ColregEngine.Heading(before), ColregEngine.Heading(after)) < 0) return true;
            }
            return false;
        }

        private static void RestrictedTurns(List<ColregFrame> frames, ColregSpan span, bool own,
            ObservedManeuver action, ColregThresholds t, out bool foreApplicable, out bool aftApplicable,
            out bool foreViolation, out bool aftViolation)
        {
            foreApplicable = aftApplicable = foreViolation = aftViolation = false;
            for (int i = span.First; i < span.Last || i == span.First; i++)
            {
                var f = frames[i];
                if (!f.HasCollisionRisk && !CloseQuarters(f, t)) continue;
                double bearing = own ? f.OwnBearingDeg : f.TargetBearingDeg;
                bool forward = bearing < 90 || bearing > 270;
                bool overtakingTarget = f.Overtaker == (own ? 1 : 2);
                if (forward && !overtakingTarget) foreApplicable = true;
                if (!forward) aftApplicable = true;
                if (i == span.Last) continue;
                var before = own ? f.Own : f.Target;
                var after = own ? frames[i + 1].Own : frames[i + 1].Target;
                double change = ColregEngine.Delta(ColregEngine.Heading(before), ColregEngine.Heading(after));
                bool port = change < 0 && action.MaxPortTurnDeg > t.MaintainHeadingToleranceDeg;
                bool starboard = change > 0 && action.MaxStarboardTurnDeg > t.MaintainHeadingToleranceDeg;
                if (forward && !overtakingTarget && port) foreViolation = true;
                if (!forward && ((bearing <= 180 && starboard) || (bearing >= 180 && port))) aftViolation = true;
            }
        }

        private static bool CloseQuarters(ColregFrame frame, ColregThresholds t)
        {
            return !frame.Cpa.IsDegenerate && frame.Cpa.TcpaSec > 0 &&
                frame.Cpa.TcpaSec <= t.CloseQuartersTcpaSeconds && frame.Cpa.DcpaNm < t.CloseQuartersDcpaNm;
        }

        private static string SpeedReview(List<ColregFrame> frames, ColregSpan span, bool own, ColregThresholds t)
        {
            double speed = MaximumSpeed(frames, span, own);
            return string.Format(System.Globalization.CultureInfo.InvariantCulture,
                "需研判：观察最大航速={0:F3}m/s；能见度={1:F3}nm；航速提示值={2:F3}m/s{3}；" +
                "需要操纵性能、停船距离、交通密度、海况和驾驶台/雷达记录，提示值不作安全航速硬判。",
                speed, frames[span.First].VisibilityNm, t.SafeSpeedMps, speed > t.SafeSpeedMps ? "，超过提示值" : "");
        }

        private static IEnumerable<ColregSpan> RiskSpans(List<ColregFrame> frames, ColregSpan span, ColregThresholds t)
        {
            int first = span.First;
            bool active = frames[first].HasCollisionRisk || CloseQuarters(frames[first], t);
            for (int i = span.First + 1; i < span.Last; i++)
            {
                bool next = frames[i].HasCollisionRisk || CloseQuarters(frames[i], t);
                if (next == active) continue;
                yield return new ColregSpan(first, i, span.Band);
                first = i;
                active = next;
            }
            yield return new ColregSpan(first, span.Last, span.Band);
        }

        private static void AddPhaseCheck(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, List<ColregRuleCheck> checks, ColregRuleId id,
            RuleCheckStatus status, string clause, string expected, string explanation)
        {
            var first = frames[span.First]; var last = frames[span.Last];
            var action = Observe(frames, span, own, r.Thresholds);
            var evidence = new ColregEvidence(own ? first.OwnBearingDeg : first.TargetBearingDeg,
                first.HeadingDifferenceDeg, first.Cpa.DcpaM, first.Cpa.TcpaSec, action.HeadingChangeDeg,
                action.SpeedChangeMps, first.VisibilityNm, first.Cpa.CurrentDistanceM, last.Cpa.DcpaM,
                MinimumObservedDistance(frames, span), last.Cpa.TcpaSec, last.Cpa.CurrentDistanceM);
            checks.Add(new ColregRuleCheck(first.Own.Time, last.Own.Time, id,
                own ? r.OwnVesselId : r.TargetVesselId, status, clause, expected, action, evidence, explanation));
        }

        private static void AddGeneralChecks(ColregAnalysisRequest r, List<ColregFrame> frames,
            ColregSpan span, bool own, List<ColregRuleCheck> checks)
        {
            foreach (var phase in RiskSpans(frames, span, r.Thresholds))
            {
                var first = frames[phase.First]; var last = frames[phase.Last];
                bool risk = first.HasCollisionRisk || CloseQuarters(first, r.Thresholds);
                Action<ColregRuleId, RuleCheckStatus, string, string, string> add = (id, status, clause, expected, explanation) =>
                    AddPhaseCheck(r, frames, phase, own, checks, id, status, clause, expected, explanation);
                add(ColregRuleId.R5, risk ? RuleCheckStatus.NotAssessable : RuleCheckStatus.NotApplicable, "R5",
                    "保持正规瞭望，并使用适合当时环境的一切有效手段。",
                    risk ? "缺少 VDR 音频、驾驶台值班记录及视觉/听觉瞭望记录，无法核查是否保持正规瞭望。" : "本区段无碰撞危险。");
                add(ColregRuleId.R6, risk ? RuleCheckStatus.NeedsReview : RuleCheckStatus.NotApplicable, "R6",
                    "综合能见度、交通密度、操纵性能等因素判断安全航速。", risk ? SpeedReview(frames, phase, own, r.Thresholds) : "本区段无碰撞危险。");
                add(ColregRuleId.R7, risk ? RuleCheckStatus.Partial : RuleCheckStatus.NotApplicable, "R7",
                    "用一切有效手段判断是否存在碰撞危险，避免凭不充分资料作推断。",
                    risk ? string.Format(System.Globalization.CultureInfo.InvariantCulture,
                        "航迹 CPA 序列可识别碰撞危险：本区段首次危险时刻={0:F3}s；DCPA {1:F3}→{2:F3}m；TCPA {3:F3}→{4:F3}s。" +
                        "这是航迹推算的技术事实；是否实际使用雷达/ARPA 标绘与连续观察仍需雷达/ARPA、VDR 和驾驶台记录。",
                        first.Own.Time.Seconds, first.Cpa.DcpaM, last.Cpa.DcpaM, first.Cpa.TcpaSec, last.Cpa.TcpaSec) :
                        "本区段 CPA 序列未形成碰撞危险。");
                add(ColregRuleId.R34_35, risk ? RuleCheckStatus.NotAssessable : RuleCheckStatus.NotApplicable, "R34/35",
                    "按互见、操纵及能见度条件发出相应操纵、警告与声号。",
                    risk ? "缺少 VDR 音频、汽笛/声号记录、灯号记录及驾驶台值班记录，无法核查操纵、警告和能见度不良声号。" : "本区段无碰撞危险。");
            }
        }

        private static RuleCheckStatus ChannelRightSide(IReadOnlyList<EnuPosition> centerline,
            List<ColregFrame> frames, ColregSpan span, bool own)
        {
            for (int i = span.First; i <= span.Last; i++)
            {
                var sample = own ? frames[i].Own : frames[i].Target;
                double bestDistance = double.PositiveInfinity, bestSide = 0;
                for (int j = 0; j + 1 < centerline.Count; j++)
                {
                    var a = centerline[j]; var b = centerline[j + 1];
                    double east = b.EastM - a.EastM, north = b.NorthM - a.NorthM;
                    double lengthSquared = east * east + north * north;
                    if (lengthSquared <= 1e-12) continue;
                    double offsetEast = sample.EnuCenter.EastM - a.EastM;
                    double offsetNorth = sample.EnuCenter.NorthM - a.NorthM;
                    double along = Math.Max(0, Math.Min(1, (offsetEast * east + offsetNorth * north) / lengthSquared));
                    double de = offsetEast - along * east, dn = offsetNorth - along * north;
                    double distance = de * de + dn * dn;
                    if (distance >= bestDistance) continue;
                    bestDistance = distance;
                    double rad = ColregEngine.Heading(sample) * Math.PI / 180;
                    double travel = Math.Sin(rad) * east + Math.Cos(rad) * north;
                    // 折线顶点的顺序不决定船舶的右侧；方向按本船局部航行方向选择。
                    bestSide = (north * offsetEast - east * offsetNorth) * (travel < 0 ? -1 : 1);
                }
                if (double.IsPositiveInfinity(bestDistance)) return RuleCheckStatus.NotAssessable;
                if (bestSide < -1e-7) return RuleCheckStatus.NotSatisfied;
            }
            return RuleCheckStatus.Satisfied;
        }

        private static double MaximumSpeed(List<ColregFrame> frames, ColregSpan span, bool own)
        {
            double result = 0;
            for (int i = span.First; i <= span.Last; i++)
                result = Math.Max(result, own ? frames[i].Own.SogMps : frames[i].Target.SogMps);
            return result;
        }

        private static string ObservationNote(bool observed)
        {
            return observed ? "" : "仅有单时刻观测，无法核实操纵过程。";
        }
    }
}
