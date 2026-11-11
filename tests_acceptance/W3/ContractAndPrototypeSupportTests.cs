using System;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.Recommendations;
using Xunit;

namespace Mcis.Acceptance.W3
{
    /// <summary>
    /// 对照 contracts/ 与原型截图 09/10/15，检查领域模型是否支撑截图字段与合同必填项。
    /// 缺失即记为缺陷（GISIS / 双语报告属功能⑪，不在 W3 范围，见缺陷单「规格待澄清」）。
    /// </summary>
    public class ContractAndPrototypeSupportTests
    {
        [Fact]
        public void W3_D03_EvidenceItem_HasContractRequiredCaseId()
        {
            // evidence-item.schema.json required 含 caseId；说明写明前 7 字段与 C# EvidenceItem 对齐。
            Assert.NotNull(typeof(EvidenceItem).GetProperty("CaseId"));
        }

        [Fact]
        public void W3_D03_Evidence_SupportsConfidentialityAndNeedsReview()
        {
            // 原型 09：EV-006 状态「保密 · 受限」；EV-005「需复核纸本」。
            // schema：confidentiality=Normal|Restricted；status 含 NeedsReview（由调查员标注）。
            Type item = typeof(EvidenceItem);
            Type ledger = typeof(CustodyLedger);
            bool hasConfidentiality = item.GetProperty("Confidentiality") != null
                                      || item.GetProperty("IsRestricted") != null
                                      || item.GetProperty("Restricted") != null;
            Assert.True(hasConfidentiality, "领域模型缺少保密/受限标记，无法支撑原型「保密 · 受限」状态。");

            bool hasNeedsReview = item.GetProperty("Status") != null
                                  || ledger.GetMethods(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly)
                                      .Any(m => m.Name.IndexOf("Review", StringComparison.OrdinalIgnoreCase) >= 0
                                                || m.Name.IndexOf("NeedsReview", StringComparison.OrdinalIgnoreCase) >= 0
                                                || m.Name.IndexOf("Annotate", StringComparison.OrdinalIgnoreCase) >= 0);
            Assert.True(hasNeedsReview, "领域模型缺少 NeedsReview / 需复核 标注能力，无法支撑原型「需复核纸本」。");
        }

        [Fact]
        public void W3_D05_EvidenceId_MustMatchEVPattern()
        {
            // common.schema.json evidenceRef: ^EV-[0-9]{3,}$
            var item = new EvidenceItem("NOT-EV", "虚构标题", "虚构来源", W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40), W3AccFixture.ShaMaryVdr);
            var ledger = new CustodyLedger();
            Mcis.Core.Result<CustodyEvent> r = ledger.Register(item, W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40));
            Assert.False(r.IsSuccess, "非法证据编号 NOT-EV 应被拒绝，实际 ErrorCode=" + r.ErrorCode + " IsSuccess=" + r.IsSuccess);
        }

        [Fact]
        public void Evidence_AccessAndVerify_CoverScreenshotOperationalFields()
        {
            // 原型 09 列：编号 / 证据 / 来源·提取人 / 提取时间 / SHA-256 / 访问 / 状态(一致)。
            var ledger = new CustodyLedger();
            Assert.True(ledger.Register(W3AccFixture.MaryVdr(), W3AccFixture.OpA, W3AccFixture.Cst(5, 18, 18, 40)).IsSuccess);
            EvidenceItem ev = ledger.Get("EV-001");
            Assert.Equal("EV-001", ev.EvidenceId);
            Assert.False(string.IsNullOrWhiteSpace(ev.Title));
            Assert.False(string.IsNullOrWhiteSpace(ev.Source));
            Assert.False(string.IsNullOrWhiteSpace(ev.ExtractedBy));
            Assert.Equal(64, ev.Sha256.Length);
            Assert.True(ledger.RecordAccess("EV-001", W3AccFixture.OpB, W3AccFixture.Cst(5, 22, 15, 31), "只读回放").IsSuccess);
            Assert.Equal(1, ledger.AccessCount("EV-001"));
            Assert.True(ledger.Verify("EV-001", W3AccFixture.OpA, W3AccFixture.Cst(5, 22, 16, 0), W3AccFixture.ShaMaryVdr).Value.VerifyMatched);
        }

        [Fact]
        public void Interview_SupportsScreenshotCoreFields()
        {
            InterviewRecord rec = W3AccFixture.Ir03WithTurns();
            Assert.Equal("IR-03", rec.RecordId);
            Assert.Equal("二副（OOW）", rec.Interviewee.Role);
            Assert.Equal("Mary 轮（虚构）", rec.Interviewee.Affiliation);
            Assert.Equal("星屿海事局询问室（虚构）", rec.Location);
            Assert.Equal("调查员 B（虚构）", rec.Recorder);
            Assert.Contains(W3AccFixture.OpA, rec.Interviewers);
            Assert.Equal(W3AccFixture.ShaOther, rec.SourceSha256);
            Assert.Equal(7, rec.Turns.Count);
        }

        [Fact]
        public void Recommendation_SupportsScreenshotCoreFields_ExceptKnownGaps()
        {
            var board = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            SafetyRecommendation rec = board.CreateDraft(
                "SR-2026-06",
                "星屿 VTS 对雾航双向通航实施单向交通管制（虚构）",
                "星屿 VTS（虚构）",
                new[] { "ECFC-C4", "Bow-tie-B1" },
                W3AccFixture.Cst(8, 30, 0, 0),
                W3AccFixture.OpA,
                W3AccFixture.Cst(5, 20, 10, 0),
                isInterim: false).Value;
            Assert.Equal("SR-2026-06", rec.Id);
            Assert.Equal("星屿 VTS（虚构）", rec.Addressee);
            Assert.Contains("ECFC-C4", rec.CauseNodeIds);
            Assert.Equal(RecommendationStatus.Draft, rec.Status);
            Assert.Equal(W3AccFixture.Cst(8, 30, 0, 0), rec.DueUtc);
        }
    }
}
