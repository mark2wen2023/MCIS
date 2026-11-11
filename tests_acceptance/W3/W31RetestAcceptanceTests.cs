using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>
    /// W3.1 复测（2026-11-11，Codex）：D07 批量确认原子性（故障注入）、UpdateDraft、CrossCheckEntry.ToJson 与 contracts 对照、
    /// 「空数字不允许」= 编号不能为空、允许跳号（Gemini bot 裁定）。全部为虚构数据。
    /// </summary>
    public class W31RetestAcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static CrossCheckResult R(string sid, CrossCheckOutcome o, double? delta = 0.0)
        {
            return new CrossCheckResult(sid, "IR-03", o, delta, "s", "声称（虚构）", "数据（虚构）", "VDR（虚构）", "|Δt| ≤ 30 s");
        }

        /// <summary>可注入故障的审计汇：在第 k 条 batch_confirm（1 起）写入时抛异常；可选让 batch_abort 也失败。
        /// 每次 Append 时记录登记簿中已非 Pending 的条目数，用于证明“审计全部写完前不改状态”。</summary>
        private sealed class FaultSink : IInvestigationAuditSink
        {
            public int FailOnBatchConfirmNo = -1;
            public bool FailAbort;
            public CrossCheckRegister Register;
            public readonly List<InvestigationAuditEntry> Written = new List<InvestigationAuditEntry>();
            public readonly List<int> DecidedCountAtAppend = new List<int>();
            private int _batchConfirmSeen;

            public void Append(InvestigationAuditEntry entry)
            {
                if (Register != null)
                {
                    DecidedCountAtAppend.Add(Register.Entries.Count(e => e.State != CrossCheckState.PendingConfirmation));
                }

                if (entry.Action == CrossCheckRegister.ActionBatchConfirm)
                {
                    _batchConfirmSeen++;
                    if (_batchConfirmSeen == FailOnBatchConfirmNo)
                    {
                        throw new IOException("模拟审计写盘失败（虚构）");
                    }
                }

                if (entry.Action == CrossCheckRegister.ActionBatchAbort && FailAbort)
                {
                    throw new IOException("模拟 batch_abort 写盘失败（虚构）");
                }

                Written.Add(entry);
            }
        }

        private static readonly string[] BatchIds = { "S-c1", "S-c2", "S-c3", "S-c4", "S-c5" };

        private static CrossCheckRegister Seed(FaultSink sink)
        {
            var reg = new CrossCheckRegister(sink);
            foreach (string id in BatchIds)
            {
                AssertOk(reg.Submit(R(id, CrossCheckOutcome.Consistent), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            }

            AssertOk(reg.Submit(R("S-x1", CrossCheckOutcome.Contradictory), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
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

            Assert.Empty(reg.Effective());
            Assert.Equal(BatchIds.Length, reg.PendingConsistent().Count);
        }

        [Theory]
        [InlineData(1)]   // 第 1 条
        [InlineData(3)]   // 中间
        [InlineData(5)]   // 最后一条
        public void D07_AuditFailureAt_FirstMiddleLast_RollsBackWhole_WritesAbort(int failAt)
        {
            var sink = new FaultSink();
            CrossCheckRegister reg = Seed(sink);
            int before = sink.Written.Count;
            sink.FailOnBatchConfirmNo = failAt;

            var res = reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "批量（虚构）");

            Assert.False(res.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, res.ErrorCode);
            Assert.Equal("crosscheck_audit_failed", res.ErrorCode);
            AssertUntouched(reg);

            List<InvestigationAuditEntry> added = sink.Written.Skip(before).ToList();
            Assert.Equal(failAt - 1, added.Count(e => e.Action == CrossCheckRegister.ActionBatchConfirm));
            Assert.Equal(CrossCheckRegister.ActionBatchAbort, added.Last().Action);
            Assert.Equal("interview.crosscheck.batch_abort", added.Last().Action);
            Assert.Single(added, e => e.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.Equal(W3AccFixture.OpA, added.Last().OperatorName);
            // 审计全部写完前不改状态：每次 Append 时已决定条目数均为 0
            Assert.All(sink.DecidedCountAtAppend, n => Assert.Equal(0, n));

            // 故障解除后可重试成功
            sink.FailOnBatchConfirmNo = -1;
            AssertOk(reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 5)));
            Assert.All(BatchIds, id => Assert.True(reg.Get(id).ConfirmedInBatch));
        }

        [Fact]
        public void D07_Success_StateChangesOnlyAfterAllAuditsWritten()
        {
            var sink = new FaultSink();
            CrossCheckRegister reg = Seed(sink);
            int before = sink.DecidedCountAtAppend.Count;
            AssertOk(reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)));
            List<int> during = sink.DecidedCountAtAppend.Skip(before).ToList();
            // W3.2 改写：写审计次数 5 → 6（5 条 batch_confirm + 1 条 batch_commit），各次已决定数仍全为 0。
            Assert.Equal(BatchIds.Length + 1, during.Count);
            Assert.All(during, n => Assert.Equal(0, n));
            Assert.Equal(BatchIds.Length, reg.Effective().Count);
            Assert.DoesNotContain(sink.Written, e => e.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.Equal(CrossCheckRegister.ActionBatchCommit, sink.Written[sink.Written.Count - 1].Action);
        }

        [Theory]
        [InlineData(1)]
        [InlineData(3)]
        [InlineData(5)]
        public void D07_AbortAlsoFails_RecordActualBehaviour(int failAt)
        {
            // 裁定未规定 batch_abort 本身写失败时的处理；本用例只锁定「状态不变 + 返回 crosscheck_audit_failed + 不抛异常」，
            // 遗留的 (failAt-1) 条孤立 batch_confirm 审计记为待确认项。
            var sink = new FaultSink { FailAbort = true };
            CrossCheckRegister reg = Seed(sink);
            int before = sink.Written.Count;
            sink.FailOnBatchConfirmNo = failAt;
            Mcis.Core.Result<IReadOnlyList<CrossCheckEntry>> res = default;
            Exception thrown = Record.Exception(() => res = reg.ConfirmConsistentBatch(BatchIds, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0)));
            Assert.Null(thrown);
            Assert.False(res.IsSuccess);
            Assert.Equal(CrossCheckRegister.ErrAuditFailed, res.ErrorCode);
            AssertUntouched(reg);
            List<InvestigationAuditEntry> added = sink.Written.Skip(before).ToList();
            Assert.DoesNotContain(added, e => e.Action == CrossCheckRegister.ActionBatchAbort);
            Assert.Equal(failAt - 1, added.Count(e => e.Action == CrossCheckRegister.ActionBatchConfirm));
            File.AppendAllText(Path.Combine(Path.GetTempPath(), "w3.1-retest-abort-also-fails.txt"),
                "failAt=" + failAt + " result=" + res.ErrorCode + " orphanBatchConfirm=" + added.Count + " abortWritten=false stateUnchanged=true msg=" + res.ErrorMessage + Environment.NewLine);
        }

        // ---------------- UpdateDraft ----------------

        private static SafetyRecommendationBoard BoardAt(RecommendationStatus target, out InMemoryInvestigationAuditSink audit)
        {
            audit = new InMemoryInvestigationAuditSink();
            var b = new SafetyRecommendationBoard(audit);
            AssertOk(b.CreateDraft("SR-2026-01", "雾航专项程序（虚构）", "Mary 船公司（虚构）", new[] { "HFACS-1" }, W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 0), body: "正文（虚构）", caseId: W3AccFixture.CaseId));
            if (target == RecommendationStatus.Draft) return b;
            AssertOk(b.Issue("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            if (target == RecommendationStatus.Issued) return b;
            AssertOk(b.RecordResponse("SR-2026-01", "Mary 船公司（虚构）", "已开始修订（虚构）", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 10, 0)));
            if (target == RecommendationStatus.Responded) return b;
            if (target == RecommendationStatus.NotAdopted)
            {
                AssertOk(b.MarkNotAdopted("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 10, 0), "理由（虚构）"));
                return b;
            }

            AssertOk(b.MarkImplemented("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 10, 0), "现场核实（虚构）"));
            if (target == RecommendationStatus.Implemented) return b;
            AssertOk(b.Close("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 24, 10, 0), "关闭（虚构）"));
            return b;
        }

        private static string Snapshot(SafetyRecommendation r)
        {
            return string.Join("|", r.Title, r.Body, r.Addressee, string.Join(",", r.CauseNodeIds), r.DueUtc.ToString("O"), r.IsInterim, r.Status, r.ProgressPct, r.CaseId, r.History.Count);
        }

        [Fact]
        public void UpdateDraft_OnDraft_UpdatesFields_WritesOneSafetyrecUpdateAudit()
        {
            SafetyRecommendationBoard b = BoardAt(RecommendationStatus.Draft, out InMemoryInvestigationAuditSink audit);
            int n = audit.Entries.Count;
            var res = b.UpdateDraft("SR-2026-01", W3AccFixture.OpB, W3AccFixture.Cst(5, 20, 11, 0),
                title: "雾航与狭水道专项程序（虚构）", causeNodeIds: new[] { "HFACS-2", "R9" }, dueUtc: W3AccFixture.Cst(9, 30, 0, 0), isInterim: true);
            AssertOk(res);
            SafetyRecommendation r = b.Get("SR-2026-01");
            Assert.Equal("雾航与狭水道专项程序（虚构）", r.Title);
            Assert.Equal("正文（虚构）", r.Body);               // null = 不变
            Assert.Equal("Mary 船公司（虚构）", r.Addressee);
            Assert.Equal(new[] { "HFACS-2", "R9" }, r.CauseNodeIds.ToArray());
            Assert.Equal(W3AccFixture.Cst(9, 30, 0, 0), r.DueUtc);
            Assert.True(r.IsInterim);
            Assert.Equal(RecommendationStatus.Draft, r.Status);
            Assert.Equal(W3AccFixture.CaseId, r.CaseId);
            Assert.Empty(b.ByCauseNode("HFACS-1"));
            Assert.Single(b.ByCauseNode("R9"));

            Assert.Equal(n + 1, audit.Entries.Count);
            InvestigationAuditEntry a = audit.Entries.Last();
            Assert.Equal("safetyrec.update", a.Action);
            Assert.Equal(SafetyRecommendationBoard.ActionUpdate, a.Action);
            Assert.Equal(W3AccFixture.OpB, a.OperatorName);
            Assert.Contains("雾航专项程序（虚构）", a.BeforeValueSummary, StringComparison.Ordinal);
            Assert.Contains("雾航与狭水道专项程序（虚构）", a.AfterValueSummary, StringComparison.Ordinal);
        }

        [Theory]
        [InlineData(RecommendationStatus.Issued)]
        [InlineData(RecommendationStatus.Responded)]
        [InlineData(RecommendationStatus.Implemented)]
        [InlineData(RecommendationStatus.NotAdopted)]
        [InlineData(RecommendationStatus.Closed)]
        public void UpdateDraft_OnNonDraft_ReturnsNotDraft_ContentAndAuditUnchanged(RecommendationStatus status)
        {
            SafetyRecommendationBoard b = BoardAt(status, out InMemoryInvestigationAuditSink audit);
            SafetyRecommendation r = b.Get("SR-2026-01");
            Assert.Equal(status, r.Status);
            string snap = Snapshot(r);
            int n = audit.Entries.Count;

            var res = b.UpdateDraft("SR-2026-01", W3AccFixture.OpB, W3AccFixture.Cst(5, 25, 0, 0),
                title: "篡改标题（虚构）", body: "篡改正文（虚构）", addressee: "他方（虚构）", causeNodeIds: new[] { "X" }, dueUtc: W3AccFixture.Cst(12, 1, 0, 0), isInterim: true);
            Assert.False(res.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrNotDraft, res.ErrorCode);
            Assert.Equal("safetyrec_not_draft", res.ErrorCode);
            Assert.Equal(snap, Snapshot(r));
            Assert.Equal(n, audit.Entries.Count);

            // 即使参数本身也非法（空操作人），非草稿仍应报 not_draft 且无副作用
            var res2 = b.UpdateDraft("SR-2026-01", " ", W3AccFixture.Cst(5, 25, 0, 0), title: "x");
            Assert.False(res2.IsSuccess);
            Assert.Equal(snap, Snapshot(r));
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void UpdateDraft_InvalidInputs_OnDraft_Rejected_NoChange_NoAudit()
        {
            SafetyRecommendationBoard b = BoardAt(RecommendationStatus.Draft, out InMemoryInvestigationAuditSink audit);
            SafetyRecommendation r = b.Get("SR-2026-01");
            string snap = Snapshot(r);
            int n = audit.Entries.Count;
            DateTimeOffset t = W3AccFixture.Cst(5, 20, 11, 0);
            Assert.Equal(SafetyRecommendationBoard.ErrNotFound, b.UpdateDraft("SR-2026-99", W3AccFixture.OpA, t, title: "x").ErrorCode);
            Assert.False(b.UpdateDraft("SR-2026-01", " ", t, title: "x").IsSuccess);
            Assert.False(b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t, title: "  ").IsSuccess);
            Assert.False(b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t, addressee: "").IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t, causeNodeIds: new[] { " ", "" }).ErrorCode);
            Assert.False(b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t, dueUtc: t).IsSuccess);        // 期限须晚于修改时间
            Assert.False(b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t).IsSuccess);                    // 无字段变化
            Assert.False(b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, t, title: r.Title).IsSuccess);   // 值相同 = 无变化
            Assert.Equal(snap, Snapshot(r));
            Assert.Equal(n, audit.Entries.Count);
        }

        private sealed class ThrowingSink : IInvestigationAuditSink
        {
            public bool Armed;
            public void Append(InvestigationAuditEntry entry)
            {
                if (Armed) throw new IOException("模拟审计失败（虚构）");
            }
        }

        [Fact]
        public void UpdateDraft_AuditFailure_LeavesDraftUnchanged()
        {
            var sink = new ThrowingSink();
            var b = new SafetyRecommendationBoard(sink);
            AssertOk(b.CreateDraft("SR-2026-01", "标题（虚构）", "对象（虚构）", new[] { "N1" }, W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 0)));
            SafetyRecommendation r = b.Get("SR-2026-01");
            string snap = Snapshot(r);
            sink.Armed = true;
            Record.Exception(() => b.UpdateDraft("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 11, 0), title: "新标题（虚构）", causeNodeIds: new[] { "N2" }));
            Assert.Equal(snap, Snapshot(r));
        }

        // ---------------- CrossCheckEntry.ToJson ----------------

        private static string RepoFile(string rel)
        {
            var dir = new DirectoryInfo(AppContext.BaseDirectory);
            while (dir != null && !File.Exists(Path.Combine(dir.FullName, rel)))
            {
                dir = dir.Parent;
            }

            Assert.NotNull(dir);
            return Path.Combine(dir.FullName, rel);
        }

        private static JsonElement CrossCheckSchema()
        {
            using JsonDocument doc = JsonDocument.Parse(File.ReadAllText(RepoFile("contracts/schemas/interview.schema.json")));
            return doc.RootElement.GetProperty("$defs").GetProperty("crossCheckResult").Clone();
        }

        /// <summary>按 schema 的 type / enum / required / additionalProperties:false 校验（仓库无 jsonschema 库，手工实现足够本 schema 的子集）。</summary>
        private static void ValidateAgainstSchema(string json)
        {
            JsonElement schema = CrossCheckSchema();
            using JsonDocument doc = JsonDocument.Parse(json);
            JsonElement o = doc.RootElement;
            Assert.Equal(JsonValueKind.Object, o.ValueKind);
            JsonElement props = schema.GetProperty("properties");
            var allowed = props.EnumerateObject().Select(p => p.Name).ToHashSet();
            foreach (JsonProperty p in o.EnumerateObject())
            {
                Assert.True(allowed.Contains(p.Name), "schema 不允许的键（additionalProperties:false）：" + p.Name);
                JsonElement ps = props.GetProperty(p.Name);
                var types = new List<string>();
                if (ps.TryGetProperty("type", out JsonElement t))
                {
                    if (t.ValueKind == JsonValueKind.Array) types.AddRange(t.EnumerateArray().Select(x => x.GetString()));
                    else types.Add(t.GetString());
                }
                else if (ps.TryGetProperty("anyOf", out JsonElement any))
                {
                    foreach (JsonElement alt in any.EnumerateArray())
                    {
                        if (alt.TryGetProperty("type", out JsonElement at)) types.Add(at.GetString());
                        else types.Add("string"); // $ref common utc = string(date-time)
                    }
                }

                string kind = p.Value.ValueKind switch
                {
                    JsonValueKind.String => "string",
                    JsonValueKind.Number => "number",
                    JsonValueKind.True => "boolean",
                    JsonValueKind.False => "boolean",
                    JsonValueKind.Null => "null",
                    _ => p.Value.ValueKind.ToString(),
                };
                Assert.True(types.Contains(kind), p.Name + " 类型 " + kind + " 不在 schema 允许的 [" + string.Join(",", types) + "]");
                if (ps.TryGetProperty("enum", out JsonElement en))
                {
                    Assert.Contains(p.Value.GetString(), en.EnumerateArray().Select(x => x.GetString()));
                }
            }

            foreach (JsonElement req in schema.GetProperty("required").EnumerateArray())
            {
                Assert.True(o.TryGetProperty(req.GetString(), out _), "缺少 required 键：" + req.GetString());
            }
        }

        private static readonly string[] ExpectedKeys =
        {
            "statementId", "recordId", "outcome", "delta", "deltaUnit", "claimedText", "observedText", "sourceLabel", "rule",
            "state", "decidedBy", "decidedUtc", "note", "confirmedInBatch",
        };

        [Fact]
        public void ToJson_CamelCaseKeys_IncludesConfirmedInBatch_MatchesSchemaPropertySet()
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            AssertOk(reg.Submit(R("S-c1", CrossCheckOutcome.Consistent, 12.5), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Submit(R("S-u1", CrossCheckOutcome.Unverifiable, null), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            string pending = reg.Get("S-c1").ToJson();
            using (JsonDocument d = JsonDocument.Parse(pending))
            {
                string[] keys = d.RootElement.EnumerateObject().Select(p => p.Name).ToArray();
                Assert.Equal(ExpectedKeys, keys);
                Assert.All(keys, k => Assert.True(char.IsLower(k[0]) && !k.Contains('_'), "非 camelCase 键：" + k));
                Assert.False(d.RootElement.GetProperty("confirmedInBatch").GetBoolean());
                Assert.Equal("PendingConfirmation", d.RootElement.GetProperty("state").GetString());
                Assert.Equal(JsonValueKind.Null, d.RootElement.GetProperty("decidedBy").ValueKind);
                Assert.Equal(JsonValueKind.Null, d.RootElement.GetProperty("decidedUtc").ValueKind);
                Assert.Equal(12.5, d.RootElement.GetProperty("delta").GetDouble());
            }

            // schema 属性集合与输出键一致（双向）
            var schemaKeys = CrossCheckSchema().GetProperty("properties").EnumerateObject().Select(p => p.Name).OrderBy(x => x, StringComparer.Ordinal).ToArray();
            Assert.Equal(ExpectedKeys.OrderBy(x => x, StringComparer.Ordinal).ToArray(), schemaKeys);
            ValidateAgainstSchema(pending);

            string unv = reg.Get("S-u1").ToJson();
            using (JsonDocument d = JsonDocument.Parse(unv))
            {
                Assert.Equal(JsonValueKind.Null, d.RootElement.GetProperty("delta").ValueKind);
                Assert.Equal("Unverifiable", d.RootElement.GetProperty("outcome").GetString());
            }

            ValidateAgainstSchema(unv);

            AssertOk(reg.ConfirmConsistentBatch(new[] { "S-c1" }, W3AccFixture.OpA, W3AccFixture.Cst(5, 19, 12, 0), "批量（虚构）"));
            string batched = reg.Get("S-c1").ToJson();
            using (JsonDocument d = JsonDocument.Parse(batched))
            {
                Assert.True(d.RootElement.GetProperty("confirmedInBatch").GetBoolean());
                Assert.Equal("Confirmed", d.RootElement.GetProperty("state").GetString());
                Assert.Equal(W3AccFixture.OpA, d.RootElement.GetProperty("decidedBy").GetString());
                // W3.2 改写：decidedUtc 带毫秒，整秒也写作 .000Z。
                Assert.Equal("2026-05-19T04:00:00.000Z", d.RootElement.GetProperty("decidedUtc").GetString());
                Assert.Equal("批量（虚构）", d.RootElement.GetProperty("note").GetString());
            }

            ValidateAgainstSchema(batched);

            AssertOk(reg.Dismiss("S-u1", W3AccFixture.OpB, W3AccFixture.Cst(5, 19, 12, 1), "数据源有误（虚构）"));
            string dismissed = reg.Get("S-u1").ToJson();
            ValidateAgainstSchema(dismissed);
            using (JsonDocument d = JsonDocument.Parse(dismissed))
            {
                Assert.False(d.RootElement.GetProperty("confirmedInBatch").GetBoolean());
                Assert.Equal("Dismissed", d.RootElement.GetProperty("state").GetString());
            }

            File.WriteAllLines(Path.Combine(Path.GetTempPath(), "w3.1-retest-tojson-samples.jsonl"), new[] { pending, unv, batched, dismissed });
        }

        [Theory]
        [InlineData(double.NaN)]
        [InlineData(double.PositiveInfinity)]
        [InlineData(1e-7)]
        [InlineData(-123456789.125)]
        public void ToJson_Delta_IsValidJsonNumberOrNull(double delta)
        {
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            AssertOk(reg.Submit(R("S-d", CrossCheckOutcome.Contradictory, delta), "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            string json = reg.Get("S-d").ToJson();
            using JsonDocument d = JsonDocument.Parse(json);
            JsonElement v = d.RootElement.GetProperty("delta");
            if (double.IsNaN(delta) || double.IsInfinity(delta)) Assert.Equal(JsonValueKind.Null, v.ValueKind);
            else Assert.Equal(delta, v.GetDouble());
            ValidateAgainstSchema(json);
        }

        [Fact]
        public void ToJson_EscapesSpecialCharacters_RoundTrips()
        {
            string tricky = "引号\"反斜杠\\换行\n回车\r制表\t控制\u0001结束（虚构）";
            var reg = new CrossCheckRegister(new InMemoryInvestigationAuditSink());
            var r = new CrossCheckResult("S-esc", "IR-03", CrossCheckOutcome.Contradictory, 1.0, "s", tricky, tricky, tricky, tricky);
            AssertOk(reg.Submit(r, "笔录智能体（虚构）", W3AccFixture.Cst(5, 19, 11, 0)));
            AssertOk(reg.Confirm("S-esc", tricky, W3AccFixture.Cst(5, 19, 12, 0), tricky));
            string json = reg.Get("S-esc").ToJson();
            Assert.DoesNotContain("\n", json);
            using JsonDocument d = JsonDocument.Parse(json);
            foreach (string k in new[] { "claimedText", "observedText", "sourceLabel", "rule", "decidedBy", "note" })
            {
                Assert.Equal(tricky, d.RootElement.GetProperty(k).GetString());
            }

            ValidateAgainstSchema(json);
        }

        // ---------------- 「空数字不允许」= 编号不能为空，允许跳号（Gemini bot 裁定） ----------------

        [Fact]
        public void EmptyNumberRuling_EmptyIdRejected_GapsAllowed()
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            foreach (string bad in new[] { null, "", " ", "SR-2026-", "SR--01" })
            {
                Assert.False(b.CreateDraft(bad, "t（虚构）", "a（虚构）", new[] { "N" }, W3AccFixture.Cst(8, 1, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 0, 0)).IsSuccess);
            }

            Assert.Empty(b.All);
            AssertOk(b.CreateDraft("SR-2026-01", "t（虚构）", "a（虚构）", new[] { "N" }, W3AccFixture.Cst(8, 1, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 0, 0)));
            AssertOk(b.CreateDraft("SR-2026-03", "t（虚构）", "a（虚构）", new[] { "N" }, W3AccFixture.Cst(8, 1, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 0, 1)));  // 跳号允许
            Assert.Equal("SR-2026-04", b.NextId(2026));
            Assert.Equal("SR-2027-01", b.NextId(2027));
        }
    }
}
