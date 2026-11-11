using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.W5.Tests
{
    /// <summary>W5 测试夹具。全部为虚构合成数据（星屿港 Lily × Mary，2026-05-18，船时 UTC+8），不读 reports/。</summary>
    internal static class W5Fx
    {
        public static readonly TimeSpan Cst = TimeSpan.FromHours(8);

        public static DateTimeOffset At(int h, int m, int s = 0) { return new DateTimeOffset(2026, 5, 18, h, m, s, Cst); }

        public static DateTimeOffset Day19(int h, int m, int s = 0) { return new DateTimeOffset(2026, 5, 19, h, m, s, Cst); }

        public static T Ok<T>(Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static void Code<T>(string code, Result<T> r)
        {
            Assert.False(r.IsSuccess, "期望失败 " + code);
            Assert.Equal(code, r.ErrorCode);
        }

        public static InterviewRecord Empty(string id = "IR-09")
        {
            return new InterviewRecord(id, new Interviewee("P-09", "虚构证人", "水手", "Mary 轮"), Day19(9, 0), caseId: "CASE-2026-LM01");
        }

        /// <summary>两轮问答 + 3 条陈述（时间 / 舵角 / 声号），全部虚构。</summary>
        public static InterviewRecord Small(out CrossCheckRegister register, out InMemoryInvestigationAuditSink audit)
        {
            var r = Empty();
            Ok(r.AddTurn("几点开始左舵？", "就在 14:23 开始左舵，左舵 20 度，同时鸣了一长声。", Day19(9, 5)));
            Ok(r.AddTurn("船长在哪？", "船长 14:23 半才上来。", Day19(9, 6)));
            Ok(r.AddStatement("S1", StatementKind.Time, "Mary.helm_left", "14:23 开始左舵", StatementClaim.EventTime(At(14, 23)), Ok(r.Locate(1, QaField.Answer, "14:23 开始左舵"))));
            Ok(r.AddStatement("S2", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(r.Locate(1, QaField.Answer, "左舵 20 度")), At(14, 22, 15)));
            Ok(r.AddStatement("S3", StatementKind.Operation, "Mary.sound_signal", "鸣一长声", StatementClaim.Occurrence(true), Ok(r.Locate(1, QaField.Answer, "鸣了一长声")), At(14, 22, 15)));
            audit = new InMemoryInvestigationAuditSink();
            register = new CrossCheckRegister(audit);
            return r;
        }

        public sealed class DictSource : IStatementDataSource
        {
            private readonly Dictionary<string, DataObservation> _d = new Dictionary<string, DataObservation>();

            public DictSource Add(string subject, DataObservation o) { _d[subject] = o; return this; }

            public DataObservation Query(StatementQuery q)
            {
                DataObservation o;
                return _d.TryGetValue(q.Subject, out o) ? o : DataObservation.NotFound("虚构数据源");
            }
        }

        /// <summary>S1 矛盾（Δ=+45 s）、S2 一致、S3 矛盾（无声号）。</summary>
        public static DictSource SmallSource()
        {
            return new DictSource()
                .Add("Mary.helm_left", DataObservation.EventAt(At(14, 22, 15), "VDR 舵角"))
                .Add("Mary.rudder_angle", DataObservation.ScalarValue(20, "deg", "VDR", At(14, 22, 15)))
                .Add("Mary.sound_signal", DataObservation.Occurrence(false, "VDR 音频", At(14, 22, 15)));
        }

        public static void SubmitAll(InterviewRecord r, CrossCheckRegister reg)
        {
            foreach (var res in new StatementCrossChecker().CheckAll(r, SmallSource()))
            {
                Ok(reg.Submit(res, "系统", Day19(10, 0)));
            }
        }
    }
}
