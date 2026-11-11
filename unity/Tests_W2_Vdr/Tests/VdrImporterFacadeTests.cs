using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class VdrImporterFacadeTests
    {
        [Fact]
        public void ImportAll_MergesTracksAnchorsDiagnosticsAndCsv()
        {
            string nmea = "2026-05-18T06:15:03.200Z," +
                          TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A");
            string[] media =
            {
                "id,kind,channel,file,start_utc,duration_s",
                "m1,audio,CH1,a.wav,2026-05-18T06:15:00.000Z,60"
            };
            string[] csv =
            {
                "time_utc,sog_kn",
                "2026-05-18T06:15:20.000Z,12.4"
            };
            VdrCsvMapping mapping = new VdrCsvMapping
            {
                TimeColumn = "time_utc",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "sog_kn",
                        Kind = TrackKind.SpeedOverGround
                    }
                }
            };

            Result<VdrImportResult> result = VdrImporter.ImportAll(
                TestHelpers.Options("S"),
                new[] { nmea },
                media,
                new[] { (lines: (IEnumerable<string>)csv, mapping: mapping) });

            Assert.True(result.IsSuccess, result.ErrorMessage);
            VdrImportResult value = result.Value;

            Track speed = value.Tracks.First(t => t.Id == "S/SpeedOverGround");
            Assert.Equal(2, speed.Samples.Count);
            Assert.Equal(903.2, speed.Samples[0].Time.Seconds, 6);
            Assert.Equal(920.0, speed.Samples[1].Time.Seconds, 6);

            Assert.Single(value.Tracks, t => t.Kind == TrackKind.Audio);
            Assert.Equal(2, value.Anchors.Count);
            Assert.Equal(5, value.LinesRead);
            Assert.Equal(3, value.SentencesUsed);
        }

        [Fact]
        public void ImportAll_PropagatesCsvFailure()
        {
            VdrCsvMapping mapping = new VdrCsvMapping
            {
                TimeColumn = "missing",
                Columns = new List<VdrCsvColumnMapping>()
            };

            Result<VdrImportResult> result = VdrImporter.ImportAll(
                TestHelpers.Options("S"),
                new string[0],
                null,
                new[] { (lines: (IEnumerable<string>)new[] { "a,b", "1,2" }, mapping: mapping) });

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_csv_missing_column", result.ErrorCode);
        }

        [Fact]
        public void ImportAll_WithoutOptionalParts_Works()
        {
            Result<VdrImportResult> result = VdrImporter.ImportAll(
                TestHelpers.Options("S"),
                new[]
                {
                    "2026-05-18T06:15:03.200Z," +
                    TestHelpers.Nmea("GPRMC,061500.00,A,3006.0000,N,12203.6000,E,12.0,45.0,180526,,,A")
                });

            Assert.True(result.IsSuccess);
            Assert.NotEmpty(result.Value.Tracks);
        }
    }
}
