using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Tests.W2
{
    public sealed class MediaImporterTests
    {
        [Fact]
        public void SampleManifest_ImportsChannelsMediaAndMarkers()
        {
            Result<VdrImportResult> result = VdrMediaManifestImporter.Import(
                TestHelpers.ReadSampleLines("mary_media_manifest.csv"),
                TestHelpers.Options("MARY-MEDIA"));

            Assert.True(result.IsSuccess, result.ErrorMessage);
            VdrImportResult value = result.Value;
            Assert.Equal(4, value.Tracks.Count);
            Assert.Equal(6, value.SentencesUsed);
            Assert.Equal(8, value.LinesRead);

            Track ch1 = value.Tracks.First(t => t.Id == "MARY-MEDIA/Audio/CH1");
            Assert.Equal(TrackKind.Audio, ch1.Kind);
            Assert.Empty(ch1.Samples);
            Assert.Equal(2, ch1.Media.Count);
            Assert.Equal(2, ch1.Markers.Count);

            MediaItem first = ch1.Media.First(m => m.Id == "AUD-CH1-001");
            Assert.Equal("CH1", first.Channel);
            Assert.Equal("audio_ch1_0615.wav", first.FileName);
            Assert.Equal(900.0, first.Range.Start.Seconds, 9);
            Assert.Equal(1620.0, first.Range.End.Seconds, 9);
            Assert.Equal("audio_ch1_0615.wav", first.Metadata["file"]);
            Assert.Equal("驾驶台音频", first.Metadata["note"]);
            Assert.True(first.Metadata.ContainsKey("sha256"));

            Track radar = value.Tracks.First(t => t.Id == "MARY-MEDIA/RadarImage/X-BAND");
            Assert.Equal(2, radar.Media.Count);
            Assert.Equal("media", radar.Markers[0].Kind);

            IReadOnlyList<MediaItem> activeCh1 = ch1.MediaAt(new SimTime(1410));
            Assert.Equal(2, activeCh1.Count);

            Track ecdis = value.Tracks.First(t => t.Kind == TrackKind.EcdisImage);
            Assert.Single(ecdis.MediaAt(new SimTime(1410)));
        }

        [Fact]
        public void MissingRequiredColumn_Fails()
        {
            string[] lines =
            {
                "# 示例数据（虚构）",
                "id,kind,channel,file,start_utc",
                "a,audio,CH1,a.wav,2026-05-18T06:15:00.000Z"
            };

            Result<VdrImportResult> result = VdrMediaManifestImporter.Import(
                lines,
                TestHelpers.Options("MARY-MEDIA"));

            Assert.False(result.IsSuccess);
            Assert.Equal("vdr_media_missing_column", result.ErrorCode);
        }

        [Fact]
        public void UnknownKind_WritesDiagnosticOnce()
        {
            string[] lines =
            {
                "id,kind,channel,file,start_utc,duration_s",
                "a,unknown,CH1,a.wav,2026-05-18T06:15:00.000Z,10",
                "b,unknown,CH1,b.wav,2026-05-18T06:16:00.000Z,10"
            };

            Result<VdrImportResult> result = VdrMediaManifestImporter.Import(
                lines,
                TestHelpers.Options("MARY-MEDIA"));

            Assert.True(result.IsSuccess);
            Assert.Single(result.Value.Diagnostics, d => d.Code == "vdr_unsupported");
            Assert.Empty(result.Value.Tracks);
        }
    }
}
