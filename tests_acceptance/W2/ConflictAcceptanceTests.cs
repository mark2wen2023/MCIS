using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using Mcis.Domain.Timeline;
using Xunit;

namespace Mcis.Acceptance.W2
{
    /// <summary>
    /// 冲突检测：阈值刚好等于/略超、最短持续时间边界、编号格式/唯一/连续。
    /// </summary>
    public class ConflictAcceptanceTests
    {
        private static readonly Regex ConflictIdPattern = new Regex("^C-[0-9]{2,}$", RegexOptions.CultureInvariant);

        [Fact]
        public void Speed_EqualToThreshold_IsNotConflict()
        {
            // 默认航速阈值 0.3 kn；差刚好等于阈值不应判冲突（实现为严格大于）。
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 12.3)
            });

            Assert.Empty(ConflictDetector.Detect(timeline));
        }

        [Fact]
        public void Speed_SlightlyOverThreshold_IsConflict()
        {
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 10, 12.0),
                W2AccFixture.Constant("B/SOG", "B", TrackKind.SpeedOverGround, 0, 10, 12.31)
            });

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(timeline);
            Assert.Single(conflicts);
            Assert.True(conflicts[0].MaxDifference > 0.3);
            Assert.Equal(0.3, conflicts[0].Threshold, 9);
        }

        [Fact]
        public void Heading_EqualToThreshold_IsNotConflict_SlightlyOverIs()
        {
            MultiTrackTimeline equal = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                W2AccFixture.Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 2.0)
            });
            Assert.Empty(ConflictDetector.Detect(equal));

            MultiTrackTimeline over = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 0.0),
                W2AccFixture.Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 2.01)
            });
            Assert.Single(ConflictDetector.Detect(over));
        }

        [Fact]
        public void Heading_AcrossZero_UsesShortestArcForThreshold()
        {
            // 359° 与 1° 最短弧差 2°，等于默认阈值，不应冲突；1.5° 应冲突。
            MultiTrackTimeline equal = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 359.0),
                W2AccFixture.Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 1.0)
            });
            Assert.Empty(ConflictDetector.Detect(equal));

            MultiTrackTimeline over = new MultiTrackTimeline(new[]
            {
                W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 10, 359.0),
                W2AccFixture.Constant("B/HDG", "B", TrackKind.Heading, 0, 10, 1.5)
            });
            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(over);
            Assert.Single(conflicts);
            Assert.Equal(2.5, conflicts[0].MaxDifference, 9);
        }

        [Fact]
        public void MinDuration_EqualToLimit_IsKept_SlightlyUnderIsDropped()
        {
            // A 恒 0°，B 在 0–4 s 超限（差 5°），之后回到 0。采样步长 1 s，持续 4 s。
            Track a = W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 20, 0.0);
            Track b = W2AccFixture.ScalarTrack(
                "B/HDG", "B", TrackKind.Heading,
                W2AccFixture.S(0, 5.0),
                W2AccFixture.S(4, 5.0),
                W2AccFixture.S(5, 0.0),
                W2AccFixture.S(20, 0.0));
            MultiTrackTimeline timeline = new MultiTrackTimeline(new[] { a, b });

            ConflictThresholds equal = new ConflictThresholds { MinDurationSeconds = 4.0, SampleStepSeconds = 1.0 };
            Assert.Single(ConflictDetector.Detect(timeline, equal));

            ConflictThresholds slightlyOver = new ConflictThresholds { MinDurationSeconds = 4.001, SampleStepSeconds = 1.0 };
            Assert.Empty(ConflictDetector.Detect(timeline, slightlyOver));
        }

        [Fact]
        public void ConflictIds_MatchContractPattern_AreUniqueAndContiguous()
        {
            Track headingA = W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 100, 0.0);
            Track headingB = W2AccFixture.ScalarTrack(
                "B/HDG", "B", TrackKind.Heading,
                W2AccFixture.S(0, 0.0), W2AccFixture.S(20, 0.0),
                W2AccFixture.S(30, 3.0), W2AccFixture.S(40, 3.0),
                W2AccFixture.S(50, 0.0), W2AccFixture.S(100, 0.0));
            Track courseA = W2AccFixture.Constant("A/COG", "A", TrackKind.CourseOverGround, 0, 100, 0.0);
            Track courseB = W2AccFixture.ScalarTrack(
                "B/COG", "B", TrackKind.CourseOverGround,
                W2AccFixture.S(0, 0.0), W2AccFixture.S(10, 3.0),
                W2AccFixture.S(20, 3.0), W2AccFixture.S(30, 0.0),
                W2AccFixture.S(100, 0.0));
            Track speedA = W2AccFixture.Constant("A/SOG", "A", TrackKind.SpeedOverGround, 0, 100, 0.0);
            Track speedB = W2AccFixture.ScalarTrack(
                "B/SOG", "B", TrackKind.SpeedOverGround,
                W2AccFixture.S(0, 0.0), W2AccFixture.S(10, 0.0),
                W2AccFixture.S(20, 0.5), W2AccFixture.S(30, 0.5),
                W2AccFixture.S(40, 0.0), W2AccFixture.S(100, 0.0));

            IReadOnlyList<TimelineConflict> conflicts = ConflictDetector.Detect(
                new MultiTrackTimeline(new[] { headingA, courseA, speedA, headingB, courseB, speedB }));

            Assert.Equal(3, conflicts.Count);
            for (int i = 0; i < conflicts.Count; i++)
            {
                Assert.Matches(ConflictIdPattern, conflicts[i].Id);
                string expected = "C-" + (i + 1).ToString("00");
                Assert.Equal(expected, conflicts[i].Id);
            }

            Assert.Equal(conflicts.Count, conflicts.Select(c => c.Id).Distinct().Count());
            Assert.True(conflicts[0].Range.Start < conflicts[1].Range.Start);
            Assert.True(conflicts[1].Range.Start < conflicts[2].Range.Start);
        }

        [Fact]
        public void ConflictIds_ContinueToTwoDigitsBeyondNine()
        {
            List<Track> tracks = new List<Track>();
            tracks.Add(W2AccFixture.Constant("A/HDG", "A", TrackKind.Heading, 0, 200, 0.0));
            List<TimelineSample> samples = new List<TimelineSample>();
            for (int i = 0; i < 12; i++)
            {
                double start = i * 16;
                samples.Add(W2AccFixture.S(start, 0.0));
                samples.Add(W2AccFixture.S(start + 2, 0.0));
                samples.Add(W2AccFixture.S(start + 4, 5.0));
                samples.Add(W2AccFixture.S(start + 8, 5.0));
                samples.Add(W2AccFixture.S(start + 10, 0.0));
            }

            samples.Add(W2AccFixture.S(200, 0.0));
            tracks.Add(W2AccFixture.ScalarTrack("B/HDG", "B", TrackKind.Heading, samples.ToArray()));

            IReadOnlyList<TimelineConflict> conflicts =
                ConflictDetector.Detect(new MultiTrackTimeline(tracks));
            Assert.True(conflicts.Count >= 10, "应产生不少于 10 条冲突以便检查 C-10 编号，实际=" + conflicts.Count);
            Assert.Equal("C-01", conflicts[0].Id);
            Assert.Equal("C-10", conflicts[9].Id);
            Assert.All(conflicts, c => Assert.Matches(ConflictIdPattern, c.Id));
            Assert.Equal(conflicts.Count, conflicts.Select(c => c.Id).Distinct().Count());
        }

        [Fact]
        public void TimelineConflict_ExposesContractAndScreenshotFields()
        {
            // contracts/schemas/conflict.schema.json 必填：conflictId, caseId, summary, a, b, status；
            // 原型 09 冲突表列：编号 / 内容 / 差值 / 处理（待询问核实、钟差已校正、待定-采信 AIS）。
            Type type = typeof(TimelineConflict);
            Assert.True(
                W2AccFixture.HasPublicProperty(type, "Id") || W2AccFixture.HasPublicProperty(type, "ConflictId"),
                "缺少冲突编号字段。");
            Assert.True(
                W2AccFixture.HasPublicProperty(type, "Description") || W2AccFixture.HasPublicProperty(type, "Summary"),
                "缺少冲突内容/摘要字段。");
            Assert.True(
                W2AccFixture.HasPublicProperty(type, "MaxDifference") || W2AccFixture.HasPublicProperty(type, "Delta"),
                "缺少差值字段。");

            Assert.True(
                W2AccFixture.HasPublicProperty(type, "CaseId"),
                "TimelineConflict 缺少合同必填 caseId，无法写入 analysis/time-alignment.json。");
            Assert.True(
                W2AccFixture.HasPublicProperty(type, "Status"),
                "TimelineConflict 缺少 status，无法支撑原型「处理」列（待询问核实 / 钟差已校正 / 待定-采信 AIS）。");
            bool hasResolution = W2AccFixture.HasPublicProperty(type, "Resolution")
                                 || W2AccFixture.HasPublicProperty(type, "Disposition");
            Assert.True(hasResolution, "TimelineConflict 缺少 resolution/处理说明字段。");
        }

        [Fact]
        public void DefaultThresholds_AreNotASharedMutableSingleton()
        {
            ConflictThresholds first = ConflictThresholds.Default;
            ConflictThresholds second = ConflictThresholds.Default;
            Assert.False(
                object.ReferenceEquals(first, second),
                "ConflictThresholds.Default 返回共享可变单例，调用方改阈值会污染后续 Detect(null) 结果。");
        }
    }
}
