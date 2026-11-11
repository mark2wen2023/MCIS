using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    /// <summary>
    /// W2.1 复核补充用例（执行器复核 dsh 实现时发现的两处遗漏）。演示数据虚构。
    /// </summary>
    public sealed class W21ReviewTests
    {
        private static readonly DateTimeOffset Epoch = new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        private static VdrImportOptions Options(string source)
        {
            return new VdrImportOptions { SourceId = source, CaseEpochUtc = Epoch };
        }

        private static string Ttm(int n, double range, double bearing, string unit, string name)
        {
            return TestHelpers.Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "RATTM,{0:00},{1:0.00},{2:0.0},{3},0.0,000.0,T,0.00,0.0,N,{4},T,,061500.00",
                n, range, bearing, unit, name));
        }

        // 门面 VdrImporter.ImportAll 合并轨道时必须保留 BearingReference，否则相对方位会被当作真方位参与比对。
        [Fact]
        public void Facade_ImportAll_PreservesRelativeBearingReference()
        {
            Result<VdrImportResult> r = VdrImporter.ImportAll(
                Options("MARY-VDR"),
                new[] { "2026-05-18T06:15:00.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY") });
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Track rel = Assert.Single(r.Value.Tracks, t => t.Kind == TrackKind.TargetBearing);
            Assert.Equal(BearingReference.Relative, rel.BearingReference);
            Assert.EndsWith("/REL", rel.Id);
        }

        [Fact]
        public void Facade_RelativeTrack_IsNotComparedWithTrueBearingOfOtherSource()
        {
            List<Track> tracks = new List<Track>();
            List<string> mary = new List<string>();
            List<string> vts = new List<string>();
            for (int s = 0; s <= 10; s++)
            {
                string prefix = "2026-05-18T06:15:" + s.ToString("00", CultureInfo.InvariantCulture) + ".000Z,";
                mary.Add(prefix + Ttm(1, 1.2, 30.0, "R", "LILY"));
                vts.Add(prefix + Ttm(1, 1.2, 75.0, "T", "LILY"));
            }

            tracks.AddRange(VdrImporter.ImportAll(Options("MARY-VDR"), mary).Value.Tracks);
            tracks.AddRange(VdrImporter.ImportAll(Options("VTS"), vts).Value.Tracks);
            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(tracks));
            Assert.DoesNotContain(result.Conflicts, c => c.Kind == TrackKind.TargetBearing);
            Assert.Contains(result.Diagnostics, d => d.Reason == "bearing_relative_no_heading");
        }

        // 不走时间选择的行（不支持的句型、校验和错误被丢弃）也要报告无效的标签块 / 日志前缀，且每行只报一次。
        [Fact]
        public void InvalidTagBlock_OnUnsupportedSentence_StillDiagnosedOnce()
        {
            string line = "\\c:1779084900*00\\" + TestHelpers.Nmea("GPXYZ,1,2,3");
            VdrImportResult r = VdrNmeaImporter.Import(new[] { line }, Options("MARY-VDR")).Value;
            Assert.Single(r.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        [Fact]
        public void InvalidPrefix_OnBadChecksumLine_StillDiagnosed()
        {
            string good = TestHelpers.Nmea("GPRMC,061450.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string bad = good.Substring(0, good.Length - 2) + (good.EndsWith("00") ? "11" : "00");
            VdrImportResult r = VdrNmeaImporter.Import(new[] { "not-a-time," + bad }, Options("MARY-VDR")).Value;
            Assert.Contains(r.Diagnostics, d => d.Code == "vdr_bad_checksum");
            Assert.Single(r.Diagnostics, d => d.Code == "vdr_logprefix_invalid");
        }

        [Fact]
        public void InvalidTagBlock_OnRmc_IsDiagnosedOnlyOnce()
        {
            string line = "2026-05-18T06:15:30.000Z,\\c:1779084900*00\\" +
                          TestHelpers.Nmea("GPRMC,061450.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            VdrImportResult r = VdrNmeaImporter.Import(new[] { line }, Options("MARY-VDR")).Value;
            Assert.Single(r.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }
    }
}
