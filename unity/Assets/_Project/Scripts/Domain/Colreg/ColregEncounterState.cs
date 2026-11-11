using System;
using System.Collections.Generic;

namespace Mcis.Domain.Colreg
{
    /// <summary>一次分析内的会遇锁定；不跨请求保存状态。</summary>
    internal sealed class ColregEncounterState
    {
        private bool locked, pending;
        private int overtaker, encounterId;
        private bool? previousInSight;
        private ColregVesselStatus? previousOwnStatus, previousTargetStatus;
        private double? riskStart;
        internal double? LockDeadline { get; private set; }

        // 未互见的展示不覆盖锁定几何；推迟期保留独立身份，不回填后来的判定。
        private EncounterSituation lockedSituation;
        private TrafficRole lockedOwnRole, lockedTargetRole;
        private bool lockedAmbiguous, lockedDoubt;
        private string lockedBasis, lockedDoubtReason;

        internal void Apply(ColregFrame frame, ColregAnalysisRequest request)
        {
            var t = request.Thresholds;
            bool clear = frame.Cpa.IsDiverging && frame.Cpa.CurrentDistanceNm >= t.ClearDistanceNm;
            bool released = overtaker != 0 ? clear : clear || (!frame.HasCollisionRisk &&
                (frame.Cpa.TcpaSec <= 0 || frame.Cpa.DcpaNm >= t.CollisionRiskDcpaNm));
            if (released)
            {
                locked = pending = false;
                overtaker = 0;
                riskStart = null;
            }
            bool statusChanged = previousOwnStatus.HasValue &&
                (previousOwnStatus.Value != frame.OwnStatus || previousTargetStatus.Value != frame.TargetStatus);
            bool continuingRisk = locked || pending;
            bool becameVisible = previousInSight == false && frame.InSight;
            if (becameVisible || statusChanged)
            {
                locked = pending = false;
                // 状态变化不能解除尚未驶过让清的 R13 身份；互见重判仍按裁定重新识别几何。
                if (becameVisible) overtaker = 0;
            }
            if (!locked && !pending && (frame.HasCollisionRisk || overtaker != 0 || (statusChanged && continuingRisk)))
            {
                riskStart = riskStart ?? frame.Own.Time.Seconds;
                pending = true;
                encounterId++;
            }
            LockDeadline = null;
            if (pending)
            {
                bool statusRelation = Special(frame.OwnStatus) || Special(frame.TargetStatus);
                bool stable = Stable(request.OwnSamples, frame.Own.Time.Seconds, t) &&
                    Stable(request.TargetSamples, frame.Own.Time.Seconds, t);
                bool forced = !stable && frame.Own.Time.Seconds - riskStart.Value >= t.LockMaxDeferSeconds - 1e-7;
                bool retainedOvertaker = overtaker != 0;
                // R18 的状态责任无需等待几何稳定；R19 内部追越身份照旧保存，仅供例外核查。
                if (overtaker != 0 || statusRelation || !frame.InSight || stable || forced)
                {
                    if (overtaker == 0) overtaker = FindOvertaker(frame, t);
                    ClassifyVisible(frame, t, overtaker);
                    if (forced && frame.InSight && !statusRelation && !retainedOvertaker)
                    {
                        lockedDoubt = true;
                        lockedDoubtReason = ColregDoubtReasons.LockedDuringTurn;
                        lockedBasis += "风险首次形成后达到最大延后时限，仍在转向中，按此刻几何锁定并存疑；不事后重判。";
                    }
                    locked = true;
                    pending = false;
                }
                else LockDeadline = riskStart.Value + t.LockMaxDeferSeconds;
            }
            frame.Overtaker = overtaker;
            frame.EncounterId = locked || pending ? encounterId : 0;
            frame.RiskStartTime = riskStart;
            if (!frame.InSight)
            {
                frame.Situation = EncounterSituation.RestrictedVisibility;
                frame.OwnRole = frame.TargetRole = TrafficRole.BothActionRequired;
                frame.Basis = "未互见，按R19核查；追越身份仅保留用于R19(d)(i)例外。";
            }
            else if (pending)
            {
                frame.Situation = EncounterSituation.Undetermined;
                frame.OwnRole = frame.TargetRole = TrafficRole.Undetermined;
                frame.Doubt = true;
                frame.DoubtReason = ColregDoubtReasons.PendingStableHeading;
                frame.Basis = "转向中，延后判定；待两船航向在配置窗口内稳定，或达到最大延后时限后锁定。";
            }
            else if (locked)
            {
                frame.Situation = lockedSituation;
                frame.OwnRole = lockedOwnRole;
                frame.TargetRole = lockedTargetRole;
                frame.CrossingGeometryAmbiguous = lockedAmbiguous;
                frame.Doubt = lockedDoubt;
                frame.DoubtReason = lockedDoubtReason;
                frame.Basis = lockedBasis;
            }
            else
            {
                frame.Situation = EncounterSituation.NoCollisionRisk;
                frame.OwnRole = frame.TargetRole = TrafficRole.None;
                frame.Basis = "当前不满足碰撞危险判据，且没有持续至驶过让清的追越义务。";
            }
            if (locked || pending) ApplyStatusRoles(frame);
            previousInSight = frame.InSight;
            previousOwnStatus = frame.OwnStatus;
            previousTargetStatus = frame.TargetStatus;
        }

