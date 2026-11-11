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

namespace Mcis.W3.Tests
{
    public class CustodyLedgerTests
    {
        private static readonly string ShaA = Sha256Hex.OfUtf8("示例数据（虚构）Mary VDR 包");
        private static readonly string ShaB = Sha256Hex.OfUtf8("示例数据（虚构）Lily S-VDR 包");
        private static readonly string ShaDerived = Sha256Hex.OfUtf8("示例数据（虚构）Mary VDR 转写稿");

        private static EvidenceItem Ev001()
        {
            return new EvidenceItem("EV-001", "Mary 轮 VDR 数据包（12 h，虚构）", "Mary 轮 VDR 舱", "调查员 A（虚构）", W3Demo.Day(5, 18, 18, 40), ShaA, "raw/vdr/mary.zip");
        }

        private static CustodyLedger Seeded(ICustodyLineSink sink = null)
        {
            var l = new CustodyLedger(sink);
            Assert.True(l.Register(Ev001(), "调查员 A（虚构）", W3Demo.Day(5, 18, 18, 45)).IsSuccess);
            Assert.True(l.Register(new EvidenceItem("EV-002", "Lily 轮 S-VDR（虚构）", "救助现场", "调查员 B（虚构）", W3Demo.Day(5, 18, 19, 0), ShaB), "调查员 B（虚构）", W3Demo.Day(5, 18, 19, 5)).IsSuccess);
            return l;
        }

        private sealed class ListSink : ICustodyLineSink
        {
            public readonly List<string> Lines = new List<string>();
            public bool Throw;

            public void AppendLine(string jsonLine)
            {
                if (Throw)
                {
                    throw new IOException("disk full (simulated)");
                }

                Lines.Add(jsonLine);
            }
        }

        [Fact]
        public void Sha256Hex_MatchesDataLayerSha256Util()
        {
            byte[] data = Encoding.UTF8.GetBytes("虚构证据 bytes \u0001");
            Assert.Equal(Sha256Util.ComputeBytesHex(data), Sha256Hex.Of(data));
            Assert.Equal(Sha256Util.ComputeBytesHex(Array.Empty<byte>()), Sha256Hex.Of((byte[])null));
            Assert.True(Sha256Hex.IsValid(ShaA));
            Assert.False(Sha256Hex.IsValid("abc"));
            Assert.False(Sha256Hex.IsValid(new string('g', 64)));
        }

        [Fact]
        public void Register_RecordsSourceExtractorTimeAndHash()
        {
            CustodyLedger l = Seeded();
            EvidenceItem it = l.Get("EV-001");
            Assert.Equal("Mary 轮 VDR 舱", it.Source);
            Assert.Equal("调查员 A（虚构）", it.ExtractedBy);
            Assert.Equal(W3Demo.Day(5, 18, 18, 40), it.ExtractedUtc);
            Assert.Equal(ShaA, it.Sha256);
            Assert.Equal(ShaA, l.CurrentSha256("EV-001"));
            Assert.Equal(2, l.Items.Count);
            Assert.Equal(1, l.Events[0].Seq);
            Assert.Equal(Sha256Hex.Zero, l.Events[0].PrevLineHash);
            Assert.Equal(Sha256Hex.OfUtf8(l.JsonLines[0]), l.Events[1].PrevLineHash);
        }

        [Fact]
        public void Register_UppercaseHashIsNormalized()
        {
            var l = new CustodyLedger();
            var it = new EvidenceItem("EV-009", "t", "s", "x", W3Demo.Day(5, 18), ShaA.ToUpperInvariant());
            Assert.True(l.Register(it, "op", W3Demo.Day(5, 18)).IsSuccess);
            Assert.Equal(ShaA, l.CurrentSha256("EV-009"));
        }

