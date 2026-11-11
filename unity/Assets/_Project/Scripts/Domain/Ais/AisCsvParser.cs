using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// AIS CSV 航迹文件解析器（支持可配置列名映射、多种 UTC 时间格式与速度单位换算）。
    /// </summary>
    public static class AisCsvParser
    {
        private static readonly string[] CommonTimeFormats = new string[]
        {
            "yyyy-MM-ddTHH:mm:ss.fffK",
            "yyyy-MM-ddTHH:mm:ssK",
            "yyyy-MM-ddTHH:mm:ss.fff",
            "yyyy-MM-ddTHH:mm:ss",
            "yyyy-MM-dd HH:mm:ss.fff",
            "yyyy-MM-dd HH:mm:ss",
            "yyyy-MM-dd HH:mm",
            "yyyy/MM/dd HH:mm:ss",
            "yyyy/M/d H:m:s",
            "yyyy/M/d HH:mm:ss",
            "MM/dd/yyyy HH:mm:ss",
            "dd/MM/yyyy HH:mm:ss"
        };

        /// <summary>解析 CSV 文本流并生成批量导入结果。</summary>
        public static Result<AisImportBatchResult> ParseStream(
            TextReader reader,
            CsvMappingProfile mapping,
            double clockOffsetSeconds = 0.0)
        {
            if (reader == null)
            {
                return Result<AisImportBatchResult>.Fail("ARG_NULL", "CSV TextReader cannot be null.");
            }

            CsvMappingProfile profile = mapping ?? CsvMappingProfile.CreateDefault();
            var recordsByMmsi = new Dictionary<string, List<AisDecodedRecord>>(StringComparer.Ordinal);
            var staticByMmsi = new Dictionary<string, VesselParticulars>(StringComparer.Ordinal);
            var errors = new List<RejectedSample>();

            string headerLine = null;
            int lineNum = 0;
            while ((headerLine = reader.ReadLine()) != null)
            {
                lineNum++;
                if (!string.IsNullOrWhiteSpace(headerLine) && !headerLine.TrimStart().StartsWith("#", StringComparison.Ordinal))
                {
                    break;
                }
            }

            if (headerLine == null)
            {
                return Result<AisImportBatchResult>.Ok(new AisImportBatchResult(
                    new Dictionary<string, IReadOnlyList<AisDecodedRecord>>(), staticByMmsi, errors, 0));
            }

            List<string> headers = SplitCsvLine(headerLine);
            int idxMmsi = FindColumnIndex(headers, profile.MmsiColumn, "MMSI", "mmsi", "UserID");
            int idxTime = FindColumnIndex(headers, profile.TimestampColumn, "BaseDateTime", "Timestamp", "timestamp_utc", "Time", "DateTime", "UTC", "postime");
            int idxLon = FindColumnIndex(headers, profile.LonColumn, "LON", "Longitude", "lon", "lng");
            int idxLat = FindColumnIndex(headers, profile.LatColumn, "LAT", "Latitude", "lat");
            int idxSog = FindColumnIndex(headers, profile.SogColumn, "SOG", "sog_kn", "Speed", "sog");
            int idxCog = FindColumnIndex(headers, profile.CogColumn, "COG", "cog_deg", "Course", "cog");
            int idxHdg = FindColumnIndex(headers, profile.HdgColumn, "Heading", "HDG", "hdg_deg", "TrueHeading", "hdg");
            int idxName = FindColumnIndex(headers, profile.VesselNameColumn, "VesselName", "vessel_name", "Name", "ShipName");

            if (idxMmsi < 0 || idxTime < 0 || idxLon < 0 || idxLat < 0)
            {
                return Result<AisImportBatchResult>.Fail(
                    "CSV_HEADER_MISSING",
                    "Required CSV columns (MMSI, Timestamp, Lon, Lat) not found in header.");
            }

            int processedDataLines = 0;
            string line;
            while ((line = reader.ReadLine()) != null)
            {
                lineNum++;
                if (string.IsNullOrWhiteSpace(line) || line.TrimStart().StartsWith("#", StringComparison.Ordinal))
                {
                    continue;
                }
                processedDataLines++;
                List<string> cols = SplitCsvLine(line);

                string mmsi = GetCol(cols, idxMmsi);
                string timeStr = GetCol(cols, idxTime);
                string lonStr = GetCol(cols, idxLon);
                string latStr = GetCol(cols, idxLat);

                double lonDeg;
                double latDeg;
                DateTimeOffset timestampUtc;
                if (string.IsNullOrEmpty(mmsi) ||
                    !double.TryParse(lonStr, NumberStyles.Float, CultureInfo.InvariantCulture, out lonDeg) ||
                    !double.TryParse(latStr, NumberStyles.Float, CultureInfo.InvariantCulture, out latDeg) ||
                    !TryParseTimestampUtc(timeStr, profile.TimestampFormat, profile.SourceTimeZoneOffsetMinutes, out timestampUtc))
                {
                    errors.Add(new RejectedSample(
                        lineNum, SimTime.Zero, new GeoCoord(181.0, 91.0, 0.0),
                        102.3f, 360.0f, RejectReason.InvalidField, "Malformed CSV row at line " + lineNum));
                    continue;
                }

                if (Math.Abs(clockOffsetSeconds) > 1e-9)
                {
                    timestampUtc = timestampUtc.AddSeconds(clockOffsetSeconds);
                }

                float sogKn = ParseOptionalFloat(GetCol(cols, idxSog), 102.3f);
                if (sogKn < 102.25f)
                {
                    sogKn = ConvertSpeedToKnots(sogKn, profile.SpeedUnit);
                }
                float cogDeg = ParseOptionalFloat(GetCol(cols, idxCog), 360.0f);
                float hdgDeg = ParseOptionalFloat(GetCol(cols, idxHdg), 511.0f);

                AisDecodedRecord rec = new AisDecodedRecord(
                    lineNum, line, 0, mmsi, timestampUtc, TimeQuality.LogPrefix,
                    lonDeg, latDeg, sogKn, cogDeg, hdgDeg, float.NaN, 0, -128, (byte)timestampUtc.Second);

                List<AisDecodedRecord> list;
                if (!recordsByMmsi.TryGetValue(mmsi, out list))
                {
                    list = new List<AisDecodedRecord>();
                    recordsByMmsi[mmsi] = list;
                }
                list.Add(rec);

                string vName = GetCol(cols, idxName);
                if (!string.IsNullOrEmpty(vName))
                {
                    AisMessageParser.MergeStaticParticulars(
                        staticByMmsi, mmsi, vName, null, null, 0, AntennaOffset.Zero, 0f, null);
                }
            }

            var readonlyByMmsi = new Dictionary<string, IReadOnlyList<AisDecodedRecord>>(recordsByMmsi.Count, StringComparer.Ordinal);
            foreach (KeyValuePair<string, List<AisDecodedRecord>> kv in recordsByMmsi)
            {
                readonlyByMmsi[kv.Key] = kv.Value;
            }

            return Result<AisImportBatchResult>.Ok(
                new AisImportBatchResult(readonlyByMmsi, staticByMmsi, errors, processedDataLines));
        }

        private static int FindColumnIndex(List<string> headers, string preferred, params string[] fallbacks)
        {
            if (!string.IsNullOrEmpty(preferred))
            {
                for (int i = 0; i < headers.Count; i++)
                {
                    if (string.Equals(headers[i], preferred, StringComparison.OrdinalIgnoreCase))
                        return i;
                }
            }
            for (int f = 0; f < fallbacks.Length; f++)
            {
                for (int i = 0; i < headers.Count; i++)
                {
                    if (string.Equals(headers[i], fallbacks[f], StringComparison.OrdinalIgnoreCase))
                        return i;
                }
            }
            return -1;
        }

        private static string GetCol(List<string> cols, int index)
        {
            return (index >= 0 && index < cols.Count) ? cols[index].Trim() : string.Empty;
        }

        private static float ParseOptionalFloat(string text, float unavailableDefault)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return unavailableDefault;
            }
            float val;
            if (float.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out val))
            {
                return val;
            }
            return unavailableDefault;
        }

        private static float ConvertSpeedToKnots(float value, string unit)
        {
            if (string.Equals(unit, "mps", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(unit, "m/s", StringComparison.OrdinalIgnoreCase))
            {
                return (float)(value * (3600.0 / 1852.0));
            }
            if (string.Equals(unit, "kmh", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(unit, "km/h", StringComparison.OrdinalIgnoreCase))
            {
                return (float)(value / 1.852);
            }
            return value;
        }

        private static bool TryParseTimestampUtc(string text, string customFormat, int tzOffsetMinutes, out DateTimeOffset utc)
        {
            utc = default(DateTimeOffset);
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            double unixSec;
            if (double.TryParse(text, NumberStyles.Float, CultureInfo.InvariantCulture, out unixSec) && unixSec > 100000000.0)
            {
                long ms = unixSec > 9999999999.0 ? (long)unixSec : (long)Math.Round(unixSec * 1000.0);
                utc = DateTimeOffset.FromUnixTimeMilliseconds(ms);
                return true;
            }

            TimeSpan sourceOffset = TimeSpan.FromMinutes(tzOffsetMinutes);
            bool hasExplicitTz = text.EndsWith("Z", StringComparison.OrdinalIgnoreCase) ||
                                 (text.Length > 19 && (text.IndexOf('+', 19) > 0 || text.IndexOf('-', 19) > 0));

            DateTime dt;
            if (!string.IsNullOrWhiteSpace(customFormat))
            {
                if (hasExplicitTz && DateTimeOffset.TryParseExact(text, customFormat, CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal, out utc))
                {
                    return true;
                }
                if (DateTime.TryParseExact(text, customFormat, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
                {
                    utc = new DateTimeOffset(DateTime.SpecifyKind(dt, DateTimeKind.Unspecified), sourceOffset).ToUniversalTime();
                    return true;
                }
            }

            if (hasExplicitTz && DateTimeOffset.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.AdjustToUniversal, out utc))
            {
                return true;
            }

            if (DateTime.TryParseExact(text, CommonTimeFormats, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt) ||
                DateTime.TryParse(text, CultureInfo.InvariantCulture, DateTimeStyles.None, out dt))
            {
                utc = new DateTimeOffset(DateTime.SpecifyKind(dt, DateTimeKind.Unspecified), sourceOffset).ToUniversalTime();
                return true;
            }

            return false;
        }

        private static List<string> SplitCsvLine(string line)
        {
            List<string> result = new List<string>(12);
            StringBuilder current = new StringBuilder();
            bool inQuotes = false;
            for (int i = 0; i < line.Length; i++)
            {
                char c = line[i];
                if (c == '"')
                {
                    if (inQuotes && i + 1 < line.Length && line[i + 1] == '"')
                    {
                        current.Append('"');
                        i++;
                    }
                    else
                    {
                        inQuotes = !inQuotes;
                    }
                }
                else if (c == ',' && !inQuotes)
                {
                    result.Add(current.ToString().Trim());
                    current.Clear();
                }
                else
                {
                    current.Append(c);
                }
            }
            result.Add(current.ToString().Trim());
            return result;
        }
    }
}
