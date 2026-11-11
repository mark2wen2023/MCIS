using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>W18 修复复测：覆盖裁定 D01–D05、B1–B7。示例数据均为虚构，除非另有说明。</summary>
    public sealed class RetestW18RulingsAcceptanceTests
    {
        private static readonly string[] Ev = { "EV-001" };
        private static readonly string[] Node = { "C2" };
        private static readonly DateTimeOffset Inc = HM(38, 24);
        private const string GoodSha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
        private const string BadSha  = "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff";

        private static FatigueIndicators Fat(DateTimeOffset incident, TimeSpan? offset, (DateTimeOffset, DateTimeOffset)[] sleep, WorkRestSchedule s = null, FatigueRules rules = null, bool complete = false)
        {
            var r = FatigueCalculator.Compute(incident, offset, sleep, s, rules, complete);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        // ---------- D01 ----------

        [Fact]
        public void D01_ThreeStatuses_Measured_NoSleepWithinLimit_InsufficientCoverage()
        {
            var measured = Fat(Inc, Ship, new[] { (Inc.AddHours(-38), Inc.AddHours(-30)) });
            Assert.Equal(TimeSpan.FromHours(30), measured.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.Measured, measured.ContinuousAwakeStatus);

            var atLimit = Fat(Inc, Ship, new[] { (Inc.AddHours(-170), Inc.AddDays(-7)) });
            Assert.Equal(TimeSpan.FromDays(7), atLimit.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.Measured, atLimit.ContinuousAwakeStatus);

            var beyond = Fat(Inc, Ship, new[] { (Inc.AddHours(-180), Inc.AddHours(-169)) });
            Assert.Null(beyond.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, beyond.ContinuousAwakeStatus);
            Assert.Contains(">7d", beyond.ContinuousAwakeNote);

            var shortRec = WorkRestSchedule.FromWork(Inc.AddHours(-12), Inc, new[] { (Inc.AddHours(-12), Inc) }).Value;
            var cov = Fat(Inc, Ship, null, shortRec);
            Assert.Null(cov.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.InsufficientCoverage, cov.ContinuousAwakeStatus);
        }

        // ---------- D02 / D03 already in rewritten original tests; tighten D03 flags ----------

        [Fact]
        public void D03_CoverageFlags_AndUnknownNotCountedAsAwake()
        {
            var s = WorkRestSchedule.FromRest(Inc.AddHours(-12), Inc, new[] { (Inc.AddHours(-10), Inc.AddHours(-6)) }).Value;
            var f = Fat(Inc, Ship, null, s);
            Assert.True(f.Truncated);
            Assert.True(f.RestLast7dTruncated);
            Assert.Equal(Inc.AddHours(-12), f.CoverageStart);
            Assert.Equal(Inc, f.CoverageEnd);
            Assert.Equal(TimeSpan.FromHours(4), f.SleepLast24h);
            Assert.Equal(TimeSpan.FromHours(12), f.UnknownLast24h); // 回看 24h 中记录只覆盖事发前 12h
            Assert.Equal(TimeSpan.FromHours(8), f.AwakeLast24h);    // 记录内工作，记录外不计清醒
            Assert.True(f.SleepIsRestProxy);
        }

        // ---------- D04 already in original; D05 workflow ----------

        [Fact]
        public void D05_ConfirmReject_AuditAndCounting()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var a = new HfacsAnalysis("虚构二副甲", sink);
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node, origin: HfacsOrigin.Agent).IsSuccess);
            Assert.Equal(HfacsReviewStatus.Draft, a.Findings[0].ReviewStatus);
            Assert.Equal(HfacsOrigin.Agent, a.Findings[0].Origin);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            Assert.Single(a.Pending());

            Assert.Equal("hf_invalid_argument", a.Reject("F1", "调查员甲", T0, "  ").ErrorCode);
            Assert.Equal(HfacsReviewStatus.Draft, a.Findings[0].ReviewStatus);

            Assert.True(a.Confirm("F1", "调查员甲", T0, "属实").IsSuccess);
            Assert.Equal(HfacsReviewStatus.Confirmed, a.Findings[0].ReviewStatus);
            Assert.Equal("调查员甲", a.Findings[0].ReviewedBy);
            Assert.Equal(1, a.CountByLayer()[HfacsLayer.UnsafeActs]);
            Assert.Contains(sink.Entries, e => e.Action == HfacsAnalysis.ActionConfirm && e.Category == HumanFactorsAudit.Category);

            Assert.Equal("hf_invalid_state", a.Confirm("F1", "调查员甲", T0).ErrorCode);
            Assert.True(a.AddFinding("F2", "UA-VIO-EXC", "d", EvidenceStrength.Moderate, Ev, Node).IsSuccess);
            Assert.True(a.Reject("F2", "调查员甲", T0, "证据不足").IsSuccess);
            Assert.Equal(0, a.CountByLayerIncludingDrafts()[HfacsLayer.UnsafeActs] - 1); // F1 confirmed only; F2 rejected
            Assert.DoesNotContain(a.ByLayerIncludingDrafts(HfacsLayer.UnsafeActs), f => f.Id == "F2");
            Assert.Contains(sink.Entries, e => e.Action == HfacsAnalysis.ActionReject);
        }

        [Fact]
        public void D05_AuditFailure_LeavesDraft()
        {
            var a = new HfacsAnalysis("虚构二副甲", new BoomSink());
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node).IsSuccess);
            var ex = Record.Exception(() => a.Confirm("F1", "调查员甲", T0));
            Assert.IsType<IOException>(ex);
            Assert.Equal(HfacsReviewStatus.Draft, a.Findings[0].ReviewStatus);
            Assert.Equal(0, a.CountByLayer()[HfacsLayer.UnsafeActs]);
        }

        private sealed class BoomSink : IInvestigationAuditSink
        {
            public void Append(InvestigationAuditEntry entry) { throw new IOException("audit down (simulated)"); }
        }

        // ---------- B1 + Python brute force ----------

        [Fact]
        public void B1_Any24h_TruncatedRestCounts_AndPythonBruteForceAgrees()
        {
            var s = Rest(96, P(12, 18), P(24, 30), P(36, 41), P(46, 51), P(52, 60), P(70, 80), P(88, 96));
            var rep = Check(s, RestOnly());

            // 总量规则仍按严格任意窗口：记录开头 [0,24) 只有 [12,18) 共 6h，应报 Rest24h。
            var r24 = Assert.Single(rep.Violations, v => v.Rule == RestRule.Rest24h);
            Assert.True(r24.ViolatingFrom <= H(0) && H(0) <= r24.ViolatingTo, r24.Detail);
            Assert.Equal(TimeSpan.FromHours(6), r24.Actual);

            // 拆分规则按完整休息段：[24,30) 全长 6h，窗口 [27,51) 最长段为 6h，不得报 LongestRest / RestSplit。
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.RestSplit);
            Assert.DoesNotContain(rep.InsufficientData, v => v.Rule == RestRule.LongestRest || v.Rule == RestRule.RestSplit);

            object payload = B1Payload(96, P(12, 18), P(24, 30), P(36, 41), P(46, 51), P(52, 60), P(70, 80), P(88, 96));
            using (JsonDocument clipped = RunBruteForce(payload, "--mode", "clipped"))
            {
                // 截断口径下 27h 窗口仍是 5h / 3 段（只作对照，不是 C# 拆分规则的期望）
                var at27c = clipped.RootElement.GetProperty("clippedAt27");
                Assert.Equal(5.0, at27c.GetProperty("longestHours").GetDouble(), 3);
                Assert.Equal(3, at27c.GetProperty("periods").GetInt32());
                Assert.Contains(at27c.GetProperty("violations").EnumerateArray().Select(x => x.GetString()), x => x == "LongestRest");
                Assert.Contains(clipped.RootElement.GetProperty("rest24hStartsHours").EnumerateArray(), e => Math.Abs(e.GetDouble()) < 1.0 / 60);
            }

            using (JsonDocument full = RunBruteForce(payload, "--mode", "fullsegment"))
            {
                // 27h 不是休息段起止点，完整段模式不对齐该窗口；对齐窗口上不应出现拆分违规。
                var starts = full.RootElement.GetProperty("alignedStartsHours").EnumerateArray().Select(e => e.GetDouble()).ToList();
                Assert.DoesNotContain(starts, h => Math.Abs(h - 27.0) < 1.0 / 120.0);
                Assert.Contains(starts, h => Math.Abs(h - 24.0) < 1.0 / 60.0);
                Assert.Contains(starts, h => Math.Abs(h - 30.0) < 1.0 / 60.0);
                Assert.False(full.RootElement.GetProperty("covers27h").GetBoolean(), full.RootElement.GetRawText());
                Assert.Equal(0, full.RootElement.GetProperty("violationCounts").GetProperty("LongestRest").GetInt32());
                Assert.Equal(0, full.RootElement.GetProperty("violationCounts").GetProperty("RestSplit").GetInt32());
                Assert.Equal(JsonValueKind.Null, full.RootElement.GetProperty("windowAt27").ValueKind);
            }
        }

        /// <summary>
        /// 21:25 复裁后，拆分规则不再按“窗口截断后最长段”判定。
        /// 休息段 [24,30) 恰 6h 时，窗口起点 24h01m 把该段截成 5h59m，但该起点不是对齐窗口，
        /// 完整段仍为 6h，不得报 LongestRest。原 D06 严格任意窗口断言改写为此口径（不再是缺陷）。
        /// </summary>
        [Fact]
        public void W18_D06_B1_WindowsJustAfterRestStart_AreCaught()
        {
            var s = Rest(96, P(12, 18), P(24, 30), P(36, 41), P(46, 51), P(52, 60), P(70, 80), P(88, 96));
            var rep = Check(s, RestOnly());
            var start = H(24).AddMinutes(1);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest && v.ViolatingFrom <= start && start <= v.ViolatingTo);

            using JsonDocument full = RunBruteForce(
                B1Payload(96, P(12, 18), P(24, 30), P(36, 41), P(46, 51), P(52, 60), P(70, 80), P(88, 96)),
                "--mode", "fullsegment");
            Assert.Equal(JsonValueKind.Null, full.RootElement.GetProperty("windowAt24h01m").ValueKind);
            var starts = full.RootElement.GetProperty("alignedStartsHours").EnumerateArray().Select(e => e.GetDouble()).ToList();
            Assert.DoesNotContain(starts, h => Math.Abs(h - (24.0 + 1.0 / 60.0)) < 1.0 / 120.0);
            Assert.Contains(starts, h => Math.Abs(h - 24.0) < 1.0 / 60.0);
            Assert.Contains(starts, h => Math.Abs(h - 30.0) < 1.0 / 60.0);
        }

        private static object B1Payload(double recordHours, params (DateTimeOffset, DateTimeOffset)[] rest)
        {
            return new
            {
                recordStart = T0.ToString("o"),
                recordEnd = H(recordHours).ToString("o"),
                rest = rest.Select(x => new[] { x.Item1.ToString("o"), x.Item2.ToString("o") }).ToArray(),
                windowHours = 24,
                minRestHours = 10,
                minLongestHours = 6,
                maxPeriods = 2,
                stepSeconds = 60
            };
        }

        private static JsonDocument RunBruteForce(object payload, params string[] extraArgs) => Fx.RunBruteForce(payload, extraArgs);


        // ---------- B2 ----------

        [Fact]
        public void B2_OptimisticPessimistic_UnknownYieldsInsufficientDataOrViolation()
        {
            // 8h 休息 + 8h 未标注 + 8h 工作：乐观（未标注当休息）合规，悲观违规 → 数据不足
            var s = WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(8), DutyKind.Rest),
                new DutyInterval(H(16), H(24), DutyKind.Work)
            }).Value;
            Assert.Single(s.UnknownPeriods());
            var rep = Check(s);
            Assert.Empty(rep.Violations);
            Assert.Contains(rep.InsufficientData, x => x.Rule == RestRule.Rest24h && x.Actual == TimeSpan.FromHours(8));
            Assert.False(rep.IsCompliant);
            Assert.False(rep.IsConclusive);

            // 即使把未标注全当休息也不足 10h → 确认违规，不重复进 InsufficientData
            var hard = WorkRestSchedule.Create(T0, H(24), new[]
            {
                new DutyInterval(H(0), H(4), DutyKind.Rest),
                new DutyInterval(H(6), H(24), DutyKind.Work)
            }).Value;
            var hv = Check(hard);
            Assert.Contains(hv.Violations, x => x.Rule == RestRule.Rest24h);
            Assert.DoesNotContain(hv.InsufficientData, x => x.Rule == RestRule.Rest24h);
        }

        // ---------- B3 ----------

        [Fact]
        public void B3_StrongRejectsUnreliable_ModerateWarns()
        {
            var ledger = new CustodyLedger();
            Assert.True(ledger.Register(new EvidenceItem("EV-001", "虚构", "VDR", "甲", T0, GoodSha), "甲", T0).IsSuccess);
            Assert.True(ledger.Register(new EvidenceItem("EV-002", "虚构", "VDR", "甲", T0, GoodSha), "甲", T0).IsSuccess);
            Assert.True(ledger.Verify("EV-001", "甲", T0.AddMinutes(1), BadSha).IsSuccess);
            Assert.Equal(EvidenceStatus.Mismatch, ledger.StatusOf("EV-001"));
            Assert.True(ledger.MarkNeedsReview("EV-002", "甲", T0.AddMinutes(2), "待复核").IsSuccess);

            var a = new HfacsAnalysis("虚构对象");
            Assert.Equal("hf_evidence_unreliable", a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-001" }, Node, ledger).ErrorCode);
            Assert.Empty(a.Findings);
            Assert.Equal("hf_evidence_unreliable", a.AddFinding("F1b", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-002" }, Node, ledger).ErrorCode);

            Assert.True(a.AddFinding("F2", "UA-ERR-SKL", "d", EvidenceStrength.Moderate, new[] { "EV-001" }, Node, ledger).IsSuccess);
            Assert.Contains("EV-001", a.Findings[0].EvidenceWarnings);
            Assert.True(a.AddFinding("F3", "UA-ERR-PER", "d", EvidenceStrength.Moderate, new[] { "EV-002" }, Node, ledger).IsSuccess);
            Assert.Contains("EV-002", a.Findings[1].EvidenceWarnings);
        }

        // ---------- B4 ----------

        [Fact]
        public void B4_StrongModerate_MustBeLeaf_GroupOnlyToBeVerified()
        {
            var a = new HfacsAnalysis("虚构对象");
            Assert.Equal("hf_non_leaf_category", a.AddFinding("F1", "UA", "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.Equal("hf_non_leaf_category", a.AddFinding("F1", "UA-ERR", "d", EvidenceStrength.Moderate, Ev, Node).ErrorCode);
            Assert.True(a.AddFinding("F1", "UA", "假设", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            Assert.True(a.AddFinding("F2", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node).IsSuccess);
        }

        // ---------- B5 ----------

        [Fact]
        public void B5_WorkKind_AndDailyTotals_ByShipCalendarDay()
        {
            var s = WorkRestSchedule.Create(T0, H(36), new[]
            {
                new DutyInterval(H(0), H(8), WorkKind.Watch),
                new DutyInterval(H(8), H(12), WorkKind.Rest),
                new DutyInterval(H(12), H(16), WorkKind.OtherWork),
                new DutyInterval(H(16), H(24), WorkKind.Rest),
                new DutyInterval(H(24), H(28), WorkKind.Watch)
            }).Value;
            Assert.Equal(WorkKind.Watch, s.WorkPeriods[0].WorkKind);
            Assert.Equal(WorkKind.OtherWork, s.WorkPeriods.First(w => w.Start == H(12)).WorkKind);
            var days = s.DailyTotals(Ship).Value;
            Assert.Equal(2, days.Count);
            var d0 = days[0];
            Assert.Equal(new DateTime(2026, 5, 11), d0.LocalDate);
            Assert.Equal(TimeSpan.FromHours(12), d0.Rest); // 8-12 + 16-24
            Assert.Equal(TimeSpan.FromHours(8), d0.Watch);
            Assert.Equal(TimeSpan.FromHours(4), d0.OtherWork);
            Assert.Equal(TimeSpan.Zero, d0.Unknown);
            Assert.False(d0.IsPartialDay);
            Assert.True(days[1].IsPartialDay);
            Assert.Equal(TimeSpan.FromHours(4), days[1].Watch);
        }

        // ---------- B6 ----------

        [Fact]
        public void B6_BrmDraftConfirm_HistoryAndConfirmedSummary()
        {
            var sink = new InMemoryInvestigationAuditSink();
            var c = BrmChecklist.CreateDefault("虚构值班组", sink);
            Assert.True(c.SetResult("HF-CAP-01", BrmResult.Fail, Ev, "调查员甲").IsSuccess);
            Assert.Equal(BrmReviewStatus.Draft, c.Items.First(i => i.Id == "HF-CAP-01").ReviewStatus);
            Assert.Equal(1, c.Summary()[BrmResult.Fail]);
            Assert.Equal(0, c.ConfirmedSummary()[BrmResult.Fail]);
            Assert.Equal(6, c.ConfirmedSummary()[BrmResult.NotAssessed]);

            Assert.True(c.ConfirmResult("HF-CAP-01", "调查员甲", T0, "确认").IsSuccess);
            Assert.Equal(BrmReviewStatus.Confirmed, c.Items.First(i => i.Id == "HF-CAP-01").ReviewStatus);
            Assert.Equal(1, c.ConfirmedSummary()[BrmResult.Fail]);
            Assert.Contains(sink.Entries, e => e.Action == BrmChecklist.ActionConfirm);

            Assert.True(c.SetResult("HF-CAP-01", BrmResult.Pass, null, "调查员乙", "改判").IsSuccess);
            Assert.Equal(BrmReviewStatus.Draft, c.Items.First(i => i.Id == "HF-CAP-01").ReviewStatus);
            Assert.True(c.History("HF-CAP-01").Count >= 2);
            // 尚未确认新版本时，已确认摘要仍保留上一份 Confirmed
            Assert.Equal(1, c.ConfirmedSummary()[BrmResult.Fail]);
        }

        // ---------- B7 covered by rewritten NoSleepAtAll; extra edge ----------

        [Fact]
        public void B7_CompleteEmpty_OverridesScheduleProxy()
        {
            var s = WorkRestSchedule.FromRest(T0, H(48), new[] { P(23, 31) }).Value;
            var proxied = Fat(Inc, Ship, new (DateTimeOffset, DateTimeOffset)[0], s);
            Assert.True(proxied.SleepIsRestProxy);
            var complete = Fat(Inc, Ship, new (DateTimeOffset, DateTimeOffset)[0], s, complete: true);
            Assert.False(complete.SleepIsRestProxy);
            Assert.Null(complete.ContinuousAwake);
            Assert.Equal(ContinuousAwakeStatus.NoSleepWithinLimit, complete.ContinuousAwakeStatus);
        }

        // ---------- collection exposure (possible new defect) ----------

        [Fact]
        public void W18_D07_FindingsAndItems_AreReadOnlyViews()
        {
            var a = new HfacsAnalysis("虚构对象");
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            var findings = a.Findings as IList<HfacsFinding>;
            bool findingsMutable = findings != null && !findings.IsReadOnly;
            if (findingsMutable)
            {
                try { findings.Clear(); }
                catch (NotSupportedException) { findingsMutable = false; }
            }

            var c = BrmChecklist.CreateDefault("虚构值班组");
            var items = c.Items as IList<BrmItem>;
            bool itemsMutable = items != null && !items.IsReadOnly;
            if (itemsMutable)
            {
                try { items.Clear(); }
                catch (NotSupportedException) { itemsMutable = false; }
            }

            Assert.True(!findingsMutable && a.Findings.Count == 1 && !itemsMutable && c.Items.Count == 6,
                "公开集合可被绕过：Findings mutable=" + findingsMutable + " Items mutable=" + itemsMutable);
        }
    }
}
