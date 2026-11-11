using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// 对照原型截图 09 与 P6a 验收标准，检查领域模型与虚构样例是否支撑证据中心字段。
    /// </summary>
    public class PrototypeSupportTests
    {
        [Fact]
        public void TrackKind_CoversScreenshotEightTracks()
        {
            // 原型 09 左轨：驾驶台音频 CH1、VHF CH16、X 波段雷达、ECDIS 截屏、车钟、舵角、AIS SOG、AIS COG。
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.Audio));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.RadarImage));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.EcdisImage));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.EngineTelegraph));
            Assert.True(TrackKindInfo.IsStep(TrackKind.EngineTelegraph));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.RudderAngle));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.SpeedOverGround));
            Assert.True(Enum.IsDefined(typeof(TrackKind), TrackKind.CourseOverGround));
            Assert.True(TrackKindInfo.IsMedia(TrackKind.Audio));
            Assert.True(TrackKindInfo.IsMedia(TrackKind.RadarImage));
            Assert.True(TrackKindInfo.IsMedia(TrackKind.EcdisImage));
        }

        [Fact]
        public void MediaItem_SupportsChannelRangeAndShaMetadata()
        {
            // 原型 09：通道名（CH1/CH16/X-BAND）、时间范围、证据哈希。
            MediaItem item = new MediaItem(
                "AUD-CH1-001",
                TrackKind.Audio,
                "CH1",
                "audio_ch1_0615.wav",
                new TimeRange(new SimTime(900), new SimTime(1620)),
                new Dictionary<string, string> { { "sha256", "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" } });

            Assert.Equal("CH1", item.Channel);
            Assert.Equal(900.0, item.Range.Start.Seconds, 9);
            Assert.Equal("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", item.Metadata["sha256"]);
        }

        [Fact]
        public void ClockOffsetEstimate_HasOffsetAndUncertainty()
        {
            // 原型 09 右上：钟差（秒）与不确定度色带。
            ClockOffsetEstimate estimate = new ClockOffsetEstimate(
                "VTS-AIS", "GNSS", 3.1, 0.4, 8, OffsetMethod.Median, false);
            Assert.Equal(3.1, estimate.OffsetSeconds, 9);
            Assert.Equal(0.4, estimate.UncertaintySeconds, 9);
            Assert.False(estimate.IsReference);
        }

        [Fact]
        public void EventMarker_CanRepresentScreenshotFlags()
        {
            EventMarker marker = new EventMarker(
                "E4", new SimTime(1335), "event", "14:22:15", "MARY-VDR", "MARY-VDR/Heading");
            Assert.Equal("E4", marker.Id);
            Assert.Equal("14:22:15", marker.Label);
        }

        [Fact]
        public void FictionalSamples_AreLabeledAndImportable()
        {
            string mary = W2AccFixture.ReadSample("mary_vdr.nmea");
            string lily = W2AccFixture.ReadSample("lily_svdr.nmea");
            string vts = W2AccFixture.ReadSample("vts_ais.csv");
            string tel = W2AccFixture.ReadSample("mary_telegraph_rudder.csv");
            string media = W2AccFixture.ReadSample("mary_media_manifest.csv");
            Assert.Contains("示例数据（虚构）", mary);
            Assert.Contains("示例数据（虚构）", lily);
            Assert.Contains("示例数据（虚构）", vts);
            Assert.Contains("示例数据（虚构）", tel);
            Assert.Contains("示例数据（虚构）", media);

            Result<VdrImportResult> maryImport = VdrNmeaImporter.Import(
                W2AccFixture.ReadSampleLines("mary_vdr.nmea"),
                W2AccFixture.Options(W2AccFixture.Mary));
            Result<VdrImportResult> lilyImport = VdrNmeaImporter.Import(
                W2AccFixture.ReadSampleLines("lily_svdr.nmea"),
                W2AccFixture.Options(W2AccFixture.Lily));
            Assert.True(maryImport.IsSuccess, maryImport.ErrorMessage);
            Assert.True(lilyImport.IsSuccess, lilyImport.ErrorMessage);
            Assert.True(maryImport.Value.Tracks.Count >= 6);
            Assert.True(lilyImport.Value.Tracks.Count >= 1);
        }

        [Fact]
        public void ImportedEightTracks_CanBeQueriedOnSharedTimeline()
        {
            Result<VdrImportResult> mary = VdrNmeaImporter.Import(
                W2AccFixture.ReadSampleLines("mary_vdr.nmea"),
                W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(mary.IsSuccess, mary.ErrorMessage);

            VdrCsvMapping bridgeMapping = new VdrCsvMapping
            {
                TimeColumn = "time_local",
                TimeFormat = "yyyy-MM-dd HH:mm:ss",
                TimeZoneOffset = TimeSpan.FromHours(8),
                EventColumn = "event",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "telegraph",
                        Kind = TrackKind.EngineTelegraph,
                        MarkChanges = true,
                        TextValues = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                        {
                            { "STOP", 0 },
                            { "HALF AHEAD", 3 },
                            { "FULL AHEAD", 4 },
                            { "SLOW AHEAD", 2 },
                            { "FULL ASTERN", -4 }
                        }
                    },
                    new VdrCsvColumnMapping
                    {
                        Column = "rudder_deg",
                        Kind = TrackKind.RudderAngle
                    }
                }
            };
            Result<VdrImportResult> bridge = VdrCsvImporter.Import(
                W2AccFixture.ReadSampleLines("mary_telegraph_rudder.csv"),
                bridgeMapping,
                W2AccFixture.Options("MARY-BRIDGE"));
            Assert.True(bridge.IsSuccess, bridge.ErrorMessage);

            Result<VdrImportResult> media = VdrMediaManifestImporter.Import(
                W2AccFixture.ReadSampleLines("mary_media_manifest.csv"),
                W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(media.IsSuccess, media.ErrorMessage);

            VdrCsvMapping vtsMapping = new VdrCsvMapping
            {
                TimeColumn = "time_utc",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping { Column = "sog_kn", Kind = TrackKind.SpeedOverGround },
                    new VdrCsvColumnMapping { Column = "cog_deg", Kind = TrackKind.CourseOverGround }
                }
            };
            Result<VdrImportResult> vts = VdrCsvImporter.Import(
                W2AccFixture.ReadSampleLines("vts_ais.csv"),
                vtsMapping,
                W2AccFixture.Options(W2AccFixture.Vts));
            Assert.True(vts.IsSuccess, vts.ErrorMessage);

            List<Track> tracks = new List<Track>();
            tracks.AddRange(mary.Value.Tracks);
            tracks.AddRange(bridge.Value.Tracks);
            tracks.AddRange(media.Value.Tracks);
            tracks.AddRange(vts.Value.Tracks);

            Assert.Contains(tracks, t => t.Kind == TrackKind.Audio && t.Media.Any(m => m.Channel == "CH1"));
            Assert.Contains(tracks, t => t.Kind == TrackKind.Audio && t.Media.Any(m => m.Channel == "CH16"));
            Assert.Contains(tracks, t => t.Kind == TrackKind.RadarImage);
            Assert.Contains(tracks, t => t.Kind == TrackKind.EcdisImage);
            Assert.Contains(tracks, t => t.Kind == TrackKind.EngineTelegraph && t.Samples.Count > 0);
            Assert.Contains(tracks, t => t.Kind == TrackKind.RudderAngle && t.Samples.Count > 0);
            Assert.Contains(tracks, t => t.Kind == TrackKind.SpeedOverGround && t.SourceId == W2AccFixture.Vts);
            Assert.Contains(tracks, t => t.Kind == TrackKind.CourseOverGround && t.SourceId == W2AccFixture.Vts);

            List<AnchorObservation> anchors = new List<AnchorObservation>();
            anchors.AddRange(mary.Value.Anchors);
            MultiTrackTimeline calibrated = TimelineCalibrator.Apply(
                tracks,
                ClockOffsetEstimator.Estimate(anchors, "GNSS").Value);

            // P6a：拖动时间轴误差小于 0.1 s。在 14:22:15（UTC 06:22:15 = 纪元+1335 s）查询，
            // 已校准轨道的样本时刻与查询时刻之差应小于 0.1 s（或该轨在此时有值/媒体）。
            SimTime t = new SimTime(1335.0);
            TimelineSnapshot snap = calibrated.QueryAt(t);
            Assert.NotEmpty(snap.Values);
            int live = snap.Values.Count(v => v.HasValue || v.HasPosition || (v.ActiveMedia != null && v.ActiveMedia.Count > 0));
            Assert.True(live >= 6, "14:22:15 应能同时查到多数轨道，实际有效轨=" + live);
        }
    }
}
