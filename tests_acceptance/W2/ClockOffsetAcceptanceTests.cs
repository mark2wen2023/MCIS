using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// 钟差估计：最小二乘 / 中位数、离群锚点、无共同锚点、校准平移。
    /// </summary>
    public class ClockOffsetAcceptanceTests
    {
        private static AnchorObservation A(string key, string source, double time)
        {
            return new AnchorObservation(key, source, new SimTime(time));
        }

        [Fact]
        public void LeastSquares_MatchesMeanAndStandardError()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                A("k1", "GNSS", 100), A("k2", "GNSS", 110), A("k3", "GNSS", 120),
                A("k1", "A", 110), A("k2", "A", 122), A("k3", "A", 134)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.LeastSquares);
            Assert.True(result.IsSuccess, result.ErrorMessage);
            ClockOffsetEstimate estimate = result.Value[1];
            Assert.Equal("A", estimate.SourceId);
            Assert.Equal(12.0, estimate.OffsetSeconds, 9);
            Assert.Equal(2.0 / System.Math.Sqrt(3.0), estimate.UncertaintySeconds, 9);
            Assert.Equal(3, estimate.AnchorCount);
        }

        [Fact]
        public void Median_ResistsSingleOutlier_OffsetStaysAtCluster()
        {
            List<AnchorObservation> anchors = OutlierSet();

            Result<IReadOnlyList<ClockOffsetEstimate>> median =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.Median);
            Assert.True(median.IsSuccess, median.ErrorMessage);
            Assert.Equal(10.0, median.Value[1].OffsetSeconds, 9);
        }

        [Fact]
        public void Median_OutlierMustNotZeroUncertaintyOrStayInCountUnremarked()
        {
            // 四个差值为 10/10/10/100。若真正剔除离群点，AnchorCount 应为 3；
            // 若保留全部点，不确定度不应被算成 0（否则调查人员会误以为无分歧）。
            List<AnchorObservation> anchors = OutlierSet();
            ClockOffsetEstimate estimate =
                ClockOffsetEstimator.Estimate(anchors, "GNSS", OffsetMethod.Median).Value[1];

            bool rejected = estimate.AnchorCount == 3;
            bool uncertaintyReflectsSpread = !double.IsNaN(estimate.UncertaintySeconds)
                                            && estimate.UncertaintySeconds > 1e-9;
            Assert.True(
                rejected || uncertaintyReflectsSpread,
                "离群锚点未剔除（AnchorCount=" + estimate.AnchorCount +
                "）且不确定度为 " + estimate.UncertaintySeconds + "，会把 90s 残差掩盖为 0。");
        }

        [Fact]
        public void NoCommonAnchors_ReturnsNaNAndZeroCount()
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                A("k1", "GNSS", 0),
                A("z1", "C", 10)
            };

            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(anchors, "GNSS");
            Assert.True(result.IsSuccess, result.ErrorMessage);
            ClockOffsetEstimate c = result.Value[1];
            Assert.Equal("C", c.SourceId);
            Assert.Equal(0, c.AnchorCount);
            Assert.True(double.IsNaN(c.OffsetSeconds));
            Assert.True(double.IsNaN(c.UncertaintySeconds));
        }

        [Fact]
        public void MissingReference_Fails()
        {
            Result<IReadOnlyList<ClockOffsetEstimate>> result =
                ClockOffsetEstimator.Estimate(new[] { A("k1", "A", 0) }, "GNSS");
            Assert.False(result.IsSuccess);
            Assert.Equal("timeline_no_reference", result.ErrorCode);
        }

        [Fact]
        public void Calibrator_ShiftsFiniteOffsetsOnly_LeavesNaNUnchanged()
        {
            Track a = W2AccFixture.ScalarTrack(
                "A/HDG", "A", TrackKind.Heading,
                W2AccFixture.S(0, 0.0), W2AccFixture.S(10, 10.0));
            Track b = W2AccFixture.ScalarTrack(
                "B/HDG", "B", TrackKind.Heading,
                W2AccFixture.S(0, 0.0), W2AccFixture.S(10, 10.0));

            ClockOffsetEstimate[] offsets =
            {
                new ClockOffsetEstimate("A", "GNSS", 5.0, 0.1, 2, OffsetMethod.Median, false),
                new ClockOffsetEstimate("B", "GNSS", double.NaN, double.NaN, 0, OffsetMethod.Median, false)
            };

            MultiTrackTimeline calibrated = TimelineCalibrator.Apply(new[] { a, b }, offsets);
            Assert.Equal(-5.0, calibrated.Find("A/HDG").Samples[0].Time.Seconds, 9);
            Assert.Equal(5.0, calibrated.Find("A/HDG").Samples[1].Time.Seconds, 9);
            Assert.Equal(0.0, calibrated.Find("B/HDG").Samples[0].Time.Seconds, 9);
            Assert.Equal(new[] { "B" }, TimelineCalibrator.UncalibratedSources(new[] { a, b }, offsets));
        }

        private static List<AnchorObservation> OutlierSet()
        {
            return new List<AnchorObservation>
            {
                A("k1", "GNSS", 0), A("k2", "GNSS", 0), A("k3", "GNSS", 0), A("k4", "GNSS", 0),
                A("k1", "A", 10), A("k2", "A", 10), A("k3", "A", 10), A("k4", "A", 100)
            };
        }
    }
}
