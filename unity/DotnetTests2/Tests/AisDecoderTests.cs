using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Ais;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class AisDecoderTests
    {
        [Fact]
        public void Decode_Type1_Sample1_DecodesExpectedFields()
        {
            // 公认 GPSD AIVDM 样例 1（类型 1，MMSI 366053209）
            const string raw = "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*5C";
            AisDecoder decoder = new AisDecoder();

            byte expectedXor, actualXor;
            Assert.True(decoder.ValidateNmeaChecksum(raw, out expectedXor, out actualXor));
            Assert.Equal(0x5C, expectedXor);

            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(raw);
            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.True(res.Value.RecordsByMmsi.ContainsKey("366053209"));

            AisDecodedRecord rec = res.Value.RecordsByMmsi["366053209"][0];
            Assert.Equal(1, rec.MessageType);
            Assert.Equal("366053209", rec.Mmsi);
            // 载荷 C000 对应 NavStatus=3（操纵受限），RawRot=0（0°/min）
            Assert.Equal((byte)3, rec.NavStatus);
            Assert.Equal((sbyte)0, rec.RawRot);
            Assert.Equal(0.0f, rec.RotDegPerMin, 3);
            Assert.Equal(0.0f, rec.SogKn, 3);
            Assert.True(rec.IsPositionValid);
            Assert.InRange(rec.LonDeg, -123.0, -121.0);
            Assert.InRange(rec.LatDeg, 37.0, 38.5);
            Assert.Equal(1.0f, rec.HdgDeg, 3);
            Assert.True(rec.IsHdgValid);
        }

        [Fact]
        public void Decode_Type1_Sample2_DecodesExpectedFields()
        {
            // 公认 AIVDM 样例 2（类型 1，MMSI 244670316）
            const string raw = "!AIVDM,1,1,,A,13aEOK?P00PD2wVMdLDRhgvL289?,0*26";
            AisDecoder decoder = new AisDecoder();

            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(raw);
            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.True(res.Value.RecordsByMmsi.ContainsKey("244670316"));

            AisDecodedRecord rec = res.Value.RecordsByMmsi["244670316"][0];
            Assert.Equal(1, rec.MessageType);
            Assert.Equal("244670316", rec.Mmsi);
            Assert.True(rec.IsPositionValid);
            Assert.InRange(rec.LonDeg, 4.0, 5.0);
            Assert.InRange(rec.LatDeg, 51.0, 52.5);
            Assert.True(rec.IsSogValid);
            Assert.True(rec.IsCogValid);
        }

        [Fact]
        public void Decode_Type5_MultiSentence_ReassemblesAndExtractsStaticParticulars()
        {
            // 公认 GPSD 类型 5 两句样例（EVER DIADEM, MMSI 351759000, IMO 9134270, CallSign 3FOF8）
            string nmea =
                "!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C\n" +
                "!AIVDM,2,2,1,A,88888888880,2*25";

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(nmea);

            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.True(res.Value.DiscoveredStaticParticulars.ContainsKey("351759000"));

            VesselParticulars vp = res.Value.DiscoveredStaticParticulars["351759000"];
            Assert.Equal("351759000", vp.Mmsi);
            Assert.Equal("9134270", vp.ImoNumber);
            Assert.Equal("3FOF8", vp.CallSign);
            Assert.Equal("EVER DIADEM", vp.Name);
            Assert.Equal(70, vp.ShipTypeCodeNumber);
            Assert.Equal(225f, vp.AntennaOffset.ToBowA);
            Assert.Equal(70f, vp.AntennaOffset.ToSternB);
            Assert.Equal(1f, vp.AntennaOffset.ToPortC);
            Assert.Equal(31f, vp.AntennaOffset.ToStarboardD);
            Assert.Equal(295f, vp.LoaM);
            Assert.Equal(32f, vp.BeamM);
            Assert.Equal(12.2f, vp.DraftForeM, 2);
            Assert.Equal("NEW YORK", vp.Destination);
        }

        [Fact]
        public void Decode_Type18_And_Type24PartA_Samples()
        {
            // 注：P1_TASK_A.md 中类型 18 样例 "!AIVDM,1,1,,B,B52K>;h00Fc>jpUlNV@ikwpUoP06,0*4C"
            // 源自 GPSD AIVDM 文档，原句信道为 A 时异或校验和为 *4C（'A'=0x41），改为信道 B（'B'=0x42）后
            // 真实异或校验和为 0x4C ^ 0x03 = 0x4F (*4F)。
            // 此处同时验证：原样 *4C 在信道 B 下触发 ChecksumError，以及修正信道 A(*4C)/信道 B(*4F) 与类型 24 正常解码。
            AisDecoder decoder = new AisDecoder();

            byte exp18, act18;
            Assert.False(decoder.ValidateNmeaChecksum("!AIVDM,1,1,,B,B52K>;h00Fc>jpUlNV@ikwpUoP06,0*4C", out exp18, out act18));
            Assert.Equal(0x4C, exp18);
            Assert.Equal(0x4F, act18);

            string nmea =
                "!AIVDM,1,1,,A,B52K>;h00Fc>jpUlNV@ikwpUoP06,0*4C\n" +
                "!AIVDM,1,1,,A,H42O55i18tMET00000000000000,2*6D";

            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(nmea);

            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.True(res.Value.RecordsByMmsi.ContainsKey("338087471"));
            AisDecodedRecord r18 = res.Value.RecordsByMmsi["338087471"][0];
            Assert.Equal(18, r18.MessageType);
            Assert.True(r18.IsPositionValid);
            Assert.Equal(-74.07213, r18.LonDeg, 4);
            Assert.InRange(r18.LatDeg, 40.0, 41.5);

            Assert.True(res.Value.DiscoveredStaticParticulars.ContainsKey("271041815"));
            VesselParticulars vp24 = res.Value.DiscoveredStaticParticulars["271041815"];
            Assert.Equal("PROGUY", vp24.Name);
        }

        [Fact]
        public void EncodeAndDecode_Type19_And_Type24PartB_RoundTrip()
        {
            AntennaOffset dims19 = new AntennaOffset(45f, 15f, 5f, 7f);
            string sentence19 = AisMessageEncoder.EncodeType19Extended(
                413123456u, 113.7525, 22.345, 12.4f, 185.6f, 184f, "ZHAOQING EXPRESS", 60u, dims19, 28, "B");

            AntennaOffset dims24 = new AntennaOffset(18f, 6f, 3f, 3f);
            string sentence24A = AisMessageEncoder.EncodeType24PartA(271041815u, "PROGUY", "A");
            string sentence24B = AisMessageEncoder.EncodeType24PartB(271041815u, 37u, "VEND01", "TC1234", dims24, "B");

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(
                sentence19 + "\n" + sentence24A + "\n" + sentence24B);

            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);

            // 验证类型 19 位置与静态扩展往返一致
            AisDecodedRecord rec19 = res.Value.RecordsByMmsi["413123456"][0];
            Assert.Equal(19, rec19.MessageType);
            Assert.Equal(113.7525, rec19.LonDeg, 5);
            Assert.Equal(22.3450, rec19.LatDeg, 5);
            Assert.Equal(12.4f, rec19.SogKn, 2);
            Assert.Equal(185.6f, rec19.CogDeg, 2);
            Assert.Equal(184.0f, rec19.HdgDeg, 2);

            VesselParticulars vp19 = res.Value.DiscoveredStaticParticulars["413123456"];
            Assert.Equal("ZHAOQING EXPRESS", vp19.Name);
            Assert.Equal(60, vp19.ShipTypeCodeNumber);
            Assert.Equal(60f, vp19.LoaM);
            Assert.Equal(12f, vp19.BeamM);

            // 验证类型 24 Part A + Part B 合并结果
            VesselParticulars vp24 = res.Value.DiscoveredStaticParticulars["271041815"];
            Assert.Equal("PROGUY", vp24.Name);
            Assert.Equal("TC1234", vp24.CallSign);
            Assert.Equal(37, vp24.ShipTypeCodeNumber);
            Assert.Equal(24f, vp24.LoaM);
            Assert.Equal(6f, vp24.BeamM);
        }

        [Fact]
        public void Decode_UnavailableValues_ChecksumErrors_And_TagBlockTimeout()
        {
            // 构造全部不可用值（Lon=181, Lat=91, SOG=1023, COG=3600, HDG=511, ROT=NaN）
            string unavailSentence = AisMessageEncoder.EncodeType1Position(
                412000111u, 181.0, 91.0, 102.3f, 360.0f, 511.0f, float.NaN, 15, 60);

            // 篡改校验和使其错误
            string badChecksum = "!AIVDM,1,1,,B,15M67FC000G?ufbE`FepT@3n00Sa,0*FF";

            // 带 Tag Block 时间戳且超时的残缺多句
            string timedOutFrag1 = "\\s:st1,c:1700000000*00\\!AIVDM,2,1,9,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*14";
            string validTagged = "\\s:st1,c:1700000010*00\\" + unavailSentence;

            AisDecoder decoder = new AisDecoder(5.0);
            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(
                badChecksum + "\n" + timedOutFrag1 + "\n" + validTagged);

            Assert.True(res.IsSuccess);
            Assert.Equal(2, res.Value.ChecksumOrSyntaxErrors.Count);
            Assert.Equal(RejectReason.ChecksumError, res.Value.ChecksumOrSyntaxErrors[0].Reason);
            Assert.Equal(RejectReason.OutOfOrder, res.Value.ChecksumOrSyntaxErrors[1].Reason);

            AisDecodedRecord rec = res.Value.RecordsByMmsi["412000111"][0];
            Assert.Equal(181.0, rec.LonDeg, 5);
            Assert.Equal(91.0, rec.LatDeg, 5);
            Assert.False(rec.IsPositionValid);
            Assert.Equal(102.3f, rec.SogKn, 2);
            Assert.False(rec.IsSogValid);
            Assert.Equal(360.0f, rec.CogDeg, 2);
            Assert.False(rec.IsCogValid);
            Assert.Equal(511.0f, rec.HdgDeg, 2);
            Assert.False(rec.IsHdgValid);
            Assert.Equal(TimeQuality.ExactTagBlock, rec.TimeQuality);
            Assert.Equal(DateTimeOffset.FromUnixTimeSeconds(1700000010L), rec.TimestampUtc);
        }

        [Fact]
        public void Decode_Type2_Type3_RotFormula_And_OutOfOrderFragments()
        {
            // 测试类型 2/3、转向率 ROT 公式 (ROT_AIS = 4.733 * sqrt(ROT_deg_min)) 与多句乱序到达重组
            string type2 = AisMessageEncoder.EncodeType1Position(
                413555666u, -122.4194, 37.7749, 14.2f, 275.3f, 274.0f, -9.0f, 0, 32, 2, "A");
            string type3 = AisMessageEncoder.EncodeType1Position(
                413555777u, 114.1694, 22.3193, 8.5f, 45.0f, 46.0f, 16.0f, 5, 12, 3, "B");

            // 片段 2 先于片段 1 到达（同信道 A、同 seqId 1）
            string outOfOrderType5 =
                "!AIVDM,2,2,1,A,88888888880,2*25\n" +
                "!AIVDM,2,1,1,A,55?MbV02;H;s<HtKR20EHE:0@T4@Dn2222222216L961O5Gf0NSQEp6ClRp8,0*1C";

            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> res = decoder.DecodeNmeaText(
                type2 + "\n" + type3 + "\n" + outOfOrderType5);

            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);

            AisDecodedRecord r2 = res.Value.RecordsByMmsi["413555666"][0];
            Assert.Equal(2, r2.MessageType);
            Assert.InRange(r2.RotDegPerMin, -9.5f, -8.5f);

            AisDecodedRecord r3 = res.Value.RecordsByMmsi["413555777"][0];
            Assert.Equal(3, r3.MessageType);
            Assert.InRange(r3.RotDegPerMin, 15.2f, 16.8f);

            Assert.Equal("EVER DIADEM", res.Value.DiscoveredStaticParticulars["351759000"].Name);
        }
    }
}
