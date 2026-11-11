using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 多轨时间轴：把来自不同数据源、不同物理量的轨道聚合在一起，
    /// 提供按标识/来源/种类查询、某一时刻快照与事件合并查询。
    /// </summary>
    public sealed class MultiTrackTimeline
    {
        private readonly Track[] _tracks;
        private readonly Dictionary<string, Track> _byId;

        /// <summary>全部轨道（保持构造时顺序）。</summary>
        public IReadOnlyList<Track> Tracks
        {
            get { return _tracks; }
        }

        /// <summary>所有有数据轨道的总时间范围；完全为空时为 [0,0]。</summary>
        public TimeRange Range { get; }

        /// <summary>
        /// 构造多轨时间轴。
        /// </summary>
        /// <param name="tracks">轨道集合，可为 null（视为空集合）。</param>
        public MultiTrackTimeline(IEnumerable<Track> tracks)
        {
            _tracks = tracks == null
                ? new Track[0]
                : tracks.Where(t => t != null).ToArray();

            _byId = new Dictionary<string, Track>(StringComparer.Ordinal);
            for (int i = 0; i < _tracks.Length; i++)
            {
                Track track = _tracks[i];
                if (!_byId.ContainsKey(track.Id))
                {
                    _byId.Add(track.Id, track);
                }
            }

            bool any = false;
            SimTime start = new SimTime(double.PositiveInfinity);
            SimTime end = new SimTime(double.NegativeInfinity);
            for (int i = 0; i < _tracks.Length; i++)
            {
                Track track = _tracks[i];
                if (!track.HasData)
                {
                    continue;
                }

                any = true;
                if (track.Range.Start < start)
                {
                    start = track.Range.Start;
                }
                if (track.Range.End > end)
                {
                    end = track.Range.End;
                }
            }

            Range = any
                ? new TimeRange(start, end)
                : new TimeRange(SimTime.Zero, SimTime.Zero);
        }

        /// <summary>
        /// 按轨道标识查找轨道；不存在时返回 null。
        /// </summary>
        /// <param name="id">轨道标识。</param>
        /// <returns>找到的轨道或 null。</returns>
        public Track Find(string id)
        {
            if (id == null)
            {
                return null;
            }

            Track track;
            return _byId.TryGetValue(id, out track) ? track : null;
        }

        /// <summary>
        /// 按种类筛选轨道（保持原顺序）。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>匹配的轨道序列。</returns>
        public IEnumerable<Track> OfKind(TrackKind kind)
        {
            return _tracks.Where(t => t.Kind == kind);
        }

        /// <summary>
        /// 按数据源筛选轨道（保持原顺序）。
        /// </summary>
        /// <param name="sourceId">数据源标识。</param>
        /// <returns>匹配的轨道序列。</returns>
        public IEnumerable<Track> FromSource(string sourceId)
        {
            return _tracks.Where(t => string.Equals(t.SourceId, sourceId, StringComparison.Ordinal));
        }

        /// <summary>
        /// 生成指定时刻的轨道值快照（包含所有轨道；无值的轨道以 HasValue=false 表示）。
        /// </summary>
        /// <param name="t">查询时刻。</param>
        /// <returns>该时刻的快照。</returns>
        public TimelineSnapshot QueryAt(SimTime t)
        {
            TrackValue[] values = new TrackValue[_tracks.Length];
            for (int i = 0; i < _tracks.Length; i++)
            {
                Track track = _tracks[i];

                double scalar;
                bool hasValue = track.TryGetValueAt(t, out scalar);

                GeoCoord position;
                bool hasPosition = track.TryGetPositionAt(t, out position);

                TimelineSample sample;
                string text = null;
                if (track.TryGetSampleAt(t, out sample))
                {
                    text = sample.Text;
                }

                IReadOnlyList<MediaItem> media = track.MediaAt(t);

                values[i] = new TrackValue(
                    track.Id,
                    track.SourceId,
                    track.Kind,
                    hasValue,
                    hasValue ? scalar : double.NaN,
                    hasPosition,
                    position,
                    text,
                    media,
                    track.CalibrationStatus);
            }

            return new TimelineSnapshot(t, values);
        }

        /// <summary>
        /// 返回当前时间轴中仍处于未校准状态的数据源，按序数排序且去重。
        /// </summary>
        /// <returns>未校准数据源标识列表。</returns>
        public IReadOnlyList<string> UncalibratedSources()
        {
            HashSet<string> sources = new HashSet<string>(StringComparer.Ordinal);
            for (int i = 0; i < _tracks.Length; i++)
            {
                Track track = _tracks[i];
                if (track.CalibrationStatus == CalibrationStatus.Uncalibrated)
                {
                    sources.Add(track.SourceId ?? string.Empty);
                }
            }

            return sources.OrderBy(s => s, StringComparer.Ordinal).ToArray();
        }

        /// <summary>
        /// 返回所有轨道中落在指定闭区间内的事件标记，按时间排序（同一时刻按 Id 序数排序）。
        /// </summary>
        /// <param name="range">查询时间范围。</param>
        /// <returns>合并后的事件标记列表。</returns>
        public IReadOnlyList<EventMarker> MarkersIn(TimeRange range)
        {
            List<EventMarker> markers = new List<EventMarker>();
            for (int i = 0; i < _tracks.Length; i++)
            {
                markers.AddRange(_tracks[i].MarkersIn(range));
            }

            return markers
                .OrderBy(m => m.Time)
                .ThenBy(m => m.Id, StringComparer.Ordinal)
                .ToArray();
        }
    }

    /// <summary>
    /// 某一时刻的多轨快照。
    /// </summary>
    public sealed class TimelineSnapshot
    {
        private static readonly IReadOnlyList<TrackValue> EmptyValues = new TrackValue[0];

        /// <summary>快照时刻。</summary>
        public SimTime Time { get; }

        /// <summary>各轨道的取值。</summary>
        public IReadOnlyList<TrackValue> Values { get; }

        /// <summary>
        /// 构造时间轴快照。
        /// </summary>
        /// <param name="time">快照时刻。</param>
        /// <param name="values">轨道取值列表，可为 null。</param>
        public TimelineSnapshot(SimTime time, IReadOnlyList<TrackValue> values)
        {
            Time = time;
            Values = values ?? EmptyValues;
        }
    }

    /// <summary>
    /// 单条轨道在某一时刻的取值。
    /// </summary>
    public readonly struct TrackValue
    {
        /// <summary>轨道标识。</summary>
        public string TrackId { get; }

        /// <summary>数据源标识。</summary>
        public string SourceId { get; }

        /// <summary>轨道种类。</summary>
        public TrackKind Kind { get; }

        /// <summary>是否取得标量值。</summary>
        public bool HasValue { get; }

        /// <summary>标量值；无值时为 NaN。</summary>
        public double Value { get; }

        /// <summary>是否取得经纬度位置。</summary>
        public bool HasPosition { get; }

        /// <summary>经纬度位置；无位置时为默认零坐标。</summary>
        public GeoCoord Position { get; }

        /// <summary>样本附加文本，可为 null。</summary>
        public string Text { get; }

        /// <summary>该时刻处于活动状态的媒体条目。</summary>
        public IReadOnlyList<MediaItem> ActiveMedia { get; }

        /// <summary>轨道数据源的校准状态。</summary>
        public CalibrationStatus CalibrationStatus { get; }

        /// <summary>
        /// 构造轨道取值（校准状态默认为未校准）。
        /// </summary>
        /// <param name="trackId">轨道标识。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="hasValue">是否取得标量值。</param>
        /// <param name="value">标量值。</param>
        /// <param name="hasPosition">是否取得位置。</param>
        /// <param name="position">经纬度位置。</param>
        /// <param name="text">附加文本。</param>
        /// <param name="activeMedia">活动媒体列表。</param>
        public TrackValue(
            string trackId,
            string sourceId,
            TrackKind kind,
            bool hasValue,
            double value,
            bool hasPosition,
            GeoCoord position,
            string text,
            IReadOnlyList<MediaItem> activeMedia)
            : this(
                trackId,
                sourceId,
                kind,
                hasValue,
                value,
                hasPosition,
                position,
                text,
                activeMedia,
                Mcis.Domain.Timeline.CalibrationStatus.Uncalibrated)
        {
        }

        /// <summary>
        /// 构造轨道取值。
        /// </summary>
        /// <param name="trackId">轨道标识。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="hasValue">是否取得标量值。</param>
        /// <param name="value">标量值。</param>
        /// <param name="hasPosition">是否取得位置。</param>
        /// <param name="position">经纬度位置。</param>
        /// <param name="text">附加文本。</param>
        /// <param name="activeMedia">活动媒体列表。</param>
        /// <param name="calibrationStatus">校准状态。</param>
        public TrackValue(
            string trackId,
            string sourceId,
            TrackKind kind,
            bool hasValue,
            double value,
            bool hasPosition,
            GeoCoord position,
            string text,
            IReadOnlyList<MediaItem> activeMedia,
            CalibrationStatus calibrationStatus)
        {
            TrackId = trackId;
            SourceId = sourceId;
            Kind = kind;
            HasValue = hasValue;
            Value = value;
            HasPosition = hasPosition;
            Position = position;
            Text = text;
            ActiveMedia = activeMedia ?? new MediaItem[0];
            CalibrationStatus = calibrationStatus;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            if (HasPosition)
            {
                return string.Format(
                    System.Globalization.CultureInfo.InvariantCulture,
                    "{0}={1}",
                    TrackId,
                    Position);
            }

            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "{0}={1}",
                TrackId,
                HasValue ? Value.ToString("0.###", System.Globalization.CultureInfo.InvariantCulture) : "n/a");
        }
    }
}
