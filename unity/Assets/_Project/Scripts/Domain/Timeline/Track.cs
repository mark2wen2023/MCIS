using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 单一数据源、单一物理量的时间轴轨道。样本按时间稳定排序，
    /// 查询使用二分查找，避免对样本做线性扫描。
    /// </summary>
    public sealed class Track
    {
        private static readonly IReadOnlyList<TimelineSample> EmptySamples =
            new TimelineSample[0];
        private static readonly IReadOnlyList<EventMarker> EmptyMarkers =
            new EventMarker[0];
        private static readonly IReadOnlyList<MediaItem> EmptyMedia =
            new MediaItem[0];

        private readonly TimelineSample[] _samples;

        /// <summary>轨道唯一标识（如 "MARY-VDR/Heading"）。</summary>
        public string Id { get; }

        /// <summary>轨道所属数据源标识（如 "MARY-VDR"）。</summary>
        public string SourceId { get; }

        /// <summary>轨道数据种类。</summary>
        public TrackKind Kind { get; }

        /// <summary>方位参考基准；非方位轨道及真方位轨道为 True，缺船首向的相对方位为 Relative（W2.1/D09）。</summary>
        public BearingReference BearingReference { get; }

        /// <summary>轨道单位。</summary>
        public string Unit { get; }

        /// <summary>按时间升序排列的样本列表。</summary>
        public IReadOnlyList<TimelineSample> Samples
        {
            get { return _samples; }
        }

        /// <summary>按时间升序排列的事件标记。</summary>
        public IReadOnlyList<EventMarker> Markers { get; }

        /// <summary>按开始时间升序排列的媒体条目。</summary>
        public IReadOnlyList<MediaItem> Media { get; }

        /// <summary>轨道是否包含任何样本、标记或媒体。</summary>
        public bool HasData { get; }

        /// <summary>
        /// 样本、媒体与事件标记的总时间范围；完全为空时为 [0,0] 且 HasData=false。
        /// </summary>
        public TimeRange Range { get; }

        /// <summary>数据源时间校准状态；导入得到的轨道默认为未校准。</summary>
        public CalibrationStatus CalibrationStatus { get; }

        /// <summary>
        /// 已应用到轨道时间的平移量（秒，= −钟差）；未校准时为 0。
        /// </summary>
        public double AppliedOffsetSeconds { get; }

        /// <summary>
        /// 构造轨道。样本会按时间稳定排序；标记与媒体同样按时间排序。
        /// 校准状态默认为未校准。
        /// </summary>
        /// <param name="id">轨道唯一标识。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="unit">单位文本，可为 null（自动使用默认单位）。</param>
        /// <param name="samples">样本集合，可为 null。</param>
        /// <param name="markers">事件标记集合，可为 null。</param>
        /// <param name="media">媒体条目集合，可为 null。</param>
        public Track(
            string id,
            string sourceId,
            TrackKind kind,
            string unit,
            IEnumerable<TimelineSample> samples,
            IEnumerable<EventMarker> markers = null,
            IEnumerable<MediaItem> media = null)
            : this(
                id,
                sourceId,
                kind,
                unit,
                samples,
                markers,
                media,
                Mcis.Domain.Timeline.CalibrationStatus.Uncalibrated,
                0.0,
                BearingReference.True)
        {
        }

        /// <summary>
        /// 构造轨道并指定方位参考基准。样本会按时间稳定排序；标记与媒体同样按时间排序。
        /// 校准状态默认为未校准。
        /// </summary>
        /// <param name="id">轨道唯一标识。</param>
        /// <param name="sourceId">数据源标识。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="unit">单位文本，可为 null（自动使用默认单位）。</param>
        /// <param name="samples">样本集合，可为 null。</param>
        /// <param name="markers">事件标记集合，可为 null。</param>
        /// <param name="media">媒体条目集合，可为 null。</param>
        /// <param name="bearingReference">方位参考基准。</param>
        public Track(
            string id,
            string sourceId,
            TrackKind kind,
            string unit,
            IEnumerable<TimelineSample> samples,
            IEnumerable<EventMarker> markers,
            IEnumerable<MediaItem> media,
            BearingReference bearingReference)
            : this(
                id,
                sourceId,
                kind,
                unit,
                samples,
                markers,
                media,
                Mcis.Domain.Timeline.CalibrationStatus.Uncalibrated,
                0.0,
                bearingReference)
        {
        }

        private Track(
            string id,
            string sourceId,
            TrackKind kind,
            string unit,
            IEnumerable<TimelineSample> samples,
            IEnumerable<EventMarker> markers,
            IEnumerable<MediaItem> media,
            CalibrationStatus calibrationStatus,
            double appliedOffsetSeconds,
            BearingReference bearingReference)
        {
            if (id == null)
            {
                throw new ArgumentNullException(nameof(id));
            }

            Id = id;
            CalibrationStatus = calibrationStatus;
            AppliedOffsetSeconds = appliedOffsetSeconds;
            BearingReference = bearingReference;
            SourceId = sourceId ?? string.Empty;
            Kind = kind;
            Unit = unit ?? TrackKindInfo.DefaultUnit(kind);

            _samples = samples == null
                ? new TimelineSample[0]
                : samples.OrderBy(s => s.Time).ToArray();

            Markers = markers == null
                ? EmptyMarkers
                : markers.OrderBy(m => m.Time).ToArray();

            Media = media == null
                ? EmptyMedia
                : media.OrderBy(m => m.Range.Start).ToArray();

            bool hasData = _samples.Length > 0 || Markers.Count > 0 || Media.Count > 0;
            HasData = hasData;
            if (!hasData)
            {
                Range = new TimeRange(SimTime.Zero, SimTime.Zero);
                return;
            }

            SimTime start = new SimTime(double.PositiveInfinity);
            SimTime end = new SimTime(double.NegativeInfinity);

            if (_samples.Length > 0)
            {
                start = _samples[0].Time;
                end = _samples[_samples.Length - 1].Time;
            }

            for (int i = 0; i < Markers.Count; i++)
            {
                EventMarker marker = Markers[i];
                if (marker.Time < start)
                {
                    start = marker.Time;
                }
                if (marker.Time > end)
                {
                    end = marker.Time;
                }
            }

            for (int i = 0; i < Media.Count; i++)
            {
                MediaItem item = Media[i];
                if (item.Range.Start < start)
                {
                    start = item.Range.Start;
                }
                if (item.Range.End > end)
                {
                    end = item.Range.End;
                }
            }

            Range = new TimeRange(start, end);
        }

        /// <summary>
        /// 查询指定时刻的标量值。范围外返回 false；位置轨道返回 false；
        /// 标量做线性插值；角度量按最短弧插值并归一到 [0,360)；阶跃量取 t 之前最近值。
        /// </summary>
        /// <param name="t">查询时刻。</param>
        /// <param name="value">查询到的值。</param>
        /// <returns>查询成功返回 true。</returns>
        public bool TryGetValueAt(SimTime t, out double value)
        {
            value = double.NaN;
            if (_samples.Length == 0 || IsPositionKind(Kind))
            {
                return false;
            }

            if (t < _samples[0].Time || t > _samples[_samples.Length - 1].Time)
            {
                return false;
            }

            int index = FindAtOrBefore(t);
            if (index < 0)
            {
                return false;
            }

            TimelineSample left = _samples[index];
            if (index >= _samples.Length - 1 || left.Time == t)
            {
                value = left.Value;
                return true;
            }

            if (TrackKindInfo.IsStep(Kind))
            {
                value = left.Value;
                return true;
            }

            TimelineSample right = _samples[index + 1];
            double span = right.Time.Seconds - left.Time.Seconds;
            if (span <= 0.0)
            {
                value = left.Value;
                return true;
            }

            double fraction = (t.Seconds - left.Time.Seconds) / span;
            if (TrackKindInfo.IsAngular(Kind))
            {
                double diff = AngleMath.ShortestDiff(left.Value, right.Value);
                value = AngleMath.Normalize360(left.Value + diff * fraction);
            }
            else
            {
                value = left.Value + (right.Value - left.Value) * fraction;
            }

            return true;
        }

        /// <summary>
        /// 查询指定时刻的经纬度位置（仅位置轨道有效）。经纬度按线性插值。
        /// </summary>
        /// <param name="t">查询时刻。</param>
        /// <param name="p">查询到的位置。</param>
        /// <returns>查询成功返回 true。</returns>
        public bool TryGetPositionAt(SimTime t, out GeoCoord p)
        {
            p = default(GeoCoord);
            if (_samples.Length == 0 || !IsPositionKind(Kind))
            {
                return false;
            }

            if (t < _samples[0].Time || t > _samples[_samples.Length - 1].Time)
            {
                return false;
            }

            int index = FindAtOrBefore(t);
            if (index < 0)
            {
                return false;
            }

            TimelineSample left = _samples[index];
            if (!left.HasPosition)
            {
                return false;
            }

            if (index >= _samples.Length - 1 || left.Time == t)
            {
                p = left.Position;
                return true;
            }

            TimelineSample right = _samples[index + 1];
            if (!right.HasPosition)
            {
                p = left.Position;
                return true;
            }

            double span = right.Time.Seconds - left.Time.Seconds;
            if (span <= 0.0)
            {
                p = left.Position;
                return true;
            }

            double fraction = (t.Seconds - left.Time.Seconds) / span;
            double lon = left.Position.LonDeg +
                         (right.Position.LonDeg - left.Position.LonDeg) * fraction;
            double lat = left.Position.LatDeg +
                         (right.Position.LatDeg - left.Position.LatDeg) * fraction;
            double height = left.Position.HeightM +
                            (right.Position.HeightM - left.Position.HeightM) * fraction;
            p = new GeoCoord(lon, lat, height);
            return true;
        }

        /// <summary>
        /// 查询指定时刻“最近的前一个样本”，用于取得阶跃值文本（如车钟档位、目标名称）。
        /// 时刻早于首个样本或晚于末个样本时返回 false。
        /// </summary>
        /// <param name="t">查询时刻。</param>
        /// <param name="s">查询到的样本。</param>
        /// <returns>查询成功返回 true。</returns>
        public bool TryGetSampleAt(SimTime t, out TimelineSample s)
        {
            s = default(TimelineSample);
            if (_samples.Length == 0)
            {
                return false;
            }

            if (t < _samples[0].Time || t > _samples[_samples.Length - 1].Time)
            {
                return false;
            }

            int index = FindAtOrBefore(t);
            if (index < 0)
            {
                return false;
            }

            s = _samples[index];
            return true;
        }

        /// <summary>
        /// 返回落在指定闭区间内的事件标记，按时间升序。
        /// </summary>
        /// <param name="range">查询时间范围。</param>
        /// <returns>事件标记列表。</returns>
        public IReadOnlyList<EventMarker> MarkersIn(TimeRange range)
        {
            List<EventMarker> result = new List<EventMarker>();
            for (int i = 0; i < Markers.Count; i++)
            {
                EventMarker marker = Markers[i];
                if (range.Contains(marker.Time))
                {
                    result.Add(marker);
                }
            }

            return result;
        }

        /// <summary>
        /// 返回在指定时刻处于活动状态的媒体条目，按开始时间升序。
        /// </summary>
        /// <param name="t">查询时刻。</param>
        /// <returns>活动媒体列表。</returns>
        public IReadOnlyList<MediaItem> MediaAt(SimTime t)
        {
            List<MediaItem> result = new List<MediaItem>();
            for (int i = 0; i < Media.Count; i++)
            {
                MediaItem item = Media[i];
                if (item.Range.Contains(t))
                {
                    result.Add(item);
                }
            }

            return result;
        }

        /// <summary>
        /// 返回所有样本、事件标记与媒体时间整体平移后的新轨道（不修改原对象）。
        /// </summary>
        /// <param name="seconds">平移秒数，可为负。</param>
        /// <returns>新的轨道对象。</returns>
        public Track WithTimeShift(double seconds)
        {
            TimelineSample[] samples = new TimelineSample[_samples.Length];
            for (int i = 0; i < _samples.Length; i++)
            {
                TimelineSample sample = _samples[i];
                SimTime time = sample.Time + seconds;
                samples[i] = sample.HasPosition
                    ? TimelineSample.AtPosition(time, sample.Position, sample.Text)
                    : TimelineSample.Scalar(time, sample.Value, sample.Text);
            }

            EventMarker[] markers = new EventMarker[Markers.Count];
            for (int i = 0; i < Markers.Count; i++)
            {
                EventMarker marker = Markers[i];
                markers[i] = new EventMarker(
                    marker.Id,
                    marker.Time + seconds,
                    marker.Kind,
                    marker.Label,
                    marker.SourceId,
                    marker.TrackId);
            }

            MediaItem[] media = new MediaItem[Media.Count];
            for (int i = 0; i < Media.Count; i++)
            {
                media[i] = Media[i].Shift(seconds);
            }

            return new Track(
                Id,
                SourceId,
                Kind,
                Unit,
                samples,
                markers,
                media,
                CalibrationStatus,
                AppliedOffsetSeconds,
                BearingReference);
        }

        /// <summary>
        /// 返回带有指定校准状态与已应用平移量的新轨道（不修改原对象）。
        /// </summary>
        /// <param name="status">校准状态。</param>
        /// <param name="appliedOffsetSeconds">已应用到轨道时间的平移量（秒，= −钟差）。</param>
        /// <returns>新的轨道对象。</returns>
        public Track WithCalibration(CalibrationStatus status, double appliedOffsetSeconds)
        {
            return new Track(
                Id,
                SourceId,
                Kind,
                Unit,
                _samples,
                Markers,
                Media,
                status,
                appliedOffsetSeconds,
                BearingReference);
        }

        private static bool IsPositionKind(TrackKind kind)
        {
            return kind == TrackKind.Position || kind == TrackKind.TargetPosition;
        }

        /// <summary>
        /// 二分查找最后一个时间不大于 t 的样本下标；不存在时返回 -1。
        /// </summary>
        private int FindAtOrBefore(SimTime t)
        {
            int low = 0;
            int high = _samples.Length - 1;
            int answer = -1;
            while (low <= high)
            {
                int mid = low + ((high - low) >> 1);
                if (_samples[mid].Time <= t)
                {
                    answer = mid;
                    low = mid + 1;
                }
                else
                {
                    high = mid - 1;
                }
            }

            return answer;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                System.Globalization.CultureInfo.InvariantCulture,
                "{0} ({1}/{2}) n={3} range={4}",
                Id,
                SourceId,
                Kind,
                _samples.Length,
                Range);
        }
    }
}
