using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    /// <summary>
    /// 示例数据（虚构）：原型页 10（#interview）的 6 份询问笔录与 IR-03 交叉比对表。
    /// 人名、港口、时间、数据全部虚构（星屿港 Lily × Mary，2026-05-18，船时 UTC+8），与任何真实事故/报告无关。
    /// </summary>
    public static class InterviewCompareDemo
    {
        public const string Disclaimer = "示例数据（虚构），仅用于演示与测试，不代表任何真实事故或人员。";
        public const string CaseId = "CASE-2026-LM01";
        public const string Operator = "演示系统（虚构）";
        public const string Investigator = "调查员 A（虚构）";

        private static readonly TimeSpan Cst = TimeSpan.FromHours(8);

        public static readonly DateTimeOffset IncidentAnchorLocal = new DateTimeOffset(2026, 5, 18, 14, 27, 0, Cst);
        public static readonly DateTimeOffset Ir03StartUtc = new DateTimeOffset(2026, 5, 19, 9, 30, 0, Cst).ToUniversalTime();

        /// <summary>IR-03 二副笔录转写（虚构），7 轮，时间戳相对录音开始。</summary>
        public const string Ir03Transcript =
            "IR-03 询问笔录（示例数据，虚构）\n" +
            "受询问人：二副（虚构）  询问人：调查员 A（虚构）\n" +
            "\n" +
            "[02:00] 第1问 问：你什么时候第一次在雷达上看到 Lily 轮？\n" +
            "答：大概 14:17，在雷达上看到她，当时距离只有 3 海里左右。\n" +
            "[10:00] 第2问 问：之后你做了什么操作？\n" +
            "答：14:19 我把车钟拉到半速。\n" +
            "[20:00] 第3问 问：什么时候开始用舵？\n" +
            "答：14:23 才开始左舵，左舵 20 度。\n" +
            "[30:00] 第4问 问：有没有鸣放声号？\n" +
            "答：有，我鸣放了一长声。\n" +
            "[40:00] 第5问 问：VTS 有没有呼叫你们？\n" +
            "答：VTS 14:20 在 16 频道呼叫过我们。\n" +
            "[55:00] 第6问 问：船长什么时候上驾驶台？\n" +
            "答：船长 14:23:30 上的驾驶台。\n" +
            "[1:08:00] 第7问 问：以上笔录是否属实？\n" +
            "答：以上内容属实。\n";

        private static DateTimeOffset L(int h, int m, int s = 0) { return new DateTimeOffset(2026, 5, 18, h, m, s, Cst); }

        /// <summary>IR-03（虚构）：解析转写 → 7 轮 → 7 条草稿陈述。</summary>
        public static InterviewRecord Ir03()
        {
            var r = new InterviewRecord("IR-03", new Interviewee("P-03", "二副（虚构）", "二副", "Mary 轮"), Ir03StartUtc,
                new[] { Investigator }, "记录员 B（虚构）", "星屿港海事局询问室（虚构）", caseId: CaseId, signed: true);
            var parsed = TranscriptParser.Parse(Ir03Transcript, new TranscriptParseOptions { RecordingStartUtc = Ir03StartUtc });
            Must(TranscriptParser.ApplyTo(parsed, r).IsSuccess, "IR-03 转写写入失败");
            Add(r, "IR-03-S1", StatementKind.Observation, "Mary.first_radar_range", "首次发现距离 3 nm", StatementClaim.ScalarValue(3, "nm"), 1, "距离只有 3 海里", L(14, 17));
            Add(r, "IR-03-S2", StatementKind.Time, "Mary.telegraph_half", "14:19 车钟半速", StatementClaim.EventTime(L(14, 19)), 2, "14:19 我把车钟拉到半速", null);
            Add(r, "IR-03-S3", StatementKind.Time, "Mary.helm_left_start", "14:23 才开始左舵", StatementClaim.EventTime(L(14, 23)), 3, "14:23 才开始左舵", null);
            Add(r, "IR-03-S4", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), 3, "左舵 20 度", L(14, 22, 15));
            Add(r, "IR-03-S5", StatementKind.Operation, "Mary.sound_signal", "鸣放一长声", StatementClaim.Occurrence(true), 4, "鸣放了一长声", L(14, 21));
            Add(r, "IR-03-S6", StatementKind.Time, "VTS.call_mary", "VTS 14:20 呼叫", StatementClaim.EventTime(L(14, 20)), 5, "VTS 14:20 在 16 频道呼叫过我们", null);
            Add(r, "IR-03-S7", StatementKind.Time, "Mary.master_on_bridge", "船长 14:23:30 上驾驶台", StatementClaim.EventTime(L(14, 23, 30)), 6, "船长 14:23:30 上的驾驶台", null);
            return r;
        }

        /// <summary>6 份笔录（虚构）：IR-03 完整，其余为最小笔录（1 条陈述）。</summary>
        public static IReadOnlyList<InterviewRecord> Records()
        {
            var list = new List<InterviewRecord>
            {
                Mini("IR-01", "船长（虚构）", "船长", "Mary 轮", 5, 18, 18, 0, "我 14:21 就上了驾驶台。", "14:21", "IR-01-S1", "Mary.master_on_bridge_ir01", L(14, 21)),
                Mini("IR-02", "船长（虚构）", "船长", "Lily 轮", 5, 18, 19, 0, "14:22 我们向右转向。", "14:22", "IR-02-S1", "Lily.turn_right", L(14, 22)),
                Ir03(),
                Mini("IR-04", "舵工（虚构）", "舵工", "Mary 轮", 5, 19, 11, 0, "14:22 接到左舵口令。", "14:22", "IR-04-S1", "Mary.helm_order", L(14, 22)),
                Mini("IR-05", "大副（虚构）", "大副", "Lily 轮", 5, 19, 14, 0, "14:18 我们减了速。", "14:18", "IR-05-S1", "Lily.slow_down", L(14, 18)),
                Mini("IR-06", "VTS 值班员（虚构）", "VTS 值班员", "星屿港 VTS（虚构）", 5, 19, 16, 0, "14:20 我在 16 频道呼叫 Mary 轮。", "14:20", "IR-06-S1", "VTS.call_mary_ir06", L(14, 20)),
            };
            return new ReadOnlyCollection<InterviewRecord>(list);
        }

        /// <summary>虚构数据源（AIS/VDR/VHF）。IR-03 产生 3 处矛盾（距离、左舵 +45 s、无声号），IR-01、IR-05 各 1 处。</summary>
        public static IStatementDataSource DataSource()
        {
            return new DemoSource(new Dictionary<string, DataObservation>
            {
                { "Mary.first_radar_range", DataObservation.ScalarValue(5.1, "nm", "AIS 14:17", L(14, 17)) },
                { "Mary.telegraph_half", DataObservation.EventAt(L(14, 19, 8), "VDR") },
                { "Mary.helm_left_start", DataObservation.EventAt(L(14, 22, 15), "VDR 舵角") },
                { "Mary.rudder_angle", DataObservation.ScalarValue(20, "deg", "VDR", L(14, 22, 15)) },
                { "Mary.sound_signal", DataObservation.Occurrence(false, "VDR 音频：无声号", L(14, 21)) },
                { "VTS.call_mary", DataObservation.EventAt(L(14, 20, 12), "VHF16") },
                { "Mary.master_on_bridge", DataObservation.EventAt(L(14, 23, 34), "VDR 音频") },
                { "Mary.master_on_bridge_ir01", DataObservation.EventAt(L(14, 23, 34), "VDR 音频") },
                { "Lily.turn_right", DataObservation.EventAt(L(14, 22, 10), "AIS") },
                { "Mary.helm_order", DataObservation.EventAt(L(14, 22, 5), "VDR 音频") },
                { "Lily.slow_down", DataObservation.EventAt(L(14, 20, 0), "AIS 航速") },
                { "VTS.call_mary_ir06", DataObservation.EventAt(L(14, 20, 12), "VHF16") },
            });
        }

        /// <summary>容差：时刻 30 s（W3 默认）；首次发现距离 0.5 nm；舵角 2°。</summary>
        public static CrossCheckTolerance Tolerance()
        {
            return new CrossCheckTolerance().SetScalar("Mary.first_radar_range", 0.5).SetScalar("Mary.rudder_angle", 2.0);
        }

        /// <summary>对一份笔录跑比对并登记（全部待确认）。</summary>
        public static CrossCheckRegister CheckedRegister(InterviewRecord record, out InMemoryInvestigationAuditSink audit)
        {
            audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            Submit(record, reg);
            return reg;
        }

        /// <summary>6 份笔录全部比对并逐条确认后的名单（与原型左栏一致）。</summary>
        public static IReadOnlyList<RosterEntry> ConfirmedRoster()
        {
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            var recs = Records();
            var at = new DateTimeOffset(2026, 5, 20, 10, 0, 0, Cst);
            foreach (var r in recs)
            {
                Submit(r, reg);
                foreach (var s in new List<Statement>(r.Statements)) // ConfirmRow 会替换列表元素
                {
                    Must(InterviewReviewActions.ConfirmRow(r, reg, s.StatementId, Investigator, at, audit).IsSuccess, "确认失败 " + s.StatementId);
                }
            }

            return InterviewComparisonView.Roster(recs, reg);
        }

        private static void Submit(InterviewRecord record, CrossCheckRegister reg)
        {
            var at = new DateTimeOffset(2026, 5, 20, 9, 0, 0, Cst);
            foreach (var res in new StatementCrossChecker(Tolerance()).CheckAll(record, DataSource()))
            {
                Must(reg.Submit(res, Operator, at).IsSuccess, "登记失败 " + res.StatementId);
            }
        }

        private static InterviewRecord Mini(string id, string name, string role, string ship, int mo, int d, int h, int mi, string answer, string fragment, string sid, string subject, DateTimeOffset claim)
        {
            var start = new DateTimeOffset(2026, mo, d, h, mi, 0, Cst).ToUniversalTime();
            var r = new InterviewRecord(id, new Interviewee("P-" + id.Substring(3), name, role, ship), start, new[] { Investigator }, caseId: CaseId, signed: true);
            Must(r.AddTurn("请陈述当时的情况。", answer, start.AddMinutes(30)).IsSuccess, "AddTurn " + id);
            Add(r, sid, StatementKind.Time, subject, fragment + " " + role, StatementClaim.EventTime(claim), 1, fragment, null);
            return r;
        }

        private static void Add(InterviewRecord r, string id, StatementKind kind, string subject, string summary, StatementClaim claim, int round, string fragment, DateTimeOffset? reference)
        {
            var span = r.Locate(round, QaField.Answer, fragment);
            Must(span.IsSuccess, "定位失败 " + id);
            Must(r.AddStatement(id, kind, subject, summary, claim, span.Value, reference).IsSuccess, "AddStatement " + id);
        }

        private static void Must(bool ok, string what)
        {
            if (!ok)
            {
                throw new InvalidOperationException("演示数据构造失败：" + what);
            }
        }

        private sealed class DemoSource : IStatementDataSource
        {
            private readonly Dictionary<string, DataObservation> _d;

            public DemoSource(Dictionary<string, DataObservation> d) { _d = d; }

            public DataObservation Query(StatementQuery q)
            {
                DataObservation o;
                return _d.TryGetValue(q.Subject, out o) ? o : DataObservation.NotFound("示例数据源（虚构）");
            }
        }
    }
}
