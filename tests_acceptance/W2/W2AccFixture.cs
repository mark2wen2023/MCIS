using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// W2 验收共用夹具。演示数据全部虚构；案件纪元与样例一致（2026-05-18 06:00 UTC，对应原型 14:00 UTC+8）。
    /// </summary>
    internal static class W2AccFixture
    {
        public const string CaseId = "CASE-2026-LN01";
        public const string Mary = "MARY-VDR";
        public const string Lily = "LILY-SVDR";
        public const string Vts = "VTS-AIS";

        public static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        public static string SamplesDirectory
        {
            get { return Path.Combine(AppContext.BaseDirectory, "Samples"); }
        }

        public static string[] ReadSampleLines(string fileName)
        {
            return File.ReadAllLines(Path.Combine(SamplesDirectory, fileName));
        }

        public static string ReadSample(string fileName)
        {
            return File.ReadAllText(Path.Combine(SamplesDirectory, fileName));
        }

        public static VdrImportOptions Options(string sourceId, DateTime? defaultDate = null)
        {
            return new VdrImportOptions
            {
                SourceId = sourceId,
                CaseEpochUtc = Epoch,
                DefaultDateUtc = defaultDate
            };
        }

        public static string Nmea(string body)
        {
            return "$" + body + "*" + XorChecksum(body).ToString("X2", CultureInfo.InvariantCulture);
        }

        public static string NmeaLower(string body)
        {
            return "$" + body + "*" + XorChecksum(body).ToString("x2", CultureInfo.InvariantCulture);
        }

        public static string TagBlock(string body)
        {
            return "\\" + body + "*" + XorChecksum(body).ToString("X2", CultureInfo.InvariantCulture) + "\\";
        }

        public static int XorChecksum(string text)
        {
            int checksum = 0;
            if (text != null)
            {
                for (int i = 0; i < text.Length; i++)
                {
                    checksum ^= text[i];
                }
            }

            return checksum & 0xFF;
        }

        public static string Rmc(string time, string date, double sog = 12.0, double cog = 45.0, string status = "A")
        {
            return Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "GPRMC,{0},{1},3006.0000,N,12203.6000,E,{2:0.0},{3:0.0},{4},,,A",
                time, status, sog, cog, date));
        }

        public static string Gga(string time, int quality = 1)
        {
            return Nmea(string.Format(
                CultureInfo.InvariantCulture,
                "GPGGA,{0},3006.0000,N,12203.6000,E,{1},12,0.8,5.0,M,0.0,M,,",
                time, quality));
        }

        public static Track ScalarTrack(
            string id,
            string sourceId,
            TrackKind kind,
            params TimelineSample[] samples)
        {
            return new Track(id, sourceId, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        public static TimelineSample S(double time, double value, string text = null)
        {
            return TimelineSample.Scalar(new SimTime(time), value, text);
        }

        public static TimelineSample P(double time, double lon, double lat)
        {
            return TimelineSample.AtPosition(new SimTime(time), new GeoCoord(lon, lat, 0.0));
        }

        public static Track Constant(
            string id,
            string source,
            TrackKind kind,
            double start,
            double end,
            double value,
            double step = 1.0)
        {
            List<TimelineSample> samples = new List<TimelineSample>();
            for (double t = start; t <= end + 1e-9; t += step)
            {
                samples.Add(S(t, value));
            }

            return ScalarTrack(id, source, kind, samples.ToArray());
        }

        public static bool HasPublicProperty(Type type, string name)
        {
            return type.GetProperty(name, BindingFlags.Public | BindingFlags.Instance) != null;
        }
    }
}
