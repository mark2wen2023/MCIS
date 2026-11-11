using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class CsvImporterTests
    {
        private static VdrCsvMapping BuildMapping()
        {
            return new VdrCsvMapping
            {
                TimeColumn = "time_local",
                TimeFormat = "yyyy-MM-dd HH:mm:ss",
                TimeZoneOffset = TimeSpan.FromHours(8),
                EventColumn = "event",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "telegraph",
                        Kind = TrackKind.EngineTelegraph,
                        MarkChanges = true,
                        TextValues = new Dictionary<string, double>(StringComparer.OrdinalIgnoreCase)
                        {
                            { "STOP", 0 },
                            { "HALF AHEAD", 3 },
                            { "FULL AHEAD", 4 },
                            { "FULL ASTERN", -4 }
                        }
                    },
                    new VdrCsvColumnMapping
                    {
                        Column = "rudder_deg",
                        Kind = TrackKind.RudderAngle
                    }
                }
            };
        }

        [Fact]
        public void Import_MapsTextTimezoneChangesAndEvents()
        {
            string[] lines =
            {
                "# 示例数据（虚构）",
                "time_local,telegraph,rudder_deg,event",
                "2026-05-18 14:15:00,\" half ahead \",0,",
                "2026-05-18 14:16:00,FULL AHEAD,5,加速",
                "2026-05-18 14:17:00,\"FULL AHEAD\",-3,\"左舵, 注意\""
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, BuildMapping(), TestHelpers.Options("MARY-BRIDGE"));

            Assert.True(result.IsSuccess, result.ErrorMessage);
            VdrImportResult value = result.Value;
            Track telegraph = value.Tracks.FirstOrDefault(t => t.Id == "MARY-BRIDGE/EngineTelegraph");

            Assert.NotNull(telegraph);
            Assert.Equal(3, telegraph.Samples.Count);
            Assert.Equal(900.0, telegraph.Samples[0].Time.Seconds, 9);
            Assert.Equal(3.0, telegraph.Samples[0].Value, 9);
            Assert.Equal("half ahead", telegraph.Samples[0].Text);
            Assert.Equal(4.0, telegraph.Samples[1].Value, 9);

            Track rudder = value.Tracks.FirstOrDefault(t => t.Id == "MARY-BRIDGE/RudderAngle");
            Assert.NotNull(rudder);
            Assert.Equal(-3.0, rudder.Samples[2].Value, 9);

            List<EventMarker> markers = new List<EventMarker>(telegraph.Markers);
            EventMarker change = markers.Find(m => m.Kind == "change");
            Assert.NotNull(change);
            Assert.Equal(960.0, change.Time.Seconds, 9);
            Assert.Contains("half ahead", change.Label);
            Assert.Contains("FULL AHEAD", change.Label);
            Assert.Contains("→", change.Label);

            List<EventMarker> events = markers.FindAll(m => m.Kind == "event");
            Assert.Equal(2, events.Count);
            Assert.Equal("加速", events[0].Label);
            Assert.Equal("左舵, 注意", events[1].Label);
            Assert.Equal(1020.0, events[1].Time.Seconds, 9);
        }

        [Fact]
        public void Import_ScaleAndOffset_Applied()
        {
            string[] lines =
            {
                "time,val",
                "2026-05-18 14:15:00,5"
            };
            VdrCsvMapping mapping = new VdrCsvMapping
            {
                TimeColumn = "time",
                TimeFormat = "yyyy-MM-dd HH:mm:ss",
                TimeZoneOffset = TimeSpan.FromHours(8),
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping
                    {
                        Column = "val",
                        Kind = TrackKind.Other,
                        TrackName = "Scaled",
                        Scale = 2.0,
                        Offset = 1.0
                    }
                }
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, mapping, TestHelpers.Options("S"));

            Assert.True(result.IsSuccess);
            Track track = result.Value.Tracks.FirstOrDefault(t => t.Id == "S/Scaled");
            Assert.NotNull(track);
            Assert.Equal(11.0, track.Samples[0].Value, 9);
        }

        [Fact]
        public void Import_MissingColumn_Fails()
        {
            string[] lines =
            {
                "time_local,telegraph",
                "2026-05-18 14:15:00,HALF AHEAD"
            };
            VdrCsvMapping mapping = BuildMapping();
            mapping.Columns.Add(new VdrCsvColumnMapping
            {
                Column = "rudder_deg",
                Kind = TrackKind.RudderAngle
            });

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, mapping, TestHelpers.Options("S"));

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_csv_missing_column", result.ErrorCode);
        }

        [Fact]
        public void Import_MissingTimeColumn_Fails()
        {
            string[] lines =
            {
                "a,b",
                "1,2"
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, BuildMapping(), TestHelpers.Options("S"));

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_csv_missing_column", result.ErrorCode);
        }

        [Fact]
        public void Import_EmptyFile_Fails()
        {
            Result<VdrImportResult> result =
                VdrCsvImporter.Import(new[] { "# 只有注释" }, BuildMapping(), TestHelpers.Options("S"));

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_csv_missing_header", result.ErrorCode);
        }

        [Fact]
        public void Import_BadNumericValue_WritesDiagnostic()
        {
            string[] lines =
            {
                "time_local,telegraph,rudder_deg,event",
                "2026-05-18 14:15:00,HALF AHEAD,NOT_A_NUMBER,"
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, BuildMapping(), TestHelpers.Options("S"));

            Assert.True(result.IsSuccess);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_csv_bad_value");
        }

        [Fact]
        public void Import_BadTime_WritesDiagnostic()
        {
            string[] lines =
            {
                "time_local,telegraph,rudder_deg,event",
                "not-a-time,HALF AHEAD,0,"
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, BuildMapping(), TestHelpers.Options("S"));

            Assert.True(result.IsSuccess);
            Assert.Contains(result.Value.Diagnostics, d => d.Code == "vdr_csv_bad_time");
        }

        [Fact]
        public void Import_IsoTimeWithoutFormat_ParsesOffset()
        {
            string[] lines =
            {
                "time_utc,sog_kn",
                "2026-05-18T06:15:00.000Z,12.0"
            };
            VdrCsvMapping mapping = new VdrCsvMapping
            {
                TimeColumn = "time_utc",
                Columns = new List<VdrCsvColumnMapping>
                {
                    new VdrCsvColumnMapping { Column = "sog_kn", Kind = TrackKind.SpeedOverGround }
                }
            };

            Result<VdrImportResult> result =
                VdrCsvImporter.Import(lines, mapping, TestHelpers.Options("VTS-AIS"));

            Assert.True(result.IsSuccess);
            Track track = result.Value.Tracks.FirstOrDefault(t => t.Kind == TrackKind.SpeedOverGround);
            Assert.Equal(900.0, track.Samples[0].Time.Seconds, 9);
            Assert.Equal(12.0, track.Samples[0].Value, 9);
        }
    }
}
