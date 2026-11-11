using System;
using System.Collections.Generic;
using System.IO;
using Mcis.Core;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// CSV 航迹导入列映射与单位配置模板。
    /// </summary>
    public sealed class CsvMappingProfile
    {
        /// <summary>配置模板名称。</summary>
        public string ProfileName { get; }

        /// <summary>MMSI 列名。</summary>
        public string MmsiColumn { get; }

        /// <summary>时间戳列名。</summary>
        public string TimestampColumn { get; }

        /// <summary>自定义时间格式字符串（为空或 null 时自动识别常见 UTC 时间格式）。</summary>
        public string TimestampFormat { get; }

        /// <summary>源数据时间相对 UTC 的时区偏移分钟数（UTC 为 0，北京时间 UTC+8 为 480）。</summary>
        public int SourceTimeZoneOffsetMinutes { get; }

        /// <summary>经度列名。</summary>
        public string LonColumn { get; }

        /// <summary>纬度列名。</summary>
        public string LatColumn { get; }

        /// <summary>对地航速 SOG 列名。</summary>
        public string SogColumn { get; }

        /// <summary>对地航向 COG 列名。</summary>
        public string CogColumn { get; }

        /// <summary>船首向 HDG 列名（可选）。</summary>
        public string HdgColumn { get; }

        /// <summary>船名列名（可选）。</summary>
        public string VesselNameColumn { get; }

        /// <summary>速度单位（"kn" | "mps" | "kmh"）。</summary>
        public string SpeedUnit { get; }

        /// <summary>构造 CSV 列映射配置。</summary>
        public CsvMappingProfile(
            string profileName,
            string mmsiColumn,
            string timestampColumn,
            string timestampFormat,
            int sourceTimeZoneOffsetMinutes,
            string lonColumn,
            string latColumn,
            string sogColumn,
            string cogColumn,
            string hdgColumn = "Heading",
            string vesselNameColumn = "VesselName",
            string speedUnit = "kn")
        {
            ProfileName = profileName ?? "Default";
            MmsiColumn = mmsiColumn ?? "MMSI";
            TimestampColumn = timestampColumn ?? "BaseDateTime";
            TimestampFormat = timestampFormat;
            SourceTimeZoneOffsetMinutes = sourceTimeZoneOffsetMinutes;
            LonColumn = lonColumn ?? "LON";
            LatColumn = latColumn ?? "LAT";
            SogColumn = sogColumn ?? "SOG";
            CogColumn = cogColumn ?? "COG";
            HdgColumn = hdgColumn;
            VesselNameColumn = vesselNameColumn;
            SpeedUnit = string.IsNullOrWhiteSpace(speedUnit) ? "kn" : speedUnit;
        }

        /// <summary>创建标准默认映射（兼容 NOAA MarineCadastre 与常规导出表头）。</summary>
        public static CsvMappingProfile CreateDefault()
        {
            return new CsvMappingProfile(
                "StandardUtc",
                "MMSI",
                "BaseDateTime",
                null,
                0,
                "LON",
                "LAT",
                "SOG",
                "COG",
                "Heading",
                "VesselName",
                "kn");
        }
    }

    /// <summary>
    /// AIS 批量导入结果汇总（包含按 MMSI 分组的动态位置记录、静态船舶资料及校验/语法错误报告）。
    /// </summary>
    public sealed class AisImportBatchResult
    {
        /// <summary>按 MMSI 分组的解码位置记录字典。</summary>
        public IReadOnlyDictionary<string, IReadOnlyList<AisDecodedRecord>> RecordsByMmsi { get; }

        /// <summary>从消息 5 / 19 / 24 或 CSV 中提取的船舶静态参数字典（按 MMSI 索引）。</summary>
        public IReadOnlyDictionary<string, VesselParticulars> DiscoveredStaticParticulars { get; }

        /// <summary>因校验和失败、语法错误或多句重组失败被拒绝的记录列表。</summary>
        public IReadOnlyList<RejectedSample> ChecksumOrSyntaxErrors { get; }

        /// <summary>已处理的原始非空总行数。</summary>
        public int TotalLinesProcessed { get; }

        /// <summary>构造 AIS 批量导入结果。</summary>
        public AisImportBatchResult(
            IReadOnlyDictionary<string, IReadOnlyList<AisDecodedRecord>> recordsByMmsi,
            IReadOnlyDictionary<string, VesselParticulars> discoveredStaticParticulars,
            IReadOnlyList<RejectedSample> checksumOrSyntaxErrors,
            int totalLinesProcessed)
        {
            RecordsByMmsi = recordsByMmsi ?? new Dictionary<string, IReadOnlyList<AisDecodedRecord>>();
            DiscoveredStaticParticulars = discoveredStaticParticulars ?? new Dictionary<string, VesselParticulars>();
            ChecksumOrSyntaxErrors = checksumOrSyntaxErrors ?? Array.Empty<RejectedSample>();
            TotalLinesProcessed = totalLinesProcessed;
        }
    }

    /// <summary>
    /// 纯 C# AIS 报文与 CSV 解析器接口，支持 ITU-R M.1371 消息 1/2/3/5/18/19/24、Tag Block 时间戳与多片段重组。
    /// </summary>
    public interface IAisDecoder
    {
        /// <summary>从文本流解码 NMEA !AIVDM / !AIVDO 报文序列。</summary>
        Result<AisImportBatchResult> DecodeNmeaStream(
            TextReader reader,
            DateTimeOffset? fallbackStartTimeUtc = null,
            double clockOffsetSeconds = 0.0);

        /// <summary>从文本流按指定列映射配置解码 CSV 航迹数据。</summary>
        Result<AisImportBatchResult> DecodeCsvStream(
            TextReader reader,
            CsvMappingProfile mapping,
            double clockOffsetSeconds = 0.0);

        /// <summary>验证单行 NMEA 语句的异或校验和。</summary>
        bool ValidateNmeaChecksum(string rawLine, out byte expected, out byte actual);
    }
}
