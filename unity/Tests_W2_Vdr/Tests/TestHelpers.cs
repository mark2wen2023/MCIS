using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Common;
using Mcis.Domain.Timeline;

namespace Mcis.Tests.W2
{
    internal static class TestHelpers
    {
        public static readonly DateTimeOffset Epoch =
            new DateTimeOffset(2026, 5, 18, 6, 0, 0, TimeSpan.Zero);

        public static string SamplesDirectory
        {
            get { return Path.Combine(AppContext.BaseDirectory, "Samples"); }
        }

        public static string ReadSample(string fileName)
        {
            return File.ReadAllText(Path.Combine(SamplesDirectory, fileName));
        }

        public static string[] ReadSampleLines(string fileName)
        {
            return File.ReadAllLines(Path.Combine(SamplesDirectory, fileName));
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
            int checksum = 0;
            for (int i = 0; i < body.Length; i++)
            {
                checksum ^= body[i];
            }

            return "$" + body + "*" + checksum.ToString("X2", CultureInfo.InvariantCulture);
        }

        /// <summary>生成带正确自身校验和的 NMEA 4.x 标签块，如 \c:1779084900*hh\。</summary>
        public static string TagBlock(string content)
        {
            int checksum = 0;
            for (int i = 0; i < content.Length; i++)
            {
                checksum ^= content[i];
            }

            return "\\" + content + "*" + checksum.ToString("X2", CultureInfo.InvariantCulture) + "\\";
        }

        public static string Nmea(string body, int checksumOverride)
        {
            return "$" + body + "*" + checksumOverride.ToString("X2", CultureInfo.InvariantCulture);
        }

        public static Track ScalarTrack(
            string id,
            string sourceId,
            TrackKind kind,
            params TimelineSample[] samples)
        {
            return new Track(id, sourceId, kind, TrackKindInfo.DefaultUnit(kind), samples);
        }

        public static Track PositionTrack(
            string id,
            string sourceId,
            params TimelineSample[] samples)
        {
            return new Track(id, sourceId, TrackKind.Position, string.Empty, samples);
        }

        public static TimelineSample S(double time, double value, string text = null)
        {
            return TimelineSample.Scalar(new SimTime(time), value, text);
        }

        public static TimelineSample P(double time, double lon, double lat)
        {
            return TimelineSample.AtPosition(new SimTime(time), new GeoCoord(lon, lat, 0.0));
        }

        public static Track FindTrack(VdrImportResult result, TrackKind kind, string sourceId = null)
        {
            foreach (Track track in result.Tracks)
            {
                if (track.Kind == kind &&
                    (sourceId == null || track.SourceId == sourceId))
                {
                    return track;
                }
            }

            return null;
        }
    }
}
