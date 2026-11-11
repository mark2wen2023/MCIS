using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;

namespace Mcis.Acceptance.W3
{
    /// <summary>虚构演示数据（星屿港 Lily × Mary，标注为示例）。禁止使用 reports/ 下真实报告。</summary>
    internal static class W3AccFixture
    {
        public const string CaseId = "CASE-2026-LN01";
        public const string OpA = "调查员 A（虚构）";
        public const string OpB = "调查员 B（虚构）";

        // 64-char fictional SHA-256 hex (not from any real file).
        public const string ShaMaryVdr = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        public const string ShaLilyVdr = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
        public const string ShaDerived = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc";
        public const string ShaOther   = "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd";

        public static DateTimeOffset Utc(int month, int day, int hour = 0, int minute = 0, int second = 0)
        {
            return new DateTimeOffset(2026, month, day, hour, minute, second, TimeSpan.Zero);
        }

        public static DateTimeOffset Cst(int month, int day, int hour, int minute, int second = 0)
        {
            return new DateTimeOffset(2026, month, day, hour, minute, second, TimeSpan.FromHours(8));
        }

        public static EvidenceItem MaryVdr()
        {
            return new EvidenceItem("EV-001", "Mary 轮 VDR 数据包（12 h）（虚构）", "Mary 轮 VDR 舱（虚构）", OpA, Cst(5, 18, 18, 40), ShaMaryVdr, "raw/vdr/mary.zip");
        }

        public static EvidenceItem LilyVdr()
        {
            return new EvidenceItem("EV-002", "Lily 轮 S-VDR 数据包（虚构）", "救助现场（虚构）", OpB, Cst(5, 19, 10, 5), ShaLilyVdr, "raw/vdr/lily.zip");
        }

        public sealed class LineSink : ICustodyLineSink
        {
            public readonly List<string> Lines = new List<string>();
            public void AppendLine(string jsonLine) { Lines.Add(jsonLine); }
        }

        public sealed class MapSource : IStatementDataSource
        {
            public readonly Dictionary<string, DataObservation> BySubject = new Dictionary<string, DataObservation>(StringComparer.Ordinal);
            public DataObservation Query(StatementQuery query)
            {
                return query != null && BySubject.TryGetValue(query.Subject, out DataObservation o) ? o : DataObservation.NotFound();
            }
        }

        public static InterviewRecord Ir03WithTurns()
        {
            var person = new Interviewee("P-MARY-OOW", "（虚构角色）", "二副（OOW）", "Mary 轮（虚构）");
            var rec = new InterviewRecord("IR-03", person, Cst(5, 19, 9, 30), new[] { OpA }, "调查员 B（虚构）", "星屿海事局询问室（虚构）", ShaOther);
            rec.AddTurn("大约 14:17 左右，在 3 号浮标北面，距离差不多 3 海里，当时看它是出港的。", "大约 14:17 左右，在 3 号浮标北面，距离差不多 3 海里，当时看它是出港的。", Cst(5, 19, 9, 32));
            rec.AddTurn("当时能见度怎么样？", "有雾，能见度大约 1.5 海里。我把车钟拉到了半速，14:19 前后。", Cst(5, 19, 9, 35));
            rec.AddTurn("两船接近后你采取了什么行动？", "我就觉得它会从我右边过，就在 14:23 才开始左舵，左舵 20 度，同时鸣了一长声。", Cst(5, 19, 9, 40));
            rec.AddTurn("当时船长在驾驶台吗？", "船长 14:23 半才上来，之前在房间，我没有叫他。", Cst(5, 19, 9, 50));
            rec.AddTurn("你和 Lily 轮或 VTS 有没有 VHF 联系？", "VTS 在 14:20 叫过我们，我回答了“保持航向”，没有直接呼叫 Lily。", Cst(5, 19, 10, 0));
            rec.AddTurn("你上一次连续休息是什么时候，睡了多久？", "前一天下午一直在装卸，晚上 22 点才下半。0 点又接班，中间大概睡了不到两个小时。", Cst(5, 19, 10, 10));
            rec.AddTurn("碰撞前有没有用 ARPA 发现 Lily 轮？", "发现了，但矢量设成了 3 分钟，报警响过一次我按掉了。", Cst(5, 19, 10, 38));
            return rec;
        }

        public static Statement AddScalar(InterviewRecord rec, string id, string subject, string fragment, double value, string unit, DateTimeOffset? referenceUtc = null)
        {
            SourceSpan span = Find(rec, fragment);
            return rec.AddStatement(id, StatementKind.Observation, subject, fragment, StatementClaim.ScalarValue(value, unit), span, referenceUtc).Value;
        }

        public static SourceSpan Find(InterviewRecord rec, string fragment)
        {
            for (int i = 1; i <= rec.Turns.Count; i++)
            {
                var r = rec.Locate(i, QaField.Answer, fragment);
                if (r.IsSuccess) return r.Value;
                r = rec.Locate(i, QaField.Question, fragment);
                if (r.IsSuccess) return r.Value;
            }
            throw new InvalidOperationException("片段不在笔录中: " + fragment);
        }

        public static Statement AddEvent(InterviewRecord rec, string id, string subject, string fragment, DateTimeOffset when)
        {
            SourceSpan span = rec.Locate(3, QaField.Answer, fragment).Value;
            return rec.AddStatement(id, StatementKind.Time, subject, fragment, StatementClaim.EventTime(when), span, when).Value;
        }

        public static Statement AddOccurrence(InterviewRecord rec, string id, string subject, string fragment, bool occurred)
        {
            SourceSpan span = rec.Locate(3, QaField.Answer, fragment).Value;
            return rec.AddStatement(id, StatementKind.Operation, subject, fragment, StatementClaim.Occurrence(occurred), span).Value;
        }
    }
}