        [Fact]
        public void Register_RejectsDuplicateInvalidHashAndMissingFields()
        {
            CustodyLedger l = Seeded();
            Assert.Equal(CustodyLedger.ErrDuplicateId, l.Register(Ev001(), "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidSha256, l.Register(new EvidenceItem("EV-003", "t", "s", "x", W3Demo.Day(5, 18), "1234"), "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.Register(new EvidenceItem("EV-004", "t", "", "x", W3Demo.Day(5, 18), ShaA), "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.Register(new EvidenceItem("EV-005", "t", "s", "", W3Demo.Day(5, 18), ShaA), "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.Register(new EvidenceItem("", "t", "s", "x", W3Demo.Day(5, 18), ShaA), "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.Register(new EvidenceItem("EV-006", "t", "s", "x", W3Demo.Day(5, 18), ShaA), " ", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.Register(null, "op", W3Demo.Day(5, 20)).ErrorCode);
            Assert.Equal(2, l.Events.Count);
        }

        [Fact]
        public void Access_IsRecordedAndCounted()
        {
            CustodyLedger l = Seeded();
            Assert.True(l.RecordAccess("EV-001", "调查员 B（虚构）", W3Demo.Day(5, 22, 15, 31), "只读回放").IsSuccess);
            Assert.True(l.RecordAccess("EV-001", "调查员 A（虚构）", W3Demo.Day(5, 22, 16, 0), "截取舵角序列").IsSuccess);
            Assert.Equal(2, l.AccessCount("EV-001"));
            Assert.Equal(0, l.AccessCount("EV-002"));
            Assert.Equal(3, l.HistoryOf("EV-001").Count);
            Assert.Equal(CustodyEventKind.Access, l.Events.Last().Kind);
            Assert.Equal(ShaA, l.Events.Last().Sha256);
        }

        [Fact]
        public void Access_RejectsUnknownEvidenceAndEmptyPurpose()
        {
            CustodyLedger l = Seeded();
            Assert.Equal(CustodyLedger.ErrUnknownEvidence, l.RecordAccess("EV-404", "op", W3Demo.Day(5, 22), "x").ErrorCode);
            Assert.Equal(CustodyLedger.ErrUnknownEvidence, l.RecordAccess(null, "op", W3Demo.Day(5, 22), "x").ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.RecordAccess("EV-001", "op", W3Demo.Day(5, 22), "").ErrorCode);
            Assert.Equal(2, l.Events.Count);
        }

        [Fact]
        public void Change_AppendsWithoutRewritingRegisteredSnapshot()
        {
            CustodyLedger l = Seeded();
            string firstLine = l.JsonLines[0];
            Result_Ok(l.RecordChange("EV-001", "调查员 A（虚构）", W3Demo.Day(5, 23), ShaDerived, "生成转写派生件"));
            Assert.Equal(ShaA, l.Get("EV-001").Sha256);
            Assert.Equal(ShaDerived, l.CurrentSha256("EV-001"));
            Assert.Equal(firstLine, l.JsonLines[0]);
            CustodyEvent ch = l.Events.Last();
            Assert.Equal(ShaA, ch.PreviousSha256);
            Assert.Equal(ShaDerived, ch.Sha256);
            Assert.Equal("生成转写派生件", ch.Detail);
        }

        [Fact]
        public void Change_RejectsSameHashMissingReasonAndInvalidHash()
        {
            CustodyLedger l = Seeded();
            Assert.Equal(CustodyLedger.ErrNoChange, l.RecordChange("EV-001", "op", W3Demo.Day(5, 23), ShaA.ToUpperInvariant(), "r").ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, l.RecordChange("EV-001", "op", W3Demo.Day(5, 23), ShaDerived, " ").ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidSha256, l.RecordChange("EV-001", "op", W3Demo.Day(5, 23), "zz", "r").ErrorCode);
            Assert.Equal(2, l.Events.Count);
        }

        [Fact]
        public void Verify_AppendsMatchAndMismatch()
        {
            CustodyLedger l = Seeded();
            CustodyEvent ok = l.Verify("EV-001", "op", W3Demo.Day(5, 23), ShaA).Value;
            CustodyEvent bad = l.Verify("EV-002", "op", W3Demo.Day(5, 23), ShaDerived).Value;
            Assert.True(ok.VerifyMatched);
            Assert.False(bad.VerifyMatched);
            Assert.Equal(ShaB, bad.PreviousSha256);
            Assert.Contains("\"result\":\"mismatch\"", l.JsonLines.Last());
            Assert.Equal(4, l.Events.Count);
            Assert.Equal(ShaB, l.CurrentSha256("EV-002"));
        }

        [Fact]
        public void TimeRegression_IsRejected()
        {
            CustodyLedger l = Seeded();
            Assert.Equal(CustodyLedger.ErrTimeRegression, l.RecordAccess("EV-001", "op", W3Demo.Day(5, 17), "x").ErrorCode);
            Assert.True(l.RecordAccess("EV-001", "op", W3Demo.Day(5, 18, 19, 5), "same second ok").IsSuccess);
        }

        [Fact]
        public void Sink_ReceivesIdenticalLines_AndFailureLeavesLedgerUnchanged()
        {
            var sink = new ListSink();
            CustodyLedger l = Seeded(sink);
            Assert.Equal(l.JsonLines, sink.Lines);
            sink.Throw = true;
            Assert.Throws<IOException>(() => l.RecordAccess("EV-001", "op", W3Demo.Day(5, 22), "x"));
            Assert.Equal(2, l.Events.Count);
            Assert.Equal(2, l.JsonLines.Count);
        }

        [Fact]
        public void Lines_AreReadableByExistingAuditRecordParser()
        {
            CustodyLedger l = Seeded();
            l.RecordAccess("EV-001", "调查员 B（虚构）", W3Demo.Day(5, 22, 15, 31), "只读回放 \"引号\"\n换行");
            l.RecordChange("EV-001", "调查员 A（虚构）", W3Demo.Day(5, 23), ShaDerived, "派生");
            for (int i = 0; i < l.Events.Count; i++)
            {
                CustodyEvent e = l.Events[i];
                AuditRecord r = AuditRecord.FromJsonLine(l.JsonLines[i]);
                Assert.Equal(e.Utc, r.Utc);
                Assert.Equal(e.OperatorName, r.OperatorName);
                Assert.Equal(e.Action, r.Action);
                Assert.Equal("Custody", r.Category);
                Assert.Equal(e.CommandName, r.CommandName);
                Assert.Equal(e.BeforeSummary, r.BeforeValueSummary);
                Assert.Equal(e.AfterSummary, r.AfterValueSummary);
                Assert.Equal(l.JsonLines[i].Substring(0, r.ToJsonLine().Length - 1), r.ToJsonLine().Substring(0, r.ToJsonLine().Length - 1));
                SimpleJson.JsonValue v = SimpleJson.Parse(l.JsonLines[i]);
                Assert.Equal(e.EvidenceId, v.GetString("evidence_id"));
                Assert.Equal(e.Seq, v.GetInt("seq"));
            }
        }

        [Fact]
        public void Lines_WrittenToFile_AreReadByExistingAuditLog()
        {
            string dir = Path.Combine(Path.GetTempPath(), "w3-custody-" + Guid.NewGuid().ToString("N"));
            try
            {
                string path = Path.Combine(dir, "audit", "custody.jsonl");
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                CustodyLedger l = Seeded();
                l.RecordAccess("EV-002", "op", W3Demo.Day(5, 22), "回放");
                File.WriteAllText(path, string.Join("\n", l.JsonLines) + "\n", new UTF8Encoding(false));
                var log = new AuditLog(path);
                IReadOnlyList<AuditRecord> all = log.ReadAll();
                Assert.Equal(3, all.Count);
                Assert.Equal(CustodyEvent.ActionAccess, all[2].Action);

                Mcis.Core.Result<CustodyLedger> reloaded = CustodyLedger.Load(File.ReadAllLines(path, Encoding.UTF8));
                Assert.True(reloaded.IsSuccess, reloaded.ErrorMessage);
                Assert.Equal(l.JsonLines, reloaded.Value.JsonLines);
                Assert.Equal(CustodyLedger.RelativePath, "audit/" + Path.GetFileName(path));
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
        public void Load_RoundTripsStateAndContinuesChain()
        {
            CustodyLedger l = Seeded();
            l.RecordChange("EV-001", "op", W3Demo.Day(5, 23), ShaDerived, "派生");
            l.Verify("EV-001", "op", W3Demo.Day(5, 23), ShaDerived);
            var withBlanks = new List<string>(l.JsonLines) { "", "   " };
            CustodyLedger r = CustodyLedger.Load(withBlanks).Value;
            Assert.Equal(ShaDerived, r.CurrentSha256("EV-001"));
            Assert.Equal(ShaA, r.Get("EV-001").Sha256);
            Assert.Equal("raw/vdr/mary.zip", r.Get("EV-001").RelativePath);
            Assert.Equal(W3Demo.Day(5, 18, 18, 40), r.Get("EV-001").ExtractedUtc);
            Assert.True(r.Events.Last().VerifyMatched);
            Assert.True(r.RecordAccess("EV-002", "op", W3Demo.Day(5, 24), "x").IsSuccess);
            Assert.Equal(Sha256Hex.OfUtf8(l.JsonLines.Last()), r.Events.Last().PrevLineHash);
            Assert.Equal(5, r.Events.Last().Seq);
        }

        [Fact]
        public void Load_DetectsEditedLine()
        {
            CustodyLedger l = Seeded();
            l.RecordAccess("EV-001", "op", W3Demo.Day(5, 22), "x");
            var lines = new List<string>(l.JsonLines);
            lines[0] = lines[0].Replace(ShaA, ShaDerived);
            Assert.Equal(CustodyLedger.ErrChainBroken, CustodyLedger.Load(lines).ErrorCode);
        }

        [Fact]
        public void Load_DetectsEditedLastLine_ViaCanonicalFormCheck()
        {
            CustodyLedger l = Seeded();
            var lines = new List<string>(l.JsonLines);
            lines[1] = lines[1].Replace("\"operator\":\"调查员 B（虚构）\"", "\"operator\": \"调查员 B（虚构）\"");
            Assert.Equal(CustodyLedger.ErrChainBroken, CustodyLedger.Load(lines).ErrorCode);
        }

        [Fact]
        public void Load_DetectsDeletedAndReorderedLines()
        {
            CustodyLedger l = Seeded();
            l.RecordAccess("EV-001", "op", W3Demo.Day(5, 22), "x");
            var deleted = new List<string> { l.JsonLines[0], l.JsonLines[2] };
            Assert.Equal(CustodyLedger.ErrChainBroken, CustodyLedger.Load(deleted).ErrorCode);
            var reordered = new List<string> { l.JsonLines[1], l.JsonLines[0], l.JsonLines[2] };
            Assert.Equal(CustodyLedger.ErrChainBroken, CustodyLedger.Load(reordered).ErrorCode);
        }

        [Fact]
        public void Load_RejectsGarbageAndForeignCategory()
        {
            Assert.Equal(CustodyLedger.ErrParse, CustodyLedger.Load(new[] { "not json" }).ErrorCode);
            string foreign = new AuditRecord(DateTimeOffset.UtcNow, "op", "edit", "ECFC", "cmd", "a", "b").ToJsonLine();
            Assert.Equal(CustodyLedger.ErrParse, CustodyLedger.Load(new[] { foreign }).ErrorCode);
            Assert.Equal(CustodyLedger.ErrInvalidArgument, CustodyLedger.Load(null).ErrorCode);
        }

        [Fact]
        public void PublicApi_HasNoDeleteOrUpdateOperations()
        {
            string[] forbidden = { "Remove", "Delete", "Update", "Edit", "Clear", "Set", "Replace" };
            foreach (MethodInfo m in typeof(CustodyLedger).GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly))
            {
                Assert.DoesNotContain(forbidden, f => m.Name.StartsWith(f, StringComparison.Ordinal));
            }

            Assert.Null(typeof(EvidenceItem).GetProperty(nameof(EvidenceItem.Sha256)).GetSetMethod());
        }

        private static void Result_Ok<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }
    }

    public class InvestigationAuditCompatTests
    {
        [Theory]
        [InlineData("调查员 A（虚构）", "interview.contradiction.confirm", "确认矛盾 S-03-2", "待确认；\"引号\"\\反斜杠", "已确认\n换行\t制表\u0001")]
        [InlineData("", "", "", "", "")]
        public void AuditEntry_IsByteIdenticalToAuditRecord(string op, string action, string cmd, string before, string after)
        {
            var utc = new DateTimeOffset(2026, 5, 19, 9, 31, 12, 345, TimeSpan.FromHours(8));
            var e = new InvestigationAuditEntry(utc, op, action, "Interview", cmd, before, after);
            var r = new AuditRecord(utc, op, action, "Interview", cmd, before, after);
            Assert.Equal(r.ToJsonLine(), e.ToJsonLine());
            AuditRecord parsed = AuditRecord.FromJsonLine(e.ToJsonLine());
            Assert.Equal(e.ToJsonLine(), parsed.ToJsonLine());
            Assert.Equal(after, parsed.AfterValueSummary);
        }

        [Fact]
        public void AuditEntry_NullFieldsBecomeEmpty_AndSinkRejectsNull()
        {
            var e = new InvestigationAuditEntry(DateTimeOffset.UnixEpoch, null, null, null, null, null, null);
            Assert.Equal(string.Empty, e.OperatorName);
            var sink = new InMemoryInvestigationAuditSink();
            Assert.Throws<ArgumentNullException>(() => sink.Append(null));
        }

        [Theory]
        [InlineData("{}", true)]
        [InlineData("{\"a\":\"x\",\"n\":12,\"b\":true,\"z\":null}", true)]
        [InlineData("{\"a\":{\"nested\":1}}", false)]
        [InlineData("{\"a\":[1]}", false)]
        [InlineData("{\"a\":\"x\"} trailing", false)]
        [InlineData("{\"a\":\"\\u4e2d\"}", true)]
        [InlineData("{\"a\":\"bad\\q\"}", false)]
        [InlineData("{\"a\"}", false)]
        public void FlatParser_AcceptsOnlyFlatObjects(string json, bool ok)
        {
            Assert.Equal(ok, AuditJson.TryParseFlatObject(json, out Dictionary<string, string> f));
            if (ok && json.Contains("u4e2d"))
            {
                Assert.Equal("中", f["a"]);
            }
        }
    }
}
