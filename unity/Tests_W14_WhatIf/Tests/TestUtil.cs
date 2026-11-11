using System;
using Mcis.Domain.Cpa;
using Mcis.Simulation.WhatIf;

namespace Mcis.Tests.W14
{
    internal static class TestUtil
    {
        public static ManeuverParams Params(
            double k = 0.10,
            double t = 60.0,
            double referenceSpeedKn = 12.0,
            double maxRudderDeg = 35.0,
            double rudderRateDegPerSec = 2.5,
            double speedTau = 90.0,
            double stopTau = 60.0,
            double asternTau = 30.0,
            double minSpeedKn = 0.0,
            double loaM = 120.0,
            double beamM = 20.0,
            double displacementTons = 9000.0,
            AnchorParams anchor = null)
        {
            return new ManeuverParams(
                k, t, referenceSpeedKn, maxRudderDeg, rudderRateDegPerSec,
                speedTau, stopTau, asternTau, minSpeedKn,
                loaM, beamM, displacementTons, anchor);
        }

        public static void AssertNear(double expected, double actual, double tolerance, string message = null)
        {
            if (Math.Abs(expected - actual) > tolerance)
            {
                throw new Xunit.Sdk.XunitException(
                    (message ?? "数值不在容差内") +
                    "：expected=" + expected.ToString("R", System.Globalization.CultureInfo.InvariantCulture) +
                    " actual=" + actual.ToString("R", System.Globalization.CultureInfo.InvariantCulture) +
                    " tolerance=" + tolerance.ToString("R", System.Globalization.CultureInfo.InvariantCulture));
            }
        }

        public static KinematicState LastState(System.Collections.Generic.IReadOnlyList<KinematicState> states)
        {
            return states[states.Count - 1];
        }

        public static double MpsToKnots(double mps)
        {
            return mps / VesselMotionState.MpsPerKnot;
        }

        public static double HeadingDifference(double a, double b)
        {
            double d = (a - b) % 360.0;
            if (d > 180.0) d -= 360.0;
            if (d < -180.0) d += 360.0;
            return Math.Abs(d);
        }
    }
}
