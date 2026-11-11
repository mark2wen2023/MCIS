using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// ITU-R M.1371 AIS 消息比特流解析器（支持消息 1/2/3/5/18/19/24 Part A/B）。
    /// </summary>
    public static class AisMessageParser
    {
        private const int RawLonUnavailable = 0x6791AC0; // 181 * 600000
        private const int RawLatUnavailable = 0x3412140; // 91 * 600000

        /// <summary>将 AIS 原始转向率整数换算为度/分钟（-128 返回 NaN）。</summary>
        public static float DecodeRotDegPerMin(sbyte rawRot)
        {
            if (rawRot == -128)
            {
                return float.NaN;
            }
            if (rawRot == 0)
            {
                return 0f;
            }
            double ratio = rawRot / 4.733;
            return (float)(Math.Sign(rawRot) * ratio * ratio);
        }

        /// <summary>将度/分钟转向率编码为 AIS 原始整数值。</summary>
        public static sbyte EncodeRotRaw(float rotDegPerMin)
        {
            if (float.IsNaN(rotDegPerMin))
            {
                return -128;
            }
            int sign = Math.Sign(rotDegPerMin);
            double val = Math.Round(4.733 * Math.Sqrt(Math.Abs(rotDegPerMin)));
            if (val > 126.0)
            {
                val = 126.0;
            }
            return (sbyte)(sign * (int)val);
        }

        /// <summary>解析重组后的 AIS 比特缓冲，提取位置记录及/或静态船舶资料。</summary>
        public static bool TryDecodeMessage(
            AisBitBuffer bits,
            int lineNumber,
            string rawSentence,
            DateTimeOffset timestampUtc,
            TimeQuality timeQuality,
            out AisDecodedRecord? positionRecord,
            out VesselParticulars staticParticulars,
            IDictionary<string, VesselParticulars> existingStaticByMmsi,
            out string error)
        {
            positionRecord = null;
            staticParticulars = null;
            error = null;

            if (bits == null || bits.BitLength < 38)
            {
                error = "AIS bit buffer too short (< 38 bits).";
                return false;
            }

            int msgType = (int)bits.GetUInt(0, 6);
            uint mmsiNum = bits.GetUInt(8, 30);
            string mmsi = mmsiNum.ToString("D9", CultureInfo.InvariantCulture);

            switch (msgType)
            {
                case 1:
                case 2:
                case 3:
                    return TryDecodeClassAPosition(bits, msgType, mmsi, lineNumber, rawSentence, timestampUtc, timeQuality, out positionRecord, out error);
                case 5:
                    return TryDecodeType5Static(bits, mmsi, existingStaticByMmsi, out staticParticulars, out error);
                case 18:
                    return TryDecodeClassBPosition(bits, 18, mmsi, lineNumber, rawSentence, timestampUtc, timeQuality, out positionRecord, out error);
                case 19:
                    return TryDecodeType19Extended(bits, mmsi, lineNumber, rawSentence, timestampUtc, timeQuality, existingStaticByMmsi, out positionRecord, out staticParticulars, out error);
                case 24:
                    return TryDecodeType24Static(bits, mmsi, existingStaticByMmsi, out staticParticulars, out error);
                default:
                    error = string.Format(CultureInfo.InvariantCulture, "Unsupported AIS message type {0}.", msgType);
                    return false;
            }
        }

        private static bool TryDecodeClassAPosition(
            AisBitBuffer bits, int msgType, string mmsi, int lineNumber, string rawSentence,
            DateTimeOffset timestampUtc, TimeQuality timeQuality,
            out AisDecodedRecord? record, out string error)
        {
            record = null;
            error = null;
            if (bits.BitLength < 137)
            {
                error = "Type 1/2/3 bit length too short.";
                return false;
            }

            byte navStatus = (byte)bits.GetUInt(38, 4);
            sbyte rawRot = (sbyte)bits.GetInt(42, 8);
            float rotDegPerMin = DecodeRotDegPerMin(rawRot);
            uint rawSog = bits.GetUInt(50, 10);
            float sogKn = rawSog >= 1023u ? 102.3f : rawSog * 0.1f;

            int rawLon = bits.GetInt(61, 28);
            int rawLat = bits.GetInt(89, 27);
            double lonDeg = rawLon == RawLonUnavailable ? 181.0 : rawLon / 600000.0;
            double latDeg = rawLat == RawLatUnavailable ? 91.0 : rawLat / 600000.0;

            uint rawCog = bits.GetUInt(116, 12);
            float cogDeg = rawCog >= 3600u ? 360.0f : rawCog * 0.1f;
            uint rawHdg = bits.GetUInt(128, 9);
            float hdgDeg = rawHdg >= 360u ? 511.0f : (float)rawHdg;
            byte tsSec = bits.BitLength >= 143 ? (byte)bits.GetUInt(137, 6) : (byte)60;

            DateTimeOffset finalTs = AlignSecondIfApplicable(timestampUtc, timeQuality, tsSec, out timeQuality);
            record = new AisDecodedRecord(
                lineNumber, rawSentence, msgType, mmsi, finalTs, timeQuality,
                lonDeg, latDeg, sogKn, cogDeg, hdgDeg, rotDegPerMin, navStatus, rawRot, tsSec);
            return true;
        }

        private static bool TryDecodeClassBPosition(
            AisBitBuffer bits, int msgType, string mmsi, int lineNumber, string rawSentence,
            DateTimeOffset timestampUtc, TimeQuality timeQuality,
            out AisDecodedRecord? record, out string error)
        {
            record = null;
            error = null;
            if (bits.BitLength < 133)
            {
                error = "Type 18/19 bit length too short.";
                return false;
            }

            uint rawSog = bits.GetUInt(46, 10);
            float sogKn = rawSog >= 1023u ? 102.3f : rawSog * 0.1f;
            int rawLon = bits.GetInt(57, 28);
            int rawLat = bits.GetInt(85, 27);
            double lonDeg = rawLon == RawLonUnavailable ? 181.0 : rawLon / 600000.0;
            double latDeg = rawLat == RawLatUnavailable ? 91.0 : rawLat / 600000.0;

            uint rawCog = bits.GetUInt(112, 12);
            float cogDeg = rawCog >= 3600u ? 360.0f : rawCog * 0.1f;
            uint rawHdg = bits.GetUInt(124, 9);
            float hdgDeg = rawHdg >= 360u ? 511.0f : (float)rawHdg;
            byte tsSec = bits.BitLength >= 139 ? (byte)bits.GetUInt(133, 6) : (byte)60;

            DateTimeOffset finalTs = AlignSecondIfApplicable(timestampUtc, timeQuality, tsSec, out timeQuality);
            record = new AisDecodedRecord(
                lineNumber, rawSentence, msgType, mmsi, finalTs, timeQuality,
                lonDeg, latDeg, sogKn, cogDeg, hdgDeg, float.NaN, 15, -128, tsSec);
            return true;
        }

        private static bool TryDecodeType5Static(
            AisBitBuffer bits, string mmsi, IDictionary<string, VesselParticulars> existingByMmsi,
            out VesselParticulars particulars, out string error)
        {
            particulars = null;
            error = null;
            if (bits.BitLength < 302)
            {
                error = "Type 5 bit length too short.";
                return false;
            }

            uint imo = bits.GetUInt(40, 30);
            string imoStr = imo > 0u ? imo.ToString(CultureInfo.InvariantCulture) : string.Empty;
            string callSign = bits.GetString(70, 42);
            string name = bits.GetString(112, 120);
            int shipType = (int)bits.GetUInt(232, 8);
            float dimA = bits.GetUInt(240, 9);
            float dimB = bits.GetUInt(249, 9);
            float dimC = bits.GetUInt(258, 6);
            float dimD = bits.GetUInt(264, 6);
            float draught = bits.GetUInt(294, 8) * 0.1f;
            int destBits = Math.Min(120, Math.Max(0, bits.BitLength - 302));
            string dest = bits.GetString(302, destBits);

            AntennaOffset offset = new AntennaOffset(dimA, dimB, dimC, dimD);
            particulars = MergeStaticParticulars(existingByMmsi, mmsi, name, imoStr, callSign, shipType, offset, draught, dest);
            return true;
        }

        private static bool TryDecodeType19Extended(
            AisBitBuffer bits, string mmsi, int lineNumber, string rawSentence,
            DateTimeOffset timestampUtc, TimeQuality timeQuality,
            IDictionary<string, VesselParticulars> existingByMmsi,
            out AisDecodedRecord? record, out VesselParticulars particulars, out string error)
        {
            particulars = null;
            if (!TryDecodeClassBPosition(bits, 19, mmsi, lineNumber, rawSentence, timestampUtc, timeQuality, out record, out error))
            {
                return false;
            }
            if (bits.BitLength < 301)
            {
                error = "Type 19 bit length too short for static extension (< 301 bits).";
                return false;
            }

            string name = bits.GetString(143, 120);
            int shipType = (int)bits.GetUInt(263, 8);
            float dimA = bits.GetUInt(271, 9);
            float dimB = bits.GetUInt(280, 9);
            float dimC = bits.GetUInt(289, 6);
            float dimD = bits.GetUInt(295, 6);
            AntennaOffset offset = new AntennaOffset(dimA, dimB, dimC, dimD);
            particulars = MergeStaticParticulars(existingByMmsi, mmsi, name, null, null, shipType, offset, 0f, null);
            return true;
        }

        private static bool TryDecodeType24Static(
            AisBitBuffer bits, string mmsi, IDictionary<string, VesselParticulars> existingByMmsi,
            out VesselParticulars particulars, out string error)
        {
            particulars = null;
            error = null;
            if (bits.BitLength < 156)
            {
                error = "Type 24 bit length too short.";
                return false;
            }

            int partNum = (int)bits.GetUInt(38, 2);
            if (partNum == 0)
            {
                int nameBits = Math.Min(120, bits.BitLength - 40);
                string name = bits.GetString(40, nameBits);
                particulars = MergeStaticParticulars(existingByMmsi, mmsi, name, null, null, 0, AntennaOffset.Zero, 0f, null);
                return true;
            }
            if (partNum == 1)
            {
                if (bits.BitLength < 162)
                {
                    error = "Type 24 Part B bit length too short (< 162 bits).";
                    return false;
                }
                int shipType = (int)bits.GetUInt(40, 8);
                string callSign = bits.GetString(90, 42);
                float dimA = bits.GetUInt(132, 9);
                float dimB = bits.GetUInt(141, 9);
                float dimC = bits.GetUInt(150, 6);
                float dimD = bits.GetUInt(156, 6);
                AntennaOffset offset = new AntennaOffset(dimA, dimB, dimC, dimD);
                particulars = MergeStaticParticulars(existingByMmsi, mmsi, null, null, callSign, shipType, offset, 0f, null);
                return true;
            }

            error = string.Format(CultureInfo.InvariantCulture, "Invalid Type 24 part number {0}.", partNum);
            return false;
        }

        private static DateTimeOffset AlignSecondIfApplicable(
            DateTimeOffset baseUtc, TimeQuality currentQuality, byte aisSecond, out TimeQuality outQuality)
        {
            outQuality = currentQuality;
            if (aisSecond < 60 && currentQuality == TimeQuality.LogPrefix)
            {
                int diff = aisSecond - baseUtc.Second;
                if (diff > 30) diff -= 60;
                else if (diff < -30) diff += 60;
                outQuality = TimeQuality.MinuteAligned;
                return baseUtc.AddSeconds(diff);
            }
            return baseUtc;
        }

        internal static VesselParticulars MergeStaticParticulars(
            IDictionary<string, VesselParticulars> existingByMmsi,
            string mmsi, string name, string imo, string callSign,
            int shipTypeNum, AntennaOffset offset, float draughtM, string destination)
        {
            VesselParticulars prev = null;
            if (existingByMmsi != null)
            {
                existingByMmsi.TryGetValue(mmsi, out prev);
            }

            string finalName = !string.IsNullOrEmpty(name) ? name : (prev != null ? prev.Name : string.Empty);
            string finalImo = !string.IsNullOrEmpty(imo) ? imo : (prev != null ? prev.ImoNumber : string.Empty);
            string finalCall = !string.IsNullOrEmpty(callSign) ? callSign : (prev != null ? prev.CallSign : string.Empty);
            int finalTypeNum = shipTypeNum > 0 ? shipTypeNum : (prev != null ? prev.ShipTypeCodeNumber : 0);
            AntennaOffset finalOffset = (offset.LoaM > 0f || offset.BeamM > 0f) ? offset : (prev != null ? prev.AntennaOffset : AntennaOffset.Zero);
            float finalDraught = draughtM > 0f ? draughtM : (prev != null ? prev.DraftForeM : 0f);
            string finalDest = !string.IsNullOrEmpty(destination) ? destination : (prev != null ? prev.Destination : string.Empty);

            VesselParticulars merged = new VesselParticulars(
                mmsi, finalName, prev != null ? prev.NameCn : null, mmsi, finalImo, finalCall,
                prev != null ? prev.FlagState : string.Empty, MapShipTypeCategory(finalTypeNum),
                string.Empty, finalOffset.LoaM, finalOffset.BeamM, finalDraught, finalDraught,
                0f, 0f, "FullLoad", finalOffset, Double3.Zero, 0.1f, 30f, null, finalTypeNum, finalDest);

            if (existingByMmsi != null)
            {
                existingByMmsi[mmsi] = merged;
            }
            return merged;
        }

        private static string MapShipTypeCategory(int code)
        {
            if (code == 30) return "Fishing";
            if (code == 31 || code == 32 || code == 52) return "Tug";
            if (code >= 60 && code <= 69) return "Passenger";
            if (code >= 70 && code <= 79) return "Cargo";
            if (code >= 80 && code <= 89) return "Tanker";
            return code > 0 ? code.ToString(CultureInfo.InvariantCulture) : "Unknown";
        }
    }
}
