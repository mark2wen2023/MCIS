using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>
    /// W3.2 独立验收（2026-11-11，Gemini bot）：两阶段提交故障注入、EffectiveAudit 重放过滤、
    /// 单条 Confirm/Dismiss 审计失败返回错误码、decidedUtc 毫秒格式与往返解析。全部为虚构数据。
    /// 不修改被测实现。依据：DEFECTS/W3.md 文末 20:34 裁定。
    /// </summary>
    public class W32AcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static CrossCheckResult Consistent(string sid)
        {
            return new CrossCheckResult(sid, "IR-03", CrossCheckOutcome.Consistent, 0.0, "s", "声称（虚构）", "数据（虚构）", "VDR（虚构）", "|Δt| ≤ 30 s");
        }

        private static CrossCheckResult Contra(string sid)
        {
            return new CrossCheckResult(sid, "IR-03", CrossCheckOutcome.Contradictory, 45.0, "s", "14:23（虚构）", "14:22:15（虚构）", "VDR（虚构）", "|Δt| ≤ 30 s");
        }

        /// <summary>
        /// 按动作注入故障：FailAction 的第 FailNth 次（1 起）写入时抛异常；FailAbort 让 batch_abort 也失败。
        /// 每次 Append（含即将失败的那次）记录登记簿中已非 Pending 的条目数，用于证明改状态发生在全部写完之后。
        /// </summary>
        private sealed class FaultSink : IInvestigationAuditSink
        {
            public string FailAction;
            public int FailNth = -1;
            public bool FailAbort;
            public CrossCheckRegister Register;
            public readonly List<InvestigationAuditEntry> Written = new List<InvestigationAuditEntry>();
            public readonly List<int> DecidedCountAtAppend = new List<int>();
            private int _seen;

            public void Append(InvestigationAuditEntry entry)
            {
                if (Register != null)
                {
                    DecidedCountAtAppend.Add(Register.Entries.Count(e => e.State != CrossCheckState.PendingConfirmation));
                }

                if (FailAbort && entry.Action == CrossCheckRegister.ActionBatchAbort)
                {
                    throw new IOException("模拟 batch_abort 写盘失败（虚构）");
                }

                if (FailAction != null && entry.Action == FailAction && FailNth > 0 && ++_seen == FailNth)
                {
                    throw new IOException("模拟审计写盘失败（虚构）");
                }

                Written.Add(entry);
            }
        }

        private static readonly string[] BatchIds = { "S-c1", "S-c2", "S-c3", "S-c4", "S-c5" };

        private static CrossCheckRegister Seed(FaultSink sink, params string[] ids)
        {
            var reg = new CrossCheckRegister(sink);
            string[] use = ids != null && ids.Length > 0 ? ids : BatchIds;
            foreach (string id in use)
            {
                AssertOk(reg.Submit(Consistent(id), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            }

            sink.Register = reg;
            return reg;
        }

        private static void AssertUntouched(CrossCheckRegister reg)
        {
            foreach (CrossCheckEntry e in reg.Entries)
            {
                Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
                Assert.False(e.IsEffective);
                Assert.False(e.ConfirmedInBatch);
                Assert.Null(e.DecidedBy);
                Assert.Null(e.DecidedUtc);
            }
        }

        private static void AssertValidBatchId(string id)
        {
            Assert.False(string.IsNullOrEmpty(id));
            Assert.Equal(32, id.Length);
            Assert.Matches("^[0-9a-f]{32}$", id);
        }

        // ---------------- 两阶段提交：在第 1、3、5 条，以及 commit / abort 本身注入失败 ----------------

        [Theory]
        [InlineData(1)]
        [InlineData(3)]
        [InlineData(5)]
        public void TwoPhase_FailAtConfirm_ReturnsAuditFailed_WritesAbort_StateUnchanged(int failAt)
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionBatchConfirm, FailNth = failAt };
            CrossCheckRegister reg = Seed(sink);
            int before = sink.Written.Count;

            var res = reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "批量（虚构）");

            Assert.False(res.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, res.ErrorCode);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            AssertUntouched(reg);

            List<InvestigationAuditEntry> added = sink.Written.Skip(before).ToList();
            Assert.Equal(failAt - 1, added.Count(e => e.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(added, e => e.Action == CrossCheckRegister.ActionBatchCommit);
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, added[added.Count - 1].Action);
            Assert.Single(added, e => e.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.All(sink.DecidedCountAtAppend, n => Assert.Equal(0, n));

            if (failAt > 1)
            {
                string id = CrossCheckRegister.BatchIdOf(added[0]);
                AssertValidBatchId(id);
                Assert.Equal(id, CrossCheckRegister.BatchIdOf(added[added.Count - 1]));
            }
            else
            {
                AssertValidBatchId(CrossCheckRegister.BatchIdOf(added[added.Count - 1]));
            }

            // 无 commit 的批量行在重放时一律作废
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);

            // 故障解除后可重试
            sink.FailAction = null;
            AssertOk(reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 5)));
            Assert.All(BatchIds, id => Assert.True(reg.Get(id).ConfirmedInBatch));
        }

        [Fact]
        public void TwoPhase_FailAtCommit_ReturnsAuditFailed_WritesAbort_StateUnchanged_RetrySucceeds()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionBatchCommit, FailNth = 1 };
            CrossCheckRegister reg = Seed(sink);
            int before = sink.Written.Count;

            var res = reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "批量（虚构）");

            Assert.False(res.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            AssertUntouched(reg);

            List<InvestigationAuditEntry> added = sink.Written.Skip(before).ToList();
            Assert.Equal(5, added.Count(e => e.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(added, e => e.Action == CrossCheckRegister.ActionBatchCommit);
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, added[added.Count - 1].Action);
            string batchId = CrossCheckRegister.BatchIdOf(added[0]);
            AssertValidBatchId(batchId);
            Assert.All(added, a => Assert.Equal(batchId, CrossCheckRegister.BatchIdOf(a)));
            Assert.All(sink.DecidedCountAtAppend, n => Assert.Equal(0, n));
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);

            sink.FailAction = null;
            AssertOk(reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 13, 0)));
            Assert.Equal(5, reg.Effective().Count);
            var effectiveConfirms = CrossCheckRegister.EffectiveAudit(sink.Written)
                .Where(a => a.Action == CrossCheckRegister.ActionBatchConfirm).ToList();
            Assert.Equal(5, effectiveConfirms.Count);
            Assert.Single(effectiveConfirms.Select(CrossCheckRegister.BatchIdOf).Distinct());
            Assert.NotEqual(batchId, CrossCheckRegister.BatchIdOf(effectiveConfirms[0]));
        }

        [Theory]
        [InlineData("confirm", 1)]
        [InlineData("confirm", 3)]
        [InlineData("confirm", 5)]
        [InlineData("commit", 1)]
        public void TwoPhase_AbortAlsoFails_NoThrow_AuditFailed_StateUnchanged_OrphansVoidOnReplay(string stage, int failAt)
        {
            var sink = new FaultSink
            {
                FailAction = stage == "commit" ? CrossCheckRegister.ActionBatchCommit : CrossCheckRegister.ActionBatchConfirm,
                FailNth = failAt,
                FailAbort = true
            };
            CrossCheckRegister reg = Seed(sink);
            int before = sink.Written.Count;

            Mcis.Core.Result<IReadOnlyList<CrossCheckEntry>> res = default;
            Exception thrown = Record.Exception(() =>
                res = reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)));

            Assert.Null(thrown);
            Assert.False(res.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            AssertUntouched(reg);

            List<InvestigationAuditEntry> added = sink.Written.Skip(before).ToList();
            Assert.DoesNotContain(added, e => e.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.DoesNotContain(added, e => e.Action == CrossCheckRegister.ActionBatchCommit);
            int expectedConfirms = stage == "commit" ? BatchIds.Length : failAt - 1;
            Assert.Equal(expectedConfirms, added.Count(e => e.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(sink.Written), a => a.Action == CrossCheckRegister.ActionBatchConfirm);
        }

        [Fact]
        public void TwoPhase_Success_AllRowsShareBatchId_ThenSingleCommit_StateChangesAfterAudits()
        {
            var sink = new FaultSink();
            CrossCheckRegister reg = Seed(sink);
            int decidedBefore = sink.DecidedCountAtAppend.Count;
            int writtenBefore = sink.Written.Count;

            AssertOk(reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "批量（虚构）"));

            List<int> during = sink.DecidedCountAtAppend.Skip(decidedBefore).ToList();
            Assert.Equal(6, during.Count);
            Assert.All(during, n => Assert.Equal(0, n));

            var added = sink.Written.Skip(writtenBefore).ToList();
            Assert.Equal(6, added.Count);
            Assert.All(added.Take(5), a => Assert.Equal(CrossCheckRegister.ActionBatchConfirm, a.Action));
            Assert.Equal(CrossCheckRegister.ActionBatchCommit, added[5].Action);
            Assert.Equal(string.Join(",", BatchIds), added[5].AfterValueSummary);
            string id = CrossCheckRegister.BatchIdOf(added[0]);
            AssertValidBatchId(id);
            Assert.All(added, a => Assert.Equal(id, CrossCheckRegister.BatchIdOf(a)));
            Assert.Equal(5, reg.Effective().Count);
            Assert.Equal(added.Count, CrossCheckRegister.EffectiveAudit(sink.Written).Count - writtenBefore);
        }

        // ---------------- EffectiveAudit 重放 ----------------

        private static DateTimeOffset T()
        {
            return W3AccFixture.Cst(5, 19, 12, 0);
        }

        private static InvestigationAuditEntry Audit(string action, string command, string after = "", string before = "")
        {
            return new InvestigationAuditEntry(T(), W3AccFixture.OpA, action, InvestigationAuditCategories.Interview, command, before, after);
        }

        private static string Tag(string batchId)
        {
            return " [batch=" + batchId + "]";
        }

        [Fact]
        public void EffectiveAudit_RowsWithoutCommit_AreVoid_OtherRowsKeptInOrder()
        {
            const string bid = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
            var submit = Audit(CrossCheckRegister.ActionSubmit, "登记比对 S-c1（IR-03）");
            var confirm1 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/2）" + Tag(bid));
            var confirm2 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c2（IR-03，2/2）" + Tag(bid));
            var single = Audit(CrossCheckRegister.ActionConfirm, "确认比对结论 S-x1（IR-03）");
            var abort = Audit(CrossCheckRegister.ActionBatchAbort, "批量确认中止" + Tag(bid), "S-c1,S-c2");

            var eff = CrossCheckRegister.EffectiveAudit(new[] { submit, confirm1, confirm2, abort, single });
            Assert.Equal(new[] { submit, abort, single }, eff);
            Assert.Empty(CrossCheckRegister.EffectiveAudit(null));
            Assert.Throws<NotSupportedException>(() => ((IList<InvestigationAuditEntry>)eff).Clear());
        }

        [Fact]
        public void EffectiveAudit_CommitCountMismatch_VoidsWholeBatch()
        {
            const string bid = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
            var c1 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/2）" + Tag(bid));
            var c2 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c2（IR-03，2/2）" + Tag(bid));
            var tooFew = Audit(CrossCheckRegister.ActionBatchCommit, "批量确认提交 1 条" + Tag(bid), "S-c1");
            var tooMany = Audit(CrossCheckRegister.ActionBatchCommit, "批量确认提交 3 条" + Tag(bid), "S-c1,S-c2,S-c3");
            var submit = Audit(CrossCheckRegister.ActionSubmit, "登记比对 S-c1（IR-03）");

            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(new[] { submit, c1, c2, tooFew }),
                a => a.Action == CrossCheckRegister.ActionBatchConfirm);
            Assert.DoesNotContain(CrossCheckRegister.EffectiveAudit(new[] { submit, c1, c2, tooMany }),
                a => a.Action == CrossCheckRegister.ActionBatchConfirm);
            // 提交行本身与非批量行仍保留
            var eff = CrossCheckRegister.EffectiveAudit(new[] { submit, c1, c2, tooFew });
            Assert.Contains(submit, eff);
            Assert.Contains(tooFew, eff);
        }

        [Fact]
        public void EffectiveAudit_RowsAfterCommit_AreVoid_RowsBeforeKept()
        {
            const string bid = "cccccccccccccccccccccccccccccccc";
            var c1 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/2）" + Tag(bid));
            var c2 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c2（IR-03，2/2）" + Tag(bid));
            var commit = Audit(CrossCheckRegister.ActionBatchCommit, "批量确认提交 2 条" + Tag(bid), "S-c1,S-c2");
            var late = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/2）" + Tag(bid));

            var eff = CrossCheckRegister.EffectiveAudit(new[] { c1, c2, commit, late });
            Assert.Equal(new[] { c1, c2, commit }, eff);
            Assert.DoesNotContain(late, eff);
        }

        [Fact]
        public void EffectiveAudit_CommitBeforeRows_DoesNotValidateThoseRows()
        {
            const string bid = "dddddddddddddddddddddddddddddddd";
            var commit = Audit(CrossCheckRegister.ActionBatchCommit, "批量确认提交 1 条" + Tag(bid), "S-c1");
            var c1 = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/1）" + Tag(bid));
            var submit = Audit(CrossCheckRegister.ActionSubmit, "登记比对 S-c1（IR-03）");

            var eff = CrossCheckRegister.EffectiveAudit(new[] { submit, commit, c1 });
            Assert.Equal(new[] { submit, commit }, eff);
            Assert.DoesNotContain(c1, eff);
        }

        [Fact]
        public void EffectiveAudit_LegacyRowsWithoutBatchId_AreVoid()
        {
            var legacy = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c1（IR-03，1/1）");
            var submit = Audit(CrossCheckRegister.ActionSubmit, "登记比对 S-c1（IR-03）");
            var single = Audit(CrossCheckRegister.ActionConfirm, "确认比对结论 S-x1（IR-03）");
            // 残缺标记：未闭合、空 id、标记后还有文字，均视为无 batchId
            var unclosed = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c2（IR-03，1/1） [batch=abc");
            var emptyTag = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c3（IR-03，1/1） [batch=]");
            var trailing = Audit(CrossCheckRegister.ActionBatchConfirm, "批量确认一致 S-c4（IR-03，1/1） [batch=abc] 尾注");

            var eff = CrossCheckRegister.EffectiveAudit(new[] { submit, legacy, unclosed, emptyTag, trailing, single });
            Assert.Equal(new[] { submit, single }, eff);
            Assert.Null(CrossCheckRegister.BatchIdOf(legacy));
            Assert.Null(CrossCheckRegister.BatchIdOf(unclosed));
            Assert.Null(CrossCheckRegister.BatchIdOf(emptyTag));
            Assert.Null(CrossCheckRegister.BatchIdOf(trailing));
            Assert.Null(CrossCheckRegister.BatchIdOf(null));
            Assert.Null(CrossCheckRegister.BatchIdOf(submit));
        }

        // ---------------- 单条 Confirm / Dismiss 审计失败 ----------------

        [Fact]
        public void SingleConfirm_AuditFails_ReturnsAuditFailed_NoThrow_StateUnchanged()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionConfirm, FailNth = 1 };
            var reg = new CrossCheckRegister(sink);
            AssertOk(reg.Submit(Contra("S-x1"), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            CrossCheckEntry before = reg.Get("S-x1");
            Assert.Equal(CrossCheckState.PendingConfirmation, before.State);

            Mcis.Core.Result<CrossCheckEntry> res = default;
            Exception thrown = Record.Exception(() =>
                res = reg.Confirm("S-x1", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "核对（虚构）"));

            Assert.Null(thrown);
            Assert.False(res.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, res.ErrorCode);
            CrossCheckEntry e = reg.Get("S-x1");
            Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
            Assert.False(e.IsEffective);
            Assert.Null(e.DecidedBy);
            Assert.Null(e.DecidedUtc);
            Assert.DoesNotContain(sink.Written, a => a.Action == CrossCheckRegister.ActionConfirm);

            // 故障只注入一次，重试成功
            AssertOk(reg.Confirm("S-x1", W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 5), "核对（虚构）"));
            Assert.Equal(CrossCheckState.Confirmed, reg.Get("S-x1").State);
        }

        [Fact]
        public void SingleDismiss_AuditFails_ReturnsAuditFailed_NoThrow_StateUnchanged()
        {
            var sink = new FaultSink { FailAction = CrossCheckRegister.ActionDismiss, FailNth = 1 };
            var reg = new CrossCheckRegister(sink);
            AssertOk(reg.Submit(Contra("S-x1"), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));

            Mcis.Core.Result<CrossCheckEntry> res = default;
            Exception thrown = Record.Exception(() =>
                res = reg.Dismiss("S-x1", W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 12, 0), "数据源有误（虚构）"));

            Assert.Null(thrown);
            Assert.False(res.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            CrossCheckEntry e = reg.Get("S-x1");
            Assert.Equal(CrossCheckState.PendingConfirmation, e.State);
            Assert.Null(e.DecidedBy);
            Assert.Null(e.DecidedUtc);
            Assert.True(string.IsNullOrEmpty(e.Note));
            Assert.DoesNotContain(sink.Written, a => a.Action == CrossCheckRegister.ActionDismiss);
        }

        // ---------------- decidedUtc：.fffZ 且可往返解析 ----------------

        [Fact]
        public void ToJson_DecidedUtc_FormatIsFfFZ_AndRoundTrips()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            AssertOk(reg.Submit(Contra("S-x1"), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            // 带毫秒与不足毫秒的 tick，以及东八区偏移。
            var t = new DateTimeOffset(2026, 5, 19, 12, 0, 7, 123, TimeSpan.FromHours(8)).AddTicks(4567);
            AssertOk(reg.Confirm("S-x1", W3AccFixture.OpA, t, "核对（虚构）"));

            string json = reg.Get("S-x1").ToJson();
            using JsonDocument d = JsonDocument.Parse(json);
            string s = d.RootElement.GetProperty("decidedUtc").GetString();
            Assert.Equal("2026-05-19T04:00:07.123Z", s);
            Assert.Matches(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", s);
            Assert.Equal(CrossCheckEntry.DecidedUtcFormat, "yyyy-MM-ddTHH:mm:ss.fffZ");

            DateTimeOffset parsed = DateTimeOffset.ParseExact(
                s, CrossCheckEntry.DecidedUtcFormat, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
            Assert.Equal(TimeSpan.Zero, parsed.Offset);
            Assert.Equal(new DateTimeOffset(2026, 5, 19, 4, 0, 7, 123, TimeSpan.Zero), parsed);
            Assert.Equal(s, parsed.ToString(CrossCheckEntry.DecidedUtcFormat, CultureInfo.InvariantCulture));
        }

        [Fact]
        public void ToJson_DecidedUtc_WholeSecond_StillHasThreeDigits_AndRoundTrips()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(sink);
            AssertOk(reg.Submit(Consistent("S-c1"), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.ConfirmConsistentBatch(new[] { "S-c1" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)));

            string json = reg.Get("S-c1").ToJson();
            using JsonDocument d = JsonDocument.Parse(json);
            string s = d.RootElement.GetProperty("decidedUtc").GetString();
            Assert.Equal("2026-05-19T04:00:00.000Z", s);
            Assert.Matches(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$", s);
            DateTimeOffset parsed = DateTimeOffset.ParseExact(
                s, CrossCheckEntry.DecidedUtcFormat, CultureInfo.InvariantCulture,
                DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
            Assert.Equal(new DateTimeOffset(2026, 5, 19, 4, 0, 0, TimeSpan.Zero), parsed);
        }
    }
}
