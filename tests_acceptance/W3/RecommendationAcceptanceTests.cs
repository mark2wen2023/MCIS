using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Evidence;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>验收重点③：安全建议状态机非法转移、逾期、编号（唯一/连续/格式）。对照原型 15 与 recommendation.schema.json。</summary>
    public class RecommendationAcceptanceTests
    {
        private static void AssertOk<T>(Mcis.Core.Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ToString());
        }

        private static SafetyRecommendationBoard Board(out InMemoryInvestigationAuditSink audit)
        {
            audit = new InMemoryInvestigationAuditSink();
            return new SafetyRecommendationBoard(audit);
        }

        private static SafetyRecommendation Draft(SafetyRecommendationBoard board, string id, DateTimeOffset? due = null)
        {
            DateTimeOffset created = W3AccFixture.Cst(5, 20, 10, 0);
            return board.CreateDraft(
                id,
                "Mary 轮公司 SMS 增加狭水道与雾航专项程序（虚构）",
                "Mary 船公司（虚构）",
                new[] { "HFACS-1", "R9" },
                due ?? W3AccFixture.Cst(8, 30, 0, 0),
                W3AccFixture.OpA,
                created,
                body: "虚构建议正文",
                isInterim: false).Value;
        }

        [Fact]
        public void Id_FormatUniquenessAndNextIdAreSequential()
        {
            SafetyRecommendationBoard board = Board(out _);
            Assert.True(SafetyRecommendationBoard.IsValidId("SR-2026-01"));
            Assert.True(SafetyRecommendationBoard.IsValidId("SR-2026-07"));
            Assert.False(SafetyRecommendationBoard.IsValidId("SR-26-01"));
            Assert.False(SafetyRecommendationBoard.IsValidId("SR-2026-1"));
            Assert.False(SafetyRecommendationBoard.IsValidId("sr-2026-01"));
            Assert.Equal("SR-2026-01", board.NextId(2026));
            AssertOk(board.CreateDraft(board.NextId(2026), "星屿 VTS 雾航单向管制（虚构）", "星屿 VTS（虚构）", new[] { "ECFC-C4" }, W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 0)));
            AssertOk(board.CreateDraft(board.NextId(2026), "航道增设 AIS 虚拟航标（虚构）", "航标处（虚构）", new[] { "HFACS-EXT" }, W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 1)));
            Assert.Equal("SR-2026-03", board.NextId(2026));
            Assert.Equal(2, board.All.Select(r => r.Id).Distinct().Count());
            Mcis.Core.Result<SafetyRecommendation> dup = board.CreateDraft("SR-2026-01", "重复（虚构）", "X", new[] { "C1" }, W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 2));
            Assert.False(dup.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrDuplicateId, dup.ErrorCode);
        }

        [Fact]
        public void IllegalTransition_IsRejected_WithoutStateChangeOrAudit()
        {
            SafetyRecommendationBoard board = Board(out InMemoryInvestigationAuditSink audit);
            Draft(board, "SR-2026-01");
            int n = audit.Entries.Count;
            Mcis.Core.Result<SafetyRecommendation> closed = board.Close("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0));
            Assert.False(closed.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, closed.ErrorCode);
            Assert.Equal(RecommendationStatus.Draft, board.Get("SR-2026-01").Status);
            Assert.Equal(n, audit.Entries.Count);

            AssertOk(board.Issue("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            n = audit.Entries.Count;
            Mcis.Core.Result<SafetyRecommendation> impl = board.MarkImplemented("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 10, 0));
            Assert.False(impl.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrIllegalTransition, impl.ErrorCode);
            Assert.Equal(RecommendationStatus.Issued, board.Get("SR-2026-01").Status);
            Assert.Equal(n, audit.Entries.Count);
        }

        [Fact]
        public void Overdue_IsExclusiveOfDueInstant_AndOnlyForOpenIssuedOrResponded()
        {
            SafetyRecommendationBoard board = Board(out _);
            DateTimeOffset created = W3AccFixture.Cst(5, 20, 10, 0);
            DateTimeOffset due = W3AccFixture.Cst(8, 30, 0, 0);
            AssertOk(board.CreateDraft("SR-2026-01", "期限检查（虚构）", "Mary 船公司（虚构）", new[] { "HFACS-1" }, due, W3AccFixture.OpA, created));
            Assert.Empty(board.Overdue(due));
            Assert.Empty(board.Overdue(due.AddSeconds(-1)));
            // 草稿即使过期也不计入（尚未发出）
            Assert.Empty(board.Overdue(due.AddSeconds(1)));

            AssertOk(board.Issue("SR-2026-01", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            Assert.Empty(board.Overdue(due));
            Assert.Single(board.Overdue(due.AddSeconds(1)));
            Assert.True(board.Get("SR-2026-01").IsOverdue(due.AddDays(1)));
        }

        [Fact]
        public void Transitions_WriteAudit()
        {
            SafetyRecommendationBoard board = Board(out InMemoryInvestigationAuditSink audit);
            Draft(board, "SR-2026-05");
            Assert.Contains(audit.Entries, e => e.Action == "safetyrec.create" && e.Category == InvestigationAuditCategories.SafetyRec);
            AssertOk(board.Issue("SR-2026-05", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0), "发出（虚构）"));
            Assert.Equal("safetyrec.transition", audit.Entries.Last().Action);
            Assert.Contains("Issued", audit.Entries.Last().AfterValueSummary, StringComparison.Ordinal);
        }

        [Fact]
        public void InterimMeasure_Flag_IsRecorded()
        {
            SafetyRecommendationBoard board = Board(out _);
            SafetyRecommendation rec = board.CreateDraft(
                "SR-2026-05",
                "临时措施：雾航限速 8 kn（虚构）",
                "Mary 船公司（虚构）",
                new[] { "R6" },
                W3AccFixture.Cst(6, 2, 0, 0),
                W3AccFixture.OpA,
                W3AccFixture.Cst(5, 20, 10, 0),
                isInterim: true).Value;
            Assert.True(rec.IsInterim);
        }

        [Fact]
        public void CauseLink_IsRequired_AndQueryable()
        {
            SafetyRecommendationBoard board = Board(out _);
            Mcis.Core.Result<SafetyRecommendation> noCause = board.CreateDraft("SR-2026-01", "无原因（虚构）", "X", Array.Empty<string>(), W3AccFixture.Cst(8, 30, 0, 0), W3AccFixture.OpA, W3AccFixture.Cst(5, 20, 10, 0));
            Assert.False(noCause.IsSuccess);
            Assert.Equal(SafetyRecommendationBoard.ErrNoCauseLink, noCause.ErrorCode);
            Draft(board, "SR-2026-01");
            Assert.Single(board.ByCauseNode("HFACS-1"));
            Assert.Empty(board.ByCauseNode("NO-SUCH"));
        }

        // 架构师裁定 D02（2026-11-11）：保留 W3 六态状态机 Draft/Issued/Responded/Implemented/NotAdopted/Closed，
        // 新增 ProgressPct 0–100（仅 Responded 可改、进入 Implemented 自动 100、越界拒绝），
        // 看板映射 Draft→草拟、Issued→已发布、Responded→落实中、其余→已关闭；不要求任意状态可驳回。
        [Fact]
        public void W3_D02_StatusModel_MatchesContractAndPrototypeKanban()
        {
            string[] names = Enum.GetNames(typeof(RecommendationStatus));
            Assert.Equal(new[] { "Draft", "Issued", "Responded", "Implemented", "NotAdopted", "Closed" }, names);
            Assert.Equal(4, Enum.GetNames(typeof(KanbanColumn)).Length);

            Type rec = typeof(SafetyRecommendation);
            Assert.NotNull(rec.GetProperty("ProgressPct"));
            Assert.NotNull(rec.GetProperty("VerificationNote"));
            Assert.NotNull(rec.GetProperty("ResponseSummary"));
            Assert.NotNull(rec.GetProperty("CaseId"));
            Assert.Null(rec.GetProperty("ProgressPct").GetSetMethod());

            var expected = new Dictionary<RecommendationStatus, string>
            {
                { RecommendationStatus.Draft, "草拟" },
                { RecommendationStatus.Issued, "已发布" },
                { RecommendationStatus.Responded, "落实中" },
                { RecommendationStatus.Implemented, "已关闭" },
                { RecommendationStatus.NotAdopted, "已关闭" },
                { RecommendationStatus.Closed, "已关闭" },
            };
            foreach (KeyValuePair<RecommendationStatus, string> kv in expected)
            {
                Assert.Equal(kv.Value, SafetyRecommendationBoard.KanbanLabel(SafetyRecommendationBoard.ToKanbanColumn(kv.Key)));
            }

            // 实例：各状态的卡片落在对应看板列。
            SafetyRecommendationBoard board = Board(out _);
            Draft(board, "SR-2026-01");
            Draft(board, "SR-2026-02");
            Draft(board, "SR-2026-03");
            AssertOk(board.Issue("SR-2026-02", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            AssertOk(board.Issue("SR-2026-03", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            AssertOk(board.RecordResponse("SR-2026-03", "Mary 船公司（虚构）", "已开始修订（虚构）", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 10, 0)));
            Assert.Equal("草拟", SafetyRecommendationBoard.KanbanLabel(board.Get("SR-2026-01").Column));
            Assert.Equal("已发布", SafetyRecommendationBoard.KanbanLabel(board.Get("SR-2026-02").Column));
            Assert.Equal("落实中", SafetyRecommendationBoard.KanbanLabel(board.Get("SR-2026-03").Column));
            Assert.Single(board.ByKanbanColumn(KanbanColumn.InProgress));
            Assert.Empty(board.ByKanbanColumn(KanbanColumn.Closed));
        }

        [Fact]
        public void W3_D02_ContractTransition_ProgressOnlyInResponded_ImplementedAuto100_OutOfRangeRejected()
        {
            SafetyRecommendationBoard board = Board(out InMemoryInvestigationAuditSink audit);
            Draft(board, "SR-2026-03");
            SafetyRecommendation r = board.Get("SR-2026-03");
            Assert.Equal(0, r.ProgressPct);

            // Draft / Issued 不可改进度，且不写审计、不改值
            int n = audit.Entries.Count;
            Assert.False(board.SetProgress("SR-2026-03", 10, W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 9, 0)).IsSuccess);
            AssertOk(board.Issue("SR-2026-03", W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 10, 0)));
            n = audit.Entries.Count;
            Assert.False(board.SetProgress("SR-2026-03", 10, W3AccFixture.OpA, W3AccFixture.Cst(5, 21, 11, 0)).IsSuccess);
            Assert.Equal(0, r.ProgressPct);
            Assert.Equal(n, audit.Entries.Count);

            // Responded：0..100 闭区间可改，每次写审计
            AssertOk(board.RecordResponse("SR-2026-03", "Mary 船公司（虚构）", "已开始修订 SMS（虚构）", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 10, 0)));
            Assert.Equal(KanbanColumn.InProgress, r.Column);
            n = audit.Entries.Count;
            AssertOk(board.SetProgress("SR-2026-03", 0, W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 10, 0)));
            AssertOk(board.SetProgress("SR-2026-03", 100, W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 10, 1)));
            AssertOk(board.SetProgress("SR-2026-03", 60, W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 10, 2), "培训完成过半（虚构）"));
            Assert.Equal(60, r.ProgressPct);
            Assert.Equal(n + 3, audit.Entries.Count);
            Assert.Equal(RecommendationStatus.Responded, r.Status);

            // 越界拒绝：值不变、无审计
            n = audit.Entries.Count;
            foreach (int bad in new[] { -1, 101, int.MinValue, int.MaxValue })
            {
                Mcis.Core.Result<SafetyRecommendation> res = board.SetProgress("SR-2026-03", bad, W3AccFixture.OpA, W3AccFixture.Cst(5, 23, 11, 0));
                Assert.False(res.IsSuccess, "越界进度 " + bad + " 应拒绝");
                Assert.Equal(SafetyRecommendationBoard.ErrInvalidProgress, res.ErrorCode);
            }

            Assert.Equal(60, r.ProgressPct);
            Assert.Equal(n, audit.Entries.Count);

            // 进入 Implemented 自动 100，之后不可再改进度
            AssertOk(board.MarkImplemented("SR-2026-03", W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 10, 0), "现场核实（虚构）"));
            Assert.Equal(100, r.ProgressPct);
            Assert.Equal("已关闭", SafetyRecommendationBoard.KanbanLabel(r.Column));
            Assert.False(board.SetProgress("SR-2026-03", 50, W3AccFixture.OpA, W3AccFixture.Cst(6, 1, 11, 0)).IsSuccess);
            Assert.Equal(100, r.ProgressPct);
            AssertOk(board.Close("SR-2026-03", W3AccFixture.OpA, W3AccFixture.Cst(6, 2, 10, 0), "已核实落实（虚构）"));
            Assert.False(board.SetProgress("SR-2026-03", 50, W3AccFixture.OpA, W3AccFixture.Cst(6, 2, 11, 0)).IsSuccess);
            Assert.Equal(100, r.ProgressPct);

            // 六态迁移表：非法迁移仍被拒绝（不要求任意状态可驳回）
            Assert.False(SafetyRecommendationBoard.CanTransition(RecommendationStatus.Draft, RecommendationStatus.NotAdopted));
            Assert.False(SafetyRecommendationBoard.CanTransition(RecommendationStatus.Draft, RecommendationStatus.Closed));
            Assert.False(SafetyRecommendationBoard.CanTransition(RecommendationStatus.Closed, RecommendationStatus.Draft));
            Assert.True(SafetyRecommendationBoard.CanTransition(RecommendationStatus.Responded, RecommendationStatus.Implemented));
            Assert.True(SafetyRecommendationBoard.CanTransition(RecommendationStatus.Responded, RecommendationStatus.NotAdopted));
        }

        private static object FindEnum(Type enumType, string name)
        {
            return Enum.GetNames(enumType).Contains(name) ? Enum.Parse(enumType, name) : null;
        }

        private static void AssertSuccess(object result, string message)
        {
            Assert.NotNull(result);
            PropertyInfo ok = result.GetType().GetProperty("IsSuccess");
            PropertyInfo err = result.GetType().GetProperty("ErrorMessage");
            Assert.True((bool)ok.GetValue(result), message + " 实际：" + (err != null ? err.GetValue(result) : result));
        }
    }
}
