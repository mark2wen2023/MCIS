using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// 解析后的单条 NMEA !AIVDM / !AIVDO 语句结构。
    /// </summary>
    public readonly struct ParsedNmeaSentence
    {
        /// <summary>原始行号。</summary>
        public int LineNumber { get; }
        /// <summary>原始行字符串。</summary>
        public string RawLine { get; }
        /// <summary>片段总数 (1..9)。</summary>
        public int FragmentCount { get; }
        /// <summary>当前片段序号 (1..FragmentCount)。</summary>
        public int FragmentNumber { get; }
        /// <summary>顺序消息 ID。</summary>
        public string SequentialMessageId { get; }
        /// <summary>无线电利用信道 (A/B)。</summary>
        public string Channel { get; }
        /// <summary>6-bit 装甲载荷。</summary>
        public string Payload { get; }
        /// <summary>填充比特数 (0..5)。</summary>
        public int FillBits { get; }
        /// <summary>行级提取的时间戳（若无则为 null）。</summary>
        public DateTimeOffset? ExtractedTimestampUtc { get; }
        /// <summary>时间戳质量等级。</summary>
        public TimeQuality TimeQuality { get; }

        /// <summary>构造已解析的 NMEA 语句。</summary>
        public ParsedNmeaSentence(
            int lineNumber,
            string rawLine,
            int fragmentCount,
            int fragmentNumber,
            string sequentialMessageId,
            string channel,
            string payload,
            int fillBits,
            DateTimeOffset? extractedTimestampUtc,
            TimeQuality timeQuality)
        {
            LineNumber = lineNumber;
            RawLine = rawLine;
            FragmentCount = fragmentCount;
            FragmentNumber = fragmentNumber;
            SequentialMessageId = sequentialMessageId ?? string.Empty;
            Channel = channel ?? string.Empty;
            Payload = payload ?? string.Empty;
            FillBits = fillBits;
            ExtractedTimestampUtc = extractedTimestampUtc;
            TimeQuality = timeQuality;
        }
    }

    /// <summary>
    /// NMEA 0183 !AIVDM / !AIVDO 校验和验证、标签块解析与句子构造工具。
    /// </summary>
    public static class NmeaSentenceParser
    {
        /// <summary>计算并构造带正确异或校验和的 !AIVDM 语句。</summary>
        public static string BuildAivdmSentence(
            string payload,
            int fillBits,
            int fragmentCount = 1,
            int fragmentNumber = 1,
            string seqId = "",
            string channel = "A",
            string talker = "AIVDM")
        {
            string body = string.Format(
                CultureInfo.InvariantCulture,
                "{0},{1},{2},{3},{4},{5},{6}",
                talker, fragmentCount, fragmentNumber, seqId ?? string.Empty, channel ?? "A", payload, fillBits);
            byte xor = ComputeXorChecksum(body, 0, body.Length);
            return string.Format(CultureInfo.InvariantCulture, "!{0}*{1:X2}", body, xor);
        }

        /// <summary>计算指定区间的逐字符异或校验和。</summary>
        public static byte ComputeXorChecksum(string text, int startIndex, int length)
        {
            byte xor = 0;
            int end = startIndex + length;
            for (int i = startIndex; i < end; i++)
            {
                xor ^= (byte)text[i];
            }
            return xor;
        }

        /// <summary>验证单行 NMEA 语句的异或校验和。</summary>
        public static bool ValidateChecksum(string rawLine, out byte expected, out byte actual)
        {
            expected = 0;
            actual = 0;
            if (string.IsNullOrWhiteSpace(rawLine))
            {
                return false;
            }

            int bangIdx = FindNmeaStartIndex(rawLine);
            if (bangIdx < 0)
            {
                return false;
            }

            int starIdx = rawLine.IndexOf('*', bangIdx + 1);
            if (starIdx < 0 || starIdx + 2 >= rawLine.Length)
            {
                return false;
            }

            actual = ComputeXorChecksum(rawLine, bangIdx + 1, starIdx - bangIdx - 1);
            string hex = rawLine.Substring(starIdx + 1, 2);
            if (!byte.TryParse(hex, NumberStyles.HexNumber, CultureInfo.InvariantCulture, out expected))
            {
                return false;
            }

            return expected == actual;
        }

        /// <summary>查找 !AIVDM / !AIVDO（或通用 !/$ NMEA 句首）起始位置。</summary>
        public static int FindNmeaStartIndex(string rawLine)
        {
            int idx = rawLine.IndexOf("!AIVDM", StringComparison.OrdinalIgnoreCase);
            if (idx >= 0) return idx;
            idx = rawLine.IndexOf("!AIVDO", StringComparison.OrdinalIgnoreCase);
            if (idx >= 0) return idx;
            idx = rawLine.IndexOf("!BSVDM", StringComparison.OrdinalIgnoreCase);
            if (idx >= 0) return idx;
            idx = rawLine.IndexOf("!ABVDM", StringComparison.OrdinalIgnoreCase);
            if (idx >= 0) return idx;
            return rawLine.IndexOf('!');
        }

        /// <summary>解析单行 NMEA !AIVDM / !AIVDO 语句（假定已校验或在此一并提取字段）。</summary>
        public static bool TryParseSentence(
            int lineNumber,
            string rawLine,
            out ParsedNmeaSentence parsed,
            out string error)
        {
            parsed = default(ParsedNmeaSentence);
            error = null;

            int bangIdx = FindNmeaStartIndex(rawLine);
            if (bangIdx < 0)
            {
                error = "Missing '!' NMEA start delimiter.";
                return false;
            }

            int starIdx = rawLine.IndexOf('*', bangIdx + 1);
            if (starIdx < 0)
            {
                error = "Missing '*' checksum delimiter.";
                return false;
            }

            DateTimeOffset? tsUtc;
            TimeQuality tq;
            ExtractPrefixTimestamp(rawLine, bangIdx, out tsUtc, out tq);

            string body = rawLine.Substring(bangIdx + 1, starIdx - bangIdx - 1);
            string[] parts = body.Split(',');
            if (parts.Length < 7)
            {
                error = "Insufficient NMEA fields.";
                return false;
            }

            string talker = parts[0];
            if (!talker.EndsWith("VDM", StringComparison.OrdinalIgnoreCase) &&
                !talker.EndsWith("VDO", StringComparison.OrdinalIgnoreCase))
            {
                error = "Unsupported NMEA talker: " + talker;
                return false;
            }

            int fragCount;
            int fragNum;
            int fillBits;
            if (!int.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out fragCount) ||
                !int.TryParse(parts[2], NumberStyles.Integer, CultureInfo.InvariantCulture, out fragNum) ||
                !int.TryParse(parts[6], NumberStyles.Integer, CultureInfo.InvariantCulture, out fillBits) ||
                fragCount < 1 || fragNum < 1 || fragNum > fragCount || fillBits < 0 || fillBits > 5)
            {
                error = "Invalid fragment numbers or fill bits.";
                return false;
            }

            parsed = new ParsedNmeaSentence(
                lineNumber, rawLine, fragCount, fragNum, parts[3], parts[4], parts[5], fillBits, tsUtc, tq);
            return true;
        }

        private static void ExtractPrefixTimestamp(
            string rawLine,
            int bangIdx,
            out DateTimeOffset? timestampUtc,
            out TimeQuality quality)
        {
            timestampUtc = null;
            quality = TimeQuality.Estimated;
            if (bangIdx <= 0)
            {
                return;
            }

            string prefix = rawLine.Substring(0, bangIdx).Trim();
            int cIdx = prefix.IndexOf("c:", StringComparison.OrdinalIgnoreCase);
            if (cIdx >= 0)
            {
                int start = cIdx + 2;
                int end = start;
                while (end < prefix.Length && char.IsDigit(prefix[end]))
                {
                    end++;
                }
                long unixVal;
                if (end > start && long.TryParse(prefix.Substring(start, end - start), NumberStyles.Integer, CultureInfo.InvariantCulture, out unixVal))
                {
                    timestampUtc = unixVal > 9999999999L
                        ? DateTimeOffset.FromUnixTimeMilliseconds(unixVal)
                        : DateTimeOffset.FromUnixTimeSeconds(unixVal);
                    quality = TimeQuality.ExactTagBlock;
                    return;
                }
            }

            string cleanPrefix = prefix.Trim('\\', ' ', '\t', '[', ']', ',');
            DateTimeOffset parsedDto;
            if (!string.IsNullOrEmpty(cleanPrefix) &&
                DateTimeOffset.TryParse(cleanPrefix, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out parsedDto))
            {
                timestampUtc = parsedDto;
                quality = TimeQuality.LogPrefix;
            }
        }
    }
}
