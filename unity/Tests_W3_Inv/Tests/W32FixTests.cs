using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.W3.Tests
{
    /// <summary>W3.2（DEFECTS/W3.md 文末裁定）：批量两阶段提交、单条审计失败返回错误码、decidedUtc 毫秒（示例数据·虚构）。</summary>
    public class W32FixTests
    {
        /// <summary>按动作注入故障：FailAction 的第 FailNth 次（1 起）写入抛异常；FailAbort 让 batch_abort 也失败。</summary>
        private sealed class FaultSink : IInvestigationAuditSink
        {
            public string FailAction;
            public int FailNth = 1;
            public bool FailAbort;
            private int _seen;
            public readonly List<InvestigationAuditEntry> Written = new List<InvestigationAuditEntry>();

            public void Append(InvestigationAuditEntry entry)
            {
                if (FailAbort && entry.Action == CrossCheckRegister.ActionBatchAbort)
                {
                    throw new System.IO.IOException("abort 写盘失败（模拟）");
                }

                if (entry.Action == FailAction && ++_seen == FailNth)
                {
                    throw new System.IO.IOException("审计不可用（模拟）");
                }

                Written.Add(entry);
            }
        }

        private static CrossCheckResult Consistent(string id)
        {
            return new CrossCheckResult(id, "IR-03", CrossCheckOutcome.Consistent, 0, "nm", "3 nm", "3 nm", "AIS（虚构）", "|Δ|≤0.1");
        }

        private static CrossCheckResult Contra(string id)
        {
            return new CrossCheckResult(id, "IR-03", CrossCheckOutcome.Contradictory, 45, "s", "14:23", "14:22:15", "VDR（虚构）", "|Δ|≤30 s");
        }

        private static CrossCheckRegister Reg(IInvestigationAuditSink sink, params string[] ids)
        {
            var reg = new CrossCheckRegister(sink);
            foreach (string id in ids)
            {
                Assert.True(reg.Submit(Consistent(id), "比对流程（虚构）", W3Demo.Day(5, 19, 11)).IsSuccess);
            }

            return reg;
        }

        // ---------- ① 两阶段提交 ----------

        [Fact]
        public void Batch_EveryRowCarriesSameBatchId_ThenSingleCommit()
        {
            var sink = new FaultSink();
            var reg = Reg(sink, "S-1", "S-2", "S-3");
            int n = sink.Written.Count;
            Assert.True(reg.ConfirmConsistentBatch(new[] { "S-1", "S-2", "S-3" }, "调查员甲", W3Demo.Day(5, 19, 12)).IsSuccess);
            var added = sink.Written.Skip(n).ToList();
            Assert.Equal(new[] { CrossCheckRegister.ActionBatchConfirm, CrossCheckRegister.ActionBatchConfirm, CrossCheckRegister.ActionBatchConfirm, CrossCheckRegister.ActionBatchCommit }, added.Select(a => a.Action));
            Assert.Equal("interview.crosscheck.batch_commit", CrossCheckRegister.ActionBatchCommit);
            string id = CrossCheckRegister.BatchIdOf(added[0]);
            Assert.False(string.IsNullOrEmpty(id));
            Assert.All(added, a => Assert.Equal(id, CrossCheckRegister.BatchIdOf(a)));
            Assert.Contains("S-1,S-2,S-3", added[3].AfterValueSummary);
            Assert.Equal(added.Count, CrossCheckRegister.EffectiveAudit(sink.Written).Count - n);
        }

        [Fact]
        public void Batch_TwoBatches_HaveDistinctIds_SubmitRowsHaveNone()
        {
            var sink = new FaultSink();
            var reg = Reg(sink, "S-1", "S-2");
            reg.ConfirmConsistentBatch(new[] { "S-1" }, "调查员甲", W3Demo.Day(5, 19, 12));
            reg.ConfirmConsistentBatch(new[] { "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            var ids = sink.Written.Where(w => w.Action == CrossCheckRegister.ActionBatchCommit).Select(CrossCheckRegister.BatchIdOf).ToList();
            Assert.Equal(2, ids.Distinct().Count());
            Assert.All(sink.Written.Where(w => w.Action == CrossCheckRegister.ActionSubmit), w => Assert.Null(CrossCheckRegister.BatchIdOf(w)));
            Assert.Null(CrossCheckRegister.BatchIdOf(null));
        }

        [Theory]
        [InlineData(1)]
        [InlineData(2)]
        [InlineData(3)]
        public void Batch_RowWriteFails_NoCommit_AbortCarriesBatchId_StateUnchanged_ReplayVoidsRows(int failAt)
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionBatchConfirm, FailNth = failAt };
            var reg = Reg(sink, "S-1", "S-2", "S-3");
            int n = sink.Written.Count;
            var r = reg.ConfirmConsistentBatch(new[] { "S-1", "S-2", "S-3" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            var added = sink.Written.Skip(n).ToList();
            Assert.DoesNotContain(added, a => a.Action == CrossCheckRegister.ActionBatchCommit);
            Assert.Equal(failAt - 1, added.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, added.Last().Action);
            if (failAt > 1)
            {
                Assert.Equal(CrossCheckRegister.BatchIdOf(added[0]), CrossCheckRegister.BatchIdOf(added.Last()));
            }

            Assert.All(reg.Entries, e => Assert.Equal(CrossCheckState.PendingConfirmation, e.State));
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);
        }

        [Fact]
        public void Batch_CommitWriteFails_StateUnchanged_AuditFailed_RowsVoidOnReplay_RetrySucceeds()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionBatchCommit };
            var reg = Reg(sink, "S-1", "S-2");
            int n = sink.Written.Count;
            var r = reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.False(r.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.All(reg.Entries, e => Assert.Equal(CrossCheckState.PendingConfirmation, e.State));
            Assert.All(reg.Entries, e => Assert.False(e.ConfirmedInBatch));
            var added = sink.Written.Skip(n).ToList();
            Assert.Equal(2, added.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, added.Last().Action);
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);

            // 故障解除后重试：第二批有 commit，只有第二批的行生效
            Assert.True(reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 13)).IsSuccess);
            var eff = CrossCheckRegister.EffectiveAudit(sink.Written).Where(a => a.Action == CrossCheckRegister.ActionBatchConfirm).ToList();
            Assert.Equal(2, eff.Count);
            Assert.Single(eff.Select(CrossCheckRegister.BatchIdOf).Distinct());
            Assert.NotEqual(CrossCheckRegister.BatchIdOf(added[0]), CrossCheckRegister.BatchIdOf(eff[0]));
        }

        [Fact]
        public void Batch_AbortAlsoFails_NoThrow_AuditFailed_OrphanRowsStillVoid()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionBatchCommit, FailAbort = true };
            var reg = Reg(sink, "S-1", "S-2");
            var r = reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.All(reg.Entries, e => Assert.Equal(CrossCheckState.PendingConfirmation, e.State));
            Assert.DoesNotContain(sink.Written, a => a.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.Equal(2, sink.Written.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);
        }

        [Fact]
        public void EffectiveAudit_LegacyRowsWithoutBatchId_Void_OtherRowsKeptInOrder()
        {
            DateTimeOffset t = W3Demo.Day(5, 19, 12);
            var legacy = new InvestigationAuditEntry(t, "甲", CrossCheckRegister.ActionBatchConfirm, InvestigationAuditCategories.Interview, "批量确认一致 S-1（IR-03，1/1）", "x", "Confirmed");
            var submit = new InvestigationAuditEntry(t, "流程", CrossCheckRegister.ActionSubmit, InvestigationAuditCategories.Interview, "登记比对 S-1（IR-03）", "", "x");
            var confirm = new InvestigationAuditEntry(t, "甲", CrossCheckRegister.ActionConfirm, InvestigationAuditCategories.Interview, "确认比对结论 S-2（IR-03）", "x", "Confirmed");
            var eff = CrossCheckRegister.EffectiveAudit(new[] { submit, legacy, confirm });
            Assert.Equal(new[] { submit, confirm }, eff);
            Assert.Empty(CrossCheckRegister.EffectiveAudit(null));
            Assert.Throws<NotSupportedException>(() => ((IList<InvestigationAuditEntry>)eff).Clear());
        }

        [Fact]
        public void EffectiveAudit_CommitCountMismatch_BatchVoid()
        {
            // 篡改/截断：commit 列 2 条，但只找到 1 条同 batchId 的行 → 整批作废
            var sink = new FaultSink();
            var reg = Reg(sink, "S-1", "S-2");
            reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            var rows = sink.Written.ToList();
            rows.RemoveAt(rows.FindIndex(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(rows), a => a.Action == CrossCheckRegister.ActionBatchConfirm);
        }

        [Fact]
        public void EffectiveAudit_CommitBeforeRows_DoesNotCount()
        {
            // commit 必须在其全部行之后；行出现在 commit 之后（乱序重放）视为作废
            var sink = new FaultSink();
            var reg = Reg(sink, "S-1");
            reg.ConfirmConsistentBatch(new[] { "S-1" }, "调查员甲", W3Demo.Day(5, 19, 12));
            var rows = sink.Written.ToList();
            var commit = rows.Last();
            rows.RemoveAt(rows.Count - 1);
            rows.Insert(rows.Count - 1, commit);
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(rows), a => a.Action == CrossCheckRegister.ActionBatchConfirm);
        }

        [Fact]
        public void EffectiveAudit_SameBatchRowAppendedAfterValidCommit_IsVoid()
        {
            var sink = new FaultSink();
            var reg = Reg(sink, "S-1", "S-2");
            reg.ConfirmConsistentBatch(new[] { "S-1", "S-2" }, "调查员甲", W3Demo.Day(5, 19, 12));
            var rows = sink.Written.ToList();
            var first = rows.First(a => a.Action == CrossCheckRegister.ActionBatchConfirm);
            var late = new InvestigationAuditEntry(first.Utc, first.OperatorName, first.Action, first.Category, first.CommandName, first.BeforeValueSummary, first.AfterValueSummary);
            rows.Add(late);
            var eff = CrossCheckRegister.EffectiveAudit(rows);
            Assert.Equal(2, eff.Count(a => a.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(late, eff);
        }

        [Theory]
        [InlineData("批量确认一致 S-1（IR-03，1/1） [batch=abc")]
        [InlineData("批量确认一致 S-1（IR-03，1/1） [batch=]")]
        [InlineData("批量确认一致 S-1（IR-03，1/1） [batch=abc] 尾注")]
        [InlineData("批量确认一致 S-1（IR-03，1/1）")]
        public void BatchIdOf_MalformedOrMissingTag_IsNull(string command)
        {
            var e = new InvestigationAuditEntry(W3Demo.Day(5, 19, 12), "甲", CrossCheckRegister.ActionBatchConfirm, InvestigationAuditCategories.Interview, command, "", "Confirmed");
            Assert.Null(CrossCheckRegister.BatchIdOf(e));
        }

        // ---------- ② 单条审计失败返回错误码 ----------

        [Fact]
        public void SingleConfirm_AuditFails_ReturnsAuditFailed_NoThrow_StateUnchanged()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionConfirm };
            var reg = new CrossCheckRegister(sink);
            reg.Submit(Contra("S-1"), "流程", W3Demo.Day(5, 19, 11));
            Result<CrossCheckEntry> r = reg.Confirm("S-1", "调查员甲", W3Demo.Day(5, 19, 12), "核对（虚构）");
            Assert.False(r.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", r.ErrorCode);
            var e = reg.Get("S-1");
            Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
            Assert.Null(e.DecidedBy);
            Assert.Null(e.DecidedUtc);
            Assert.True(reg.Confirm("S-1", "调查员甲", W3Demo.Day(5, 19, 13)).IsSuccess); // 故障只注入一次，重试成功
        }

        [Fact]
        public void SingleDismiss_AuditFails_ReturnsAuditFailed_NoThrow_StateUnchanged()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionDismiss };
            var reg = new CrossCheckRegister(sink);
            reg.Submit(Contra("S-1"), "流程", W3Demo.Day(5, 19, 11));
            var r = reg.Dismiss("S-1", "调查员甲", W3Demo.Day(5, 19, 12), "数据源有误（虚构）");
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, r.ErrorCode);
            Assert.Equal(CrossCheckState.PendingConfirmation, reg.Get("S-1").State);
            Assert.Equal(string.Empty, reg.Get("S-1").Note ?? string.Empty);
        }

        // ---------- ③ decidedUtc 毫秒 ----------

        [Fact]
        public void ToJson_DecidedUtc_KeepsMilliseconds_InUtc()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            reg.Submit(Contra("S-1"), "流程", W3Demo.Day(5, 19, 11));
            var t = new DateTimeOffset(2026, 5, 19, 12, 0, 7, 123, TimeSpan.FromHours(8)).AddTicks(4567);
            reg.Confirm("S-1", "调查员甲", t);
            Assert.Contains("\"decidedUtc\":\"2026-05-19T04:00:07.123Z\"", reg.Get("S-1").ToJson());
        }

        [Fact]
        public void ToJson_DecidedUtc_WholeSecond_StillHasThreeDigits()
        {
            var reg = Reg(new InMemoryInvestigationAuditSink(), "S-1");
            reg.ConfirmConsistentBatch(new[] { "S-1" }, "调查员甲", W3Demo.Day(5, 19, 12));
            Assert.Contains("\"decidedUtc\":\"2026-05-19T04:00:00.000Z\"", reg.Get("S-1").ToJson());
        }
    }
}