        private static bool Special(ColregVesselStatus status)
        {
            return status != ColregVesselStatus.PowerDriven && status != ColregVesselStatus.Unknown;
        }

        private static bool Impaired(ColregVesselStatus status)
        {
            return status == ColregVesselStatus.NotUnderCommand || status == ColregVesselStatus.RestrictedManoeuvrability;
        }

        private static void ApplyStatusRoles(ColregFrame f)
        {
            bool own = Impaired(f.OwnStatus), target = Impaired(f.TargetStatus);
            if ((own && !Special(f.TargetStatus)) || (target && !Special(f.OwnStatus)))
            {
                f.OwnRole = own ? TrafficRole.None : TrafficRole.GiveWay;
                f.TargetRole = target ? TrafficRole.None : TrafficRole.GiveWay;
                f.Basis += "R18：船舶状态为失控/操限，他船让路；失控/操限船无直航义务，直航船号为空。";
            }
            else if (Special(f.OwnStatus) || Special(f.TargetStatus))
            {
                f.OwnRole = f.TargetRole = TrafficRole.Undetermined;
                f.Doubt = true;
                f.DoubtReason = ColregDoubtReasons.VesselStatusReview;
                f.Basis += "R18：双方失控/操限或涉及限于吃水、捕鱼、帆船的状态组合，需人工研判；不确定让路/直航角色。";
            }
        }

        private void ClassifyVisible(ColregFrame frame, ColregThresholds t, int overtakingVessel)
        {
            lockedAmbiguous = lockedDoubt = false;
            lockedDoubtReason = null;
            if (overtakingVessel != 0)
            {
                lockedSituation = EncounterSituation.Overtaking;
                lockedOwnRole = overtakingVessel == 1 ? TrafficRole.GiveWay : TrafficRole.StandOn;
                lockedTargetRole = overtakingVessel == 2 ? TrafficRole.GiveWay : TrafficRole.StandOn;
                lockedBasis = "R13：正横后闭边界扇区内接近，追越优先；锁定至驶过让清。";
            }
            else if (180 - frame.HeadingDifferenceDeg <= t.HeadOnHalfAngleDeg + 1e-7 &&
                (Forward(frame.OwnBearingDeg, t.HeadOnForwardHalfAngleDeg) ||
                 Forward(frame.TargetBearingDeg, t.HeadOnForwardHalfAngleDeg) ||
                 Forward(frame.OwnBearingDeg, t.HeadOnDoubtBearingDeg) ||
                 Forward(frame.TargetBearingDeg, t.HeadOnDoubtBearingDeg)))
            {
                lockedSituation = EncounterSituation.HeadOn;
                lockedOwnRole = lockedTargetRole = TrafficRole.BothActionRequired;
                lockedDoubt = !Forward(frame.OwnBearingDeg, t.HeadOnForwardHalfAngleDeg) &&
                    !Forward(frame.TargetBearingDeg, t.HeadOnForwardHalfAngleDeg);
                lockedDoubtReason = lockedDoubt ? ColregDoubtReasons.HeadOnDoubt : null;
                lockedBasis = lockedDoubt ? "R14(c)：接近反向且任一视角在船首存疑扇区内，存疑按对遇。" :
                    "R14：接近反向且任一视角位于船首附近，有碰撞危险；锁定对遇和双方行动义务。";
            }
            else
            {
                lockedSituation = EncounterSituation.Crossing;
                bool ownAxis = OnAxis(frame.OwnBearingDeg), targetAxis = OnAxis(frame.TargetBearingDeg);
                bool ownRight = Right(frame.OwnBearingDeg), targetRight = Right(frame.TargetBearingDeg);
                lockedAmbiguous = (ownAxis && targetAxis) || (!ownAxis && !targetAxis && ownRight == targetRight);
                if (lockedAmbiguous)
                {
                    lockedDoubt = true;
                    lockedDoubtReason = ownAxis && targetAxis ? ColregDoubtReasons.AxisView : ColregDoubtReasons.ContradictoryViews;
                    lockedOwnRole = lockedTargetRole = TrafficRole.Undetermined;
                    lockedBasis = "本船视角：" + View(frame.OwnBearingDeg, "他船", "本船") +
                        "；他船视角：" + View(frame.TargetBearingDeg, "本船", "他船") +
                        "；两视角矛盾或均在轴线，存疑，不确定让路/直航角色。";
                }
                else
                {
                    bool ownGivesWay = ownAxis ? !targetRight : ownRight;
                    lockedOwnRole = ownGivesWay ? TrafficRole.GiveWay : TrafficRole.StandOn;
                    lockedTargetRole = ownGivesWay ? TrafficRole.StandOn : TrafficRole.GiveWay;
                    lockedBasis = ownAxis || targetAxis ? "R15：轴线方位同时参考他船视角确定角色，锁定至危险解除。" :
                        "R15：右舷来船确定让路/直航角色，锁定至危险解除。";
                }
            }
        }

