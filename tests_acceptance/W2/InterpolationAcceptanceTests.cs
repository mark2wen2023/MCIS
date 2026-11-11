using System;
using Mcis.Core;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// 角度最短弧插值与车钟等离散量阶跃（不插值）验收。
    /// </summary>
    public class InterpolationAcceptanceTests
    {
        [Fact]
        public void Heading_359To1_InterpolatesAcrossZeroByShortestArc()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                W2AccFixture.S(0, 359.0),
                W2AccFixture.S(10, 1.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            Assert.True(
                mid < 0.01 || mid > 359.99 || (mid >= 0.0 && mid <= 0.01) || (mid >= 359.99),
                "359°→1° 中点应按最短弧经过 0°，实际=" + mid);
            // 允许极小数值误差，中点应接近 0（或 360）。
            double nearestZero = mid > 180.0 ? 360.0 - mid : mid;
            Assert.True(nearestZero < 0.05, "359°→1° 中点应接近 0°，实际=" + mid);
        }

        [Fact]
        public void Heading_1To359_InterpolatesAcrossZeroByShortestArc()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                W2AccFixture.S(0, 1.0),
                W2AccFixture.S(10, 359.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            double nearestZero = mid > 180.0 ? 360.0 - mid : mid;
            Assert.True(nearestZero < 0.05, "1°→359° 中点应接近 0°，实际=" + mid);
        }

        [Fact]
        public void Heading_179To181_DoesNotTakeLongWay()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                W2AccFixture.S(0, 179.0),
                W2AccFixture.S(10, 181.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            Assert.True(Math.Abs(mid - 180.0) < 0.05, "179°→181° 中点应为 180°（最短弧），实际=" + mid);
        }

        [Fact]
        public void Heading_181To179_DoesNotTakeLongWay()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                W2AccFixture.S(0, 181.0),
                W2AccFixture.S(10, 179.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            Assert.True(Math.Abs(mid - 180.0) < 0.05, "181°→179° 中点应为 180°（最短弧），实际=" + mid);
        }

        [Fact]
        public void CourseOverGround_AlsoUsesShortestArc()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/COG", "A", TrackKind.CourseOverGround,
                W2AccFixture.S(0, 350.0),
                W2AccFixture.S(10, 10.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            double nearestZero = mid > 180.0 ? 360.0 - mid : mid;
            Assert.True(nearestZero < 0.05, "COG 350°→10° 中点应接近 0°，实际=" + mid);
        }

        [Fact]
        public void EngineTelegraph_IsStepped_NotInterpolated()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/TEL", "A", TrackKind.EngineTelegraph,
                W2AccFixture.S(0, 0.0, "STOP"),
                W2AccFixture.S(10, 4.0, "FULL AHEAD"));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            Assert.Equal(0.0, mid, 9);

            TimelineSample sample;
            Assert.True(track.TryGetSampleAt(new SimTime(5), out sample));
            Assert.Equal("STOP", sample.Text);
        }

        [Fact]
        public void EngineTelegraph_ChangesOnlyAtSampleInstant()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/TEL", "A", TrackKind.EngineTelegraph,
                W2AccFixture.S(0, 3.0, "HALF AHEAD"),
                W2AccFixture.S(10, 0.0, "STOP"));

            double justBefore;
            double atChange;
            Assert.True(track.TryGetValueAt(new SimTime(9.999), out justBefore));
            Assert.True(track.TryGetValueAt(new SimTime(10), out atChange));
            Assert.Equal(3.0, justBefore, 9);
            Assert.Equal(0.0, atChange, 9);
        }

        [Fact]
        public void Speed_IsLinearlyInterpolated()
        {
            Track track = W2AccFixture.ScalarTrack(
                "A/SOG", "A", TrackKind.SpeedOverGround,
                W2AccFixture.S(0, 10.0),
                W2AccFixture.S(10, 14.0));

            double mid;
            Assert.True(track.TryGetValueAt(new SimTime(5), out mid));
            Assert.Equal(12.0, mid, 9);
        }
    }
}
