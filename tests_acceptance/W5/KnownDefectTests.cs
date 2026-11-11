using System;
using System.Linq;
using System.Reflection;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Mcis.Domain.InterviewCompare;
using Xunit;
using static Mcis.Acceptance.W5.W5AccFixture;

namespace Mcis.Acceptance.W5
{
    /// <summary>
    /// 已接受但尚未落实的两条提案（REQUESTS.md 21:25 裁定），先写成 KnownDefect：
    /// 1. 比对结果带陈述版本 statementVersion / StatementRevision，修改后可识别过期结论；
    /// 2. 台账增加 Resubmit，只能从 Rejected 发起，并写审计。
    /// </summary>
    public class KnownDefectTests
    {
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W5_D01_ComparisonResult_CarriesStatementVersion_AndFlagsStaleAfterModify()
        {
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("怎么用舵？", "左舵 20 度。", rec.StartUtc.AddMinutes(2)));
            Statement st = Ok(rec.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec.Locate(1, QaField.Answer, "左舵 20 度"))));
            Assert.Equal(1, st.Revision);

            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            var submitted = Ok(reg.Submit(new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Consistent, 0, "deg", "20°", "20°", "VDR（虚构）", "|Δ|≤1"), Agent, At(5, 19, 10, 0)));

            PropertyInfo versionOnResult = typeof(CrossCheckResult).GetProperty("StatementVersion")
                ?? typeof(CrossCheckResult).GetProperty("StatementRevision");
            PropertyInfo versionOnEntry = typeof(CrossCheckEntry).GetProperty("StatementVersion")
                ?? typeof(CrossCheckEntry).GetProperty("StatementRevision");
            MethodInfo isStale = typeof(CrossCheckEntry).GetMethod("IsStale", new[] { typeof(InterviewRecord) });

            Assert.True(versionOnResult != null || versionOnEntry != null,
                "比对结果应带陈述版本（statementVersion / StatementRevision），以便识别修改后的过期结论。");
            Assert.True(isStale != null, "CrossCheckEntry 应提供 IsStale(InterviewRecord)，供视图标出「需重新比对」。");

            object ver = versionOnEntry != null ? versionOnEntry.GetValue(submitted) : versionOnResult.GetValue(submitted.Result);
            Assert.Equal(st.Revision, Convert.ToInt32(ver));
            Assert.False((bool)isStale.Invoke(submitted, new object[] { rec }));

            Ok(rec.ModifyStatement("S-r", "左舵 15°（修正，虚构）", StatementClaim.ScalarValue(15, "deg"), st.Span, st.ReferenceUtc, Investigator, At(5, 19, 11, 0), audit));
            Assert.True((bool)isStale.Invoke(reg.Get("S-r"), new object[] { rec }), "陈述修改后，旧比对结论应视为过期。");

            var rowType = typeof(ComparisonRow);
            PropertyInfo staleFlag = rowType.GetProperty("IsStale") ?? rowType.GetProperty("NeedsRecheck");
            Assert.True(staleFlag != null, "比对视图行应能标出过期结论（IsStale / NeedsRecheck /「需重新比对」）。");
            var row = InterviewComparisonView.Rows(rec, reg).Single(r => r.StatementId == "S-r");
            Assert.True((bool)staleFlag.GetValue(row));
        }

        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W5_D02_Resubmit_OnlyFromRejected_WritesAudit_AndSupersedesOldEntry()
        {
            InterviewRecord rec = NewRecord();
            Ok(rec.AddTurn("怎么用舵？", "左舵 20 度。", rec.StartUtc.AddMinutes(2)));
            Ok(rec.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec.Locate(1, QaField.Answer, "左舵 20 度"))));
            var audit = new InMemoryInvestigationAuditSink();
            var reg = new CrossCheckRegister(audit);
            var first = new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Contradictory, 5, "deg", "20°", "15°", "VDR（虚构）", "|Δ|≤1");
            Ok(reg.Submit(first, Agent, At(5, 19, 10, 0)));

            MethodInfo resubmit = typeof(CrossCheckRegister).GetMethods(BindingFlags.Public | BindingFlags.Instance)
                .FirstOrDefault(m => m.Name == "Resubmit");
            Assert.True(resubmit != null, "台账应提供 Resubmit(result, actor, utc, reason)，用于作废后重新提交比对结论。");

            var retry = new CrossCheckResult("S-r", rec.RecordId, CrossCheckOutcome.Consistent, 0, "deg", "20°", "20°", "VDR（虚构）", "|Δ|≤1");

            // 待确认不得直接 Resubmit（裁定：只能从 Rejected 发起）
            object pendingAttempt = resubmit.Invoke(reg, Bind(resubmit, retry, Investigator, At(5, 19, 10, 5), "想重提（虚构）"));
            Assert.False(IsSuccess(pendingAttempt), "Pending 条目不能 Resubmit。");

            Ok(reg.Confirm("S-r", Investigator, At(5, 19, 10, 6)));
            object confirmedAttempt = resubmit.Invoke(reg, Bind(resubmit, retry, Investigator, At(5, 19, 10, 7), "想重提（虚构）"));
            Assert.False(IsSuccess(confirmedAttempt), "已确认条目不能 Resubmit。");
            Assert.Equal(CrossCheckState.Confirmed, reg.Get("S-r").State);

            // 另走驳回路径
            InterviewRecord rec2 = NewRecord("IR-18");
            Ok(rec2.AddTurn("怎么用舵？", "左舵 20 度。", rec2.StartUtc.AddMinutes(2)));
            Ok(rec2.AddStatement("S-r", StatementKind.Operation, "Mary.rudder", "左舵 20°", StatementClaim.ScalarValue(20, "deg"), Ok(rec2.Locate(1, QaField.Answer, "左舵 20 度"))));
            var audit2 = new InMemoryInvestigationAuditSink();
            var reg2 = new CrossCheckRegister(audit2);
            Ok(reg2.Submit(first, Agent, At(5, 19, 10, 0)));
            Ok(reg2.Dismiss("S-r", Investigator, At(5, 19, 10, 5), "第一次比对有误（虚构）"));
            // 裁定用词是 Rejected；现 CrossCheckState 只有 Dismissed。本用例把 Dismissed 视为可发起的驳回态，请架构师确认用词。
            int n = audit2.Entries.Count;
            object ok = resubmit.Invoke(reg2, Bind(resubmit, retry, Investigator, At(5, 19, 11, 0), "更正后重新提交（虚构）"));
            Assert.True(IsSuccess(ok), "已驳回（Dismissed/Rejected）的条目应允许 Resubmit。");
            Assert.True(audit2.Entries.Count > n, "Resubmit 必须写审计。");

            CrossCheckEntry current = reg2.Get("S-r");
            Assert.Equal(CrossCheckOutcome.Consistent, current.Result.Outcome);
            Assert.Equal(CrossCheckState.PendingConfirmation, current.State);
            // 旧条目应进入 Superseded（若状态枚举已扩展）或至少不再作为当前有效结论
            Type stateType = typeof(CrossCheckState);
            bool hasSuperseded = Enum.GetNames(stateType).Contains("Superseded");
            Assert.True(hasSuperseded, "建议增加 CrossCheckState.Superseded，供旧条目作废后保留痕迹。");
        }

        private static object[] Bind(MethodInfo m, params object[] args)
        {
            ParameterInfo[] ps = m.GetParameters();
            var bound = new object[ps.Length];
            for (int i = 0; i < Math.Min(ps.Length, args.Length); i++)
            {
                bound[i] = args[i];
            }

            return bound;
        }

        private static bool IsSuccess(object result)
        {
            if (result == null)
            {
                return false;
            }

            PropertyInfo p = result.GetType().GetProperty("IsSuccess");
            return p != null && (bool)p.GetValue(result);
        }
    }
}