        private static string View(double bearing, string other, string self)
        {
            if (OnAxis(bearing)) return other + "在轴线上，无法单独确定" + self + "角色";
            return other + (Right(bearing) ? "在右舷→" + self + "让路" : "在左舷→" + self + "直航");
        }

        private static bool Stable(IReadOnlyList<Mcis.Domain.Models.TrackSample> samples, double time, ColregThresholds t)
        {
            double start = Math.Max(samples[0].Time.Seconds, time - t.LockHeadingStableWindowSeconds);
            double previous = ColregEngine.Heading(ColregEngine.SampleAt(samples, start));
            double cumulative = 0, minimum = 0, maximum = 0;
            int lo = 0, hi = samples.Count;
            while (lo < hi)
            {
                int mid = lo + (hi - lo) / 2;
                if (samples[mid].Time.Seconds <= start) lo = mid + 1;
                else hi = mid;
            }
            for (int i = lo; i < samples.Count && samples[i].Time.Seconds < time; i++)
            {
                double current = ColregEngine.Heading(samples[i]);
                cumulative += ColregEngine.Delta(previous, current);
                minimum = Math.Min(minimum, cumulative);
                maximum = Math.Max(maximum, cumulative);
                previous = current;
            }
            cumulative += ColregEngine.Delta(previous, ColregEngine.Heading(ColregEngine.SampleAt(samples, time)));
            minimum = Math.Min(minimum, cumulative);
            maximum = Math.Max(maximum, cumulative);
            return maximum - minimum <= t.LockHeadingStableMaxChangeDeg + 1e-7;
        }

        private static bool OnAxis(double bearing)
        {
            return Math.Abs(ColregEngine.Delta(0, bearing)) <= 1e-7 || Math.Abs(bearing - 180) <= 1e-7;
        }
        private static bool Right(double bearing) { return bearing > 0 && bearing < 180; }
        private static bool Forward(double bearing, double halfAngle)
        {
            return Math.Abs(ColregEngine.Delta(0, bearing)) <= halfAngle + 1e-7;
        }
        private static int FindOvertaker(ColregFrame frame, ColregThresholds t)
        {
            bool targetBehind = InSector(frame.OwnBearingDeg, t.OvertakingBoundaryDeg);
            bool ownBehind = InSector(frame.TargetBearingDeg, t.OvertakingBoundaryDeg);
            if (targetBehind && ownBehind)
            {
                double difference = Math.Abs(180 - frame.OwnBearingDeg) - Math.Abs(180 - frame.TargetBearingDeg);
                // 完全对称时不能以输入顺序打破平局，交由双视角存疑分支处理。
                return Math.Abs(difference) <= 1e-7 ? 0 : difference < 0 ? 2 : 1;
            }
            return targetBehind ? 2 : ownBehind ? 1 : 0;
        }
        private static bool InSector(double bearing, double boundary)
        {
            return bearing >= boundary - 1e-7 && bearing <= 360 - boundary + 1e-7;
        }

        internal static ColregDangerStage DangerStage(ColregFrame frame, ColregThresholds t)
        {
            bool close = !frame.Cpa.IsDegenerate && frame.Cpa.DcpaNm < t.CloseQuartersDcpaNm &&
                frame.Cpa.TcpaSec > 0 && frame.Cpa.TcpaSec <= t.CloseQuartersTcpaSeconds;
            if (close) return frame.Cpa.TcpaSec <= t.StandOnEmergencyTcpaSeconds
                ? ColregDangerStage.ImmediateDanger : ColregDangerStage.CloseQuarters;
            return frame.HasCollisionRisk ? ColregDangerStage.CollisionRisk : ColregDangerStage.None;
        }

        internal static IReadOnlyList<ColregStageInterval> BuildStages(ColregAnalysisRequest request, List<ColregFrame> frames)
        {
            var result = new List<ColregStageInterval>();
            int first = 0;
            for (int i = 1; i <= frames.Count; i++)
            {
                if (i < frames.Count && frames[first].DangerStage == frames[i].DangerStage) continue;
                int last = i < frames.Count ? i : frames.Count - 1;
                var start = frames[first].Own.Time;
                var end = frames[last].Own.Time;
                var stage = frames[first].DangerStage;
                result.Add(new ColregStageInterval(start, end, stage, ColregIds.Stage(request, start, end, stage)));
                first = i;
            }
            return result.AsReadOnly();
        }
    }
}
