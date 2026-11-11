using System;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    public sealed partial class TrackCleaner
    {
        private static bool ValidateFieldAvailabilityAndRange(
            AisDecodedRecord rec,
            out RejectReason reason,
            out string detail)
        {
            reason = RejectReason.None;
            detail = string.Empty;

            if (string.IsNullOrWhiteSpace(rec.Mmsi))
            {
                reason = RejectReason.Unavailable;
                detail = "MMSI is empty or unavailable.";
                return false;
            }

            if (double.IsNaN(rec.LonDeg) || double.IsNaN(rec.LatDeg) ||
                Math.Abs(rec.LonDeg - 181.0) < 1e-3 || Math.Abs(rec.LatDeg - 91.0) < 1e-3)
            {
                reason = RejectReason.Unavailable;
                detail = string.Format(CultureInfo.InvariantCulture, "Position unavailable (lon={0:F4}, lat={1:F4}).", rec.LonDeg, rec.LatDeg);
                return false;
            }

            if (rec.LonDeg < -180.0 || rec.LonDeg > 180.0 || rec.LatDeg < -90.0 || rec.LatDeg > 90.0)
            {
                reason = RejectReason.OutOfRange;
                detail = string.Format(CultureInfo.InvariantCulture, "Position out of range (lon={0:F4}, lat={1:F4}).", rec.LonDeg, rec.LatDeg);
                return false;
            }

            if (float.IsNaN(rec.SogKn) || Math.Abs(rec.SogKn - 102.3f) < 0.06f || Math.Abs(rec.SogKn - 1023.0f) < 0.5f)
            {
                reason = RejectReason.Unavailable;
                detail = string.Format(CultureInfo.InvariantCulture, "SOG unavailable ({0:F1} kn).", rec.SogKn);
                return false;
            }

            if (rec.SogKn < 0.0f || rec.SogKn > 102.25f)
            {
                reason = RejectReason.OutOfRange;
                detail = string.Format(CultureInfo.InvariantCulture, "SOG out of range ({0:F1} kn).", rec.SogKn);
                return false;
            }

            if (!float.IsNaN(rec.CogDeg) &&
                Math.Abs(rec.CogDeg - 360.0f) >= 0.05f &&
                Math.Abs(rec.CogDeg - 3600.0f) >= 0.5f &&
                (rec.CogDeg < 0.0f || rec.CogDeg > 360.0f))
            {
                reason = RejectReason.OutOfRange;
                detail = string.Format(CultureInfo.InvariantCulture, "COG out of range ({0:F1} deg).", rec.CogDeg);
                return false;
            }

            return true;
        }

        private static bool ValidateKinematicsAgainstPrevious(
            AisDecodedRecord prevRec,
            EnuPosition prevAntennaEnu,
            AisDecodedRecord currRec,
            EnuPosition currAntennaEnu,
            double dt,
            TrackCleaningConfig cfg,
            out RejectReason reason,
            out string detail)
        {
            reason = RejectReason.None;
            detail = string.Empty;

            double distM = prevAntennaEnu.HorizontalDistanceTo(currAntennaEnu);
            double impliedSpeedMps = distM / dt;
            double impliedSpeedKn = impliedSpeedMps * HermiteMath.KnotsPerMeterPerSecond;

            if (impliedSpeedKn > cfg.MaxSpeedKn)
            {
                reason = RejectReason.PositionJump;
                detail = string.Format(CultureInfo.InvariantCulture,
                    "Implied speed {0:F1} kn > max {1:F1} kn (dist={2:F1}m, dt={3:F1}s).",
                    impliedSpeedKn, cfg.MaxSpeedKn, distM, dt);
                return false;
            }

            if (currRec.IsSogValid && currRec.SogKn > cfg.MaxSpeedKn)
            {
                reason = RejectReason.SpeedJump;
                detail = string.Format(CultureInfo.InvariantCulture,
                    "Reported SOG {0:F1} kn exceeds max {1:F1} kn.", currRec.SogKn, cfg.MaxSpeedKn);
                return false;
            }

            if (prevRec.IsSogValid && currRec.IsSogValid && dt <= cfg.MovingGapThresholdSec)
            {
                double deltaSogKn = Math.Abs(currRec.SogKn - prevRec.SogKn);
                double accelKnPerSec = deltaSogKn / dt;
                if (deltaSogKn > cfg.MaxSpeedJumpKn || accelKnPerSec > cfg.MaxAccelerationKnPerSec)
                {
                    reason = RejectReason.SpeedJump;
                    detail = string.Format(CultureInfo.InvariantCulture,
                        "Reported SOG jump {0:F1} -> {1:F1} kn (delta={2:F1} kn, dt={3:F1}s).",
                        prevRec.SogKn, currRec.SogKn, deltaSogKn, dt);
                    return false;
                }

                if (distM > 25.0)
                {
                    double relativeGateKn = cfg.SpeedGateMultiplier * Math.Max(prevRec.SogKn, currRec.SogKn) + 3.0;
                    if (impliedSpeedKn > relativeGateKn)
                    {
                        reason = RejectReason.PositionJump;
                        detail = string.Format(CultureInfo.InvariantCulture,
                            "Implied speed {0:F1} kn > speed gate {1:F1} kn.", impliedSpeedKn, relativeGateKn);
                        return false;
                    }
                }
            }

            if (prevRec.IsCogValid && currRec.IsCogValid &&
                prevRec.IsSogValid && currRec.IsSogValid &&
                prevRec.SogKn >= cfg.MinSpeedForCourseCheckKn &&
                currRec.SogKn >= cfg.MinSpeedForCourseCheckKn &&
                dt <= cfg.MovingGapThresholdSec)
            {
                double deltaCog = Math.Abs(HermiteMath.DeltaAngleDeg(prevRec.CogDeg, currRec.CogDeg));
                double turnRate = deltaCog / dt;
                if (deltaCog > cfg.MaxCourseJumpDeg || turnRate > cfg.MaxTurnRateDegPerSec)
                {
                    reason = RejectReason.CourseJump;
                    detail = string.Format(CultureInfo.InvariantCulture,
                        "Course jump {0:F1} -> {1:F1} deg (delta={2:F1} deg, rate={3:F2} deg/s).",
                        prevRec.CogDeg, currRec.CogDeg, deltaCog, turnRate);
                    return false;
                }
            }

            return true;
        }

        private static TrackSample ConvertRecordToSample(
            AisDecodedRecord rec,
            SimTime simTime,
            GeoCoord rawGeo,
            EnuPosition antennaEnu,
            AntennaOffset antennaOffset,
            IGeoConverter converter,
            bool applyAntennaOffset,
            ref float lastValidHdgDeg)
        {
            float sogMps = rec.IsSogValid ? (float)(rec.SogKn * HermiteMath.MetersPerSecondPerKnot) : 0.0f;
            float cogDeg = rec.IsCogValid ? (float)HermiteMath.NormalizeAngleDeg(rec.CogDeg) : float.NaN;

            bool headingFromCog = !rec.IsHdgValid;
            float hdgDeg;
            if (rec.IsHdgValid)
            {
                hdgDeg = (float)HermiteMath.NormalizeAngleDeg(rec.HdgDeg);
                lastValidHdgDeg = hdgDeg;
            }
            else if (rec.IsCogValid && rec.SogKn >= 1.0f)
            {
                hdgDeg = (float)HermiteMath.NormalizeAngleDeg(rec.CogDeg);
                lastValidHdgDeg = hdgDeg;
            }
            else
            {
                hdgDeg = lastValidHdgDeg;
            }

            EnuPosition centerEnu = antennaEnu;
            GeoCoord finalGeo = rawGeo;
            if (applyAntennaOffset && (antennaOffset.LoaM > 0.0f || antennaOffset.BeamM > 0.0f))
            {
                Double2 offsetEnu = antennaOffset.ToEnuOffset(hdgDeg);
                centerEnu = new EnuPosition(antennaEnu.EastM + offsetEnu.X, antennaEnu.NorthM + offsetEnu.Y, antennaEnu.UpM);
                finalGeo = converter.EnuToWgs84(centerEnu);
            }

            Double2 velocityEnu = !float.IsNaN(cogDeg)
                ? HermiteMath.VelocityFromSogCog(sogMps, cogDeg)
                : Double2.Zero;
            float rotDegPerSec = !float.IsNaN(rec.RotDegPerMin) ? rec.RotDegPerMin / 60.0f : 0.0f;

            return new TrackSample(
                simTime,
                finalGeo,
                centerEnu,
                velocityEnu,
                sogMps,
                cogDeg,
                hdgDeg,
                rotDegPerSec,
                SampleProvenance.Measured,
                rec.TimeQuality,
                headingFromCog,
                rec.SourceLineNumber);
        }
    }
}
