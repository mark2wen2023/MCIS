using System;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// NMEA 校验和、标签块、时间戳（跨午夜/缺日期）、句型与异常输入验收。
    /// </summary>
    public class NmeaAcceptanceTests
    {
        [Fact]
        public void Checksum_ValidUppercase_IsAccepted()
        {
            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(W2AccFixture.Rmc("061500.00", "180526"), out sentence, out error), error);
            Assert.True(sentence.HasChecksum);
            Assert.True(sentence.ChecksumValid);
            Assert.Equal("GP", sentence.Talker);
            Assert.Equal("RMC", sentence.Type);
        }

        [Fact]
        public void Checksum_ValidLowercase_IsAccepted()
        {
            string line = W2AccFixture.NmeaLower("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            Assert.Contains("*", line);
            Assert.Equal(line, line.Substring(0, line.Length - 2) + line.Substring(line.Length - 2).ToLowerInvariant());

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error), error);
            Assert.True(sentence.HasChecksum);
            Assert.True(sentence.ChecksumValid, "NMEA 校验和十六进制大小写均应有效，实际 ChecksumValid=false。");
        }

        [Fact]
        public void Checksum_WrongValue_ParsesButMarkedInvalid()
        {
            string good = W2AccFixture.Rmc("061500.00", "180526");
            string bad = good.Substring(0, good.Length - 2) + "00";
            if (good.EndsWith("00", StringComparison.Ordinal))
            {
                bad = good.Substring(0, good.Length - 2) + "FF";
            }

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(bad, out sentence, out error), error);
            Assert.True(sentence.HasChecksum);
            Assert.False(sentence.ChecksumValid);
        }

        [Fact]
        public void Checksum_Missing_IsNotValid()
        {
            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse("$GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A", out sentence, out error), error);
            Assert.False(sentence.HasChecksum);
            Assert.False(sentence.ChecksumValid);
        }

        [Fact]
        public void TagBlock_ValidChecksum_YieldsUnixTime()
        {
            const long unix = 1779084900L;
            string line = W2AccFixture.TagBlock("c:" + unix) + W2AccFixture.Rmc("061500.00", "180526");

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error), error);
            Assert.True(sentence.TagBlockTimeUtc.HasValue, "合法标签块应解析出时间。");
            Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(unix), sentence.TagBlockTimeUtc.Value);
            Assert.True(sentence.ChecksumValid);
        }

        [Fact]
        public void TagBlock_InvalidChecksum_MustNotYieldTime()
        {
            // 标签块自身校验错误时，不得采用其中的 unix 时间。
            string line = "\\c:1779084900*00\\" + W2AccFixture.Rmc("061500.00", "180526");
            int actualTagCs = W2AccFixture.XorChecksum("c:1779084900");
            Assert.NotEqual(0, actualTagCs);

            NmeaSentence sentence;
            string error;
            Exception thrown = Record.Exception(() => NmeaParser.TryParse(line, out sentence, out error));
            Assert.Null(thrown);
            Assert.True(NmeaParser.TryParse(line, out sentence, out error), error);
            Assert.False(
                sentence.TagBlockTimeUtc.HasValue,
                "标签块校验和错误时不应采信 TagBlockTimeUtc，实际=" + sentence.TagBlockTimeUtc);
        }

        [Fact]
        public void TagBlock_MissingChecksum_MustNotYieldTime()
        {
            string line = "\\c:1779084900\\" + W2AccFixture.Rmc("061500.00", "180526");

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error), error);
            Assert.False(
                sentence.TagBlockTimeUtc.HasValue,
                "标签块缺少自身校验和时不应采信 TagBlockTimeUtc，实际=" + sentence.TagBlockTimeUtc);
        }

        [Theory]
        [InlineData("$GPR")]
        [InlineData("$GPRM")]
        [InlineData("$AI")]
        [InlineData("!AIV")]
        [InlineData("!AIVD")]
        public void TruncatedAddress_DoesNotThrow_AndReturnsFalse(string line)
        {
            NmeaSentence sentence;
            string error = null;
            Exception thrown = Record.Exception(() => NmeaParser.TryParse(line, out sentence, out error));
            Assert.Null(thrown);
            Assert.False(
                NmeaParser.TryParse(line, out sentence, out error),
                "截断地址应返回 false 而非抛异常；error=" + error);
            Assert.False(string.IsNullOrEmpty(error));
        }

        [Fact]
        public void Importer_TruncatedAddressInFile_DoesNotAbortImport()
        {
            string[] lines =
            {
                "2026-05-18T06:15:00.000Z," + W2AccFixture.Rmc("061500.00", "180526", 12.0, 45.0),
                "$GPR",
                "2026-05-18T06:15:20.000Z," + W2AccFixture.Rmc("061520.00", "180526", 12.0, 45.0)
            };

            Exception thrown = Record.Exception(() =>
            {
                Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, W2AccFixture.Options(W2AccFixture.Mary));
                Assert.True(result.IsSuccess, "含截断行的文件不应导致整次导入失败：" + result.ErrorMessage);
                Assert.NotEmpty(result.Value.Tracks);
                Track sog = result.Value.Tracks.FirstOrDefault(t => t.Kind == TrackKind.SpeedOverGround);
                Assert.NotNull(sog);
                Assert.Equal(2, sog.Samples.Count);
            });
            Assert.Null(thrown);
        }

        [Fact]
        public void GgaAfterMidnight_RollsDateForward()
        {
            // RMC 23:59:50（日期 18 日）之后的 GGA 00:00:10 应落在 19 日，而不是仍用 18 日。
            VdrImportOptions options = W2AccFixture.Options(W2AccFixture.Mary);
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;

            string[] lines =
            {
                W2AccFixture.Rmc("235950.00", "180526", 12.0, 45.0),
                W2AccFixture.Gga("000010.00", 1)
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, options);
            Assert.True(result.IsSuccess, result.ErrorMessage);

            Track position = result.Value.Tracks.FirstOrDefault(t => t.Kind == TrackKind.Position);
            Assert.NotNull(position);
            Assert.True(position.Samples.Count >= 2, "应同时导入跨午夜前后的位置点，实际点数=" + position.Samples.Count);

            DateTimeOffset expectedGga = new DateTimeOffset(2026, 5, 19, 0, 0, 10, TimeSpan.Zero);
            DateTimeOffset sameDayWrong = new DateTimeOffset(2026, 5, 18, 0, 0, 10, TimeSpan.Zero);
            double expectedSec = SimTime.FromUtc(expectedGga, options.CaseEpochUtc).Seconds;
            double wrongSec = SimTime.FromUtc(sameDayWrong, options.CaseEpochUtc).Seconds;
            string actualTimes = string.Join(", ", position.Samples.Select(s => s.Time.Seconds.ToString("F3")));
            Assert.True(
                position.Samples.Any(s => Math.Abs(s.Time.Seconds - expectedSec) < 0.5),
                "跨午夜 GGA 应记为 2026-05-19 00:00:10 UTC（相对纪元 " + expectedSec.ToString("F3") +
                " s），实际样本时刻=[" + actualTimes + "]。");
            Assert.DoesNotContain(position.Samples, s => Math.Abs(s.Time.Seconds - wrongSec) < 0.5);
        }

        [Fact]
        public void RmcWithNewDateAfterMidnight_UsesSentenceDate()
        {
            VdrImportOptions options = W2AccFixture.Options(W2AccFixture.Mary);
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;

            string[] lines =
            {
                W2AccFixture.Rmc("235950.00", "180526", 12.0, 45.0),
                W2AccFixture.Rmc("000010.00", "190526", 11.0, 46.0)
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, options);
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Track sog = result.Value.Tracks.First(t => t.Kind == TrackKind.SpeedOverGround);
            DateTimeOffset expected = new DateTimeOffset(2026, 5, 19, 0, 0, 10, TimeSpan.Zero);
            double expectedSec = SimTime.FromUtc(expected, options.CaseEpochUtc).Seconds;
            Assert.Equal(expectedSec, sog.Samples[sog.Samples.Count - 1].Time.Seconds, 3);
            Assert.Equal(11.0, sog.Samples[sog.Samples.Count - 1].Value, 9);
        }

        [Fact]
        public void GgaWithoutDateOrDefault_WritesDiagnosticAndDrops()
        {
            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { W2AccFixture.Gga("061600.00", 1) },
                W2AccFixture.Options(W2AccFixture.Mary));

            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Empty(result.Value.Tracks.Where(t => t.Kind == TrackKind.Position && t.Samples.Count > 0));
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_no_time");
        }

        [Fact]
        public void EmptyFields_DoNotThrow_AndSkipIncompleteSamples()
        {
            string line = W2AccFixture.Nmea("GPRMC,061500.00,A,,,,,180526,,,A");
            VdrImportOptions options = W2AccFixture.Options(W2AccFixture.Mary);
            options.TimeBasis = VdrTimeBasis.GnssSentenceTime;

            Exception thrown = Record.Exception(() =>
            {
                Result<VdrImportResult> result = VdrNmeaImporter.Import(new[] { line }, options);
                Assert.True(result.IsSuccess, result.ErrorMessage);
            });
            Assert.Null(thrown);
        }

        [Fact]
        public void IllegalNumericCharacters_DoNotThrow_AndAreIgnored()
        {
            string line = W2AccFixture.Nmea("GPHDT,abc,T");
            string prefixed = "2026-05-18T06:15:00.000Z," + line;

            Exception thrown = Record.Exception(() =>
            {
                Result<VdrImportResult> result = VdrNmeaImporter.Import(
                    new[] { prefixed },
                    W2AccFixture.Options(W2AccFixture.Mary));
                Assert.True(result.IsSuccess, result.ErrorMessage);
                Assert.DoesNotContain(result.Value.Tracks, t => t.Kind == TrackKind.Heading && t.Samples.Count > 0);
            });
            Assert.Null(thrown);
        }

        [Fact]
        public void OverlongLine_DoesNotThrow()
        {
            string padding = new string('0', 8000);
            string line = W2AccFixture.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526," + padding + ",,A");

            NmeaSentence sentence;
            string error = null;
            Exception thrown = Record.Exception(() => NmeaParser.TryParse(line, out sentence, out error));
            Assert.Null(thrown);
        }

        [Fact]
        public void UnknownSentenceType_IsReportedOnce()
        {
            string[] lines =
            {
                "2026-05-18T06:15:00.000Z," + W2AccFixture.Nmea("GPGLL,3006.0000,N,12203.6000,E,061500.00,A,A"),
                "2026-05-18T06:15:01.000Z," + W2AccFixture.Nmea("GPGLL,3006.0000,N,12203.6000,E,061501.00,A,A"),
                "2026-05-18T06:15:02.000Z," + W2AccFixture.Rmc("061502.00", "180526")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Single(result.Value.Diagnostics.Where(d => d.Code == "vdr_unsupported"));
            Assert.NotEmpty(result.Value.Tracks);
        }

        [Fact]
        public void SupportedSentenceTypes_CanBeImported()
        {
            string prefix = "2026-05-18T06:15:00.000Z,";
            string[] lines =
            {
                prefix + W2AccFixture.Rmc("061500.00", "180526", 12.0, 45.0),
                prefix + W2AccFixture.Gga("061500.00", 1),
                prefix + W2AccFixture.Nmea("GPVTG,45.0,T,,M,12.0,N,22.2,K,A"),
                prefix + W2AccFixture.Nmea("HEHDT,46.0,T"),
                prefix + W2AccFixture.Nmea("GPROT,1.5,A"),
                prefix + W2AccFixture.Nmea("IIRSA,5.0,A,,V"),
                prefix + W2AccFixture.Nmea("RATTM,1,1.20,90.0,T,0.0,0.0,0.0,0.0,N,LILY,Q,,061500.00,A"),
                prefix + W2AccFixture.Nmea("RATLL,1,3006.1000,N,12203.7000,E,LILY,061500.00,T,"),
                prefix + W2AccFixture.Nmea("GPZDA,061500.00,18,05,2026,00,00")
            };

            Result<VdrImportResult> result = VdrNmeaImporter.Import(lines, W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.Position && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.SpeedOverGround && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.CourseOverGround && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.Heading && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.RateOfTurn && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.RudderAngle && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.TargetRange && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.TargetBearing && t.Samples.Count > 0);
            Assert.Contains(result.Value.Tracks, t => t.Kind == TrackKind.TargetPosition && t.Samples.Count > 0);
        }

        [Fact]
        public void Importer_DropsBadAndMissingChecksum_ByDefault()
        {
            string good = "2026-05-18T06:15:00.000Z," + W2AccFixture.Rmc("061500.00", "180526", 12.0, 40.0);
            string missing = "2026-05-18T06:15:10.000Z,$GPRMC,061510.00,A,3006.0000,N,12203.6000,E,99.0,40.0,180526,,,A";
            string valid = W2AccFixture.Rmc("061520.00", "180526", 13.0, 40.0);
            string bad = "2026-05-18T06:15:20.000Z," + valid.Substring(0, valid.Length - 2) + "FF";

            Result<VdrImportResult> result = VdrNmeaImporter.Import(
                new[] { good, missing, bad },
                W2AccFixture.Options(W2AccFixture.Mary));
            Assert.True(result.IsSuccess, result.ErrorMessage);
            Track sog = result.Value.Tracks.FirstOrDefault(t => t.Kind == TrackKind.SpeedOverGround);
            Assert.NotNull(sog);
            Assert.Single(sog.Samples);
            Assert.Equal(12.0, sog.Samples[0].Value, 9);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_bad_checksum");
        }

        [Theory]
        [InlineData("")]
        [InlineData("no dollar sign")]
        [InlineData("$GP")]
        public void CompletelyMalformed_ReturnsFalse(string line)
        {
            NmeaSentence sentence;
            string error;
            Assert.False(NmeaParser.TryParse(line, out sentence, out error));
            Assert.False(string.IsNullOrEmpty(error));
        }
    }
}
