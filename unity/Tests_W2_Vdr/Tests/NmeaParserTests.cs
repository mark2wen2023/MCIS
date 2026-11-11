using System;
using Mcis.Data.Vdr;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class NmeaParserTests
    {
        [Fact]
        public void Checksum_ValidSentence_IsValid()
        {
            string line = TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.True(sentence.HasChecksum);
            Assert.True(sentence.ChecksumValid);
            Assert.Equal("GP", sentence.Talker);
            Assert.Equal("RMC", sentence.Type);
            Assert.Equal("061500.00", sentence.Fields[0]);
            Assert.Equal("45.0", sentence.Fields[7]);
        }

        [Fact]
        public void Checksum_InvalidSentence_ParsesButMarksInvalid()
        {
            string valid = TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string body = valid.Substring(0, valid.Length - 2);
            int original = Convert.ToInt32(valid.Substring(valid.Length - 2), 16);
            string line = body + ((original + 1) % 256).ToString("X2");

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.True(sentence.HasChecksum);
            Assert.False(sentence.ChecksumValid);
        }

        [Fact]
        public void Checksum_MissingChecksum_IsNotValid()
        {
            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse("$GPRMC,061500.00,A,,,,,", out sentence, out error));
            Assert.False(sentence.HasChecksum);
            Assert.False(sentence.ChecksumValid);
        }

        [Fact]
        public void LogPrefix_CommaSeparated_ParsesUtc()
        {
            string sentenceLine = TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string line = "2026-05-18T06:15:03.200Z," + sentenceLine;

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.True(sentence.LogTimestampUtc.HasValue);
            Assert.Equal(new DateTimeOffset(2026, 5, 18, 6, 15, 3, 200, TimeSpan.Zero), sentence.LogTimestampUtc.Value);
        }

        [Fact]
        public void LogPrefix_SpaceSeparatedAndOffset_ConvertsToUtc()
        {
            string sentenceLine = TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string line = "2026-05-18T14:15:03.200+08:00 " + sentenceLine;

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.True(sentence.LogTimestampUtc.HasValue);
            Assert.Equal(new DateTimeOffset(2026, 5, 18, 6, 15, 3, 200, TimeSpan.Zero), sentence.LogTimestampUtc.Value);
        }

        [Fact]
        public void TagBlock_ParsesUnixSeconds()
        {
            string sentenceLine = TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            // 标签块须带正确的自身校验和（W2-D03）；旧测试用 *00 占位，现改为真实校验。
            string line = TestHelpers.TagBlock("c:1779084900") + sentenceLine;

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.True(sentence.TagBlockTimeUtc.HasValue);
            Assert.Equal(
                DateTimeOffset.FromUnixTimeSeconds(1779084900),
                sentence.TagBlockTimeUtc.Value);
            Assert.Equal("RMC", sentence.Type);
        }

        [Fact]
        public void AisBangSentence_ParsesAsVdm()
        {
            string line = TestHelpers.Nmea("AIVDM,1,1,,A,15N:;R0P00PD;88MD5MTDww@2D0l,0");

            NmeaSentence sentence;
            string error;
            Assert.True(NmeaParser.TryParse(line, out sentence, out error));
            Assert.Equal("AI", sentence.Talker);
            Assert.Equal("VDM", sentence.Type);
        }

        [Theory]
        [InlineData("2606.2742", "S", true, -26.10457)]
        [InlineData("2606.2742", "N", true, 26.10457)]
        [InlineData("01131.0000", "W", false, -11.5166667)]
        [InlineData("01131.0000", "E", false, 11.5166667)]
        public void LatLon_ParsesHemispheres(string value, string hemi, bool isLat, double expected)
        {
            double actual;
            Assert.True(NmeaParser.TryParseLatLon(value, hemi, isLat, out actual));
            Assert.Equal(expected, actual, 5);
        }

        [Theory]
        [InlineData("2606.2742", "X", true)]
        [InlineData("2606.2742", "", true)]
        [InlineData("abcd", "N", true)]
        [InlineData("", "N", true)]
        public void LatLon_InvalidInput_ReturnsFalse(string value, string hemi, bool isLat)
        {
            double actual;
            Assert.False(NmeaParser.TryParseLatLon(value, hemi, isLat, out actual));
        }

        [Fact]
        public void UtcTime_ParsesWithFraction()
        {
            TimeSpan time;
            Assert.True(NmeaParser.TryParseUtcTime("061530.500", out time));
            Assert.Equal(6, time.Hours);
            Assert.Equal(15, time.Minutes);
            Assert.Equal(30.5, time.TotalSeconds - 6 * 3600 - 15 * 60, 6);
        }

        [Theory]
        [InlineData("")]
        [InlineData("12")]
        [InlineData("256000")]
        [InlineData("126099")]
        public void UtcTime_Invalid_ReturnsFalse(string value)
        {
            TimeSpan time;
            Assert.False(NmeaParser.TryParseUtcTime(value, out time));
        }

        [Theory]
        [InlineData("")]
        [InlineData("no dollar sign")]
        [InlineData("$GP")]
        public void Malformed_ReturnsFalse(string line)
        {
            NmeaSentence sentence;
            string error;
            Assert.False(NmeaParser.TryParse(line, out sentence, out error));
            Assert.False(string.IsNullOrEmpty(error));
        }
    }
}
