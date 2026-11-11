using System;
using System.Collections.Generic;
using System.Globalization;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// 解析后的 NMEA 0183 语句。保留地址字段之外的字段、校验和状态、
    /// 日志行前缀设备时间与 NMEA 4.x 标签块时间。
    /// </summary>
    public sealed class NmeaSentence
    {
        private static readonly IReadOnlyList<string> EmptyFields = new string[0];

        /// <summary>会话标识（如 "GP"、"AI"）。</summary>
        public string Talker { get; }

        /// <summary>语句类型（如 "RMC"、"GGA"、"VDM"）。</summary>
        public string Type { get; }

        /// <summary>地址字段之后的字段列表（不含地址字段，也不含校验和）。</summary>
        public IReadOnlyList<string> Fields { get; }

        /// <summary>原始行是否带 *hh 校验和。</summary>
        public bool HasChecksum { get; }

        /// <summary>校验和是否正确；无校验和时为 false。</summary>
        public bool ChecksumValid { get; }

        /// <summary>原始文本（去除首尾空白）。</summary>
        public string Raw { get; }

        /// <summary>行前缀设备时间（UTC），无前缀时为 null。</summary>
        public DateTimeOffset? LogTimestampUtc { get; }

        /// <summary>前缀中是否包含非空的日志前缀文本（标签块之外的文本）。</summary>
        public bool HasLogPrefix { get; }

        /// <summary>日志前缀文本能否解析为时间；无日志前缀或解析失败时为 false。</summary>
        public bool LogPrefixValid { get; }

        /// <summary>从行前缀中剥离标签块后的日志前缀文本（未做时间解析）；无文本时为 null。W2.1。</summary>
        public string LogPrefixText { get; }

        /// <summary>NMEA 4.x 标签块中的 unix 时间（UTC）。无标签块、标签块校验和缺失或错误时为 null（W2-D03）。</summary>
        public DateTimeOffset? TagBlockTimeUtc { get; }

        /// <summary>行首是否带 NMEA 4.x 标签块（\...\）。</summary>
        public bool HasTagBlock { get; }

        /// <summary>标签块自身校验和（两个反斜杠之间、'*' 之前字符异或）是否存在且正确。</summary>
        public bool TagBlockChecksumValid { get; }

        /// <summary>
        /// 语句长度（字符数）：从 '$'/'!' 起到校验和末尾（不含行前缀、标签块与行尾换行），
        /// 用于对照 IEC 61162-1 的 82 字符上限。
        /// </summary>
        public int SentenceLength { get; }

        /// <summary>
        /// 构造解析后的 NMEA 语句。
        /// </summary>
        /// <param name="talker">会话标识。</param>
        /// <param name="type">语句类型。</param>
        /// <param name="fields">字段列表（不含地址字段）。</param>
        /// <param name="hasChecksum">是否带校验和。</param>
        /// <param name="checksumValid">校验和是否正确。</param>
        /// <param name="raw">原始文本。</param>
        /// <param name="logTimestampUtc">行前缀设备时间。</param>
        /// <param name="tagBlockTimeUtc">标签块时间。</param>
        public NmeaSentence(
            string talker,
            string type,
            IReadOnlyList<string> fields,
            bool hasChecksum,
            bool checksumValid,
            string raw,
            DateTimeOffset? logTimestampUtc,
            DateTimeOffset? tagBlockTimeUtc)
        {
            Talker = talker;
            Type = type;
            Fields = fields ?? EmptyFields;
            HasChecksum = hasChecksum;
            ChecksumValid = checksumValid;
            Raw = raw;
            LogTimestampUtc = logTimestampUtc;
            TagBlockTimeUtc = tagBlockTimeUtc;
            HasTagBlock = tagBlockTimeUtc.HasValue;
            TagBlockChecksumValid = tagBlockTimeUtc.HasValue;
            HasLogPrefix = logTimestampUtc.HasValue;
            LogPrefixValid = logTimestampUtc.HasValue;
            LogPrefixText = null;
            SentenceLength = raw != null ? raw.Length : 0;
        }

        /// <summary>
        /// 构造解析后的 NMEA 语句（额外指定日志前缀是否存在及是否有效）。
        /// 标签块状态沿用 logTimestampUtc/tagBlockTimeUtc 的默认推导。
        /// </summary>
        /// <param name="talker">会话标识。</param>
        /// <param name="type">语句类型。</param>
        /// <param name="fields">字段列表（不含地址字段）。</param>
        /// <param name="hasChecksum">是否带校验和。</param>
        /// <param name="checksumValid">校验和是否正确。</param>
        /// <param name="raw">原始文本。</param>
        /// <param name="logTimestampUtc">行前缀设备时间。</param>
        /// <param name="tagBlockTimeUtc">标签块时间。</param>
        /// <param name="hasLogPrefix">前缀中是否有非空日志前缀文本。</param>
        /// <param name="logPrefixValid">日志前缀文本能否解析为时间。</param>
        public NmeaSentence(
            string talker,
            string type,
            IReadOnlyList<string> fields,
            bool hasChecksum,
            bool checksumValid,
            string raw,
            DateTimeOffset? logTimestampUtc,
            DateTimeOffset? tagBlockTimeUtc,
            bool hasLogPrefix,
            bool logPrefixValid)
            : this(talker, type, fields, hasChecksum, checksumValid, raw, logTimestampUtc, tagBlockTimeUtc)
        {
            HasLogPrefix = hasLogPrefix;
            LogPrefixValid = logPrefixValid;
        }

        /// <summary>
        /// 构造解析后的 NMEA 语句（含标签块校验状态与语句长度）。
        /// </summary>
        /// <param name="talker">会话标识。</param>
        /// <param name="type">语句类型。</param>
        /// <param name="fields">字段列表（不含地址字段）。</param>
        /// <param name="hasChecksum">是否带校验和。</param>
        /// <param name="checksumValid">校验和是否正确。</param>
        /// <param name="raw">原始文本。</param>
        /// <param name="logTimestampUtc">行前缀设备时间。</param>
        /// <param name="tagBlockTimeUtc">标签块时间（仅在标签块校验通过时给出）。</param>
        /// <param name="hasTagBlock">是否带标签块。</param>
        /// <param name="tagBlockChecksumValid">标签块校验和是否正确。</param>
        /// <param name="sentenceLength">语句长度（'$'/'!' 至校验和末尾）。</param>
        public NmeaSentence(
            string talker,
            string type,
            IReadOnlyList<string> fields,
            bool hasChecksum,
            bool checksumValid,
            string raw,
            DateTimeOffset? logTimestampUtc,
            DateTimeOffset? tagBlockTimeUtc,
            bool hasTagBlock,
            bool tagBlockChecksumValid,
            int sentenceLength)
            : this(talker, type, fields, hasChecksum, checksumValid, raw, logTimestampUtc, tagBlockTimeUtc)
        {
            HasTagBlock = hasTagBlock;
            TagBlockChecksumValid = tagBlockChecksumValid;
            SentenceLength = sentenceLength;
        }

        /// <summary>
        /// 构造解析后的 NMEA 语句（额外指定日志前缀是否存在及是否有效）。
        /// 旧构造保持兼容：HasLogPrefix 与 LogPrefixValid 均派生自 logTimestampUtc。
        /// </summary>
        /// <param name="talker">会话标识。</param>
        /// <param name="type">语句类型。</param>
        /// <param name="fields">字段列表（不含地址字段）。</param>
        /// <param name="hasChecksum">是否带校验和。</param>
        /// <param name="checksumValid">校验和是否正确。</param>
        /// <param name="raw">原始文本。</param>
        /// <param name="logTimestampUtc">行前缀设备时间。</param>
        /// <param name="tagBlockTimeUtc">标签块时间（仅在标签块校验通过时给出）。</param>
        /// <param name="hasTagBlock">是否带标签块。</param>
        /// <param name="tagBlockChecksumValid">标签块校验和是否正确。</param>
        /// <param name="sentenceLength">语句长度（'$'/'!' 至校验和末尾）。</param>
        /// <param name="hasLogPrefix">前缀中是否有非空日志前缀文本。</param>
        /// <param name="logPrefixValid">日志前缀文本能否解析为时间。</param>
        public NmeaSentence(
            string talker,
            string type,
            IReadOnlyList<string> fields,
            bool hasChecksum,
            bool checksumValid,
            string raw,
            DateTimeOffset? logTimestampUtc,
            DateTimeOffset? tagBlockTimeUtc,
            bool hasTagBlock,
            bool tagBlockChecksumValid,
            int sentenceLength,
            bool hasLogPrefix,
            bool logPrefixValid)
            : this(
                talker,
                type,
                fields,
                hasChecksum,
                checksumValid,
                raw,
                logTimestampUtc,
                tagBlockTimeUtc,
                hasTagBlock,
                tagBlockChecksumValid,
                sentenceLength)
        {
            HasLogPrefix = hasLogPrefix;
            LogPrefixValid = logPrefixValid;
        }

        /// <summary>
        /// 构造解析后的 NMEA 语句（额外指定日志前缀文本、是否存在及是否有效）。
        /// </summary>
        /// <param name="talker">会话标识。</param>
        /// <param name="type">语句类型。</param>
        /// <param name="fields">字段列表（不含地址字段）。</param>
        /// <param name="hasChecksum">是否带校验和。</param>
        /// <param name="checksumValid">校验和是否正确。</param>
        /// <param name="raw">原始文本。</param>
        /// <param name="logTimestampUtc">行前缀设备时间。</param>
        /// <param name="tagBlockTimeUtc">标签块时间（仅在标签块校验通过时给出）。</param>
        /// <param name="hasTagBlock">是否带标签块。</param>
        /// <param name="tagBlockChecksumValid">标签块校验和是否正确。</param>
        /// <param name="sentenceLength">语句长度（'$'/'!' 至校验和末尾）。</param>
        /// <param name="hasLogPrefix">前缀中是否有非空日志前缀文本。</param>
        /// <param name="logPrefixValid">日志前缀文本能否解析为时间。</param>
        /// <param name="logPrefixText">剥离标签块后的日志前缀文本。</param>
        public NmeaSentence(
            string talker,
            string type,
            IReadOnlyList<string> fields,
            bool hasChecksum,
            bool checksumValid,
            string raw,
            DateTimeOffset? logTimestampUtc,
            DateTimeOffset? tagBlockTimeUtc,
            bool hasTagBlock,
            bool tagBlockChecksumValid,
            int sentenceLength,
            bool hasLogPrefix,
            bool logPrefixValid,
            string logPrefixText)
            : this(
                talker,
                type,
                fields,
                hasChecksum,
                checksumValid,
                raw,
                logTimestampUtc,
                tagBlockTimeUtc,
                hasTagBlock,
                tagBlockChecksumValid,
                sentenceLength,
                hasLogPrefix,
                logPrefixValid)
        {
            LogPrefixText = logPrefixText;
        }

        /// <summary>
        /// 安全取得指定下标的字段；越界时返回 null。
        /// </summary>
        /// <param name="index">字段下标（从 0 开始，不含地址字段）。</param>
        /// <returns>字段文本或 null。</returns>
        public string Field(int index)
        {
            if (index < 0 || index >= Fields.Count)
            {
                return null;
            }

            return Fields[index];
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}{1} fields={2} checksum={3}",
                Talker,
                Type,
                Fields.Count,
                ChecksumValid);
        }
    }

    /// <summary>
    /// NMEA 0183 语句解析器，支持纯句子、日志行前缀时间、NMEA 4.x 标签块。
    /// 数值与时间解析全部使用不变文化。
    /// </summary>
    public static class NmeaParser
    {
        /// <summary>
        /// 解析一行 NMEA 文本。
        /// 校验和错误不算解析失败：返回 true 且 ChecksumValid=false。
        /// </summary>
        /// <param name="line">输入行（可包含日志前缀或标签块）。</param>
        /// <param name="sentence">解析成功时的语句对象。</param>
        /// <param name="error">解析失败时的错误描述。</param>
        /// <returns>能够识别出语句结构时返回 true。</returns>
        public static bool TryParse(string line, out NmeaSentence sentence, out string error)
        {
            sentence = null;
            error = null;
            try
            {
                return TryParseCore(line, out sentence, out error);
            }
            catch (Exception ex)
            {
                // 防御：任何意外异常都转为解析失败，绝不让单行中止整批导入（W2-D01）。
                sentence = null;
                error = "NMEA 解析异常：" + ex.GetType().Name;
                return false;
            }
        }

        private static bool TryParseCore(string line, out NmeaSentence sentence, out string error)
        {
            sentence = null;
            error = null;

            if (line == null)
            {
                error = "输入行为 null。";
                return false;
            }

            string raw = line.Trim();
            if (raw.Length > 0 && raw[0] == '\uFEFF')
            {
                raw = raw.Substring(1).TrimStart();
            }

            if (raw.Length == 0)
            {
                error = "输入行为空。";
                return false;
            }

            int dollar = raw.IndexOf('$');
            int bang = raw.IndexOf('!');
            int start;
            if (dollar < 0)
            {
                start = bang;
            }
            else if (bang < 0)
            {
                start = dollar;
            }
            else
            {
                start = dollar < bang ? dollar : bang;
            }

            if (start < 0)
            {
                error = "缺少 NMEA 起始符 $ 或 !。";
                return false;
            }

            string prefix = raw.Substring(0, start).Trim();
            DateTimeOffset? logTimestamp = null;
            DateTimeOffset? tagBlockTime = null;
            bool hasTagBlock = false;
            bool tagBlockChecksumValid = false;
            string logPrefixText = null;
            bool hasLogPrefix = false;
            bool logPrefixValid = false;

            if (prefix.Length > 0)
            {
                // W2-D08：标签块可在日志前缀之前或之后，定位第一个 '\' 到其后配对的 '\'，
                // 余下文本（去掉逗号/空白）作为日志前缀；不能要求前缀必须以 '\' 开头。
                int tagStart = prefix.IndexOf('\\');
                if (tagStart >= 0)
                {
                    int tagEnd = prefix.IndexOf('\\', tagStart + 1);
                    if (tagEnd > tagStart)
                    {
                        hasTagBlock = true;
                        string tagBlock = prefix.Substring(tagStart, tagEnd - tagStart + 1);
                        ParseTagBlock(tagBlock, out tagBlockTime, out tagBlockChecksumValid);
                        logPrefixText = (prefix.Substring(0, tagStart) + prefix.Substring(tagEnd + 1))
                            .Trim()
                            .Trim(',', ' ', '\t');
                    }
                    else
                    {
                        // 未配对的 '\' 不构成标签块，按普通日志前缀处理。
                        logPrefixText = prefix.Trim().Trim(',', ' ', '\t');
                    }
                }
                else
                {
                    logPrefixText = prefix.Trim().Trim(',', ' ', '\t');
                }

                if (!string.IsNullOrEmpty(logPrefixText))
                {
                    hasLogPrefix = true;
                    DateTimeOffset parsed;
                    if (DateTimeOffset.TryParse(
                        logPrefixText,
                        CultureInfo.InvariantCulture,
                        DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal,
                        out parsed))
                    {
                        logTimestamp = parsed;
                        logPrefixValid = true;
                    }
                }
            }

            string sentencePart = raw.Substring(start).TrimEnd();
            int star = sentencePart.IndexOf('*');
            string body = star >= 0 ? sentencePart.Substring(0, star) : sentencePart;
            if (body.Length < 2)
            {
                error = "NMEA 语句体过短。";
                return false;
            }

            int comma = body.IndexOf(',');
            string address;
            string fieldText;
            if (comma >= 0)
            {
                address = body.Substring(0, comma);
                fieldText = body.Substring(comma + 1);
            }
            else
            {
                address = body;
                fieldText = string.Empty;
            }

            if (address.Length > 0 && (address[0] == '$' || address[0] == '!'))
            {
                address = address.Substring(1);
            }

            // 地址字段 = 2 字符会话标识 + 3 字符语句类型；不足 5 字符即为残缺行（W2-D01）。
            if (address.Length < 5)
            {
                error = "NMEA 地址字段不完整（需至少 5 个字符，实际 " +
                        address.Length.ToString(CultureInfo.InvariantCulture) + "）。";
                return false;
            }

            string talker = address.Substring(0, 2);
            string type = address.Substring(2, 3);

            string[] fields = fieldText.Length == 0
                ? new string[0]
                : fieldText.Split(',');

            bool hasChecksum = false;
            bool checksumValid = false;
            int sentenceLength = sentencePart.Length;
            if (star >= 0 && sentencePart.Length >= star + 3)
            {
                string checksumText = sentencePart.Substring(star + 1, 2);
                int expected;
                if (int.TryParse(
                    checksumText,
                    NumberStyles.HexNumber,
                    CultureInfo.InvariantCulture,
                    out expected))
                {
                    hasChecksum = true;
                    int actual = 0;
                    for (int i = 1; i < star; i++)
                    {
                        actual ^= sentencePart[i];
                    }

                    checksumValid = actual == expected;
                }
            }

            sentence = new NmeaSentence(
                talker,
                type,
                fields,
                hasChecksum,
                checksumValid,
                raw,
                logTimestamp,
                tagBlockTime,
                hasTagBlock,
                tagBlockChecksumValid,
                star >= 0 ? Math.Min(sentenceLength, star + 3) : sentenceLength,
                hasLogPrefix,
                logPrefixValid,
                logPrefixText);
            return true;
        }

        /// <summary>
        /// 解析 NMEA 经纬度格式（ddmm.mmmm / dddmm.mmmm）与半球标识。
        /// </summary>
        /// <param name="value">经纬度数值字段。</param>
        /// <param name="hemi">半球标识 N/S/E/W（大小写不敏感）。</param>
        /// <param name="isLat">true 表示纬度，false 表示经度。</param>
        /// <param name="deg">输出十进制度（南纬/西经为负）。</param>
        /// <returns>解析成功返回 true。</returns>
        public static bool TryParseLatLon(string value, string hemi, bool isLat, out double deg)
        {
            deg = 0.0;
            if (string.IsNullOrEmpty(value) || string.IsNullOrEmpty(hemi))
            {
                return false;
            }

            double rawValue;
            if (!double.TryParse(
                value.Trim(),
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out rawValue))
            {
                return false;
            }

            if (double.IsNaN(rawValue) || double.IsInfinity(rawValue))
            {
                return false;
            }

            double absolute = Math.Abs(rawValue);
            int degrees = (int)Math.Floor(absolute / 100.0);
            double minutes = absolute - degrees * 100.0;
            if (minutes < 0.0 || minutes >= 60.0)
            {
                return false;
            }

            if (isLat && degrees > 90)
            {
                return false;
            }
            if (!isLat && degrees > 180)
            {
                return false;
            }

            string hemisphere = hemi.Trim().ToUpperInvariant();
            if (isLat)
            {
                if (hemisphere != "N" && hemisphere != "S")
                {
                    return false;
                }
            }
            else
            {
                if (hemisphere != "E" && hemisphere != "W")
                {
                    return false;
                }
            }

            double result = degrees + minutes / 60.0;
            if (hemisphere == "S" || hemisphere == "W")
            {
                result = -result;
            }

            deg = result;
            return true;
        }

        /// <summary>
        /// 解析 hhmmss 或 hhmmss.fff 形式的 UTC 时间。
        /// </summary>
        /// <param name="hhmmss">时间字段。</param>
        /// <param name="time">输出当天时间偏移。</param>
        /// <returns>解析成功返回 true。</returns>
        public static bool TryParseUtcTime(string hhmmss, out TimeSpan time)
        {
            time = TimeSpan.Zero;
            if (string.IsNullOrEmpty(hhmmss))
            {
                return false;
            }

            string text = hhmmss.Trim();
            if (text.Length < 6)
            {
                return false;
            }

            int hours;
            int minutes;
            int seconds;
            if (!int.TryParse(text.Substring(0, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out hours) ||
                !int.TryParse(text.Substring(2, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out minutes) ||
                !int.TryParse(text.Substring(4, 2), NumberStyles.Integer, CultureInfo.InvariantCulture, out seconds))
            {
                return false;
            }

            if (hours < 0 || hours > 23 || minutes < 0 || minutes > 59 || seconds < 0 || seconds > 60)
            {
                return false;
            }

            double fraction = 0.0;
            if (text.Length > 6)
            {
                if (text[6] != '.' && text[6] != ',')
                {
                    return false;
                }

                string fractionText = "0" + text.Substring(6).Replace(',', '.');
                if (!double.TryParse(
                    fractionText,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out fraction))
                {
                    return false;
                }

                if (fraction < 0.0 || fraction >= 1.0)
                {
                    return false;
                }
            }

            time = new TimeSpan(0, hours, minutes, seconds) + TimeSpan.FromSeconds(fraction);
            return true;
        }

        /// <summary>
        /// 计算 NMEA 4.x 标签块校验和是否正确：两反斜杠之间、'*' 之前字符异或，'*' 后两位十六进制（大小写均可）。
        /// </summary>
        /// <param name="tagBlockContent">两个反斜杠之间的内容（如 "c:1779084900*hh"）。</param>
        /// <returns>带校验和且正确时返回 true。</returns>
        public static bool IsTagBlockChecksumValid(string tagBlockContent)
        {
            if (string.IsNullOrEmpty(tagBlockContent))
            {
                return false;
            }

            int star = tagBlockContent.LastIndexOf('*');
            if (star < 0 || tagBlockContent.Length < star + 3)
            {
                return false;
            }

            int expected;
            if (!int.TryParse(
                tagBlockContent.Substring(star + 1, 2),
                NumberStyles.HexNumber,
                CultureInfo.InvariantCulture,
                out expected))
            {
                return false;
            }

            int actual = 0;
            for (int i = 0; i < star; i++)
            {
                actual ^= tagBlockContent[i];
            }

            return actual == expected;
        }

        private static void ParseTagBlock(string prefix, out DateTimeOffset? tagBlockTime, out bool checksumValid)
        {
            tagBlockTime = null;
            checksumValid = false;
            string text = prefix.Trim();
            if (text.Length > 0 && text[0] == '\\')
            {
                text = text.Substring(1);
            }

            text = text.TrimEnd('\\').Trim();
            checksumValid = IsTagBlockChecksumValid(text);
            if (!checksumValid)
            {
                // 校验和缺失或错误：不采信标签块中的时间（W2-D03 / 裁定 3）。
                return;
            }

            int star = text.LastIndexOf('*');
            string body = star >= 0 ? text.Substring(0, star) : text;

            string[] parts = body.Split(',');
            for (int i = 0; i < parts.Length; i++)
            {
                string part = parts[i].Trim();
                int colon = part.IndexOf(':');
                if (colon <= 0)
                {
                    continue;
                }

                string key = part.Substring(0, colon);
                string value = part.Substring(colon + 1).Trim();
                if (!string.Equals(key, "c", StringComparison.Ordinal))
                {
                    continue;
                }

                long unixSeconds;
                if (long.TryParse(value, NumberStyles.Integer, CultureInfo.InvariantCulture, out unixSeconds))
                {
                    if (unixSeconds >= 0 && unixSeconds <= 253402300799L)
                    {
                        tagBlockTime = DateTimeOffset.FromUnixTimeSeconds(unixSeconds);
                    }
                    return;
                }

                double unixWithFraction;
                if (double.TryParse(
                    value,
                    NumberStyles.Float,
                    CultureInfo.InvariantCulture,
                    out unixWithFraction))
                {
                    long milliseconds = (long)Math.Round(unixWithFraction * 1000.0, MidpointRounding.AwayFromZero);
                    if (milliseconds >= 0)
                    {
                        tagBlockTime = DateTimeOffset.FromUnixTimeMilliseconds(milliseconds);
                    }
                }

                return;
            }
        }
    }
}
