using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.Simulation.Damage
{
    /// <summary>在时间区间上对两体 OBB 净距做离线扫描，并用二分搜索定位首次接触时刻 tc（默认精度 0.05 s）。</summary>
    public static class CollisionDetector
    {
        public const double DefaultPrecisionSec = 0.05;
        public const double DefaultCoarseStepSec = 1.0;

        public static SimTime? FindFirstContactTime(
            Func<double, CollisionBodyState> sampleA,
            Func<double, CollisionBodyState> sampleB,
            SimTime start,
            SimTime end,
            double precisionSec = DefaultPrecisionSec,
            double coarseStepSec = DefaultCoarseStepSec)
        {
            if (sampleA == null || sampleB == null)
            {
                throw new ArgumentNullException("sample");
            }

            if (end <= start)
            {
                return null;
            }

            double prec = precisionSec > 0.0 ? precisionSec : DefaultPrecisionSec;
            double step = coarseStepSec > 0.0 ? coarseStepSec : DefaultCoarseStepSec;
            double t = start.Seconds;
            double tEnd = end.Seconds;
            double prevT = t;
            double prevClear = OrientedBoundingBox.Clearance(sampleA(t).Obb, sampleB(t).Obb);
            if (prevClear <= 0.0)
            {
                return new SimTime(t);
            }

            t += step;
            while (t <= tEnd + 1e-12)
            {
                double tt = Math.Min(t, tEnd);
                double clear = OrientedBoundingBox.Clearance(sampleA(tt).Obb, sampleB(tt).Obb);
                if (clear <= 0.0)
                {
                    return BinarySearchContact(sampleA, sampleB, prevT, tt, prec);
                }

                prevT = tt;
                prevClear = clear;
                t += step;
            }

            return null;
        }

        public static SimTime BinarySearchContact(
            Func<double, CollisionBodyState> sampleA,
            Func<double, CollisionBodyState> sampleB,
            double tLo,
            double tHi,
            double precisionSec)
        {
            // 不变式：clear(tLo) > 0，clear(tHi) <= 0
            for (int i = 0; i < 64; i++)
            {
                if (tHi - tLo <= precisionSec)
                {
                    break;
                }

                double mid = 0.5 * (tLo + tHi);
                double clear = OrientedBoundingBox.Clearance(sampleA(mid).Obb, sampleB(mid).Obb);
                if (clear <= 0.0)
                {
                    tHi = mid;
                }
                else
                {
                    tLo = mid;
                }
            }

            return new SimTime(tHi);
        }

        public static CollisionEvent BuildEvent(
            SimTime tc,
            CollisionBodyState striking,
            CollisionBodyState struck,
            IGeoConverter geo,
            DamageAssessment assessment)
        {
            EnuPosition contact = OrientedBoundingBox.ApproximateContact(striking.Obb, struck.Obb);
            GeoCoord geoCoord = geo != null ? geo.EnuToWgs84(contact) : default(GeoCoord);
            double intersect = Math.Abs(HermiteMath.DeltaAngleDeg(striking.HeadingDeg, struck.HeadingDeg));
            return new CollisionEvent(
                "col-" + striking.Id + "-" + struck.Id + "-" + tc.Seconds.ToString("F2", System.Globalization.CultureInfo.InvariantCulture),
                tc,
                striking.Id,
                struck.Id,
                struck.IsFixed,
                geoCoord,
                contact,
                Double3.Zero,
                (float)intersect,
                (float)assessment.RelativeNormalSpeedMps,
                assessment.EnergyMJ,
                assessment.Severity,
                (float)assessment.BreachAreaM2,
                (float)assessment.BreachDepthBelowWlM);
        }

    }
}
