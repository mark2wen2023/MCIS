using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Domain.Tracks
{
    public sealed partial class ShipTrack
    {
        private static List<TrackSample> NormalizeAndSortSamples(
            IReadOnlyList<TrackSample> input,
            ref IGeoConverter geoConverter)
        {
            List<TrackSample> list = new List<TrackSample>();
            if (input == null || input.Count == 0)
            {
                return list;
            }

            if (geoConverter == null)
            {
                GeoCoord firstGeo = input[0].Geo;
                geoConverter = new LocalEnuGeoConverter(firstGeo);
            }

            bool allEnuZero = true;
            bool anyGeoNonZero = false;
            for (int i = 0; i < input.Count; i++)
            {
                if (!input[i].EnuCenter.Equals(EnuPosition.Zero))
                {
                    allEnuZero = false;
                }
                if (Math.Abs(input[i].Geo.LonDeg) > 1e-9 || Math.Abs(input[i].Geo.LatDeg) > 1e-9)
                {
                    anyGeoNonZero = true;
                }
            }

            for (int i = 0; i < input.Count; i++)
            {
                TrackSample s = input[i];
                EnuPosition enu = s.EnuCenter;
                GeoCoord geo = s.Geo;
                if (allEnuZero && anyGeoNonZero)
                {
                    enu = geoConverter.Wgs84ToEnu(geo);
                }
                else if (Math.Abs(geo.LonDeg) < 1e-9 && Math.Abs(geo.LatDeg) < 1e-9 && !enu.Equals(EnuPosition.Zero))
                {
                    geo = geoConverter.EnuToWgs84(enu);
                }

                list.Add(new TrackSample(
                    s.Time, geo, enu, s.VelocityEnuMps, s.SogMps, s.CogDeg,
                    s.HdgDeg, s.RotDegPerSec, s.Provenance, s.TimeQuality, s.HeadingFromCog, s.RawSourceLine));
            }

            list.Sort((a, b) => a.Time.CompareTo(b.Time));
            return list;
        }

        private static Double2[] PrecomputeNodeTangents(IReadOnlyList<TrackSample> samples, InterpolationMode mode)
        {
            int n = samples.Count;
            Double2[] tangents = new Double2[n];
            if (n == 0)
            {
                return tangents;
            }

            bool anyExplicitVelocity = false;
            for (int i = 0; i < n; i++)
            {
                TrackSample s = samples[i];
                if (s.VelocityEnuMps.LengthSquared > 1e-8 ||
                    (!float.IsNaN(s.SogMps) && s.SogMps > 1e-4f && !float.IsNaN(s.CogDeg) && s.CogDeg >= 0f && s.CogDeg < 360f))
                {
                    anyExplicitVelocity = true;
                    break;
                }
            }

            for (int i = 0; i < n; i++)
            {
                if (mode == InterpolationMode.CatmullRom)
                {
                    tangents[i] = HermiteMath.ComputeFiniteDifferenceTangent(samples, i);
                    continue;
                }

                TrackSample s = samples[i];
                bool hasValidCog = !float.IsNaN(s.CogDeg) && s.CogDeg >= 0.0f && s.CogDeg < 360.0f;
                bool hasValidSog = !float.IsNaN(s.SogMps) && s.SogMps >= 0.0f && s.SogMps < 52.6f;

                if (s.VelocityEnuMps.LengthSquared > 1e-8)
                {
                    tangents[i] = s.VelocityEnuMps;
                }
                else if (hasValidSog && s.SogMps > 1e-4f && hasValidCog)
                {
                    tangents[i] = HermiteMath.VelocityFromSogCog(s.SogMps, s.CogDeg);
                }
                else if (anyExplicitVelocity && hasValidSog && s.SogMps <= 1e-4f && hasValidCog)
                {
                    tangents[i] = Double2.Zero;
                }
                else
                {
                    tangents[i] = HermiteMath.ComputeFiniteDifferenceTangent(samples, i);
                }
            }

            return tangents;
        }

        private int FindSegmentIndex(SimTime time)
        {
            int low = 0;
            int high = _samples.Count - 2;
            while (low <= high)
            {
                int mid = low + ((high - low) >> 1);
                if (_samples[mid + 1].Time.Seconds < time.Seconds)
                {
                    low = mid + 1;
                }
                else if (_samples[mid].Time.Seconds > time.Seconds)
                {
                    high = mid - 1;
                }
                else
                {
                    return mid;
                }
            }
            return Math.Max(0, Math.Min(_samples.Count - 2, low));
        }

        private TrackSample EvaluateSegment(int idx, TrackSample s0, TrackSample s1, SimTime time, bool inGap)
        {
            double dt = s1.Time - s0.Time;
            if (dt <= 1e-9)
            {
                return s0;
            }

            double u = (time - s0.Time) / dt;
            Double2 p0 = s0.EnuCenter.Horizontal;
            Double2 p1 = s1.EnuCenter.Horizontal;
            Double2 v0 = _nodeTangents[idx];
            Double2 v1 = _nodeTangents[idx + 1];

            Double2 pos2D;
            Double2 vel2D;
            SampleProvenance prov;

            if (inGap && _gapPolicy == GapPolicy.DeadReckon)
            {
                double elapsed = time - s0.Time;
                pos2D = p0 + v0 * elapsed;
                vel2D = v0;
                prov = SampleProvenance.DeadReckoned;
            }
            else
            {
                if (_mode == InterpolationMode.Linear)
                {
                    pos2D = p0 * (1.0 - u) + p1 * u;
                    vel2D = (p1 - p0) / dt;
                }
                else
                {
                    pos2D = HermiteMath.EvaluateHermitePosition(p0, v0, p1, v1, dt, u);
                    vel2D = HermiteMath.EvaluateHermiteVelocity(p0, v0, p1, v1, dt, u);
                }

                if (inGap)
                {
                    prov = SampleProvenance.LowConfidence;
                }
                else if (s0.Provenance == SampleProvenance.ManualDrawn && s1.Provenance == SampleProvenance.ManualDrawn)
                {
                    prov = SampleProvenance.ManualDrawn;
                }
                else
                {
                    prov = SampleProvenance.Interpolated;
                }
            }

            double upM = s0.EnuCenter.UpM * (1.0 - u) + s1.EnuCenter.UpM * u;
            EnuPosition interpEnu = new EnuPosition(pos2D.X, pos2D.Y, upM);
            GeoCoord interpGeo = _geoConverter.EnuToWgs84(interpEnu);

            float sogMps = (float)vel2D.Length;
            float fallbackCog = !float.IsNaN(s0.CogDeg) ? s0.CogDeg : 0.0f;
            float cogDeg = (float)HermiteMath.VelocityToCogDeg(vel2D, fallbackCog);

            bool hdgFromCog = s0.HeadingFromCog || s1.HeadingFromCog;
            float hdgDeg = hdgFromCog && sogMps >= 0.5f
                ? cogDeg
                : (float)HermiteMath.InterpolateAngleDeg(s0.HdgDeg, s1.HdgDeg, u);
            float rotDegPerSec = (float)(HermiteMath.DeltaAngleDeg(s0.HdgDeg, s1.HdgDeg) / dt);

            return new TrackSample(
                time, interpGeo, interpEnu, vel2D, sogMps, cogDeg, hdgDeg, rotDegPerSec,
                prov, s0.TimeQuality, hdgFromCog, null);
        }

        private static TrackSample CloneWithTimeAndProvenance(TrackSample src, SimTime time, SampleProvenance provenance)
        {
            return new TrackSample(
                time, src.Geo, src.EnuCenter, src.VelocityEnuMps, src.SogMps, src.CogDeg,
                src.HdgDeg, src.RotDegPerSec, provenance, src.TimeQuality, src.HeadingFromCog, src.RawSourceLine);
        }
    }
}
