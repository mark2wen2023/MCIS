using System;
using System.Linq;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    public class KnownDefectTests
    {
        /// <summary>W15-D02：SystemicRefContext 对证据（ledger.Get）与建议（board.Get）是实时查询，对 HFACS 却在构造时拷贝快照。
        /// 构造上下文之后新增的 HFACS 发现被误报 sys_unknown_hfacs；同一上下文对四类引用语义不一致。
        /// 期望：与证据/建议一致，按校验时刻的 HfacsAnalysis 内容判断（只读查询）。</summary>
        [Fact]
        public void W15_D02_HfacsContext_IsLiveQuery_LikeLedgerAndBoard()
        {
            var ledger = Ledger(new[] { "EV-001" });
            var hf = Hfacs(new[] { "HF-F01" });
            var ctx = new SystemicRefContext(ledger: ledger, hfacs: hf);

            // 上下文建立后，调查员新登记证据、新增 HFACS 发现
            Ok(ledger.Register(new EvidenceItem("EV-002", "虚构证据", "VDR", "调查员甲", T0, new string('a', 64)), "调查员甲", T0));
            Ok(hf.AddFinding("HF-F02", "UA", "虚构发现", EvidenceStrength.ToBeVerified, null, null));

            var m = Ok(AcciMapModel.Create("AM-L", "实时性"));
            Ok(m.AddNode("A", "a", AcciMapLevel.Company, M, Refs(new[] { "EV-002" }, null, new[] { "HF-F02" })));
            Ok(m.AddNode("B", "b", AcciMapLevel.CrewActs, M, Ev1));
            Ok(m.Connect("A", "B"));
            var v = m.Validate(ctx);
            Assert.False(v.Has(SystemicErrors.UnknownEvidence)); // 证据：实时 → 不误报（对照组，通过）
            Assert.True(v.IsValid, "HFACS 快照导致误报：" + Issues(v));
        }

        /// <summary>W15-D03：SystemicDocument 公开构造器不校验 caseId（null、空白、含换行均接受且原样往返），
        /// 与 Evidence 模块的 EvidenceItem.IsValidCaseId 不一致，也不走 Result&lt;T&gt;。期望：caseId 非法时 Validate 报 sys_invalid_id（或工厂方法返回失败）。</summary>
        [Theory]
        [InlineData(null)]
        [InlineData("")]
        [InlineData("  bad id \n")]
        public void W15_D03_Document_InvalidCaseId_Flagged(string caseId)
        {
            Assert.False(EvidenceItem.IsValidCaseId(caseId)); // 对照：证据模块认为非法
            var d = new SystemicDocument(caseId, false, MiniBowTie());
            Assert.True(d.Validate().Has(SystemicErrors.InvalidId), "caseId=" + (caseId ?? "(null)") + " 未被报告");
        }
    }
}
