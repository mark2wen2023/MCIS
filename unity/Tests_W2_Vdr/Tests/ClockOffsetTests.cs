using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class ClockOffsetTests
    {
        private static AnchorObservation Anchor(string key, string source, double time)
        {
            return new AnchorObservation(key, source, new SimTime(time));
        }

        private static List<AnchorObservation> ThreePointAnchors()
        {
            return new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100),
                Anchor("k2", "GNSS", 110),
                Anchor("k3", "GNSS", 120),
                Anchor("k1", "A", 110),
                Anchor("k2", "A", 122),
                Anchor("k3", "A", 134)
            };
        }

        [Fact]
        public void LeastSquares_MeanAndStandardError()
        {
            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(ThreePointAnchors(), "GNSS", OffsetMethod.LeastSquares);

            Assert.True(result.IsSuccess);
            ClockOffsetEstimate estimate = result.Value[1];
            Assert.Equal("A", estimate.SourceId);
            Assert.Equal(12.0, estimate.OffsetSeconds, 9);
            Assert.Equal(2.0 / Math.Sqrt(3.0), estimate.UncertaintySeconds, 9);
            Assert.Equal(3, estimate.AnchorCount);
            Assert.Equal(OffsetMethod.LeastSquares, estimate.Method);
            Assert.False(estimate.IsReference);
            Assert.Equal(3, estimate.Residuals.Count);
        }

        [Fact]
        public void LeastSquares_SingleAnchor_UncertaintyIsNaN()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100),
                Anchor("k1", "A", 106)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.LeastSquares);

            Assert.True(result.IsSuccess);
            ClockOffsetEstimate estimate = result.Value[1];
            Assert.Equal(6.0, estimate.OffsetSeconds, 9);
            Assert.True(double.IsNaN(estimate.UncertaintySeconds));
            Assert.Equal(1, estimate.AnchorCount);
        }


        [Fact]
        public void Median_SingleAnchor_UncertaintyIsNaN()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100),
                Anchor("k1", "A", 106)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.Median);

            Assert.True(result.IsSuccess);
            Assert.Equal(6.0, result.Value[1].OffsetSeconds, 9);
            Assert.True(double.IsNaN(result.Value[1].UncertaintySeconds));
        }

        [Fact]
        public void Median_RejectsOutlier()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 0),
                Anchor("k2", "GNSS", 0),
                Anchor("k3", "GNSS", 0),
                Anchor("k4", "GNSS", 0),
                Anchor("k1", "A", 10),
                Anchor("k2", "A", 10),
                Anchor("k3", "A", 10),
                Anchor("k4", "A", 100)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> median =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.Median);
            Assert.True(median.IsSuccess);
            Assert.Equal(10.0, median.Value[1].OffsetSeconds, 9);
            // 裁定 2（W2-D05）：中位数法只标记离群、不剔除；不确定度不得为 0。
            Assert.True(median.Value[1].UncertaintySeconds > 0.0);
            Assert.Single(median.Value[1].RejectedAnchors);
            Assert.False(median.Value[1].RejectedAnchors[0].ExcludedFromFit);

            // 最小二乘先剔除离群再拟合：10 s（旧行为 32.5 s 被离群点拉偏）。
            Result<IReadOnlyList<ClockOffsetEstimate>> leastSquares =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.LeastSquares);
            Assert.Equal(10.0, leastSquares.Value[1].OffsetSeconds, 9);
            Assert.Equal(3, leastSquares.Value[1].UsedAnchorCount);
        }

        [Fact]
        public void NoCommonAnchors_ReturnsNaNEstimate()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 0),
                Anchor("z1", "C", 10)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS");

            Assert.True(result.IsSuccess);
            ClockOffsetEstimate c = result.Value[1];
            Assert.Equal("C", c.SourceId);
            Assert.Equal(0, c.AnchorCount);
            Assert.True(double.IsNaN(c.OffsetSeconds));
            Assert.True(double.IsNaN(c.UncertaintySeconds));
            Assert.Empty(c.Residuals);
        }

        [Fact]
        public void MissingReference_ReturnsFail()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "A", 0)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS");

            Assert.False(result.IsSuccess);
            Assert.Equal("timeline_no_reference", result.ErrorCode);
        }

        [Fact]
        public void Result_ReferenceFirst_ThenOrdinal()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 0),
                Anchor("k1", "Z", 1),
                Anchor("k1", "A", 2)
            };

            IReadOnlyList<ClockOffsetEstimate> estimates =
                ClockOffsetEstimator.Estimate(anchors, "GNSS").Value;

            Assert.Equal(3, estimates.Count);
            Assert.True(estimates[0].IsReference);
            Assert.Equal("GNSS", estimates[0].SourceId);
            Assert.Equal(0.0, estimates[0].OffsetSeconds, 9);
            Assert.Equal("A", estimates[1].SourceId);
            Assert.Equal("Z", estimates[2].SourceId);
        }

        [Fact]
        public void DuplicateAnchor_UsesFirstOccurrence()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                Anchor("k1", "GNSS", 100),
                Anchor("k1", "A", 110),
                Anchor("k1", "A", 200)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.Median);

            Assert.Equal(10.0, result.Value[1].OffsetSeconds, 9);
        }

        [Fact]
        public void Calibrator_ShiftsFiniteOffsetsOnly()
        {
            Track a = TestHelpers.ScalarTrack(
                "A/Heading", "A", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 10.0));
            Track b = TestHelpers.ScalarTrack(
                "B/Heading", "B", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 10.0));
            Track c = TestHelpers.ScalarTrack(
                "C/Heading", "C", TrackKind.Heading,
                TestHelpers.S(0, 0.0), TestHelpers.S(10, 10.0));

            List<ClockOffsetEstimate> offsets = new List<ClockOffsetEstimate>
            {
                new ClockOffsetEstimate("A", "GNSS", 5.0, 0.0, 1, OffsetMethod.Median, false),
                new ClockOffsetEstimate("B", "GNSS", double.NaN, double.NaN, 0, OffsetMethod.Median, false)
            };

            MultiTrackTimeline calibrated =
                TimelineCalibrator.Apply(new[] { a, b, c }, offsets);

            Track calibratedA = calibrated.Find("A/Heading");
            Assert.Equal(-5.0, calibratedA.Samples[0].Time.Seconds, 9);
            Assert.Equal(5.0, calibratedA.Samples[1].Time.Seconds, 9);

            Track calibratedB = calibrated.Find("B/Heading");
            Assert.Equal(0.0, calibratedB.Samples[0].Time.Seconds, 9);
            Assert.Equal(10.0, calibratedB.Samples[1].Time.Seconds, 9);

            Track calibratedC = calibrated.Find("C/Heading");
            Assert.Equal(0.0, calibratedC.Samples[0].Time.Seconds, 9);

            IReadOnlyList<string> uncalibrated =
                TimelineCalibrator.UncalibratedSources(new[] { a, b, c }, offsets);
            Assert.Equal(new[] { "B", "C" }, uncalibrated);
        }
    }
}
