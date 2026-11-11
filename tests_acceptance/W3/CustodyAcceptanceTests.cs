using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Mcis.Data.Audit;
using Mcis.Data.CasePackage;
using Mcis.Domain.Evidence;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>验收重点①：保管链只追加、prev 哈希链防篡改、与现有 AuditLog 7 键格式兼容。</summary>
    public class CustodyAcceptanceTests
    {
        private static CustodyLedger Seeded(W3AccFixture.LineSink sink = null)
        {
            var ledger = new CustodyLedger(sink);
            AssertOk(ledger.Register(W3AccFixture.MaryVdr(), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40)));
            AssertOk(ledger.Register(W3AccFixture.LilyVdr(), W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 10, 5)));
            return ledger;
        }

        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        [Fact]
        public void Register_RecordsSourceExtractorTimeHash_AndIsAppendOnly()
        {
            var sink = new W3AccFixture.LineSink();
            CustodyLedger ledger = Seeded(sink);
            Assert.Equal(2, ledger.Events.Count);
            Assert.Equal(2, sink.Lines.Count);
            EvidenceItem ev = ledger.Get("EV-001");
            Assert.Equal("Mary 轮 VDR 舱（虚构）", ev.Source);
            Assert.Equal(W3AccFixture.OpA, ev.ExtractedBy);
            Assert.Equal(W3AccFixture.Cst(5, 18, 18, 40), ev.ExtractedUtc);
            Assert.Equal(W3AccFixture.ShaMaryVdr, ev.Sha256);
            Assert.Equal(CustodyLedger.RelativePath, "audit/custody.jsonl");

            string snapshot = ev.Sha256;
            AssertOk(ledger.RecordChange("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 8, 0), W3AccFixture.ShaDerived, "派生脱敏副本（虚构）"));
            Assert.Equal(snapshot, ledger.Get("EV-001").Sha256);
            Assert.Equal(W3AccFixture.ShaDerived, ledger.CurrentSha256("EV-001"));
            Assert.Equal(3, ledger.JsonLines.Count);
        }

        [Fact]
        public void PublicApi_HasNoDeleteOrInPlaceUpdate()
        {
            string[] forbidden = { "Remove", "Delete", "Update", "Edit", "Clear", "Set", "Replace" };
            foreach (MethodInfo m in typeof(CustodyLedger).GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
            {
                Assert.DoesNotContain(forbidden, f => m.Name.StartsWith(f, StringComparison.Ordinal));
            }

            Assert.Null(typeof(EvidenceItem).GetProperty(nameof(EvidenceItem.Sha256)).GetSetMethod());
            Assert.Null(typeof(CustodyEvent).GetProperty(nameof(CustodyEvent.Sha256)).GetSetMethod());
        }

        [Fact]
        public void AccessCount_AndHistory_SupportScreenshotColumns()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放"));
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 16, 0), "核对哈希"));
            Assert.Equal(2, ledger.AccessCount("EV-001"));
            Assert.Equal(0, ledger.AccessCount("EV-002"));
            IReadOnlyList<CustodyEvent> hist = ledger.HistoryOf("EV-001");
            Assert.Equal(3, hist.Count);
            Assert.Equal(CustodyEventKind.Access, hist[2].Kind);
            Assert.Equal("核对哈希", hist[2].Detail);
            Assert.Equal(W3AccFixture.OpA, hist[2].OperatorName);
        }

        [Fact]
        public void Verify_RecordsMatchAndMismatch_WithoutRewritingHistory()
        {
            CustodyLedger ledger = Seeded();
            int n = ledger.Events.Count;
            Mcis.Core.Result<CustodyEvent> ok = ledger.Verify("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 10, 0), W3AccFixture.ShaMaryVdr);
            AssertOk(ok);
            Assert.True(ok.Value.VerifyMatched);
            Mcis.Core.Result<CustodyEvent> bad = ledger.Verify("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 11, 0), W3AccFixture.ShaOther);
            AssertOk(bad);
            Assert.False(bad.Value.VerifyMatched);
            Assert.Equal(n + 2, ledger.Events.Count);
            Assert.Equal(W3AccFixture.ShaMaryVdr, ledger.CurrentSha256("EV-001"));
        }

        [Fact]
        public void Load_DetectsEditedLine()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放"));
            var lines = new List<string>(ledger.JsonLines);
            lines[0] = lines[0].Replace(W3AccFixture.ShaMaryVdr, W3AccFixture.ShaDerived);
            Mcis.Core.Result<CustodyLedger> loaded = CustodyLedger.Load(lines);
            Assert.False(loaded.IsSuccess);
            Assert.Equal(CustodyLedger.ErrChainBroken, loaded.ErrorCode);
        }

        [Fact]
        public void Load_DetectsDeletedLine()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放"));
            var deleted = new List<string> { ledger.JsonLines[0], ledger.JsonLines[2] };
            Mcis.Core.Result<CustodyLedger> loaded = CustodyLedger.Load(deleted);
            Assert.False(loaded.IsSuccess);
            Assert.Equal(CustodyLedger.ErrChainBroken, loaded.ErrorCode);
        }

        [Fact]
        public void Load_DetectsReorderedLines()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放"));
            var reordered = new List<string> { ledger.JsonLines[1], ledger.JsonLines[0], ledger.JsonLines[2] };
            Mcis.Core.Result<CustodyLedger> loaded = CustodyLedger.Load(reordered);
            Assert.False(loaded.IsSuccess);
            Assert.Equal(CustodyLedger.ErrChainBroken, loaded.ErrorCode);
        }

        [Fact]
        public void Load_DetectsCanonicalWhitespaceTamper_OnLastLine()
        {
            CustodyLedger ledger = Seeded();
            var lines = new List<string>(ledger.JsonLines);
            lines[1] = lines[1].Replace("\"operator\":", "\"operator\" :");
            Mcis.Core.Result<CustodyLedger> loaded = CustodyLedger.Load(lines);
            Assert.False(loaded.IsSuccess);
            Assert.Equal(CustodyLedger.ErrChainBroken, loaded.ErrorCode);
        }

        [Fact]
        public void Load_RoundTrips_AndContinuesPrevChain()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-002", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 12, 0), "查阅"));
            CustodyLedger reloaded = CustodyLedger.Load(ledger.JsonLines).Value;
            Assert.Equal(ledger.JsonLines, reloaded.JsonLines);
            Assert.Equal(W3AccFixture.ShaLilyVdr, reloaded.CurrentSha256("EV-002"));
            AssertOk(reloaded.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放"));
            Assert.Equal(Sha256Hex.OfUtf8(ledger.JsonLines.Last()), reloaded.Events.Last().PrevLineHash);
            Assert.Equal(ledger.Events.Count + 1, reloaded.Events.Last().Seq);
        }

        [Fact]
        public void FirstLinePrevHash_Is64Zeros()
        {
            CustodyLedger ledger = Seeded();
            Assert.Equal(Sha256Hex.Zero, ledger.Events[0].PrevLineHash);
            Assert.Equal(64, ledger.Events[0].PrevLineHash.Length);
            Assert.Equal(Sha256Hex.OfUtf8(ledger.JsonLines[0]), ledger.Events[1].PrevLineHash);
        }

        [Fact]
        public void CustodyJsonl_IsReadableByExistingAuditRecordAndAuditLog()
        {
            CustodyLedger ledger = Seeded();
            AssertOk(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放 \"引号\"\n换行"));

            for (int i = 0; i < ledger.Events.Count; i++)
            {
                CustodyEvent ev = ledger.Events[i];
                AuditRecord rec = AuditRecord.FromJsonLine(ledger.JsonLines[i]);
                Assert.Equal(ev.Utc, rec.Utc);
                Assert.Equal(ev.OperatorName, rec.OperatorName);
                Assert.Equal(ev.Action, rec.Action);
                Assert.Equal("Custody", rec.Category);
                Assert.Equal(ev.CommandName, rec.CommandName);
                Assert.Equal(ev.BeforeSummary, rec.BeforeValueSummary);
                Assert.Equal(ev.AfterSummary, rec.AfterValueSummary);
                string seven = rec.ToJsonLine();
                Assert.True(ledger.JsonLines[i].StartsWith(seven.Substring(0, seven.Length - 1), StringComparison.Ordinal),
                    "custody.jsonl 行应以 audit.jsonl 的 7 个标准键开头，以便 AuditRecord.FromJsonLine 兼容读取。");
            }

            string dir = Path.Combine(Path.GetTempPath(), "w3-acc-custody-" + Guid.NewGuid().ToString("N"));
            try
            {
                string path = Path.Combine(dir, "audit", "custody.jsonl");
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(path, string.Join("\n", ledger.JsonLines) + "\n", new UTF8Encoding(false));
                var log = new AuditLog(path);
                IReadOnlyList<AuditRecord> all = log.ReadAll();
                Assert.Equal(ledger.Events.Count, all.Count);
                Assert.Equal(CustodyEvent.ActionAccess, all.Last().Action);
            }
            finally
            {
                if (Directory.Exists(dir))
                {
                    Directory.Delete(dir, true);
                }
            }
        }

        [Fact]
        public void InvestigationAuditEntry_IsByteIdenticalToExistingAuditRecord()
        {
            var utc = new DateTimeOffset(2026, 5, 19, 9, 31, 12, 345, TimeSpan.FromHours(8));
            const string op = "调查员 A（虚构）";
            const string action = "interview.contradiction.confirm";
            const string cmd = "确认矛盾 S-03-2";
            const string before = "待确认；\"引号\"\\反斜杠";
            const string after = "已确认\n换行\t制表\u0001";
            var entry = new InvestigationAuditEntry(utc, op, action, "Interview", cmd, before, after);
            var record = new AuditRecord(utc, op, action, "Interview", cmd, before, after);
            Assert.Equal(record.ToJsonLine(), entry.ToJsonLine());

            string dir = Path.Combine(Path.GetTempPath(), "w3-acc-audit-" + Guid.NewGuid().ToString("N"));
            try
            {
                string path = Path.Combine(dir, CasePackageLayout.AuditDirectory, CasePackageLayout.AuditFileName);
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(path, entry.ToJsonLine() + "\n", new UTF8Encoding(false));
                IReadOnlyList<AuditRecord> all = new AuditLog(path).ReadAll();
                Assert.Single(all);
                Assert.Equal(action, all[0].Action);
                Assert.Equal("Interview", all[0].Category);
                Assert.Equal(entry.Utc, all[0].Utc);
            }
            finally
            {
                if (Directory.Exists(dir))
                {
                    Directory.Delete(dir, true);
                }
            }
        }
    }
}
