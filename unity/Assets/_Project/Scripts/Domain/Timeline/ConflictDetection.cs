using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 冲突检测阈值配置。各量纲阈值可分别覆盖；For 返回 null 的种类不参与比较。
    /// </summary>
    public sealed class ConflictThresholds
    {

        /// <summary>船首向差阈值（度），默认 2.0。</summary>
        public double HeadingDeg { get; set; } = 2.0;

        /// <summary>对地航向差阈值（度），默认 2.0。</summary>
        public double CourseDeg { get; set; } = 2.0;

        /// <summary>对地航速差阈值（节），默认 0.3。</summary>
        public double SpeedKn { get; set; } = 0.3;

        /// <summary>舵角差阈值（度），默认 2.0。</summary>
        public double RudderDeg { get; set; } = 2.0;

        /// <summary>转向角速度差阈值（度/分钟），默认 5.0。</summary>
        public double RateOfTurnDegPerMin { get; set; } = 5.0;

        /// <summary>位置差阈值（米），默认 50.0。</summary>
        public double PositionM { get; set; } = 50.0;

        /// <summary>目标距离差阈值（海里），默认 0.1。</summary>
        public double TargetRangeNm { get; set; } = 0.1;

        /// <summary>目标方位差阈值（度），默认 2.0。</summary>
        public double TargetBearingDeg { get; set; } = 2.0;

        /// <summary>采样步长（秒），默认 1.0。</summary>
        public double SampleStepSeconds { get; set; } = 1.0;

        /// <summary>最小冲突持续时间（秒），默认 0；短于该时长的冲突被丢弃。</summary>
        public double MinDurationSeconds { get; set; } = 0.0;

        /// <summary>目标位置（TLL）跨源差阈值（米），默认 50 m。</summary>
        public double TargetPositionM { get; set; } = 50.0;

        /// <summary>同名事件跨源时刻差阈值（秒），默认 2 s（裁定 5，P6a 默认）。</summary>
        public double EventTimeSeconds { get; set; } = 2.0;

        /// <summary>
        /// 超限判定容差（与阈值同单位）：差值 &gt; 阈值 + Tolerance 才算冲突（裁定 1 / W2-D06），默认 1e-6。
        /// </summary>
        public double Tolerance { get; set; } = 1e-6;

        /// <summary>事件名别名表：别名 → 规范名（大小写不敏感），用于跨源同名事件配对。</summary>
        public IDictionary<string, string> EventAliases { get; set; } =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

        /// <summary>默认阈值实例（全默认值）。</summary>
        public static ConflictThresholds Default
        {
            // W2-D07：每次返回新实例，避免共享可变单例污染后续 Detect(null)。
            get { return new ConflictThresholds(); }
        }

        /// <summary>
        /// 返回指定轨道种类对应的阈值；不参与比较的种类返回 null。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>阈值（单位由种类决定）或 null。</returns>
        public double? For(TrackKind kind)
        {
            switch (kind)
            {
                case TrackKind.Heading:
                    return HeadingDeg;
                case TrackKind.CourseOverGround:
                    return CourseDeg;
                case TrackKind.SpeedOverGround:
                    return SpeedKn;
                case TrackKind.RudderAngle:
                    return RudderDeg;
                case TrackKind.RateOfTurn:
                    return RateOfTurnDegPerMin;
                case TrackKind.Position:
                    return PositionM;
                case TrackKind.TargetRange:
                    return TargetRangeNm;
                case TrackKind.TargetBearing:
                    return TargetBearingDeg;
                case TrackKind.TargetPosition:
                    return TargetPositionM;
                case TrackKind.EventTime:
                    return EventTimeSeconds;
                default:
                    return null;
            }
        }
    }

    /// <summary>
    /// 一条时间轴冲突：两个不同来源的同类轨道在一段时间内差值超过阈值。
    /// </summary>
    public sealed class TimelineConflict
    {
        /// <summary>冲突编号（C-01、C-02…按开始时间排序后编号）。</summary>
        public string Id { get; }

        /// <summary>冲突涉及的轨道种类。</summary>
        public TrackKind Kind { get; }

        /// <summary>物理量名称（通常为 Kind 的英文名）。</summary>
        public string Quantity { get; }

        /// <summary>来源 A 标识。</summary>
        public string SourceA { get; }

        /// <summary>来源 A 的轨道标识。</summary>
        public string TrackIdA { get; }

        /// <summary>来源 B 标识。</summary>
        public string SourceB { get; }

        /// <summary>来源 B 的轨道标识。</summary>
        public string TrackIdB { get; }

        /// <summary>冲突区间（首个到最后一个超限采样点）。</summary>
        public TimeRange Range { get; }

        /// <summary>差值峰值时刻。</summary>
        public SimTime PeakTime { get; }

        /// <summary>峰值时刻来源 A 的取值；位置轨为 NaN。</summary>
        public double ValueA { get; }

        /// <summary>峰值时刻来源 B 的取值；位置轨为 NaN。</summary>
        public double ValueB { get; }

        /// <summary>区间内最大差值（角度为最短弧差，位置为米）。</summary>
        public double MaxDifference { get; }

        /// <summary>采用的阈值。</summary>
        public double Threshold { get; }

        /// <summary>单位文本。</summary>
        public string Unit { get; }

        /// <summary>来源 A 的校准状态。</summary>
        public CalibrationStatus CalibrationStatusA { get; }

        /// <summary>来源 B 的校准状态。</summary>
        public CalibrationStatus CalibrationStatusB { get; }

        /// <summary>是否有一方来源未校准。</summary>
        public bool InvolvesUncalibrated { get; }

        /// <summary>案件编号（合同 caseId），检测时由 DetectWithDiagnostics 写入，可为 null。</summary>
        public string CaseId { get; private set; }

        /// <summary>处理状态（合同 status），默认 Open。</summary>
        public ConflictStatus Status { get; private set; }

        /// <summary>处理说明（合同 resolution），如“标注·采信 AIS”。</summary>
        public string Resolution { get; private set; }

        /// <summary>处理人。</summary>
        public string ResolvedBy { get; private set; }

        /// <summary>处理时间。</summary>
        public DateTimeOffset? ResolvedAt { get; private set; }

        /// <summary>合同字段 conflictId（与 Id 相同）。</summary>
        public string ConflictId
        {
            get { return Id; }
        }

        /// <summary>合同字段 summary（与 Description 相同）。</summary>
        public string Summary
        {
            get { return Description; }
        }

        /// <summary>处理状态中文（如“待处理”“钟差已校正”）。</summary>
        public string StatusText
        {
            get { return ConflictStatusText.ToChinese(Status); }
        }

        /// <summary>中文描述，包含来源与数值；涉及未校准来源时末尾带提示。</summary>
        public string Description { get; }

        /// <summary>
        /// 构造时间轴冲突（兼容旧接口，不追加未校准提示）。
        /// </summary>
        /// <param name="id">冲突编号。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="quantity">物理量名称。</param>
        /// <param name="sourceA">来源 A 标识。</param>
        /// <param name="trackIdA">来源 A 轨道标识。</param>
        /// <param name="sourceB">来源 B 标识。</param>
        /// <param name="trackIdB">来源 B 轨道标识。</param>
        /// <param name="range">冲突区间。</param>
        /// <param name="peakTime">峰值时刻。</param>
        /// <param name="valueA">峰值时来源 A 取值。</param>
        /// <param name="valueB">峰值时来源 B 取值。</param>
        /// <param name="maxDifference">最大差值。</param>
        /// <param name="threshold">阈值。</param>
        /// <param name="unit">单位。</param>
        /// <param name="description">中文描述。</param>
        public TimelineConflict(
            string id,
            TrackKind kind,
            string quantity,
            string sourceA,
            string trackIdA,
            string sourceB,
            string trackIdB,
            TimeRange range,
            SimTime peakTime,
            double valueA,
            double valueB,
            double maxDifference,
            double threshold,
            string unit,
            string description)
            : this(
                id,
                kind,
                quantity,
                sourceA,
                trackIdA,
                sourceB,
                trackIdB,
                range,
                peakTime,
                valueA,
                valueB,
                maxDifference,
                threshold,
                unit,
                description,
                CalibrationStatus.Reference,
                CalibrationStatus.Reference,
                false)
        {
        }

        /// <summary>
        /// 构造时间轴冲突；涉及未校准来源时自动在描述末尾追加提示。
        /// </summary>
        /// <param name="id">冲突编号。</param>
        /// <param name="kind">轨道种类。</param>
        /// <param name="quantity">物理量名称。</param>
        /// <param name="sourceA">来源 A 标识。</param>
        /// <param name="trackIdA">来源 A 轨道标识。</param>
        /// <param name="sourceB">来源 B 标识。</param>
        /// <param name="trackIdB">来源 B 轨道标识。</param>
        /// <param name="range">冲突区间。</param>
        /// <param name="peakTime">峰值时刻。</param>
        /// <param name="valueA">峰值时来源 A 取值。</param>
        /// <param name="valueB">峰值时来源 B 取值。</param>
        /// <param name="maxDifference">最大差值。</param>
        /// <param name="threshold">阈值。</param>
        /// <param name="unit">单位。</param>
        /// <param name="description">中文描述（不含未校准提示）。</param>
        /// <param name="calibrationStatusA">来源 A 校准状态。</param>
        /// <param name="calibrationStatusB">来源 B 校准状态。</param>
        public TimelineConflict(
            string id,
            TrackKind kind,
            string quantity,
            string sourceA,
            string trackIdA,
            string sourceB,
            string trackIdB,
            TimeRange range,
            SimTime peakTime,
            double valueA,
            double valueB,
            double maxDifference,
            double threshold,
            string unit,
            string description,
            CalibrationStatus calibrationStatusA,
            CalibrationStatus calibrationStatusB)
            : this(
                id,
                kind,
                quantity,
                sourceA,
                trackIdA,
                sourceB,
                trackIdB,
                range,
                peakTime,
                valueA,
                valueB,
                maxDifference,
                threshold,
                unit,
                description,
                calibrationStatusA,
                calibrationStatusB,
                true)
        {
        }

        internal TimelineConflict(
            string id,
            TrackKind kind,
            string quantity,
            string sourceA,
            string trackIdA,
            string sourceB,
            string trackIdB,
            TimeRange range,
            SimTime peakTime,
            double valueA,
            double valueB,
            double maxDifference,
            double threshold,
            string unit,
            string description,
            CalibrationStatus calibrationStatusA,
            CalibrationStatus calibrationStatusB,
            bool appendUncalibratedSuffix)
        {
            Id = id;
            Kind = kind;
            Quantity = quantity;
            SourceA = sourceA;
            TrackIdA = trackIdA;
            SourceB = sourceB;
            TrackIdB = trackIdB;
            Range = range;
            PeakTime = peakTime;
            ValueA = valueA;
            ValueB = valueB;
            MaxDifference = maxDifference;
            Threshold = threshold;
            Unit = unit;
            CalibrationStatusA = calibrationStatusA;
            CalibrationStatusB = calibrationStatusB;
            InvolvesUncalibrated =
                calibrationStatusA == CalibrationStatus.Uncalibrated ||
                calibrationStatusB == CalibrationStatus.Uncalibrated;
            Description = appendUncalibratedSuffix
                ? AppendUncalibratedSuffix(
                    description,
                    sourceA,
                    calibrationStatusA,
                    sourceB,
                    calibrationStatusB)
                : description;
        }

        /// <summary>返回写入案件编号后的新冲突对象。</summary>
        /// <param name="caseId">案件编号。</param>
        /// <returns>新对象。</returns>
        public TimelineConflict WithCaseId(string caseId)
        {
            TimelineConflict copy = Copy(Id);
            copy.CaseId = caseId;
            return copy;
        }

        /// <summary>
        /// 返回带处理状态的新冲突对象。状态为 Resolved / AcceptedAsIs 时 resolvedBy 与 resolvedAt 必填。
        /// </summary>
        /// <param name="status">处理状态。</param>
        /// <param name="resolution">处理说明。</param>
        /// <param name="resolvedBy">处理人。</param>
        /// <param name="resolvedAt">处理时间。</param>
        /// <returns>新对象。</returns>
        public TimelineConflict WithResolution(
            ConflictStatus status,
            string resolution,
            string resolvedBy,
            DateTimeOffset? resolvedAt)
        {
            if ((status == ConflictStatus.Resolved || status == ConflictStatus.AcceptedAsIs) &&
                (string.IsNullOrWhiteSpace(resolvedBy) || !resolvedAt.HasValue))
            {
                throw new ArgumentException("状态为已解决或按现状采信时，必须给出处理人 resolvedBy 与处理时间 resolvedAt。");
            }

            TimelineConflict copy = Copy(Id);
            copy.Status = status;
            copy.Resolution = resolution;
            copy.ResolvedBy = resolvedBy;
            copy.ResolvedAt = resolvedAt;
            return copy;
        }

        internal TimelineConflict Copy(string id)
        {
            TimelineConflict copy = new TimelineConflict(
                id,
                Kind,
                Quantity,
                SourceA,
                TrackIdA,
                SourceB,
                TrackIdB,
                Range,
                PeakTime,
                ValueA,
                ValueB,
                MaxDifference,
                Threshold,
                Unit,
                Description,
                CalibrationStatusA,
                CalibrationStatusB,
                false);
            copy.CaseId = CaseId;
            copy.Status = Status;
            copy.Resolution = Resolution;
            copy.ResolvedBy = ResolvedBy;
            copy.ResolvedAt = ResolvedAt;
            return copy;
        }

        private static string AppendUncalibratedSuffix(
            string description,
            string sourceA,
            CalibrationStatus calibrationStatusA,
            string sourceB,
            CalibrationStatus calibrationStatusB)
        {
            List<string> sources = new List<string>();
            if (calibrationStatusA == CalibrationStatus.Uncalibrated &&
                !string.IsNullOrEmpty(sourceA))
            {
                sources.Add(sourceA);
            }

            if (calibrationStatusB == CalibrationStatus.Uncalibrated &&
                !string.IsNullOrEmpty(sourceB) &&
                !sources.Contains(sourceB))
            {
                sources.Add(sourceB);
            }

            if (sources.Count == 0)
            {
                return description;
            }

            return description +
                   "（含未校准来源：" + string.Join("、", sources) +
                   "，差异可能由钟差引起）";
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0} {1:F3}s..{2:F3}s {3}",
                Id,
                Range.Start.Seconds,
                Range.End.Seconds,
                Description);
        }
    }

    /// <summary>
    /// 时间轴冲突检测器：同种类、不同来源的两条轨道在时间交集上按固定步长采样，
    /// 连续超限采样合并为一条冲突。
    /// </summary>
    public static class ConflictDetector
    {
        private const double EarthRadiusM = 6371008.8;
        private const double TimeEpsilon = 1e-9;

        /// <summary>
        /// 检测跨源冲突（兼容旧接口），等价于 DetectWithDiagnostics(timeline, thresholds).Conflicts。
        /// </summary>
        /// <param name="timeline">已校准的多轨时间轴。</param>
        /// <param name="thresholds">阈值配置；null 时每次使用新的默认实例。</param>
        /// <returns>按开始时间编号的冲突列表。</returns>
        public static IReadOnlyList<TimelineConflict> Detect(
            MultiTrackTimeline timeline,
            ConflictThresholds thresholds = null)
        {
            return DetectWithDiagnostics(timeline, thresholds).Conflicts;
        }

        /// <summary>
        /// 检测跨源冲突并给出诊断：连续量（含目标量，按目标键配对）超限、同名事件时刻差超限；
        /// 无法比较的数据输出 NotAvailable 诊断，不静默跳过（裁定 4、5）。
        /// </summary>
        /// <param name="timeline">已校准的多轨时间轴。</param>
        /// <param name="thresholds">阈值配置；null 时使用新的默认实例。</param>
        /// <param name="caseId">案件编号，写入每条冲突，可为 null。</param>
        /// <returns>冲突与诊断。</returns>
        public static ConflictDetectionResult DetectWithDiagnostics(
            MultiTrackTimeline timeline,
            ConflictThresholds thresholds = null,
            string caseId = null)
        {
            List<ConflictDiagnostic> diagnostics = new List<ConflictDiagnostic>();
            if (timeline == null)
            {
                return new ConflictDetectionResult(new TimelineConflict[0], diagnostics);
            }

            ConflictThresholds config = thresholds ?? ConflictThresholds.Default;
            double tolerance = IsFinite(config.Tolerance) && config.Tolerance >= 0.0 ? config.Tolerance : 1e-6;
            List<TimelineConflict> conflicts = new List<TimelineConflict>();

            foreach (TrackKind kind in Enum.GetValues(typeof(TrackKind)))
            {
                double? threshold = config.For(kind);
                if (!threshold.HasValue || TrackKindInfo.IsMedia(kind) || kind == TrackKind.EventTime)
                {
                    continue;
                }

                List<Track> allTracks = timeline.Tracks
                    .Where(t => t.Kind == kind)
                    .OrderBy(t => t.SourceId, StringComparer.Ordinal)
                    .ThenBy(t => t.Id, StringComparer.Ordinal)
                    .ToList();
                bool targetKind = IsTargetKind(kind);
                HashSet<string> paired = new HashSet<string>(StringComparer.Ordinal);

                // W2.1/D09：相对方位轨道不参与真方位配对；逐条给出 NotAvailable 诊断。
                for (int i = 0; i < allTracks.Count; i++)
                {
                    Track relativeTrack = allTracks[i];
                    if (relativeTrack.BearingReference != BearingReference.Relative)
                    {
                        continue;
                    }

                    diagnostics.Add(new ConflictDiagnostic(
                        ConflictDiagnostic.NotAvailableCode,
                        kind,
                        relativeTrack.SourceId,
                        relativeTrack.Id,
                        string.Format(
                            CultureInfo.InvariantCulture,
                            "{0}：轨道 {1} 为相对方位（缺船首向），真方位不可用，不参与真方位比对（NotAvailable，bearing_relative_no_heading）。",
                            kind,
                            relativeTrack.Id),
                        "bearing_relative_no_heading",
                        null));
                }

                List<Track> tracks = allTracks
                    .Where(t => t.BearingReference != BearingReference.Relative)
                    .ToList();

                for (int i = 0; i < tracks.Count; i++)
                {
                    for (int j = i + 1; j < tracks.Count; j++)
                    {
                        Track trackA = tracks[i];
                        Track trackB = tracks[j];
                        if (string.Equals(trackA.SourceId, trackB.SourceId, StringComparison.Ordinal))
                        {
                            continue;
                        }

                        if (targetKind &&
                            !string.Equals(TargetKey(trackA), TargetKey(trackB), StringComparison.OrdinalIgnoreCase))
                        {
                            continue;
                        }

                        paired.Add(trackA.Id);
                        paired.Add(trackB.Id);
                        DetectPair(trackA, trackB, kind, threshold.Value, tolerance, config, conflicts, diagnostics);
                    }
                }

                if (targetKind)
                {
                    for (int i = 0; i < tracks.Count; i++)
                    {
                        if (!paired.Contains(tracks[i].Id))
                        {
                            diagnostics.Add(new ConflictDiagnostic(
                                ConflictDiagnostic.NotAvailableCode,
                                kind,
                                tracks[i].SourceId,
                                tracks[i].Id,
                                string.Format(
                                    CultureInfo.InvariantCulture,
                                    "{0}：目标「{1}」在其他数据源中没有可配对的同一目标轨，无法比对（NotAvailable）。",
                                    kind,
                                    TargetKey(tracks[i]))));
                        }
                    }
                }
            }

            DetectEventTimes(timeline, config, tolerance, conflicts);

            List<TimelineConflict> ordered = conflicts
                .OrderBy(c => c.Range.Start)
                .ThenBy(c => c.Kind)
                .ThenBy(c => c.SourceA, StringComparer.Ordinal)
                .ThenBy(c => c.SourceB, StringComparer.Ordinal)
                .ThenBy(c => c.PeakTime)
                .ThenBy(c => c.TrackIdA, StringComparer.Ordinal)
                .ThenBy(c => c.TrackIdB, StringComparer.Ordinal)
                .ToList();

            TimelineConflict[] result = new TimelineConflict[ordered.Count];
            for (int i = 0; i < ordered.Count; i++)
            {
                string id = "C-" + (i + 1).ToString("00", CultureInfo.InvariantCulture);
                TimelineConflict numbered = ordered[i].Copy(id);
                result[i] = caseId == null ? numbered : numbered.WithCaseId(caseId);
            }

            return new ConflictDetectionResult(result, diagnostics);
        }

        private static void DetectEventTimes(
            MultiTrackTimeline timeline,
            ConflictThresholds config,
            double tolerance,
            List<TimelineConflict> output)
        {
            double threshold = config.EventTimeSeconds;
            if (!IsFinite(threshold))
            {
                return;
            }

            // 源 → 规范事件名 → 按时间排序的标记
            SortedDictionary<string, Dictionary<string, List<EventMarker>>> bySource =
                new SortedDictionary<string, Dictionary<string, List<EventMarker>>>(StringComparer.Ordinal);
            foreach (Track track in timeline.Tracks)
            {
                foreach (EventMarker marker in track.Markers)
                {
                    if (marker == null || string.Equals(marker.Kind, "media", StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    string name = CanonicalEventName(marker.Label, config.EventAliases);
                    if (name.Length == 0)
                    {
                        continue;
                    }

                    string sourceId = marker.SourceId ?? track.SourceId ?? string.Empty;
                    Dictionary<string, List<EventMarker>> perName;
                    if (!bySource.TryGetValue(sourceId, out perName))
                    {
                        perName = new Dictionary<string, List<EventMarker>>(StringComparer.OrdinalIgnoreCase);
                        bySource.Add(sourceId, perName);
                    }

                    List<EventMarker> list;
                    if (!perName.TryGetValue(name, out list))
                    {
                        list = new List<EventMarker>();
                        perName.Add(name, list);
                    }

                    list.Add(marker);
                }
            }

            List<string> sources = bySource.Keys.ToList();
            for (int i = 0; i < sources.Count; i++)
            {
                for (int j = i + 1; j < sources.Count; j++)
                {
                    Dictionary<string, List<EventMarker>> a = bySource[sources[i]];
                    Dictionary<string, List<EventMarker>> b = bySource[sources[j]];
                    foreach (string name in a.Keys.OrderBy(k => k, StringComparer.OrdinalIgnoreCase))
                    {
                        List<EventMarker> listB;
                        if (!b.TryGetValue(name, out listB))
                        {
                            continue;
                        }

                        List<EventMarker> listA = a[name].OrderBy(m => m.Time).ToList();
                        listB = listB.OrderBy(m => m.Time).ToList();
                        int count = Math.Min(listA.Count, listB.Count);
                        for (int k = 0; k < count; k++)
                        {
                            EventMarker ma = listA[k];
                            EventMarker mb = listB[k];
                            double diff = Math.Abs(ma.Time.Seconds - mb.Time.Seconds);
                            if (!(diff > threshold + tolerance))
                            {
                                continue;
                            }

                            SimTime first = ma.Time < mb.Time ? ma.Time : mb.Time;
                            SimTime last = ma.Time < mb.Time ? mb.Time : ma.Time;
                            output.Add(new TimelineConflict(
                                string.Empty,
                                TrackKind.EventTime,
                                "EventTime",
                                sources[i],
                                ma.TrackId,
                                sources[j],
                                mb.TrackId,
                                new TimeRange(first, last),
                                first,
                                ma.Time.Seconds,
                                mb.Time.Seconds,
                                diff,
                                threshold,
                                "s",
                                string.Format(
                                    CultureInfo.InvariantCulture,
                                    "事件「{0}」：{1} {2:F1}s vs {3} {4:F1}s，差 {5:F1} s > {6:0.###} s",
                                    name,
                                    sources[i],
                                    ma.Time.Seconds,
                                    sources[j],
                                    mb.Time.Seconds,
                                    diff,
                                    threshold),
                                StatusOf(timeline, ma),
                                StatusOf(timeline, mb)));
                        }
                    }
                }
            }
        }

        private static CalibrationStatus StatusOf(MultiTrackTimeline timeline, EventMarker marker)
        {
            Track track = marker.TrackId == null ? null : timeline.Find(marker.TrackId);
            if (track == null)
            {
                track = timeline.FromSource(marker.SourceId).FirstOrDefault();
            }

            return track == null ? CalibrationStatus.Uncalibrated : track.CalibrationStatus;
        }

        private static string CanonicalEventName(string label, IDictionary<string, string> aliases)
        {
            string name = (label ?? string.Empty).Trim();
            if (name.Length == 0)
            {
                return name;
            }

            if (aliases != null)
            {
                foreach (KeyValuePair<string, string> alias in aliases)
                {
                    if (string.Equals((alias.Key ?? string.Empty).Trim(), name, StringComparison.OrdinalIgnoreCase))
                    {
                        name = (alias.Value ?? string.Empty).Trim();
                        break;
                    }
                }
            }

            return name.ToUpperInvariant();
        }

        /// <summary>
        /// 目标键：优先取样本 Text 中的目标名；否则取轨道 Id 中源与种类之间的目标段（如 TTM01）。
        /// </summary>
        /// <param name="track">目标类轨道。</param>
        /// <returns>大写目标键。</returns>
        public static string TargetKey(Track track)
        {
            if (track == null)
            {
                return string.Empty;
            }

            for (int i = 0; i < track.Samples.Count; i++)
            {
                string text = track.Samples[i].Text;
                if (!string.IsNullOrWhiteSpace(text))
                {
                    return text.Trim().ToUpperInvariant();
                }
            }

            string id = track.Id ?? string.Empty;
            string prefix = (track.SourceId ?? string.Empty) + "/";
            if (id.StartsWith(prefix, StringComparison.Ordinal))
            {
                id = id.Substring(prefix.Length);
            }

            int slash = id.LastIndexOf('/');
            if (slash > 0)
            {
                id = id.Substring(0, slash);
            }

            return id.ToUpperInvariant();
        }

        private static bool IsFinite(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value);
        }

        private static void DetectPair(
            Track trackA,
            Track trackB,
            TrackKind kind,
            double threshold,
            double tolerance,
            ConflictThresholds config,
            List<TimelineConflict> output,
            List<ConflictDiagnostic> diagnostics)
        {
            if (trackA.Samples.Count == 0 || trackB.Samples.Count == 0)
            {
                diagnostics.Add(new ConflictDiagnostic(
                    ConflictDiagnostic.NotAvailableCode,
                    kind,
                    trackA.Samples.Count == 0 ? trackA.SourceId : trackB.SourceId,
                    trackA.Samples.Count == 0 ? trackA.Id : trackB.Id,
                    string.Format(
                        CultureInfo.InvariantCulture,
                        "{0}：{1} 与 {2} 之一无样本，无法比对（NotAvailable）。",
                        kind,
                        trackA.Id,
                        trackB.Id)));
                return;
            }

            SimTime start = trackA.Samples[0].Time > trackB.Samples[0].Time
                ? trackA.Samples[0].Time
                : trackB.Samples[0].Time;
            SimTime end = trackA.Samples[trackA.Samples.Count - 1].Time < trackB.Samples[trackB.Samples.Count - 1].Time
                ? trackA.Samples[trackA.Samples.Count - 1].Time
                : trackB.Samples[trackB.Samples.Count - 1].Time;

            if (end < start)
            {
                diagnostics.Add(new ConflictDiagnostic(
                    ConflictDiagnostic.NotAvailableCode,
                    kind,
                    trackA.SourceId,
                    trackA.Id,
                    string.Format(
                        CultureInfo.InvariantCulture,
                        "{0}：{1} 与 {2} 时间范围不重叠，无法比对（NotAvailable）。",
                        kind,
                        trackA.Id,
                        trackB.Id)));
                return;
            }

            int missing = 0;
            double step = config.SampleStepSeconds;
            if (double.IsNaN(step) || double.IsInfinity(step) || step <= 0.0)
            {
                step = 1.0;
            }

            List<double> times = new List<double>();
            for (double t = start.Seconds; t <= end.Seconds + TimeEpsilon; t += step)
            {
                times.Add(t);
            }

            if (times.Count == 0 || times[times.Count - 1] < end.Seconds - TimeEpsilon)
            {
                times.Add(end.Seconds);
            }

            bool inRun = false;
            SimTime runStart = SimTime.Zero;
            SimTime runEnd = SimTime.Zero;
            SimTime peakTime = SimTime.Zero;
            double peakDiff = 0.0;
            double peakA = double.NaN;
            double peakB = double.NaN;

            bool inInvalidRun = false;
            SimTime invalidStart = SimTime.Zero;
            SimTime invalidEnd = SimTime.Zero;

            for (int i = 0; i < times.Count; i++)
            {
                SimTime time = new SimTime(times[i]);
                double valueA;
                double valueB;
                double difference;
                bool invalid;

                if (kind == TrackKind.Position || kind == TrackKind.TargetPosition)
                {
                    GeoCoord positionA;
                    GeoCoord positionB;
                    if (!trackA.TryGetPositionAt(time, out positionA) ||
                        !trackB.TryGetPositionAt(time, out positionB))
                    {
                        missing++;
                        FinishInvalidRun(ref inInvalidRun, invalidStart, invalidEnd,
                            trackA, trackB, kind, diagnostics);
                        FinishRun(ref inRun, runStart, runEnd, peakTime, peakDiff, peakA, peakB,
                            trackA, trackB, kind, threshold, config.MinDurationSeconds, output);
                        continue;
                    }

                    invalid = !IsFinite(positionA.LonDeg) || !IsFinite(positionA.LatDeg) ||
                              !IsFinite(positionA.HeightM) || !IsFinite(positionB.LonDeg) ||
                              !IsFinite(positionB.LatDeg) || !IsFinite(positionB.HeightM);
                    difference = invalid ? double.NaN : HaversineM(positionA, positionB);
                    if (!invalid && !IsFinite(difference))
                    {
                        invalid = true;
                    }

                    valueA = double.NaN;
                    valueB = double.NaN;
                }
                else
                {
                    if (!trackA.TryGetValueAt(time, out valueA) ||
                        !trackB.TryGetValueAt(time, out valueB))
                    {
                        missing++;
                        FinishInvalidRun(ref inInvalidRun, invalidStart, invalidEnd,
                            trackA, trackB, kind, diagnostics);
                        FinishRun(ref inRun, runStart, runEnd, peakTime, peakDiff, peakA, peakB,
                            trackA, trackB, kind, threshold, config.MinDurationSeconds, output);
                        continue;
                    }

                    invalid = !IsFinite(valueA) || !IsFinite(valueB);
                    difference = invalid
                        ? double.NaN
                        : (TrackKindInfo.IsAngular(kind)
                            ? AngleMath.AbsoluteDiff(valueA, valueB)
                            : Math.Abs(valueA - valueB));
                    if (!invalid && !IsFinite(difference))
                    {
                        invalid = true;
                    }
                }

                // W2.1/D10：NaN/±∞ 不参与比较，结束超限区段，并按连续无效时刻合并成诊断区段。
                if (invalid)
                {
                    if (!inInvalidRun)
                    {
                        inInvalidRun = true;
                        invalidStart = time;
                        invalidEnd = time;
                    }
                    else
                    {
                        invalidEnd = time;
                    }

                    FinishRun(ref inRun, runStart, runEnd, peakTime, peakDiff, peakA, peakB,
                        trackA, trackB, kind, threshold, config.MinDurationSeconds, output);
                    continue;
                }

                if (inInvalidRun)
                {
                    FinishInvalidRun(ref inInvalidRun, invalidStart, invalidEnd,
                        trackA, trackB, kind, diagnostics);
                }

                // 裁定 1 / W2-D06：严格大于且加容差，差值等于阈值（含浮点误差）不算冲突。
                bool exceeds = difference > threshold + tolerance;
                if (exceeds)
                {
                    if (!inRun)
                    {
                        inRun = true;
                        runStart = time;
                        runEnd = time;
                        peakTime = time;
                        peakDiff = difference;
                        peakA = valueA;
                        peakB = valueB;
                    }
                    else
                    {
                        runEnd = time;
                        if (difference > peakDiff)
                        {
                            peakDiff = difference;
                            peakTime = time;
                            peakA = valueA;
                            peakB = valueB;
                        }
                    }
                }
                else
                {
                    FinishRun(ref inRun, runStart, runEnd, peakTime, peakDiff, peakA, peakB,
                        trackA, trackB, kind, threshold, config.MinDurationSeconds, output);
                }
            }

            FinishInvalidRun(ref inInvalidRun, invalidStart, invalidEnd,
                trackA, trackB, kind, diagnostics);
            FinishRun(ref inRun, runStart, runEnd, peakTime, peakDiff, peakA, peakB,
                trackA, trackB, kind, threshold, config.MinDurationSeconds, output);

            if (missing > 0)
            {
                diagnostics.Add(new ConflictDiagnostic(
                    ConflictDiagnostic.NotAvailableCode,
                    kind,
                    trackA.SourceId,
                    trackA.Id,
                    string.Format(
                        CultureInfo.InvariantCulture,
                        "{0}：{1} 与 {2} 的重叠区间内有 {3} 个采样点无有效数据（NotAvailable）。",
                        kind,
                        trackA.Id,
                        trackB.Id,
                        missing)));
            }
        }

        private static void FinishRun(
            ref bool inRun,
            SimTime runStart,
            SimTime runEnd,
            SimTime peakTime,
            double peakDiff,
            double peakA,
            double peakB,
            Track trackA,
            Track trackB,
            TrackKind kind,
            double threshold,
            double minDurationSeconds,
            List<TimelineConflict> output)
        {
            if (!inRun)
            {
                return;
            }

            inRun = false;
            double duration = runEnd.Seconds - runStart.Seconds;
            if (duration < 0.0 || duration < minDurationSeconds)
            {
                return;
            }
            output.Add(new TimelineConflict(
                string.Empty,
                kind,
                kind.ToString(),
                trackA.SourceId,
                trackA.Id,
                trackB.SourceId,
                trackB.Id,
                new TimeRange(runStart, runEnd),
                peakTime,
                peakA,
                peakB,
                peakDiff,
                threshold,
                string.IsNullOrEmpty(trackA.Unit) ? TrackKindInfo.DefaultUnit(kind) : trackA.Unit,
                BuildDescription(kind, trackA.SourceId, trackB.SourceId, peakA, peakB, peakDiff, threshold),
                trackA.CalibrationStatus,
                trackB.CalibrationStatus));
        }

        private static void FinishInvalidRun(
            ref bool inInvalidRun,
            SimTime invalidStart,
            SimTime invalidEnd,
            Track trackA,
            Track trackB,
            TrackKind kind,
            List<ConflictDiagnostic> diagnostics)
        {
            if (!inInvalidRun)
            {
                return;
            }

            inInvalidRun = false;
            TimeRange range = new TimeRange(invalidStart, invalidEnd);
            diagnostics.Add(new ConflictDiagnostic(
                ConflictDiagnostic.NotAvailableCode,
                kind,
                trackA.SourceId,
                trackA.Id,
                string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}：{1} 与 {2} 在 {3:F3}s..{4:F3}s 存在无效数值（NaN/±∞），无法比对（NotAvailable，{5}）。",
                    kind,
                    trackA.Id,
                    trackB.Id,
                    range.Start.Seconds,
                    range.End.Seconds,
                    ConflictDiagnostic.InvalidNumberReason),
                ConflictDiagnostic.InvalidNumberReason,
                range));
        }

        private static bool IsTargetKind(TrackKind kind)
        {
            return kind == TrackKind.TargetRange ||
                   kind == TrackKind.TargetBearing ||
                   kind == TrackKind.TargetPosition;
        }

        private static double HaversineM(GeoCoord a, GeoCoord b)
        {
            const double degreesToRadians = Math.PI / 180.0;
            double lat1 = a.LatDeg * degreesToRadians;
            double lat2 = b.LatDeg * degreesToRadians;
            double dLat = (b.LatDeg - a.LatDeg) * degreesToRadians;
            double dLon = (b.LonDeg - a.LonDeg) * degreesToRadians;

            double sinLat = Math.Sin(dLat * 0.5);
            double sinLon = Math.Sin(dLon * 0.5);
            double h = sinLat * sinLat + Math.Cos(lat1) * Math.Cos(lat2) * sinLon * sinLon;
            if (h < 0.0)
            {
                h = 0.0;
            }
            if (h > 1.0)
            {
                h = 1.0;
            }

            return 2.0 * EarthRadiusM * Math.Asin(Math.Sqrt(h));
        }

        private static string BuildDescription(
            TrackKind kind,
            string sourceA,
            string sourceB,
            double valueA,
            double valueB,
            double maxDifference,
            double threshold)
        {
            if (kind == TrackKind.Position || kind == TrackKind.TargetPosition)
            {
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}: {1} 与 {2} 位置差 {3:F1}m > {4:0.###}m",
                    kind,
                    sourceA,
                    sourceB,
                    maxDifference,
                    threshold);
            }

            if (TrackKindInfo.IsAngular(kind))
            {
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}: {1} {2:F1}° vs {3} {4:F1}°，差 {5:F1}° > {6:0.###}°",
                    kind,
                    sourceA,
                    valueA,
                    sourceB,
                    valueB,
                    maxDifference,
                    threshold);
            }

            string unit = TrackKindInfo.DefaultUnit(kind);
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}: {1} {2:F3}{3} vs {4} {5:F3}{3}，差 {6:F3}{3} > {7:0.###}{3}",
                kind,
                sourceA,
                valueA,
                unit,
                sourceB,
                valueB,
                maxDifference,
                threshold);
        }
    }

    /// <summary>冲突处理状态；与 contracts/schemas/conflict.schema.json 的 status 枚举完全一致（W2.1）。</summary>
    public enum ConflictStatus
    {
        /// <summary>待处理。</summary>
        Open = 0,
        /// <summary>待询问核实。</summary>
        PendingInterview = 1,
        /// <summary>钟差已校正。</summary>
        ClockCorrected = 2,
        /// <summary>已标注。</summary>
        Annotated = 3,
        /// <summary>已解决。</summary>
        Resolved = 4,
        /// <summary>按现状采信（如“待定·采信 AIS”）。</summary>
        AcceptedAsIs = 5
    }

    /// <summary>冲突处理状态中文。</summary>
    public static class ConflictStatusText
    {
        /// <summary>返回状态中文。</summary>
        /// <param name="status">处理状态。</param>
        /// <returns>中文文本。</returns>
        public static string ToChinese(ConflictStatus status)
        {
            switch (status)
            {
                case ConflictStatus.PendingInterview:
                    return "待询问核实";
                case ConflictStatus.ClockCorrected:
                    return "钟差已校正";
                case ConflictStatus.Annotated:
                    return "已标注";
                case ConflictStatus.Resolved:
                    return "已解决";
                case ConflictStatus.AcceptedAsIs:
                    return "按现状采信";
                default:
                    return "待处理";
            }
        }
    }

    /// <summary>冲突检测诊断（如数据缺失无法比对时的 NotAvailable）。</summary>
    public sealed class ConflictDiagnostic
    {
        /// <summary>数据缺失、无法比对的诊断代码。</summary>
        public const string NotAvailableCode = "NotAvailable";

        /// <summary>无效数值（NaN/±∞）导致的 NotAvailable 原因代码（W2.1/D10，与 W3 D08 一致）。</summary>
        public const string InvalidNumberReason = "inv_invalid_number";

        /// <summary>诊断代码。</summary>
        public string Code { get; }

        /// <summary>量值种类。</summary>
        public TrackKind Kind { get; }

        /// <summary>相关数据源。</summary>
        public string SourceId { get; }

        /// <summary>相关轨道。</summary>
        public string TrackId { get; }

        /// <summary>中文说明。</summary>
        public string Message { get; }

        /// <summary>NotAvailable 的具体原因（如 inv_invalid_number、bearing_relative_no_heading）；无原因时为 null。</summary>
        public string Reason { get; }

        /// <summary>无效数值等诊断对应的采样时间区间；无区间时为 null。</summary>
        public TimeRange? Range { get; }

        /// <summary>构造诊断。</summary>
        /// <param name="code">诊断代码。</param>
        /// <param name="kind">量值种类。</param>
        /// <param name="sourceId">数据源。</param>
        /// <param name="trackId">轨道。</param>
        /// <param name="message">中文说明。</param>
        public ConflictDiagnostic(string code, TrackKind kind, string sourceId, string trackId, string message)
            : this(code, kind, sourceId, trackId, message, null, null)
        {
        }

        /// <summary>构造带原因与时间区间的诊断（W2.1/D09、D10）。</summary>
        /// <param name="code">诊断代码。</param>
        /// <param name="kind">量值种类。</param>
        /// <param name="sourceId">数据源。</param>
        /// <param name="trackId">轨道。</param>
        /// <param name="message">中文说明。</param>
        /// <param name="reason">NotAvailable 原因，可为 null。</param>
        /// <param name="range">相关时间区间，可为 null。</param>
        public ConflictDiagnostic(
            string code,
            TrackKind kind,
            string sourceId,
            string trackId,
            string message,
            string reason,
            TimeRange? range)
        {
            Code = code;
            Kind = kind;
            SourceId = sourceId;
            TrackId = trackId;
            Message = message;
            Reason = reason;
            Range = range;
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return Code + " " + Kind + " " + TrackId + ": " + Message;
        }
    }

    /// <summary>冲突检测结果：冲突列表与诊断列表。</summary>
    public sealed class ConflictDetectionResult
    {
        /// <summary>按开始时间编号的冲突。</summary>
        public IReadOnlyList<TimelineConflict> Conflicts { get; }

        /// <summary>诊断（NotAvailable 等）。</summary>
        public IReadOnlyList<ConflictDiagnostic> Diagnostics { get; }

        /// <summary>构造结果。</summary>
        /// <param name="conflicts">冲突列表。</param>
        /// <param name="diagnostics">诊断列表。</param>
        public ConflictDetectionResult(
            IReadOnlyList<TimelineConflict> conflicts,
            IReadOnlyList<ConflictDiagnostic> diagnostics)
        {
            Conflicts = conflicts ?? new TimelineConflict[0];
            Diagnostics = diagnostics ?? new ConflictDiagnostic[0];
        }
    }
}
