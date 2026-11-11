using System;
using System.Globalization;
using Mcis.Domain.Common;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// AIS 报文编码工具（支持构造消息类型 1/2/3、18、19、24 Part A/B 的 NMEA !AIVDM 语句，用于测试与样本生成）。
    /// </summary>
    public static class AisMessageEncoder
    {
        private const int RawLonUnavailable = 0x6791AC0;
        private const int RawLatUnavailable = 0x3412140;

        /// <summary>编码 A 类位置报告（类型 1/2/3，168 比特）为单句 !AIVDM。</summary>
        public static string EncodeType1Position(
            uint mmsi,
            double lonDeg,
            double latDeg,
            float sogKn,
            float cogDeg,
            float hdgDeg,
            float rotDegPerMin = 0f,
            byte navStatus = 0,
            byte timestampSec = 0,
            int messageType = 1,
            string channel = "A")
        {
            AisBitBuffer bits = new AisBitBuffer(168);
            bits.SetUInt(0, 6, (uint)messageType);
            bits.SetUInt(6, 2, 0u);
            bits.SetUInt(8, 30, mmsi);
            bits.SetUInt(38, 4, navStatus);
            sbyte rawRot = AisMessageParser.EncodeRotRaw(rotDegPerMin);
            bits.SetInt(42, 8, rawRot);

            uint rawSog = (float.IsNaN(sogKn) || sogKn >= 102.25f || sogKn < 0f)
                ? 1023u
                : (uint)Math.Round(sogKn * 10.0);
            bits.SetUInt(50, 10, rawSog);
            bits.SetUInt(60, 1, 1u);

            int rawLon = (double.IsNaN(lonDeg) || lonDeg < -180.0 || lonDeg > 180.0)
                ? RawLonUnavailable
                : (int)Math.Round(lonDeg * 600000.0);
            int rawLat = (double.IsNaN(latDeg) || latDeg < -90.0 || latDeg > 90.0)
                ? RawLatUnavailable
                : (int)Math.Round(latDeg * 600000.0);
            bits.SetInt(61, 28, rawLon);
            bits.SetInt(89, 27, rawLat);

            uint rawCog = (float.IsNaN(cogDeg) || cogDeg >= 360.0f || cogDeg < 0f)
                ? 3600u
                : (uint)Math.Round(cogDeg * 10.0);
            uint rawHdg = (float.IsNaN(hdgDeg) || hdgDeg >= 360.0f || hdgDeg < 0f)
                ? 511u
                : (uint)Math.Round(hdgDeg);
            bits.SetUInt(116, 12, rawCog);
            bits.SetUInt(128, 9, rawHdg);
            bits.SetUInt(137, 6, timestampSec);
            bits.SetUInt(143, 25, 0u);

            int fillBits;
            string payload = bits.ToArmoredPayload(out fillBits);
            return NmeaSentenceParser.BuildAivdmSentence(payload, fillBits, 1, 1, "", channel);
        }

        /// <summary>编码 B 类扩展位置与静态报告（类型 19，312 比特）为单句 !AIVDM。</summary>
        public static string EncodeType19Extended(
            uint mmsi,
            double lonDeg,
            double latDeg,
            float sogKn,
            float cogDeg,
            float hdgDeg,
            string vesselName,
            uint shipType,
            AntennaOffset dimensions,
            byte timestampSec = 15,
            string channel = "B")
        {
            AisBitBuffer bits = new AisBitBuffer(312);
            bits.SetUInt(0, 6, 19u);
            bits.SetUInt(6, 2, 0u);
            bits.SetUInt(8, 30, mmsi);
            bits.SetUInt(38, 8, 0u);

            uint rawSog = (float.IsNaN(sogKn) || sogKn >= 102.25f || sogKn < 0f)
                ? 1023u
                : (uint)Math.Round(sogKn * 10.0);
            bits.SetUInt(46, 10, rawSog);
            bits.SetUInt(56, 1, 1u);

            int rawLon = (double.IsNaN(lonDeg) || lonDeg < -180.0 || lonDeg > 180.0)
                ? RawLonUnavailable
                : (int)Math.Round(lonDeg * 600000.0);
            int rawLat = (double.IsNaN(latDeg) || latDeg < -90.0 || latDeg > 90.0)
                ? RawLatUnavailable
                : (int)Math.Round(latDeg * 600000.0);
            bits.SetInt(57, 28, rawLon);
            bits.SetInt(85, 27, rawLat);

            uint rawCog = (float.IsNaN(cogDeg) || cogDeg >= 360.0f || cogDeg < 0f)
                ? 3600u
                : (uint)Math.Round(cogDeg * 10.0);
            uint rawHdg = (float.IsNaN(hdgDeg) || hdgDeg >= 360.0f || hdgDeg < 0f)
                ? 511u
                : (uint)Math.Round(hdgDeg);
            bits.SetUInt(112, 12, rawCog);
            bits.SetUInt(124, 9, rawHdg);
            bits.SetUInt(133, 6, timestampSec);
            bits.SetUInt(139, 4, 0u);
            bits.SetString(143, 120, vesselName);
            bits.SetUInt(263, 8, shipType);
            bits.SetUInt(271, 9, (uint)Math.Round(dimensions.ToBowA));
            bits.SetUInt(280, 9, (uint)Math.Round(dimensions.ToSternB));
            bits.SetUInt(289, 6, (uint)Math.Round(dimensions.ToPortC));
            bits.SetUInt(295, 6, (uint)Math.Round(dimensions.ToStarboardD));
            bits.SetUInt(301, 4, 1u);
            bits.SetUInt(305, 7, 0u);

            int fillBits;
            string payload = bits.ToArmoredPayload(out fillBits);
            return NmeaSentenceParser.BuildAivdmSentence(payload, fillBits, 1, 1, "", channel);
        }

        /// <summary>编码 B 类静态数据报告 Part A（类型 24 Part A，160 比特）为单句 !AIVDM。</summary>
        public static string EncodeType24PartA(uint mmsi, string vesselName, string channel = "A")
        {
            AisBitBuffer bits = new AisBitBuffer(160);
            bits.SetUInt(0, 6, 24u);
            bits.SetUInt(6, 2, 0u);
            bits.SetUInt(8, 30, mmsi);
            bits.SetUInt(38, 2, 0u); // Part A = 0
            bits.SetString(40, 120, vesselName);

            int fillBits;
            string payload = bits.ToArmoredPayload(out fillBits);
            return NmeaSentenceParser.BuildAivdmSentence(payload, fillBits, 1, 1, "", channel);
        }

        /// <summary>编码 B 类静态数据报告 Part B（类型 24 Part B，168 比特）为单句 !AIVDM。</summary>
        public static string EncodeType24PartB(
            uint mmsi,
            uint shipType,
            string vendorId,
            string callSign,
            AntennaOffset dimensions,
            string channel = "B")
        {
            AisBitBuffer bits = new AisBitBuffer(168);
            bits.SetUInt(0, 6, 24u);
            bits.SetUInt(6, 2, 0u);
            bits.SetUInt(8, 30, mmsi);
            bits.SetUInt(38, 2, 1u); // Part B = 1
            bits.SetUInt(40, 8, shipType);
            bits.SetString(48, 42, vendorId);
            bits.SetString(90, 42, callSign);
            bits.SetUInt(132, 9, (uint)Math.Round(dimensions.ToBowA));
            bits.SetUInt(141, 9, (uint)Math.Round(dimensions.ToSternB));
            bits.SetUInt(150, 6, (uint)Math.Round(dimensions.ToPortC));
            bits.SetUInt(156, 6, (uint)Math.Round(dimensions.ToStarboardD));
            bits.SetUInt(162, 6, 0u);

            int fillBits;
            string payload = bits.ToArmoredPayload(out fillBits);
            return NmeaSentenceParser.BuildAivdmSentence(payload, fillBits, 1, 1, "", channel);
        }
    }
}
