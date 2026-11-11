using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>11 个 icmp_* 错误码、演示数据须标「虚构」、不得引用 UnityEngine。</summary>
    public class ErrorDemoGuardAcceptanceTests
    {
        public static readonly string[] ExpectedCodes =
        {
            InterviewCompareErrors.InvalidArgument,
            InterviewCompareErrors.EmptyTranscript,
            InterviewCompareErrors.OrphanAnswer,
            InterviewCompareErrors.MissingAnswer,
            InterviewCompareErrors.InvalidTimestamp,
            InterviewCompareErrors.TimeOrder,
            InterviewCompareErrors.TranscriptInvalid,
            InterviewCompareErrors.StatementNotFound,
            InterviewCompareErrors.NotReviewable,
            InterviewCompareErrors.EntryNotPending,
            InterviewCompareErrors.RecordMismatch,
        };

        [Fact]
        public void ElevenIcmpCodes_AreUnique_Prefixed_AndEachProduced()
        {
            Assert.Equal(11, ExpectedCodes.Length);
            Assert.Equal(11, ExpectedCodes.Distinct().Count());
            Assert.All(ExpectedCodes, c =>
            {
                Assert.StartsWith("icmp_", c);
                Assert.Equal(c, c.Trim());
            });

            var produced = new HashSet<string>(StringComparer.Ordinal);

            produced.Add(InterviewParserCode(TranscriptParser.Parse("")));
            produced.Add(TranscriptParser.Parse("答：没有问（虚构）\n").Issues.Single(i => i.Severity == TranscriptIssueSeverity.Error).Code);
            produced.Add(TranscriptParser.Parse("问：只有问？\n").Issues.Single().Code);
            produced.Add(TranscriptParser.Parse("[00:60] 问：非法？\n答：是。\n").Issues.Single(i => i.Severity == TranscriptIssueSeverity.Error).Code);
            produced.Add(TranscriptParser.Parse("[05:00] 问：先？\n答：先。\n[04:00] 问：后？\n答：后。\n").Issues.Single(i => i.Code == InterviewCompareErrors.TimeOrder).Code);
            produced.Add(TranscriptParser.ApplyTo(null, NewRecord()).ErrorCode);
            produced.Add(TranscriptParser.ApplyTo(TranscriptParser.Parse("答：坏（虚构）\n"), NewRecord()).ErrorCode);

            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("怎么用舵？", "左舵 20 度。", rec.StartUtc.AddMinutes(2)));
            Ok(rec.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec.Locate(1, QaField.Answer, "左舵 20 度"))));
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            Ok(reg.Submit(new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Consistent, 0, "deg", "20", "20", "VDR（虚构）", "r"), Agent, At(5, 19, 10, 0)));

            produced.Add(InterviewReviewActions.ConfirmRow(rec, reg, "S-NOPE", Investigator, At(5, 19, 11, 0), audit).ErrorCode);
            produced.Add(InterviewReviewActions.RejectRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit, "  ").ErrorCode);

            InterviewRecord other = NewRecord("IR-16");
            Ok(other.AddTurn("问", "左舵 20 度。", other.StartUtc.AddMinutes(2)));
            Ok(other.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(other.Locate(1, QaField.Answer, "左舵 20 度"))));
            produced.Add(InterviewReviewActions.ConfirmRow(other, reg, "S-r", Investigator, At(5, 19, 11, 0), audit).ErrorCode);

            Ok(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 0), audit));
            produced.Add(InterviewReviewActions.ConfirmRow(rec, reg, "S-r", Investigator, At(5, 19, 11, 5), audit).ErrorCode);

            // EntryNotPending：另建一条已确认比对、陈述仍为草稿的行再驳回
            InterviewRecord rec2 = NewRecord("IR-17");
            Ok(rec2.AddTurn("问", "左舵 20 度。", rec2.StartUtc.AddMinutes(2)));
            Ok(rec2.AddStatement("S-z", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec2.Locate(1, QaField.Answer, "左舵 20 度"))));
            var audit2 = new InMemoryInvestigationAuditSink();
            var reg2 = new CrossCheckRegister(audit2);
            Ok(reg2.Submit(new CrossCheckResult("S-z", rec2.RecordId, CrossCheckOutcome.Consistent, 0, "deg", "20", "20", "VDR（虚构）", "r"), Agent, At(5, 19, 10, 0)));
            Ok(reg2.Confirm("S-z", Investigator, At(5, 19, 11, 0)));
            produced.Add(InterviewReviewActions.RejectRow(rec2, reg2, "S-z", Investigator, At(5, 19, 11, 5), audit2, "想驳回（虚构）").ErrorCode);

            foreach (string code in ExpectedCodes)
            {
                Assert.True(produced.Contains(code), "没有触发错误码：" + code);
            }
        }

        private static string InterviewParserCode(TranscriptParseResult r)
        {
            return r.Issues.Select(i => i.Code).First();
        }

        [Fact]
        public void Demo_IsLabelledFictional_SixRecords_IR03MatchesPrototypeCounts()
        {
            Assert.Contains("虚构", InterviewCompareDemo.Disclaimer);
            Assert.Contains("虚构", InterviewCompareDemo.Ir03Transcript);
            Assert.Contains("虚构", InterviewCompareDemo.Operator);
            Assert.Contains("虚构", InterviewCompareDemo.Investigator);

            var records = InterviewCompareDemo.Records();
            Assert.Equal(6, records.Count);
            Assert.Equal(new[] { "IR-01", "IR-02", "IR-03", "IR-04", "IR-05", "IR-06" }, records.Select(r => r.RecordId).ToArray());
            Assert.All(records, r =>
            {
                Assert.Contains("虚构", r.Interviewee.Name);
                Assert.Equal(InterviewCompareDemo.CaseId, r.CaseId);
            });

            InterviewRecord ir03 = InterviewCompareDemo.Ir03();
            var parsed = TranscriptParser.Parse(InterviewCompareDemo.Ir03Transcript, new TranscriptParseOptions { RecordingStartUtc = InterviewCompareDemo.Ir03StartUtc });
            Assert.True(parsed.IsValid);
            Assert.Equal(7, parsed.Turns.Count);
            Assert.Equal(7, ir03.Turns.Count);
            Assert.Equal(7, ir03.Statements.Count);

            var audit = new InMemoryInvestigationAuditSink();
            CrossCheckRegister reg = InterviewCompareDemo.CheckedRegister(ir03, out audit);
            var sum = InterviewComparisonView.Summarize(ir03, reg);
            Assert.Equal("7 条陈述 · 3 条矛盾", sum.HeaderText);
            Assert.Equal(3, sum.ContradictionCount);
            Assert.Equal(0, sum.ConfirmedContradictionCount);

            // 矛盾逐条确认，其余一致项批量确认，使名单与原型「3 处矛盾」一致（无待确认后缀）
            foreach (var row in InterviewComparisonView.Rows(ir03, reg).Where(r => r.IsContradiction))
            {
                Ok(reg.Confirm(row.StatementId, InterviewCompareDemo.Investigator, At(5, 19, 12, 0)));
            }
            var consistentIds = InterviewComparisonView.Rows(ir03, reg)
                .Where(r => r.Outcome == CrossCheckOutcome.Consistent && r.State == CrossCheckState.PendingConfirmation)
                .Select(r => r.StatementId).ToArray();
            if (consistentIds.Length > 0)
            {
                Ok(reg.ConfirmConsistentBatch(consistentIds, InterviewCompareDemo.Investigator, At(5, 19, 12, 0)));
            }

            var roster = InterviewComparisonView.Roster(ir03, reg);
            Assert.Equal(RosterStatus.Contradictions, roster.Status);
            Assert.Equal("3 处矛盾", roster.Label);
            Assert.Contains("已签字", roster.Subtitle(TimeSpan.FromHours(8)));
            Assert.Contains("IR-03 · 05-19 09:30", roster.Subtitle(TimeSpan.FromHours(8)));
        }

        [Fact]
        public void Sources_AndAssembly_DoNotReferenceUnityEngine()
        {
            Assembly asm = typeof(TranscriptParser).Assembly;
            Assert.DoesNotContain(asm.GetReferencedAssemblies(), a => a.Name.IndexOf("UnityEngine", StringComparison.OrdinalIgnoreCase) >= 0);
            Assert.DoesNotContain(asm.GetTypes(), t => (t.Namespace ?? string.Empty).StartsWith("UnityEngine", StringComparison.Ordinal));

            string root = FindRepoRoot();
            string[] dirs =
            {
                Path.Combine(root, "unity/Assets/_Project/Scripts/Domain/InterviewCompare"),
                Path.Combine(root, "unity/Tests_W5_Interview"),
            };
            var hits = new List<string>();
            foreach (string dir in dirs)
            {
                foreach (string file in Directory.GetFiles(dir, "*.cs", SearchOption.AllDirectories))
                {
                    if (file.Contains("/bin/") || file.Contains("/obj/"))
                    {
                        continue;
                    }

                    string text = File.ReadAllText(file);
                    if (text.IndexOf("UnityEngine", StringComparison.Ordinal) >= 0)
                    {
                        hits.Add(file.Substring(root.Length).TrimStart('/'));
                    }
                }
            }

            Assert.True(hits.Count == 0, "发现 UnityEngine 引用：" + string.Join("；", hits));
        }

        private static string FindRepoRoot()
        {
            string dir = Directory.GetCurrentDirectory();
            while (dir != null)
            {
                if (File.Exists(Path.Combine(dir, "ROADMAP.md")) && Directory.Exists(Path.Combine(dir, "unity")))
                {
                    return dir;
                }

                dir = Directory.GetParent(dir)?.FullName;
            }

            throw new InvalidOperationException("找不到仓库根目录");
        }
    }
}
