using System;
using Mcis.Core;
using Mcis.Domain.Ais;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class AisCsvTests
    {
        [Fact]
        public void DecodeCsv_DefaultProfile_ParsesMultipleUtcFormats()
        {
            string csv =
                "MMSI,BaseDateTime,LAT,LON,SOG,COG,Heading,VesselName\n" +
                "413000001,2026-05-18T02:30:00Z,23.046500,112.459800,11.5,092.4,91,LILY\n" +
                "413000001,2026-05-18 02:30:10,23.046520,112.460400,11.6,093.0,,\"LILY\"\n" +
                "413000002,2026/05/18 02:30:00,23.050100,112.470200,9.8,271.5,270,MARY\n";

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> res = decoder.DecodeCsvText(csv);

            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.Equal(3, res.Value.TotalLinesProcessed);

            Assert.Equal(2, res.Value.RecordsByMmsi["413000001"].Count);
            AisDecodedRecord r0 = res.Value.RecordsByMmsi["413000001"][0];
            Assert.Equal(new DateTimeOffset(2026, 5, 18, 2, 30, 0, TimeSpan.Zero), r0.TimestampUtc);
            Assert.Equal(23.0465, r0.LatDeg, 6);
            Assert.Equal(112.4598, r0.LonDeg, 6);
            Assert.Equal(11.5f, r0.SogKn, 2);
            Assert.Equal(92.4f, r0.CogDeg, 2);
            Assert.Equal(91.0f, r0.HdgDeg, 2);

            // 第二行 Heading 为空，应记为不可用值 511
            AisDecodedRecord r1 = res.Value.RecordsByMmsi["413000001"][1];
            Assert.Equal(511.0f, r1.HdgDeg, 2);
            Assert.False(r1.IsHdgValid);

            Assert.Equal("LILY", res.Value.DiscoveredStaticParticulars["413000001"].Name);
            Assert.Equal("MARY", res.Value.DiscoveredStaticParticulars["413000002"].Name);
        }

        [Fact]
        public void DecodeCsv_CustomColumnMapping_TimezoneAndSpeedUnitConversion()
        {
            // 自定义中文/平台导出表头：北京时间 (UTC+8, +480 分钟)，速度单位为 m/s
            CsvMappingProfile customProfile = new CsvMappingProfile(
                "DomesticPlatformUtc8",
                "ship_mmsi",
                "pos_time_bj",
                "yyyy-MM-dd HH:mm:ss",
                480,
                "lng_deg",
                "lat_deg",
                "speed_mps",
                "course_deg",
                "true_hdg",
                "ship_name",
                "mps");

            // 1852 / 3600 m/s = 1.0 kn，故 5.144444 m/s ≈ 10.0 kn
            string csv =
                "ship_mmsi,pos_time_bj,lat_deg,lng_deg,speed_mps,course_deg,true_hdg,ship_name\n" +
                "413888999,2026-05-18 10:30:00,22.123456,113.654321,5.144444,180.5,180,ZHUJIANG 01\n" +
                "bad_row_without_coords,invalid_time,abc,def,0,0,0,BROKEN\n";

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> res = decoder.DecodeCsvText(csv, customProfile, clockOffsetSeconds: 2.0);

            Assert.True(res.IsSuccess);
            Assert.Single(res.Value.ChecksumOrSyntaxErrors);
            Assert.Equal(RejectReason.InvalidField, res.Value.ChecksumOrSyntaxErrors[0].Reason);

            AisDecodedRecord rec = res.Value.RecordsByMmsi["413888999"][0];
            // 北京时间 10:30:00 换算为 UTC 02:30:00，再加 clockOffsetSeconds 2s = 02:30:02 UTC
            Assert.Equal(new DateTimeOffset(2026, 5, 18, 2, 30, 2, TimeSpan.Zero), rec.TimestampUtc);
            Assert.Equal(22.123456, rec.LatDeg, 6);
            Assert.Equal(113.654321, rec.LonDeg, 6);
            Assert.Equal(10.0f, rec.SogKn, 2);
            Assert.Equal(180.5f, rec.CogDeg, 2);
            Assert.Equal(180.0f, rec.HdgDeg, 2);
            Assert.Equal("ZHUJIANG 01", res.Value.DiscoveredStaticParticulars["413888999"].Name);
        }

        [Fact]
        public void DecodeCsv_KmhUnit_UnixEpoch_And_MissingHeaderFails()
        {
            CsvMappingProfile kmhProfile = new CsvMappingProfile(
                "KmhUnix", "MMSI", "EpochSec", null, 0, "Lon", "Lat", "SpeedKmh", "Course", "Hdg", "Name", "kmh");

            // 18.52 km/h = 10.0 kn
            string csv =
                "MMSI,EpochSec,Lat,Lon,SpeedKmh,Course,Hdg,Name\n" +
                "413777000,1700000000,22.500000,113.500000,18.52,045.0,45,TEST SHIP\n";

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> okRes = decoder.DecodeCsvText(csv, kmhProfile);
            Assert.True(okRes.IsSuccess);
            AisDecodedRecord rec = okRes.Value.RecordsByMmsi["413777000"][0];
            Assert.Equal(10.0f, rec.SogKn, 2);
            Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(1700000000L), rec.TimestampUtc);

            Result<AisImportBatchResult> failRes = decoder.DecodeCsvText("ColA,ColB\n1,2\n");
            Assert.False(failRes.IsSuccess);
        }
    }
}
