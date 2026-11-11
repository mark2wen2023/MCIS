using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// TrackCleaner 异常点剔除、各原因码触发、手动恢复与天线偏移修正单元测试。
    /// </summary>
    public sealed class TrackCleanerTests
    {
        private static readonly DateTimeOffset Epoch = new DateTimeOffset(2026, 5, 18, 10, 0, 0, TimeSpan.Zero);
        private static readonly GeoCoord Origin = new GeoCoord(113.7050, 22.2600, 0.0);

        private static AisDecodedRecord MakeRecord(
            int line,
            double offsetSec,
            double eastM,
            double northM,
            float sogKn = 10.0f,
            float cogDeg = 0.0f,
            float hdgDeg = 0.0f,
            string mmsi = "413990101",
            byte navStatus = 0)
        {
            GeoCoord geo = GeoMath.EnuToWgs84(new EnuPosition(eastM, northM, 0.0), Origin);
            return new AisDecodedRecord(
                line,
                "!AIVDM",
                1,
                mmsi,
                Epoch.AddSeconds(offsetSec),
                TimeQuality.ExactTagBlock,
                geo.LonDeg,
                geo.LatDeg,
                sogKn,
                cogDeg,
                hdgDeg,
                0.0f,
                navStatus);
        }

        [Fact]
        public void Clean_UnavailableFields_TriggersUnavailableReason()
        {
            double speedMps = 10.0 * HermiteMath.MetersPerSecondPerKnot;
            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                MakeRecord(1, 0.0, 0.0, 0.0, 10.0f, 0.0f),
                new AisDecodedRecord(2, "!AIVDM", 1, "413990101", Epoch.AddSeconds(10), TimeQuality.ExactTagBlock, 181.0, 22.26, 10.0f, 0.0f, 0.0f, 0.0f, 0),
                new AisDecodedRecord(3, "!AIVDM", 1, "413990101", Epoch.AddSeconds(20), TimeQuality.ExactTagBlock, 113.705, 91.0, 10.0f, 0.0f, 0.0f, 0.0f, 0),
                new AisDecodedRecord(4, "!AIVDM", 1, "413990101", Epoch.AddSeconds(30), TimeQuality.ExactTagBlock, 113.705, 22.26, 102.3f, 0.0f, 0.0f, 0.0f, 0),
                MakeRecord(5, 40.0, 0.0, speedMps * 40.0, 10.0f, 0.0f)
            };

            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                "vessel_1", records, AntennaOffset.Zero, Epoch, new LocalEnuGeoConverter(Origin));

            Assert.Equal(2, report.CleanedSamples.Count);
            Assert.Equal(3, report.RejectedSamples.Count);
            Assert.Equal(3, report.GetRejectedCount(RejectReason.Unavailable));
            Assert.All(report.RejectedSamples, r => Assert.Equal(RejectReason.Unavailable, r.Reason));
        }

        [Fact]
        public void Clean_OutOfRangeFields_TriggersOutOfRangeReason()
        {
            double speedMps = 10.0 * HermiteMath.MetersPerSecondPerKnot;
            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                MakeRecord(1, 0.0, 0.0, 0.0, 10.0f, 0.0f),
                new AisDecodedRecord(2, "!AIVDM", 1, "413990101", Epoch.AddSeconds(10), TimeQuality.ExactTagBlock, 195.0, 22.26, 10.0f, 0.0f, 0.0f, 0.0f, 0),
                new AisDecodedRecord(3, "!AIVDM", 1, "413990101", Epoch.AddSeconds(20), TimeQuality.ExactTagBlock, 113.705, -95.0, 10.0f, 0.0f, 0.0f, 0.0f, 0),
                new AisDecodedRecord(4, "!AIVDM", 1, "413990101", Epoch.AddSeconds(30), TimeQuality.ExactTagBlock, 113.705, 22.26, -2.5f, 0.0f, 0.0f, 0.0f, 0),
                new AisDecodedRecord(5, "!AIVDM", 1, "413990101", Epoch.AddSeconds(35), TimeQuality.ExactTagBlock, 113.705, 22.26, 10.0f, 385.0f, 0.0f, 0.0f, 0),
                MakeRecord(6, 40.0, 0.0, speedMps * 40.0, 10.0f, 0.0f)
            };

            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                "vessel_1", records, AntennaOffset.Zero, Epoch, new LocalEnuGeoConverter(Origin));

            Assert.Equal(2, report.CleanedSamples.Count);
            Assert.Equal(4, report.GetRejectedCount(RejectReason.OutOfRange));
        }

        [Fact]
        public void Clean_DuplicateAndOutOfOrderTimestamps_TriggersExpectedReasons()
        {
            double v = 10.0 * HermiteMath.MetersPerSecondPerKnot;
            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                MakeRecord(1, 0.0, 0.0, 0.0, 10.0f, 0.0f),
                MakeRecord(2, 10.0, 0.0, v * 10.0, 10.0f, 0.0f),
                MakeRecord(3, 10.0, 0.0, v * 10.0, 10.0f, 0.0f), // DuplicateTimestamp
                MakeRecord(4, 5.0, 0.0, v * 5.0, 10.0f, 0.0f),   // OutOfOrder
                MakeRecord(5, 20.0, 0.0, v * 20.0, 10.0f, 0.0f)
            };

            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                "vessel_1", records, AntennaOffset.Zero, Epoch, new LocalEnuGeoConverter(Origin));

            Assert.Equal(3, report.CleanedSamples.Count);
            Assert.Equal(2, report.RejectedSamples.Count);
            Assert.Equal(RejectReason.DuplicateTimestamp, report.RejectedSamples[0].Reason);
            Assert.Equal(3, report.RejectedSamples[0].SourceLineNumber);
            Assert.Equal(RejectReason.OutOfOrder, report.RejectedSamples[1].Reason);
            Assert.Equal(4, report.RejectedSamples[1].SourceLineNumber);
        }

        [Fact]
        public void Clean_PositionJumpSpeedJumpAndCourseJump_TriggersRespectiveReasons()
        {
            double v = 10.0 * HermiteMath.MetersPerSecondPerKnot;
            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                MakeRecord(1, 0.0, 0.0, 0.0, 10.0f, 0.0f),
                MakeRecord(2, 10.0, 0.0, v * 10.0, 10.0f, 0.0f),
                MakeRecord(3, 20.0, 2500.0, v * 20.0, 10.0f, 0.0f), // PositionJump (2500m in 10s > 30kn)
                MakeRecord(4, 20.0, 0.0, v * 20.0, 28.0f, 0.0f),    // SpeedJump (10 -> 28 kn in 10s, normal pos)
                MakeRecord(5, 20.0, 0.0, v * 20.0, 10.0f, 185.0f),  // CourseJump (0 -> 185 deg in 10s)
                MakeRecord(6, 30.0, 0.0, v * 30.0, 10.0f, 0.0f)
            };

            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                "vessel_1", records, AntennaOffset.Zero, Epoch, new LocalEnuGeoConverter(Origin));

            Assert.Equal(3, report.CleanedSamples.Count);
            Assert.Equal(3, report.RejectedSamples.Count);
            Assert.Equal(RejectReason.PositionJump, report.RejectedSamples[0].Reason);
            Assert.Equal(RejectReason.SpeedJump, report.RejectedSamples[1].Reason);
            Assert.Equal(RejectReason.CourseJump, report.RejectedSamples[2].Reason);
        }

        [Fact]
        public void Clean_ManualRestoreAndAntennaOffset_AppliesCorrectly()
        {
            List<AisDecodedRecord> records = new List<AisDecodedRecord>
            {
                MakeRecord(1, 0.0, 0.0, 0.0, 10.0f, 90.0f, 90.0f),
                MakeRecord(2, 10.0, 1500.0, 0.0, 10.0f, 90.0f, 90.0f)
            };

            AntennaOffset offset = new AntennaOffset(150.0f, 50.0f, 10.0f, 20.0f);
            HashSet<int> restored = new HashSet<int> { 2 };
            TrackCleaningReport report = TrackCleaner.CleanAisRecords(
                "vessel_1", records, offset, Epoch, new LocalEnuGeoConverter(Origin),
                TrackCleaningConfig.CreateDefault(), restored);

            Assert.Equal(2, report.CleanedSamples.Count);
            Assert.Empty(report.RejectedSamples);
            // Heading = 90 deg (East): forward=(150-50)/2=+50m -> +50m East; starboard=(20-10)/2=+5m -> -5m North
            Assert.Equal(50.0, report.CleanedSamples[0].EnuCenter.EastM, 3);
            Assert.Equal(-5.0, report.CleanedSamples[0].EnuCenter.NorthM, 3);
        }
    }
}
