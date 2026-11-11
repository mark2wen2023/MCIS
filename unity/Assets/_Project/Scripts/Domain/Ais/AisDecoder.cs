using System;
using System.Collections.Generic;
using System.IO;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// 纯 C# AIS 报文与 CSV 解码器实现（支持 ITU-R M.1371 消息 1/2/3/5/18/19/24 Part A/B、多片段重组与校验和验证）。
    /// </summary>
    public sealed class AisDecoder : IAisDecoder
    {
        private readonly double _multiSentenceTimeoutSeconds;

        /// <summary>构造 AIS 解码器。</summary>
        public AisDecoder(double multiSentenceTimeoutSeconds = 5.0)
        {
            _multiSentenceTimeoutSeconds = multiSentenceTimeoutSeconds;
        }

        /// <inheritdoc />
        public bool ValidateNmeaChecksum(string rawLine, out byte expected, out byte actual)
        {
            return NmeaSentenceParser.ValidateChecksum(rawLine, out expected, out actual);
        }

        /// <summary>直接从多行字符串解码 NMEA 报文。</summary>
        public Result<AisImportBatchResult> DecodeNmeaText(
            string nmeaText,
            DateTimeOffset? fallbackStartTimeUtc = null,
            double clockOffsetSeconds = 0.0)
        {
            using (StringReader reader = new StringReader(nmeaText ?? string.Empty))
            {
                return DecodeNmeaStream(reader, fallbackStartTimeUtc, clockOffsetSeconds);
            }
        }

        /// <summary>直接从字符串解码 CSV 航迹。</summary>
        public Result<AisImportBatchResult> DecodeCsvText(
            string csvText,
            CsvMappingProfile mapping = null,
            double clockOffsetSeconds = 0.0)
        {
            using (StringReader reader = new StringReader(csvText ?? string.Empty))
            {
                return DecodeCsvStream(reader, mapping, clockOffsetSeconds);
            }
        }

        /// <inheritdoc />
        public Result<AisImportBatchResult> DecodeCsvStream(
            TextReader reader,
            CsvMappingProfile mapping,
            double clockOffsetSeconds = 0.0)
        {
            return AisCsvParser.ParseStream(reader, mapping, clockOffsetSeconds);
        }

        /// <inheritdoc />
        public Result<AisImportBatchResult> DecodeNmeaStream(
            TextReader reader,
            DateTimeOffset? fallbackStartTimeUtc = null,
            double clockOffsetSeconds = 0.0)
        {
            if (reader == null)
            {
                return Result<AisImportBatchResult>.Fail("ARG_NULL", "NMEA TextReader cannot be null.");
            }

            var recordsByMmsi = new Dictionary<string, List<AisDecodedRecord>>(StringComparer.Ordinal);
            var staticByMmsi = new Dictionary<string, VesselParticulars>(StringComparer.Ordinal);
            var lastEstimatedTsByMmsi = new Dictionary<string, DateTimeOffset>(StringComparer.Ordinal);
            var errors = new List<RejectedSample>();
            var assembler = new NmeaMultiSentenceAssembler(_multiSentenceTimeoutSeconds);

            DateTimeOffset baseFallback = fallbackStartTimeUtc ?? new DateTimeOffset(2026, 1, 1, 0, 0, 0, TimeSpan.Zero);
            int lineNum = 0;
            int processedLines = 0;
            int messageCounter = 0;

            string line;
            while ((line = reader.ReadLine()) != null)
            {
                lineNum++;
                string trimmed = line.Trim();
                if (string.IsNullOrEmpty(trimmed) || trimmed.StartsWith("#", StringComparison.Ordinal))
                {
                    if (!fallbackStartTimeUtc.HasValue && trimmed.StartsWith("#", StringComparison.Ordinal))
                    {
                        DateTimeOffset commentEpoch;
                        if (TryParseEpochComment(trimmed, out commentEpoch))
                        {
                            baseFallback = commentEpoch;
                        }
                    }
                    continue;
                }
                processedLines++;

                byte expectedXor;
                byte actualXor;
                if (!NmeaSentenceParser.ValidateChecksum(trimmed, out expectedXor, out actualXor))
                {
                    errors.Add(new RejectedSample(
                        lineNum,
                        SimTime.Zero,
                        new GeoCoord(181.0, 91.0, 0.0),
                        102.3f,
                        360.0f,
                        RejectReason.ChecksumError,
                        string.Format("NMEA checksum mismatch at line {0}: expected 0x{1:X2}, actual 0x{2:X2}.", lineNum, expectedXor, actualXor)));
                    continue;
                }

                ParsedNmeaSentence parsed;
                string parseErr;
                if (!NmeaSentenceParser.TryParseSentence(lineNum, trimmed, out parsed, out parseErr))
                {
                    errors.Add(new RejectedSample(
                        lineNum,
                        SimTime.Zero,
                        new GeoCoord(181.0, 91.0, 0.0),
                        102.3f,
                        360.0f,
                        RejectReason.InvalidField,
                        parseErr ?? "Invalid NMEA sentence syntax."));
                    continue;
                }

                AssembledAisPayload assembled;
                if (!assembler.Push(parsed, errors, out assembled))
                {
                    continue;
                }

                AisBitBuffer bitBuffer;
                string armorErr;
                if (!AisBitBuffer.TryFromPayload(assembled.Payload, assembled.FillBits, out bitBuffer, out armorErr))
                {
                    errors.Add(new RejectedSample(
                        assembled.FirstLineNumber,
                        SimTime.Zero,
                        new GeoCoord(181.0, 91.0, 0.0),
                        102.3f,
                        360.0f,
                        RejectReason.InvalidField,
                        armorErr ?? "6-bit de-armoring failed."));
                    continue;
                }

                DateTimeOffset msgTimestamp = assembled.ExtractedTimestampUtc ?? baseFallback.AddSeconds(messageCounter);
                TimeQuality msgQuality = assembled.ExtractedTimestampUtc.HasValue ? assembled.TimeQuality : TimeQuality.Estimated;
                if (Math.Abs(clockOffsetSeconds) > 1e-9)
                {
                    msgTimestamp = msgTimestamp.AddSeconds(clockOffsetSeconds);
                }
                messageCounter++;

                AisDecodedRecord? posRecord;
                VesselParticulars staticPart;
                string decodeErr;
                if (!AisMessageParser.TryDecodeMessage(
                    bitBuffer,
                    assembled.FirstLineNumber,
                    assembled.CombinedRawSentences,
                    msgTimestamp,
                    msgQuality,
                    out posRecord,
                    out staticPart,
                    staticByMmsi,
                    out decodeErr))
                {
                    errors.Add(new RejectedSample(
                        assembled.FirstLineNumber,
                        SimTime.Zero,
                        new GeoCoord(181.0, 91.0, 0.0),
                        102.3f,
                        360.0f,
                        RejectReason.InvalidField,
                        decodeErr ?? "Failed to decode AIS message bits."));
                    continue;
                }

                if (posRecord.HasValue)
                {
                    AisDecodedRecord rec = posRecord.Value;
                    if (!assembled.ExtractedTimestampUtc.HasValue && rec.TimestampSecond < 60)
                    {
                        DateTimeOffset resolvedTs = ResolveEstimatedTimestamp(
                            rec.Mmsi, rec.TimestampSecond, baseFallback, clockOffsetSeconds, lastEstimatedTsByMmsi);
                        rec = new AisDecodedRecord(
                            rec.SourceLineNumber, rec.RawSentence, rec.MessageType, rec.Mmsi,
                            resolvedTs, rec.TimeQuality, rec.LonDeg, rec.LatDeg,
                            rec.SogKn, rec.CogDeg, rec.HdgDeg, rec.RotDegPerMin,
                            rec.NavStatus, rec.RawRot, rec.TimestampSecond);
                    }

                    List<AisDecodedRecord> list;
                    if (!recordsByMmsi.TryGetValue(rec.Mmsi, out list))
                    {
                        list = new List<AisDecodedRecord>();
                        recordsByMmsi[rec.Mmsi] = list;
                    }
                    list.Add(rec);
                }
            }

            assembler.FlushRemaining(errors);

            var readonlyByMmsi = new Dictionary<string, IReadOnlyList<AisDecodedRecord>>(recordsByMmsi.Count, StringComparer.Ordinal);
            foreach (KeyValuePair<string, List<AisDecodedRecord>> kv in recordsByMmsi)
            {
                readonlyByMmsi[kv.Key] = kv.Value;
            }

            return Result<AisImportBatchResult>.Ok(
                new AisImportBatchResult(readonlyByMmsi, staticByMmsi, errors, processedLines));
        }

        private static DateTimeOffset ResolveEstimatedTimestamp(
            string mmsi,
            byte tsSec,
            DateTimeOffset baseFallback,
            double clockOffsetSeconds,
            Dictionary<string, DateTimeOffset> lastByMmsi)
        {
            DateTimeOffset prev;
            DateTimeOffset resolved;
            if (!lastByMmsi.TryGetValue(mmsi, out prev))
            {
                int delta = tsSec - baseFallback.Second;
                if (delta < 0) delta += 60;
                resolved = baseFallback.AddSeconds(delta);
            }
            else
            {
                int delta = tsSec - prev.Second;
                if (delta <= 0) delta += 60;
                resolved = prev.AddSeconds(delta);
            }

            lastByMmsi[mmsi] = resolved;
            return Math.Abs(clockOffsetSeconds) > 1e-9 ? resolved.AddSeconds(clockOffsetSeconds) : resolved;
        }

        private static bool TryParseEpochComment(string commentLine, out DateTimeOffset epochUtc)
        {
            epochUtc = default(DateTimeOffset);
            int idx = commentLine.IndexOf("epoch_utc:", StringComparison.OrdinalIgnoreCase);
            if (idx < 0)
            {
                return false;
            }
            string raw = commentLine.Substring(idx + "epoch_utc:".Length).Trim();
            return DateTimeOffset.TryParse(
                raw,
                System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.AssumeUniversal | System.Globalization.DateTimeStyles.AdjustToUniversal,
                out epochUtc);
        }
    }
}
