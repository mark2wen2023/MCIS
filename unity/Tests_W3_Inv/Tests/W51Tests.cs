using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using Mcis.Core;
using Mcis.Data.Audit;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.W3.Tests
{
    /// <summary>
    /// W5.1（DEFECTS/W5.md、DEFECTS/W3.md 21:32 裁定）对 W3 台账的合同补丁：statementVersion + IsStale、
    /// Resubmit（仅 Dismissed → 新条目，旧条目 Superseded 留痕）、Submit 审计失败返回码、batchId 落 x- 扩展键（示例数据·虚构）。
    /// </summary>
    public class W51Tests
    {
        private const string Agent = "比对流程（虚构）";
        private const string Inv = "调查员 A（虚构）";

        private sealed class FaultSink : IInvestigationAuditSink
        {
            public string FailAction;
            public readonly List<InvestigationAuditEntry> Written = new List<InvestigationAuditEntry>();

            public void Append(InvestigationAuditEntry entry)
            {
                if (entry.Action == FailAction)
                {
                    throw new System.IO.IOException("审计不可用（模拟）");
                }

                Written.Add(entry);
            }
        }

        private static CrossCheckResult R(string id, CrossCheckOutcome o = CrossCheckOutcome.Contradictory, string record = "IR-03", int? version = null)
        {
            return version.HasValue
                ? new CrossCheckResult(id, record, o, 5, "deg", "20°", "15°", "VDR（虚构）", "|Δ|≤1", version.Value)
                : new CrossCheckResult(id, record, o, 5, "deg", "20°", "15°", "VDR（虚构）", "|Δ|≤1");
        }

        private static InterviewRecord RecordWithRudder(out Statement st)
        {
            InterviewRecord ir = W3Demo.Ir03();
            st = ir.AddStatement("S-r", StatementKind.Operation, "Mary.rudder_angle", "左舵 20°", StatementClaim.ScalarValue(20, "deg"),
                ir.Locate(2, QaField.Answer, "左舵 20 度").Value, W3Demo.At(14, 23)).Value;
            return ir;
        }

        // ---------- D01 statementVersion / IsStale ----------

        [Fact]
        public void Result_StatementVersion_DefaultsTo1_AndKeepsExplicitValue()
        {
            Assert.Equal(1, R("S-1").StatementVersion);
            Assert.Equal(3, R("S-1", version: 3).StatementVersion);
            Assert.Throws<ArgumentOutOfRangeException>(() => R("S-1", version: 0));
        }

        [Fact]
        public void Checker_StampsCurrentStatementRevision()
        {
            InterviewRecord ir = RecordWithRudder(out Statement st);
            var checker = new StatementCrossChecker();
            Assert.Equal(1, checker.Check(st, FakeDataSource.LilyMary()).StatementVersion);
            var sink = new InMemoryInvestigationAuditSink();
            Statement s2 = ir.ModifyStatement("S-r", "左舵 15°（修正，虚构）", StatementClaim.ScalarValue(15, "deg"), st.Span, st.ReferenceUtc, Inv, W3Demo.Day(5, 19, 11), sink).Value;
            Assert.Equal(2, s2.Revision);
            Assert.Equal(2, checker.Check(s2, FakeDataSource.LilyMary()).StatementVersion);
            Assert.Equal(2, checker.CheckAll(ir, FakeDataSource.LilyMary()).Single(r => r.StatementId == "S-r").StatementVersion);
        }

        [Fact]
        public void Entry_IsStale_OnlyWhenStatementRevisionDiffers()
        {
            InterviewRecord ir = RecordWithRudder(out Statement st);
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            CrossCheckEntry e = reg.Submit(R("S-r"), Agent, W3Demo.Day(5, 19, 10)).Value;
            Assert.Equal(1, e.StatementVersion);
            Assert.False(e.IsStale(ir));
            Assert.False(e.IsStale(null));

            ir.ModifyStatement("S-r", "左舵 15°（虚构）", StatementClaim.ScalarValue(15, "deg"), st.Span, st.ReferenceUtc, Inv, W3Demo.Day(5, 19, 11), new InMemoryInvestigationAuditSink());
            Assert.True(e.IsStale(ir));
            // 属于别的笔录的结论，即使本笔录有同编号且已改版的陈述，也不算过期
            CrossCheckEntry foreign = new CrossCheckRegister(new InMemoryInvestigationAuditSink()).Submit(R("S-r", record: "IR-04"), Agent, W3Demo.Day(5, 19, 10)).Value;
            Assert.False(foreign.IsStale(ir));

            // 别的笔录（同陈述编号）不算；本笔录没有该陈述也不算（无从比较）
            InterviewRecord other = new InterviewRecord("IR-07", new Interviewee("P", "n", "r", "a"), W3Demo.Day(5, 19));
            Assert.False(e.IsStale(other));
            CrossCheckEntry orphan = reg.Submit(R("S-none"), Agent, W3Demo.Day(5, 19, 10)).Value;
            Assert.False(orphan.IsStale(ir));

            // 带新版本重新比对的结论与陈述一致，不过期
            CrossCheckEntry fresh = new CrossCheckRegister(new InMemoryInvestigationAuditSink()).Submit(R("S-r", version: 2), Agent, W3Demo.Day(5, 19, 12)).Value;
            Assert.False(fresh.IsStale(ir));
        }

        [Fact]
        public void ToJson_CarriesStatementVersion_AsLastKey_AndSupersededState()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            CrossCheckEntry e = reg.Submit(R("S-r", version: 4), Agent, W3Demo.Day(5, 19, 10)).Value;
            using (JsonDocument d = JsonDocument.Parse(e.ToJson()))
            {
                var keys = d.RootElement.EnumerateObject().Select(p => p.Name).ToArray();
                Assert.Equal("statementVersion", keys.Last());
                Assert.Equal(15, keys.Length);
                Assert.Equal(4, d.RootElement.GetProperty("statementVersion").GetInt32());
            }

            reg.Dismiss("S-r", Inv, W3Demo.Day(5, 19, 11), "数据源有误（虚构）");
            reg.Resubmit(R("S-r", CrossCheckOutcome.Consistent, version: 4), Inv, W3Demo.Day(5, 19, 12), "更正（虚构）");
            using (JsonDocument d = JsonDocument.Parse(e.ToJson()))
            {
                Assert.Equal("Superseded", d.RootElement.GetProperty("state").GetString());
            }
        }

        // ---------- D02 Resubmit ----------

        [Fact]
        public void Resubmit_RejectsPendingConfirmedAndUnknown_WithoutAudit()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(sink);
            reg.Submit(R("S-p"), Agent, W3Demo.Day(5, 19, 10));
            reg.Submit(R("S-c"), Agent, W3Demo.Day(5, 19, 10));
            reg.Confirm("S-c", Inv, W3Demo.Day(5, 19, 10, 5));
            int n = sink.Entries.Count;

            Assert.Equal(CrossCheckRegister.ErrNotDismissed, reg.Resubmit(R("S-p", CrossCheckOutcome.Consistent), Inv, W3Demo.Day(5, 19, 11), "重提（虚构）").ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrNotDismissed, reg.Resubmit(R("S-c", CrossCheckOutcome.Consistent), Inv, W3Demo.Day(5, 19, 11), "重提（虚构）").ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrNotFound, reg.Resubmit(R("S-x"), Inv, W3Demo.Day(5, 19, 11), "重提（虚构）").ErrorCode);
            Assert.Equal(n, sink.Entries.Count);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-p").State);
            Assert.Equal(CrossCheckState.Confirmed, reg.Get("S-c").State);
            Assert.Equal(2, reg.Entries.Count);
        }

        [Fact]
        public void Resubmit_ValidatesArguments()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(sink);
            reg.Submit(R("S-d"), Agent, W3Demo.Day(5, 19, 10));
            reg.Dismiss("S-d", Inv, W3Demo.Day(5, 19, 10, 5), "有误（虚构）");
            int n = sink.Entries.Count;
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(null, Inv, W3Demo.Day(5, 19, 11), "r").ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(R("S-d"), " ", W3Demo.Day(5, 19, 11), "r").ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(R("S-d"), Inv, W3Demo.Day(5, 19, 11), " ").ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(R("S-d"), Inv, W3Demo.Day(5, 19, 11), null).ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(R(" "), Inv, W3Demo.Day(5, 19, 11), "r").ErrorCode);
            // 换了笔录的结果不能顶替原条目
            Assert.Equal(CrossCheckRegister.ErrInvalidArgument, reg.Resubmit(R("S-d", record: "IR-04"), Inv, W3Demo.Day(5, 19, 11), "r").ErrorCode);
            Assert.Equal(n, sink.Entries.Count);
            Assert.Equal(CrossCheckState.Dismissed, reg.Get("S-d").State);
        }

        [Fact]
        public void Resubmit_FromDismissed_SupersedesOldEntry_KeepsIt_AndWritesOneAuditRow()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(sink);
            CrossCheckEntry old = reg.Submit(R("S-d"), Agent, W3Demo.Day(5, 19, 10)).Value;
            reg.Submit(R("S-other", CrossCheckOutcome.Consistent), Agent, W3Demo.Day(5, 19, 10));
            reg.Dismiss("S-d", Inv, W3Demo.Day(5, 19, 10, 5), "数据源时钟未校准（虚构）");
            int n = sink.Entries.Count;

            Result<CrossCheckEntry> r = reg.Resubmit(R("S-d", CrossCheckOutcome.Consistent, version: 2), Inv, W3Demo.Day(5, 19, 11), "校准后重新比对（虚构）");
            Assert.True(r.IsSuccess);
            CrossCheckEntry cur = r.Value;
            Assert.NotSame(old, cur);
            Assert.Same(cur, reg.Get("S-d"));
            Assert.Equal(CrossCheckState.PendingConfirmation, cur.State);
            Assert.Equal(CrossCheckOutcome.Consistent, cur.Result.Outcome);
            Assert.Equal(2, cur.StatementVersion);
            Assert.Null(cur.DecidedBy);

            // 旧条目留痕：状态 Superseded，原驳回人/时间/理由不动；仍在 Entries 中，顺序在新条目之前
            Assert.Equal(CrossCheckState.Superseded, old.State);
            Assert.Equal(Inv, old.DecidedBy);
            Assert.Equal("数据源时钟未校准（虚构）", old.Note);
            Assert.False(old.IsEffective);
            Assert.Equal(new[] { "S-d", "S-other", "S-d" }, reg.Entries.Select(e => e.Result.StatementId).ToArray());
            Assert.True(reg.Entries.ToList().IndexOf(old) < reg.Entries.ToList().IndexOf(cur));

            // 只写一条 resubmit 审计：before = 旧条目摘要（Dismissed），after = 新条目摘要 + 理由
            Assert.Equal(n + 1, sink.Entries.Count);
            InvestigationAuditEntry a = sink.Entries.Last();
            Assert.Equal(CrossCheckRegister.ActionResubmit, a.Action);
            Assert.Equal(InvestigationAuditCategories.Interview, a.Category);
            Assert.Equal(Inv, a.OperatorName);
            Assert.Contains("S-d", a.CommandName);
            Assert.StartsWith("Dismissed；Contradictory", a.BeforeValueSummary);
            Assert.StartsWith("PendingConfirmation；Consistent", a.AfterValueSummary);
            Assert.EndsWith("；理由=校准后重新比对（虚构）", a.AfterValueSummary);

            // 待确认/生效集合只看当前条目
            Assert.Equal(new[] { cur }, reg.Pending().Where(e => e.Result.StatementId == "S-d").ToArray());
            Assert.Empty(reg.Effective());

            // 新条目照常确认；再驳回后可再次重新提交（链式留痕）
            Assert.True(reg.Dismiss("S-d", Inv, W3Demo.Day(5, 19, 12), "仍有疑问（虚构）").IsSuccess);
            Assert.True(reg.Resubmit(R("S-d", version: 2), Inv, W3Demo.Day(5, 19, 13), "第三次（虚构）").IsSuccess);
            Assert.Equal(CrossCheckState.Superseded, cur.State);
            Assert.Equal(2, reg.Entries.Count(e => e.State == CrossCheckState.Superseded));
            Assert.True(reg.Confirm("S-d", Inv, W3Demo.Day(5, 19, 14)).IsSuccess);
            Assert.Single(reg.Effective());

            // 重复 Submit 仍按“已登记”拒绝
            Assert.Equal(CrossCheckRegister.ErrDuplicate, reg.Submit(R("S-d"), Agent, W3Demo.Day(5, 19, 15)).ErrorCode);
        }

        [Fact]
        public void Resubmit_AuditFailure_ReturnsAuditFailed_AndChangesNothing()
        {
            var sink = new FaultSink();
            var reg = new CrossCheckRegister(sink);
            CrossCheckEntry old = reg.Submit(R("S-d"), Agent, W3Demo.Day(5, 19, 10)).Value;
            reg.Dismiss("S-d", Inv, W3Demo.Day(5, 19, 10, 5), "有误（虚构）");
            sink.FailAction = CrossCheckRegister.ActionResubmit;
            Result<CrossCheckEntry> r = reg.Resubmit(R("S-d", CrossCheckOutcome.Consistent), Inv, W3Demo.Day(5, 19, 11), "重提（虚构）");
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.Same(old, reg.Get("S-d"));
            Assert.Equal(CrossCheckState.Dismissed, old.State);
            Assert.Single(reg.Entries);
        }

        // ---------- Submit 审计失败 ----------

        [Fact]
        public void Submit_AuditFailure_ReturnsAuditFailed_NotThrow_AndRegistersNothing()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionSubmit };
            var reg = new CrossCheckRegister(sink);
            Result<CrossCheckEntry> r = reg.Submit(R("S-1"), Agent, W3Demo.Day(5, 19, 10));
            Assert.False(r.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.Null(reg.Get("S-1"));
            Assert.Empty(reg.Entries);
            sink.FailAction = null;
            Assert.True(reg.Submit(R("S-1"), Agent, W3Demo.Day(5, 19, 10)).IsSuccess);
        }

        // ---------- batchId → x-batchId ----------

        [Fact]
        public void BatchConfirm_WritesBatchIdKey_AndKeepsCommandMarker()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(sink);
            reg.Submit(R("S-a", CrossCheckOutcome.Consistent), Agent, W3Demo.Day(5, 19, 10));
            reg.Submit(R("S-b", CrossCheckOutcome.Consistent), Agent, W3Demo.Day(5, 19, 10));
            int n = sink.Entries.Count;
            Assert.True(reg.ConfirmConsistentBatch(new[] { "S-a", "S-b" }, Inv, W3Demo.Day(5, 19, 11)).IsSuccess);
            var rows = sink.Entries.Skip(n).ToList();
            Assert.Equal(3, rows.Count);
            string id = rows[0].BatchId;
            Assert.Matches("^[0-9a-f]{32}$", id);
            Assert.All(rows, x => Assert.Equal(id, x.BatchId));
            Assert.All(rows, x => Assert.EndsWith("[batch=" + id + "]", x.CommandName));
            using (JsonDocument d = JsonDocument.Parse(rows[0].ToJsonLine()))
            {
                Assert.Equal(id, d.RootElement.GetProperty("x-batchId").GetString());
                Assert.Equal(8, d.RootElement.EnumerateObject().Count());
            }

            // 非批量行不带扩展键，保持 7 键且与 AuditRecord 逐字一致
            InvestigationAuditEntry submit = sink.Entries[0];
            Assert.Null(submit.BatchId);
            Assert.DoesNotContain("x-batchId", submit.ToJsonLine());
            Assert.Equal(AuditRecord.FromJsonLine(submit.ToJsonLine()).ToJsonLine(), submit.ToJsonLine());
        }

        [Fact]
        public void BatchIdOf_PrefersValidKey_FallsBackToMarker_IgnoresNonBatchActions()
        {
            string key = new string('a', 32);
            var keyOnly = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchConfirm, "Interview", "批量确认一致 S-1", "", "Confirmed", key);
            Assert.Equal(key, keyOnly.BatchId);
            Assert.Equal(key, CrossCheckRegister.BatchIdOf(keyOnly));

            var both = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchConfirm, "Interview", "批量确认一致 S-1 [batch=" + new string('b', 32) + "]", "", "Confirmed", key);
            Assert.Equal(key, CrossCheckRegister.BatchIdOf(both));

            var badKey = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchConfirm, "Interview", "批量确认一致 S-1 [batch=xyz]", "", "Confirmed", "NOT-HEX");
            Assert.Equal("xyz", CrossCheckRegister.BatchIdOf(badKey));
            // 长度不是 32、或含 a–f 以外字母的键都不认，退回标记
            foreach (string bad in new[] { new string('a', 31), new string('a', 33), new string('g', 32), new string('z', 32) })
            {
                var e2 = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchConfirm, "Interview", "批量确认一致 S-1 [batch=xyz]", "", "Confirmed", bad);
                Assert.Equal("xyz", CrossCheckRegister.BatchIdOf(e2));
            }

            var nonBatch = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionConfirm, "Interview", "确认", "", "Confirmed", key);
            Assert.Null(CrossCheckRegister.BatchIdOf(nonBatch));

            Assert.Null(new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, "a", "c", "x", "", "", "").BatchId);
            Assert.Null(new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, "a", "c", "x", "", "").BatchId);
        }

        [Fact]
        public void EffectiveAudit_AcceptsKeyOnlyBatchRows()
        {
            string key = new string('c', 32);
            var confirm = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchConfirm, "Interview", "批量确认一致 S-1", "", "Confirmed", key);
            var commit = new InvestigationAuditEntry(W3Demo.Day(5, 19), Inv, CrossCheckRegister.ActionBatchCommit, "Interview", "批量确认提交 1 条", "", "S-1", key);
            Assert.Equal(2, CrossCheckRegister.EffectiveAudit(new[] { confirm, commit }).Count);
            Assert.Empty(CrossCheckRegister.EffectiveAudit(new[] { confirm }));
        }
    }
}
