using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// W2 复测（2026-11-11）：按 DEFECTS/W2.md 文末架构师 7 条裁定补测。演示数据全部虚构。
    /// </summary>
    public class RetestToleranceTests
    {
        private static IReadOnlyList<TimelineConflict> Pair(TrackKind kind, double a, double b, ConflictThresholds t = null)
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/" + kind, "A", kind, 0, 10, a),
                W2AccFixture.Constant("B/" + kind, "B", kind, 0, 10, b)
            });
            return ConflictDetector.Detect(timeline, t);
        }

        // 裁定 1：严格大于才算冲突，比较时加 1e-6（同单位）容差。边界两侧各取 ±0.5e-6。
        [Theory]
        [InlineData(TrackKind.SpeedOverGround, 12.0, 12.3, false)]
        [InlineData(TrackKind.SpeedOverGround, 12.0, 12.3000009, false)]
        [InlineData(TrackKind.SpeedOverGround, 12.0, 12.3000015, true)]
        [InlineData(TrackKind.SpeedOverGround, 12.3, 12.0, false)]
        [InlineData(TrackKind.RateOfTurn, 10.0, 15.0, false)]
        [InlineData(TrackKind.RateOfTurn, 10.0, 15.0000015, true)]
        [InlineData(TrackKind.RudderAngle, -1.0, 1.0000009, false)]
        [InlineData(TrackKind.RudderAngle, -1.0, 1.0000015, true)]
        [InlineData(TrackKind.Heading, 359.0, 1.0000005, false)]
        [InlineData(TrackKind.Heading, 359.0, 1.0000015, true)]
        [InlineData(TrackKind.CourseOverGround, 0.1, 358.1, false)]
        public void Threshold_IsStrictlyGreater_WithTolerance1e6(TrackKind kind, double a, double b, bool expectConflict)
        {
            IReadOnlyList<TimelineConflict> conflicts = Pair(kind, a, b);
            Assert.True(
                expectConflict == (conflicts.Count == 1),
                kind + " " + a + " vs " + b + " 期望冲突=" + expectConflict + "，实际=" +
                string.Join(" | ", conflicts.Select(c => c.ToString())));
        }

        [Fact]
        public void DefaultTolerance_Is1e6_AndConfigurable()
        {
            Assert.Equal(1e-6, ConflictThresholds.Default.Tolerance, 12);
            ConflictThresholds loose = new ConflictThresholds { Tolerance = 0.01 };
            Assert.Empty(Pair(TrackKind.SpeedOverGround, 12.0, 12.305, loose));
            Assert.Single(Pair(TrackKind.SpeedOverGround, 12.0, 12.305));
        }

        [Fact]
        public void DefaultThresholds_MutationDoesNotLeakIntoDetectNull()
        {
            ConflictThresholds.Default.SpeedKn = 100.0;
            Assert.Equal(0.3, ConflictThresholds.Default.SpeedKn, 12);
            Assert.Single(Pair(TrackKind.SpeedOverGround, 12.0, 12.5));
        }
    }

    public class RetestOutlierTests
    {
        private static List<AnchorObservation> Set(params double[] differences)
        {
            List<AnchorObservation> anchors = new List<AnchorObservation>();
            for (int i = 0; i < differences.Length; i++)
            {
                string key = "k" + (i + 1).ToString(CultureInfo.InvariantCulture);
                double t = (i + 1) * 100.0;
                anchors.Add(new AnchorObservation(key, "GNSS", new SimTime(t)));
                anchors.Add(new AnchorObservation(key, "B", new SimTime(t + differences[i])));
            }

            return anchors;
        }

        private static ClockOffsetEstimate Est(OffsetMethod method, ClockOffsetOptions options, params double[] d)
        {
            Result<IReadOnlyList<ClockOffsetEstimate>> r = ClockOffsetEstimator.Estimate(Set(d), "GNSS", method, options);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value.Single(e => e.SourceId == "B");
        }

        // MAD=0 时门限取 1 s 下限：残差 0.9 s 不离群，1.1 s 离群。
        [Theory]
        [InlineData(OffsetMethod.LeastSquares)]
        [InlineData(OffsetMethod.Median)]
        public void TinyMad_UsesOneSecondFloor_BothSides(OffsetMethod method)
        {
            ClockOffsetEstimate inside = Est(method, null, 10, 10, 10, 10, 10.9);
            Assert.Empty(inside.RejectedAnchors);
            Assert.Equal(5, inside.UsedAnchorCount);

            ClockOffsetEstimate outside = Est(method, null, 10, 10, 10, 10, 11.1);
            RejectedAnchor rej = Assert.Single(outside.RejectedAnchors);
            Assert.Equal("k5", rej.EventKey);
            Assert.False(string.IsNullOrWhiteSpace(rej.Reason));
            Assert.Equal(5, outside.AnchorCount);
            Assert.Equal(5, outside.Residuals.Count);
            if (method == OffsetMethod.LeastSquares)
            {
                Assert.True(rej.ExcludedFromFit);
                Assert.Equal(4, outside.UsedAnchorCount);
                Assert.Equal(10.0, outside.OffsetSeconds, 9);
            }
            else
            {
                Assert.Equal(10.0, outside.OffsetSeconds, 9);
            }

            Assert.True(outside.UncertaintySeconds > 0.0, "不确定度应非零，实际=" + outside.UncertaintySeconds);
        }

        // MAD=2 s：门限 3×1.4826×2 = 8.8956 s（大于 1 s 下限）。残差 8.8 不离群，9.0 离群。
        [Fact]
        public void LargeMad_UsesScaledMadGate_BothSides()
        {
            ClockOffsetEstimate inside = Est(OffsetMethod.LeastSquares, null, 0, 2, 4, 6, 12.8);
            Assert.Empty(inside.RejectedAnchors);
            Assert.Equal(5, inside.UsedAnchorCount);
            Assert.Equal((0 + 2 + 4 + 6 + 12.8) / 5.0, inside.OffsetSeconds, 9);

            ClockOffsetEstimate outside = Est(OffsetMethod.LeastSquares, null, 0, 2, 4, 6, 13.0);
            Assert.Single(outside.RejectedAnchors);
            Assert.Equal(4, outside.UsedAnchorCount);
            Assert.Equal(3.0, outside.OffsetSeconds, 9);
        }

        [Fact]
        public void AbsoluteFloor_IsConfigurable()
        {
            ClockOffsetOptions opts = new ClockOffsetOptions { OutlierAbsoluteFloorSeconds = 0.5 };
            ClockOffsetEstimate e = Est(OffsetMethod.LeastSquares, opts, 10, 10, 10, 10, 10.9);
            Assert.Single(e.RejectedAnchors);
            Assert.Equal(4, e.UsedAnchorCount);
        }

        [Theory]
        [InlineData(OffsetMethod.LeastSquares)]
        [InlineData(OffsetMethod.Median)]
        public void ClassicOutlierSet_FlagsAndGivesNonZeroUncertainty(OffsetMethod method)
        {
            ClockOffsetEstimate e = Est(method, null, 10, 10, 10, 100);
            Assert.Equal(10.0, e.OffsetSeconds, 9);
            Assert.Equal("k4", Assert.Single(e.RejectedAnchors).EventKey);
            Assert.True(e.UncertaintySeconds > 0.0 && !double.IsNaN(e.UncertaintySeconds));
            Assert.Equal(4, e.AnchorCount);
        }
    }

    public class RetestNmeaTests
    {
        private const string SixFifteenUnix = "1779084900"; // 2026-05-18 06:15:00 UTC（虚构）

        private static VdrImportResult Import(VdrImportOptions options, params string[] lines)
        {
            Result<VdrImportResult> r = VdrNmeaImporter.Import(lines, options);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            return r.Value;
        }

        private static double[] SogTimes(VdrImportResult r)
        {
            Track sog = r.Tracks.FirstOrDefault(t => t.Kind == TrackKind.SpeedOverGround);
            return sog == null ? new double[0] : sog.Samples.Select(s => s.Time.Seconds).ToArray();
        }

        // 裁定 3：校验和有效的标签块 > 日志前缀 > 句内时间。
        [Fact]
        public void ValidTagBlock_BeatsSentenceTime_ByDefault()
        {
            string line = W2AccFixture.TagBlock("c:" + SixFifteenUnix) + W2AccFixture.Rmc("061450.00", "180526");
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), line);
            Assert.Equal(new[] { 900.0 }, SogTimes(r));
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_tagblock_invalid");
        }

        [Fact]
        public void ValidTagBlock_LowercaseHex_IsAccepted()
        {
            string body = "c:" + SixFifteenUnix;
            string tag = "\\" + body + "*" + W2AccFixture.XorChecksum(body).ToString("x2", CultureInfo.InvariantCulture) + "\\";
            NmeaSentence s;
            string err;
            Assert.True(NmeaParser.TryParse(tag + W2AccFixture.Rmc("061450.00", "180526"), out s, out err), err);
            Assert.True(s.TagBlockChecksumValid);
            Assert.True(s.TagBlockTimeUtc.HasValue);
        }

        [Fact]
        public void InvalidTagBlock_FallsBackToSentenceTime_WithWarning()
        {
            string line = "\\c:" + SixFifteenUnix + "*00\\" + W2AccFixture.Rmc("061450.00", "180526");
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), line);
            Assert.Equal(new[] { 890.0 }, SogTimes(r));
            VdrDiagnostic d = Assert.Single(r.Diagnostics, x => x.Code == "vdr_tagblock_invalid");
            Assert.Equal(DiagnosticSeverity.Warning, d.Severity);
        }

        [Fact]
        public void LogPrefix_BeatsSentenceTime()
        {
            string line = "2026-05-18T06:15:30.000Z," + W2AccFixture.Rmc("061450.00", "180526");
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), line);
            Assert.Equal(new[] { 930.0 }, SogTimes(r));
        }

        // 同一行同时带日志前缀与有效标签块（记录仪给 IEC 61162-450 流加前缀时常见），应采信标签块。
        [Fact]
        public void LogPrefixPlusValidTagBlock_TagBlockWins()
        {
            string line = "2026-05-18T06:15:30.000Z," + W2AccFixture.TagBlock("c:" + SixFifteenUnix) +
                          W2AccFixture.Rmc("061450.00", "180526");
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), line);
            Assert.True(
                SogTimes(r).SequenceEqual(new[] { 900.0 }),
                "期望采信标签块 900 s；实际样本时刻=[" + string.Join(", ", SogTimes(r)) + "]（930=日志前缀，890=句内时间）。");
        }

        [Fact]
        public void LogPrefixPlusInvalidTagBlock_FallsBackToPrefix_WithWarning()
        {
            string line = "2026-05-18T06:15:30.000Z,\\c:" + SixFifteenUnix + "*00\\" + W2AccFixture.Rmc("061450.00", "180526");
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), line);
            Assert.True(
                SogTimes(r).SequenceEqual(new[] { 930.0 }),
                "期望回落日志前缀 930 s；实际=[" + string.Join(", ", SogTimes(r)) + "]，诊断=" +
                string.Join(" | ", r.Diagnostics.Select(x => x.Code)));
            Assert.Contains(r.Diagnostics, x => x.Code == "vdr_tagblock_invalid");
        }

        private static string RmcOfLength(int targetLength)
        {
            string body = "GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A";
            int pad = targetLength - (body.Length + 4) - 1; // 额外字段 ",XXX"
            Assert.True(pad >= 1);
            return W2AccFixture.Nmea(body + "," + new string('P', pad));
        }

        // 裁定 6 + W2.1 确认②：超长仍解析（不崩、不丢），出警告。计数口径：'$' 至 "*hh"（不含 CRLF），上限 80。
        [Theory]
        // W2.1 裁定（DEFECTS/W2.md「架构师复测裁定」确认②，2026-11-11 19:42/19:58）：82 字符含 CRLF，
        // 不含 CRLF 时 >80 即告警。原 (82,false) 按裁定改为 (82,true)，并补 79/80/81 边界。
        [InlineData(79, false)]
        [InlineData(80, false)]
        [InlineData(81, true)]
        [InlineData(82, true)]
        [InlineData(83, true)]
        [InlineData(200, true)]
        public void Over82Chars_StillParsed_WithWarning(int length, bool expectWarning)
        {
            string sentence = RmcOfLength(length);
            Assert.Equal(length, sentence.Length);
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), "2026-05-18T06:15:00.000Z," + sentence);
            Assert.Single(SogTimes(r));
            List<VdrDiagnostic> warnings = r.Diagnostics.Where(d => d.Code == "vdr_line_too_long").ToList();
            Assert.Equal(expectWarning ? 1 : 0, warnings.Count);
            if (expectWarning)
            {
                Assert.Equal(DiagnosticSeverity.Warning, warnings[0].Severity);
            }
        }

        // D01 回归：截断地址只丢该行。
        [Fact]
        public void D01_TruncatedLine_OnlyThatLineDropped_WithDiagnostic()
        {
            VdrImportResult r = Import(
                W2AccFixture.Options(W2AccFixture.Mary),
                "2026-05-18T06:15:00.000Z," + W2AccFixture.Rmc("061500.00", "180526"),
                "$GPR",
                "!AIVD",
                "2026-05-18T06:15:20.000Z," + W2AccFixture.Rmc("061520.00", "180526"));
            Assert.Equal(new[] { 900.0, 920.0 }, SogTimes(r));
            Assert.Contains(r.Diagnostics, d => d.LineNumber == 2 && d.Code == "vdr_parse_error");
            Assert.Contains(r.Diagnostics, d => d.LineNumber == 3 && d.Code == "vdr_parse_error");
            Assert.Equal(2, r.SentencesUsed);
        }

        // D01 回归：合法语句的每个前缀截断都不抛异常，导入始终成功。
        [Fact]
        public void D01_EveryPrefixOfValidLine_NeverThrows()
        {
            string full = "2026-05-18T06:15:00.000Z," + W2AccFixture.TagBlock("c:" + SixFifteenUnix) +
                          W2AccFixture.Rmc("061500.00", "180526");
            string[] extras = { "$", "!", "$*", "$GP*", "$GPRMC*", "\\", "\\c:1*", "\\\\$GPRMC", "$,,,", "$GPRMC,*ZZ", "*", "$GPRMC,1,2,3*4" };
            List<string> lines = new List<string>(extras);
            for (int i = 0; i <= full.Length; i++)
            {
                lines.Add(full.Substring(0, i));
            }

            foreach (string l in lines)
            {
                NmeaSentence s;
                string e;
                Exception ex = Record.Exception(() => NmeaParser.TryParse(l, out s, out e));
                Assert.True(ex == null, "TryParse 抛异常：「" + l + "」→ " + ex);
            }

            Result<VdrImportResult> r = default(Result<VdrImportResult>);
            Exception thrown = Record.Exception(() => r = VdrNmeaImporter.Import(lines, W2AccFixture.Options(W2AccFixture.Mary)));
            Assert.Null(thrown);
            Assert.True(r.IsSuccess, r.ErrorMessage);
        }

        // D02 回归：只有 GGA 的流跨午夜，日期滚到次日；随后带新日期的 RMC 不得二次滚动。
        [Fact]
        public void D02_GgaOnlyStream_RollsOnce_AndDatedRmcDoesNotDoubleRoll()
        {
            VdrImportOptions options = W2AccFixture.Options(W2AccFixture.Mary, new DateTime(2026, 5, 18, 0, 0, 0, DateTimeKind.Utc));
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;
            VdrImportResult r = Import(
                options,
                W2AccFixture.Gga("235950.00"),
                W2AccFixture.Gga("000010.00"),
                W2AccFixture.Rmc("000020.00", "190526"),
                W2AccFixture.Gga("000030.00"));
            Track pos = r.Tracks.Single(t => t.Kind == TrackKind.Position);
            double day19 = SimTime.FromUtc(new DateTimeOffset(2026, 5, 19, 0, 0, 0, TimeSpan.Zero), W2AccFixture.Epoch).Seconds;
            double[] expected = { day19 - 10, day19 + 10, day19 + 20, day19 + 30 };
            double[] actual = pos.Samples.Select(s => s.Time.Seconds).ToArray();
            Assert.True(expected.SequenceEqual(actual), "期望=[" + string.Join(", ", expected) + "] 实际=[" + string.Join(", ", actual) + "]");
            Assert.Single(r.Diagnostics, d => d.Code == "vdr_date_rollover");
        }

        [Fact]
        public void D02_SmallBackwardJitter_DoesNotRollDate()
        {
            VdrImportOptions options = W2AccFixture.Options(W2AccFixture.Mary, new DateTime(2026, 5, 18, 0, 0, 0, DateTimeKind.Utc));
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;
            VdrImportResult r = Import(options, W2AccFixture.Gga("120000.00"), W2AccFixture.Gga("115955.00"));
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == "vdr_date_rollover");
            Track pos = r.Tracks.Single(t => t.Kind == TrackKind.Position);
            Assert.All(pos.Samples, s => Assert.True(Math.Abs(s.Time.Seconds - 21600) < 10));
        }

        private static string Ttm(int number, double rangeNm, double bearing, string bearingRef, string name)
        {
            return W2AccFixture.Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "RATTM,{0:00},{1:0.00},{2:0.0},{3},10.0,90.0,T,0.5,10.0,N,{4},T,,061500.00,A",
                number, rangeNm, bearing, bearingRef, name));
        }

        // 裁定 4（端到端）：两路 VDR 的 TTM 目标按目标名配对，目标号不同也能比对。
        [Fact]
        public void TargetRange_FromTwoVdrs_PairedByName_ConflictDetected()
        {
            List<Track> tracks = new List<Track>();
            foreach (var src in new[] { new { Id = W2AccFixture.Mary, No = 1, R = 1.20 }, new { Id = W2AccFixture.Lily, No = 7, R = 1.50 } })
            {
                List<string> lines = new List<string>();
                for (int s = 0; s <= 10; s++)
                {
                    lines.Add("2026-05-18T06:15:" + s.ToString("00", CultureInfo.InvariantCulture) + ".000Z," + Ttm(src.No, src.R, 45.0, "T", "LILY"));
                }

                tracks.AddRange(Import(W2AccFixture.Options(src.Id), lines.ToArray()).Tracks);
            }

            ConflictDetectionResult result = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(tracks));
            TimelineConflict c = Assert.Single(result.Conflicts, x => x.Kind == TrackKind.TargetRange);
            Assert.Equal(0.3, c.MaxDifference, 6);
            Assert.DoesNotContain(result.Conflicts, x => x.Kind == TrackKind.TargetBearing);
        }

        // 相对方位 'R' 且此前没有船首向时，不应把相对方位当真方位静默入库。
        [Fact]
        public void TtmRelativeBearing_WithoutHeading_IsNotStoredAsTrueBearing()
        {
            VdrImportResult r = Import(W2AccFixture.Options(W2AccFixture.Mary), "2026-05-18T06:15:00.000Z," + Ttm(1, 1.2, 30.0, "R", "LILY"));
            Track brg = r.Tracks.FirstOrDefault(t => t.Kind == TrackKind.TargetBearing);
            bool silentlyStored = brg != null && brg.Samples.Any(s => Math.Abs(s.Value - 30.0) < 1e-9) &&
                                  !r.Diagnostics.Any(d => d.LineNumber == 1);
            Assert.False(silentlyStored, "相对方位 30°R 在无船首向时被当作真方位 030° 入库，且无任何诊断。");
        }
    }

    public class RetestTargetAndEventTests
    {
        private static Track Target(string src, TrackKind kind, string name, double start, double end, double value)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += 1.0)
            {
                samples.Add(W2AccFixture.S(t, value, name));
            }

            return new Track(src + "/TTM01/" + kind, src, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        [Theory]
        [InlineData(TrackKind.TargetRange, 1.2, 1.3, false)]
        [InlineData(TrackKind.TargetRange, 1.2, 1.3000015, true)]
        [InlineData(TrackKind.TargetBearing, 359.0, 1.0, false)]
        [InlineData(TrackKind.TargetBearing, 359.0, 1.5, true)]
        public void TargetRangeBearing_AreCompared_WithThresholdAndTolerance(TrackKind kind, double a, double b, bool expect)
        {
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[]
            {
                Target("A", kind, "LILY", 0, 10, a),
                Target("B", kind, "lily", 0, 10, b)
            }));
            Assert.Equal(expect ? 1 : 0, r.Conflicts.Count);
            Assert.DoesNotContain(r.Diagnostics, d => d.Code == ConflictDiagnostic.NotAvailableCode);
        }

        [Fact]
        public void TargetWithoutCounterpart_EmitsNotAvailable_NotSilentlySkipped()
        {
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[]
            {
                Target("A", TrackKind.TargetRange, "LILY", 0, 10, 1.2),
                Target("B", TrackKind.TargetRange, "BRAVO", 0, 10, 5.0)
            }));
            Assert.Empty(r.Conflicts);
            Assert.Equal(2, r.Diagnostics.Count(d => d.Code == ConflictDiagnostic.NotAvailableCode && d.Kind == TrackKind.TargetRange));
        }

        [Fact]
        public void PairedTargets_NoTimeOverlap_EmitsNotAvailable()
        {
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[]
            {
                Target("A", TrackKind.TargetBearing, "LILY", 0, 10, 10.0),
                Target("B", TrackKind.TargetBearing, "LILY", 20, 30, 50.0)
            }));
            Assert.Empty(r.Conflicts);
            Assert.Contains(r.Diagnostics, d => d.Code == ConflictDiagnostic.NotAvailableCode && d.Kind == TrackKind.TargetBearing);
        }

        [Fact]
        public void PairedTargets_NaNValuesInOneSource_EmitsNotAvailable()
        {
            Track a = Target("A", TrackKind.TargetRange, "LILY", 0, 30, 1.2);
            Track b = new Track("B/TTM01/TargetRange", "B", TrackKind.TargetRange, "nm", new[]
            {
                W2AccFixture.S(0, double.NaN, "LILY"), W2AccFixture.S(30, double.NaN, "LILY")
            });
            ConflictDetectionResult r = ConflictDetector.DetectWithDiagnostics(new MultiTrackTimeline(new[] { a, b }));
            Assert.Empty(r.Conflicts);
            Assert.Contains(r.Diagnostics, d => d.Code == ConflictDiagnostic.NotAvailableCode);
        }

        private static Track Events(string src, params Tuple<string, double>[] events)
        {
            string id = src + "/EVT";
            return new Track(id, src, TrackKind.Other, null, new TimelineSample[0],
                events.Select((e, i) => new EventMarker(src + "-E" + i, new SimTime(e.Item2), "event", e.Item1, src, id)));
        }

        // 裁定 5：同名事件跨源时刻差 > 2 s（默认，可配）即冲突。
        [Theory]
        [InlineData(101.9, false)]
        [InlineData(102.0, false)]
        [InlineData(102.0000005, false)]
        [InlineData(102.0000015, true)]
        [InlineData(102.5, true)]
        [InlineData(97.5, true)]
        public void EventTime_DefaultThreshold2s(double tB, bool expect)
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                Events("VDR", Tuple.Create("COLLISION", 100.0)),
                Events("ER-LOG", Tuple.Create("collision", tB))
            });
            IReadOnlyList<TimelineConflict> c = ConflictDetector.Detect(tl);
            Assert.Equal(expect ? 1 : 0, c.Count);
            if (expect)
            {
                Assert.Equal(TrackKind.EventTime, c[0].Kind);
                Assert.Equal(2.0, c[0].Threshold, 9);
                Assert.Equal("s", c[0].Unit);
            }
        }

        [Fact]
        public void EventTime_ThresholdConfigurable_AndAliasPairs()
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                Events("VDR", Tuple.Create("STOP ENGINE", 100.0)),
                Events("ER-LOG", Tuple.Create("车钟停车", 165.0))
            });
            ConflictThresholds t = new ConflictThresholds();
            t.EventAliases["车钟停车"] = "STOP ENGINE";
            TimelineConflict c = Assert.Single(ConflictDetector.Detect(tl, t));
            Assert.Equal(65.0, c.MaxDifference, 9);

            ConflictThresholds wide = new ConflictThresholds { EventTimeSeconds = 70 };
            wide.EventAliases["车钟停车"] = "STOP ENGINE";
            Assert.Empty(ConflictDetector.Detect(tl, wide));
        }

        [Fact]
        public void EventTime_IsJudgedAfterCalibration()
        {
            // ER-LOG 钟快 63 s：校准前差 65 s，校准后差 2 s，不冲突。
            Track gnss = W2AccFixture.Constant("GNSS/SOG", "GNSS", TrackKind.SpeedOverGround, 0, 10, 12.0);
            List<Track> tracks = new List<Track>
            {
                gnss,
                Events("GNSS", Tuple.Create("COLLISION", 100.0)),
                Events("ER-LOG", Tuple.Create("COLLISION", 165.0))
            };
            List<AnchorObservation> anchors = new List<AnchorObservation>
            {
                new AnchorObservation("a1", "GNSS", new SimTime(0)), new AnchorObservation("a1", "ER-LOG", new SimTime(63)),
                new AnchorObservation("a2", "GNSS", new SimTime(50)), new AnchorObservation("a2", "ER-LOG", new SimTime(113))
            };
            IReadOnlyList<ClockOffsetEstimate> est = ClockOffsetEstimator.Estimate(anchors, "GNSS").Value;
            CalibrationResult cal = TimelineCalibrator.Calibrate(tracks, est);
            Assert.Empty(ConflictDetector.Detect(cal.Timeline).Where(c => c.Kind == TrackKind.EventTime));
        }
    }

    public class RetestContractTests
    {
        private static JsonElement Schema()
        {
            DirectoryInfo dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, "contracts", "schemas", "conflict.schema.json")))
            {
                dir = dir.Parent;
            }

            Assert.NotNull(dir);
            string text = File.ReadAllText(Path.Combine(dir.FullName, "contracts", "schemas", "conflict.schema.json"));
            return JsonDocument.Parse(text).RootElement.Clone();
        }

        private static string[] SchemaEnum(string property)
        {
            return Schema().GetProperty("properties").GetProperty(property).GetProperty("enum")
                .EnumerateArray().Select(e => e.GetString()).ToArray();
        }

        [Theory]
        [InlineData("Open")]
        [InlineData("PendingInterview")]
        [InlineData("ClockCorrected")]
        [InlineData("Annotated")]
        [InlineData("Resolved")]
        [InlineData("AcceptedAsIs")]
        public void ConflictStatus_HasEachContractValue(string name)
        {
            Assert.Contains(name, SchemaEnum("status"));
            Assert.Contains(name, Enum.GetNames(typeof(ConflictStatus)));
        }

        [Fact]
        public void ConflictStatus_EnumEqualsContractSet()
        {
            Assert.Equal(
                SchemaEnum("status").OrderBy(x => x, StringComparer.Ordinal),
                Enum.GetNames(typeof(ConflictStatus)).OrderBy(x => x, StringComparer.Ordinal));
        }

        [Fact]
        public void TrackKind_EnumEqualsContractTrackKindSet()
        {
            Assert.Equal(
                SchemaEnum("trackKind").OrderBy(x => x, StringComparer.Ordinal),
                Enum.GetNames(typeof(TrackKind)).OrderBy(x => x, StringComparer.Ordinal));
        }

        [Fact]
        public void StatusText_MatchesPrototypeColumn()
        {
            Assert.Equal("待询问核实", ConflictStatusText.ToChinese(ConflictStatus.PendingInterview));
            Assert.Equal("钟差已校正", ConflictStatusText.ToChinese(ConflictStatus.ClockCorrected));
        }

        private static TimelineConflict OneConflict(string caseId)
        {
            MultiTrackTimeline tl = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 13.0)
            });
            return Assert.Single(ConflictDetector.DetectWithDiagnostics(tl, null, caseId).Conflicts);
        }

        [Fact]
        public void Conflict_DefaultsOpen_CarriesCaseId_AndResolutionIsImmutableCopy()
        {
            TimelineConflict c = OneConflict(W2AccFixture.CaseId);
            Assert.Equal(W2AccFixture.CaseId, c.CaseId);
            Assert.Equal(ConflictStatus.Open, c.Status);
            Assert.Equal("C-01", c.ConflictId);

            DateTimeOffset at = new DateTimeOffset(2026, 11, 11, 12, 0, 0, TimeSpan.Zero);
            TimelineConflict r = c.WithResolution(ConflictStatus.AcceptedAsIs, "待定·采信 AIS", "调查员甲（虚构）", at);
            Assert.Equal(ConflictStatus.AcceptedAsIs, r.Status);
            Assert.Equal("待定·采信 AIS", r.Resolution);
            Assert.Equal(at, r.ResolvedAt);
            Assert.Equal(ConflictStatus.Open, c.Status);
            Assert.Equal(c.ConflictId, r.ConflictId);
            Assert.Equal(W2AccFixture.CaseId, r.CaseId);
        }

        [Theory]
        [InlineData(ConflictStatus.Resolved)]
        [InlineData(ConflictStatus.AcceptedAsIs)]
        public void TerminalStatus_RequiresResolvedByAndAt(ConflictStatus status)
        {
            TimelineConflict c = OneConflict(W2AccFixture.CaseId);
            Assert.Throws<ArgumentException>(() => c.WithResolution(status, "x", null, DateTimeOffset.UtcNow));
            Assert.Throws<ArgumentException>(() => c.WithResolution(status, "x", "甲", null));
        }
    }

    public class RetestManualAnchorCalibrationTests
    {
        private static readonly string[] Header = { "event_key,source_a,time_a_utc,source_b,time_b_utc,note,investigator" };

        [Fact]
        public void ManualAnchor_EnablesCalibration_ForSourceWithoutAutoAnchors()
        {
            // 虚构：CCTV 无自动锚点；调查员人工确认 CCTV 06:15:12 对应 GNSS 06:15:00 → CCTV 钟快 12 s。
            Result<IReadOnlyList<ManualAnchor>> csv = ManualAnchorCsvImporter.Import(new[]
            {
                "\uFEFF" + Header[0],
                "# 虚构演示数据",
                "BOW-LIGHT,CCTV,2026-05-18T14:15:12+08:00,GNSS,2026-05-18T06:15:00Z,船首灯亮起,调查员甲",
                ""
            }, W2AccFixture.Epoch);
            Assert.True(csv.IsSuccess, csv.ErrorMessage);
            ManualAnchor m = Assert.Single(csv.Value);
            Assert.Equal(912.0, m.TimeA.Seconds, 9);
            Assert.Equal(900.0, m.TimeB.Seconds, 9);
            Assert.Equal("调查员甲", m.Investigator);

            List<AnchorObservation> auto = new List<AnchorObservation>
            {
                new AnchorObservation("g1", "GNSS", new SimTime(0)), new AnchorObservation("g1", "VDR", new SimTime(5))
            };
            IReadOnlyList<AnchorObservation> merged = ManualAnchors.Merge(auto, csv.Value);
            Assert.Equal(4, merged.Count);
            Assert.Equal(2, merged.Count(o => o.Origin == AnchorOrigin.Manual));

            IReadOnlyList<ClockOffsetEstimate> est = ClockOffsetEstimator.Estimate(merged, "GNSS").Value;
            ClockOffsetEstimate cctv = est.Single(e => e.SourceId == "CCTV");
            Assert.Equal(12.0, cctv.OffsetSeconds, 9);
            Assert.Equal(1, cctv.ManualAnchorCount);
            Assert.Equal(CalibrationStatus.Calibrated, cctv.Status);

            Track raw = W2AccFixture.ScalarTrack("CCTV/HDG", "CCTV", TrackKind.Heading, W2AccFixture.S(912, 45.0));
            Track orphan = W2AccFixture.ScalarTrack("ECDIS/HDG", "ECDIS", TrackKind.Heading, W2AccFixture.S(912, 45.0));
            Track gnss = W2AccFixture.ScalarTrack("GNSS/HDG", "GNSS", TrackKind.Heading, W2AccFixture.S(900, 45.0));
            CalibrationResult cal = TimelineCalibrator.Calibrate(new[] { raw, orphan, gnss }, est);
            Track shifted = cal.Timeline.Find("CCTV/HDG");
            Assert.Equal(900.0, shifted.Samples[0].Time.Seconds, 9);
            Assert.Equal(CalibrationStatus.Calibrated, shifted.CalibrationStatus);
            Assert.Equal(CalibrationStatus.Reference, cal.Timeline.Find("GNSS/HDG").CalibrationStatus);

            Track kept = cal.Timeline.Find("ECDIS/HDG");
            Assert.Equal(CalibrationStatus.Uncalibrated, kept.CalibrationStatus);
            Assert.Equal(912.0, kept.Samples[0].Time.Seconds, 9);
            Assert.Equal(new[] { "ECDIS" }, cal.UncalibratedSources);
            Assert.False(cal.AllCalibrated);
            SourceCalibration sc = cal.Sources.Single(s => s.SourceId == "ECDIS");
            Assert.Contains("未校准", sc.Description);
            Assert.Contains("人工 1", cal.Sources.Single(s => s.SourceId == "CCTV").Description);
            Assert.Equal("未校准", CalibrationStatusText.ToChinese(CalibrationStatus.Uncalibrated));
        }

        [Fact]
        public void ConflictWithUncalibratedSource_IsMarked()
        {
            Track a = W2AccFixture.Constant("GNSS/SOG", "GNSS", TrackKind.SpeedOverGround, 0, 10, 12.0)
                .WithCalibration(CalibrationStatus.Reference, 0);
            Track b = W2AccFixture.Constant("ECDIS/SOG", "ECDIS", TrackKind.SpeedOverGround, 0, 10, 13.0);
            TimelineConflict c = Assert.Single(ConflictDetector.Detect(new MultiTrackTimeline(new[] { a, b })));
            Assert.True(c.InvolvesUncalibrated);
            // 冲突按 SourceId 序数排 A/B（ECDIS < GNSS），故未校准方为 A。
            Assert.Equal(CalibrationStatus.Uncalibrated, c.SourceA == "ECDIS" ? c.CalibrationStatusA : c.CalibrationStatusB);
            Assert.Contains("未校准", c.Description);
            Assert.Contains("ECDIS", c.Description);
        }

        [Theory]
        [InlineData("event_key,source_a,time_a_utc,source_b", "vdr_manual_anchor_missing_column")]
        [InlineData("", "vdr_manual_anchor_missing_header")]
        public void Csv_MissingHeaderOrColumn_FailsWithCode(string header, string code)
        {
            Result<IReadOnlyList<ManualAnchor>> r = ManualAnchorCsvImporter.Import(new[] { header }, W2AccFixture.Epoch);
            Assert.False(r.IsSuccess);
            Assert.Equal(code, r.ErrorCode);
        }

        [Theory]
        [InlineData("K1,CCTV,不是时间,GNSS,2026-05-18T06:15:00Z,,", "vdr_manual_anchor_bad_time")]
        [InlineData("K1,CCTV,2026-05-18T06:15:00Z,CCTV,2026-05-18T06:15:00Z,,", "vdr_manual_anchor_invalid")]
        [InlineData(",CCTV,2026-05-18T06:15:00Z,GNSS,2026-05-18T06:15:00Z,,", "vdr_manual_anchor_invalid")]
        public void Csv_BadRow_FailsWithCodeAndLine(string row, string code)
        {
            Result<IReadOnlyList<ManualAnchor>> r = ManualAnchorCsvImporter.Import(new[] { Header[0], row }, W2AccFixture.Epoch);
            Assert.False(r.IsSuccess);
            Assert.Equal(code, r.ErrorCode);
            Assert.Contains("第 2 行", r.ErrorMessage);
        }

        [Fact]
        public void Csv_QuotedNoteWithComma_IsKept()
        {
            Result<IReadOnlyList<ManualAnchor>> r = ManualAnchorCsvImporter.Import(new[]
            {
                Header[0],
                "K1,CCTV,2026-05-18T06:15:00Z,GNSS,2026-05-18T06:15:00Z,\"画面左侧,船首灯\",甲"
            }, W2AccFixture.Epoch);
            Assert.True(r.IsSuccess, r.ErrorMessage);
            Assert.Equal("画面左侧,船首灯", r.Value[0].Note);
        }
    }
}
