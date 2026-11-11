using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Timeline;

namespace Mcis.Data.Vdr
{
    /// <summary>
    /// VDR 导入门面：把 NMEA、通用 CSV 与媒体清单的导入结果合并为一个结果。
    /// </summary>
    public static class VdrImporter
    {
        /// <summary>
        /// 导入并合并全部数据源。相同轨道 Id 的样本合并（同一时刻保留先到的），
        /// 锚点、诊断直接拼接，行数与语句数求和。
        /// </summary>
        /// <param name="options">导入选项。</param>
        /// <param name="nmeaLines">NMEA 行集合，可为 null。</param>
        /// <param name="mediaManifestLines">媒体清单行集合，可为 null。</param>
        /// <param name="csvSets">CSV 行集合与映射的元组序列，可为 null。</param>
        /// <returns>合并后的导入结果；任一子导入失败时返回对应失败。</returns>
        public static Result<VdrImportResult> ImportAll(
            VdrImportOptions options,
            IEnumerable<string> nmeaLines,
            IEnumerable<string> mediaManifestLines = null,
            IEnumerable<(IEnumerable<string> lines, VdrCsvMapping mapping)> csvSets = null)
        {
            if (options == null || string.IsNullOrWhiteSpace(options.SourceId))
            {
                return Result<VdrImportResult>.Fail("vdr_missing_source", "必须指定数据源标识 SourceId。");
            }

            List<VdrImportResult> parts = new List<VdrImportResult>();

            Result<VdrImportResult> nmeaResult = VdrNmeaImporter.Import(nmeaLines, options);
            if (!nmeaResult.IsSuccess)
            {
                return Result<VdrImportResult>.Fail(nmeaResult.ErrorCode, nmeaResult.ErrorMessage);
            }
            parts.Add(nmeaResult.Value);

            if (mediaManifestLines != null)
            {
                Result<VdrImportResult> mediaResult =
                    VdrMediaManifestImporter.Import(mediaManifestLines, options);
                if (!mediaResult.IsSuccess)
                {
                    return Result<VdrImportResult>.Fail(mediaResult.ErrorCode, mediaResult.ErrorMessage);
                }
                parts.Add(mediaResult.Value);
            }

            if (csvSets != null)
            {
                foreach ((IEnumerable<string> lines, VdrCsvMapping mapping) set in csvSets)
                {
                    Result<VdrImportResult> csvResult =
                        VdrCsvImporter.Import(set.lines, set.mapping, options);
                    if (!csvResult.IsSuccess)
                    {
                        return Result<VdrImportResult>.Fail(csvResult.ErrorCode, csvResult.ErrorMessage);
                    }
                    parts.Add(csvResult.Value);
                }
            }

            return Result<VdrImportResult>.Ok(Merge(options.SourceId, parts));
        }

        private static VdrImportResult Merge(string sourceId, List<VdrImportResult> parts)
        {
            Dictionary<string, TrackMerger> mergers =
                new Dictionary<string, TrackMerger>(StringComparer.Ordinal);
            List<AnchorObservation> anchors = new List<AnchorObservation>();
            List<VdrDiagnostic> diagnostics = new List<VdrDiagnostic>();
            int linesRead = 0;
            int sentencesUsed = 0;

            for (int p = 0; p < parts.Count; p++)
            {
                VdrImportResult part = parts[p];
                linesRead += part.LinesRead;
                sentencesUsed += part.SentencesUsed;
                anchors.AddRange(part.Anchors);
                diagnostics.AddRange(part.Diagnostics);

                for (int i = 0; i < part.Tracks.Count; i++)
                {
                    Track track = part.Tracks[i];
                    TrackMerger merger;
                    if (!mergers.TryGetValue(track.Id, out merger))
                    {
                        merger = new TrackMerger(track);
                        mergers.Add(track.Id, merger);
                    }

                    merger.AddTrack(track);
                }
            }

            List<Track> tracks = new List<Track>(mergers.Count);
            foreach (TrackMerger merger in mergers.Values)
            {
                tracks.Add(merger.Build());
            }

            tracks.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));
            return new VdrImportResult(
                sourceId,
                tracks,
                anchors,
                diagnostics,
                linesRead,
                sentencesUsed);
        }

        private sealed class TrackMerger
        {
            private readonly string _id;
            private readonly string _sourceId;
            private readonly TrackKind _kind;
            private readonly string _unit;
            private readonly BearingReference _bearingReference;
            private readonly HashSet<SimTime> _times = new HashSet<SimTime>();
            private readonly HashSet<string> _markerIds = new HashSet<string>(StringComparer.Ordinal);
            private readonly HashSet<string> _mediaIds = new HashSet<string>(StringComparer.Ordinal);
            private readonly List<TimelineSample> _samples = new List<TimelineSample>();
            private readonly List<EventMarker> _markers = new List<EventMarker>();
            private readonly List<MediaItem> _media = new List<MediaItem>();

            public TrackMerger(Track first)
            {
                _id = first.Id;
                _sourceId = first.SourceId;
                _kind = first.Kind;
                _unit = first.Unit;
                // W2.1/D09：合并时保留方位参考，避免相对方位轨经门面合并后被当作真方位。
                _bearingReference = first.BearingReference;
            }

            public void AddTrack(Track track)
            {
                for (int i = 0; i < track.Samples.Count; i++)
                {
                    TimelineSample sample = track.Samples[i];
                    if (_times.Add(sample.Time))
                    {
                        _samples.Add(sample);
                    }
                }

                for (int i = 0; i < track.Markers.Count; i++)
                {
                    EventMarker marker = track.Markers[i];
                    string key = marker.Id ?? string.Empty;
                    if (_markerIds.Add(key))
                    {
                        _markers.Add(marker);
                    }
                }

                for (int i = 0; i < track.Media.Count; i++)
                {
                    MediaItem item = track.Media[i];
                    string key = item.Id ?? string.Empty;
                    if (_mediaIds.Add(key))
                    {
                        _media.Add(item);
                    }
                }
            }

            public Track Build()
            {
                return new Track(_id, _sourceId, _kind, _unit, _samples, _markers, _media, _bearingReference);
            }
        }
    }
}
