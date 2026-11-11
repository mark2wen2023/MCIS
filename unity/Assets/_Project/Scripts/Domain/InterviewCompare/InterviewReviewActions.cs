using System;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    /// <summary>一行复核的结果：陈述当前状态 + 对应比对条目（未比对时为 null）。</summary>
    public sealed class RowDecision
    {
        public Statement Statement { get; }
        public CrossCheckEntry Entry { get; }

        public RowDecision(Statement statement, CrossCheckEntry entry)
        {
            Statement = statement;
            Entry = entry;
        }
    }

    /// <summary>
    /// 比对表行按钮“✓确认并写入审计 / ✕驳回”的门面：一次操作同时处理陈述复核（W3 ReviewStatement）与比对结论（W3 Confirm/Dismiss），
    /// 每个底层动作各写一条审计。所有拒绝条件先预检，预检通过才落地，避免半更新（仅当审计 sink 抛异常时可能部分生效）。
    /// </summary>
    public static class InterviewReviewActions
    {
        public static Result<RowDecision> ConfirmRow(InterviewRecord record, CrossCheckRegister register, string statementId, string investigator, DateTimeOffset utc, IInvestigationAuditSink audit, string note = null)
        {
            Statement st;
            CrossCheckEntry entry;
            Result<RowDecision>? bad = Precheck(record, register, statementId, investigator, audit, out st, out entry);
            if (bad.HasValue)
            {
                return bad.Value;
            }

            if (entry != null && entry.State != CrossCheckState.Dismissed && entry.IsStale(record))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.EntryStale,
                    "比对结论基于陈述 r" + entry.StatementVersion + "，陈述已改为 r" + st.Revision + "，请先重新比对：" + statementId);
            }

            bool stmtPending = IsOpen(st);
            bool entryPending = entry != null && entry.State == CrossCheckState.PendingConfirmation;
            if (st.ReviewStatus == StatementReviewStatus.Rejected || (!stmtPending && !entryPending))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.NotReviewable, "该行没有待复核项：" + statementId);
            }

            if (stmtPending)
            {
                Result<Statement> r = record.ReviewStatement(statementId, StatementReviewStatus.Confirmed, investigator, utc, audit, note);
                if (!r.IsSuccess)
                {
                    return Result<RowDecision>.Fail(r.ErrorCode, r.ErrorMessage);
                }
            }

            if (entryPending)
            {
                Result<CrossCheckEntry> r = register.Confirm(statementId, investigator, utc, note);
                if (!r.IsSuccess)
                {
                    return Result<RowDecision>.Fail(r.ErrorCode, r.ErrorMessage);
                }
            }

            return Result<RowDecision>.Ok(new RowDecision(record.GetStatement(statementId), entry));
        }

        public static Result<RowDecision> RejectRow(InterviewRecord record, CrossCheckRegister register, string statementId, string investigator, DateTimeOffset utc, IInvestigationAuditSink audit, string reason)
        {
            if (string.IsNullOrWhiteSpace(reason))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.InvalidArgument, "驳回必须填写理由");
            }

            Statement st;
            CrossCheckEntry entry;
            Result<RowDecision>? bad = Precheck(record, register, statementId, investigator, audit, out st, out entry);
            if (bad.HasValue)
            {
                return bad.Value;
            }

            if (!IsOpen(st))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.NotReviewable, "陈述已复核，不能驳回：" + st.ReviewStatus);
            }

            if (entry != null && entry.State == CrossCheckState.Confirmed)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.EntryNotPending, "比对结论已确认，不能随陈述驳回：" + statementId);
            }

            Result<Statement> rs = record.ReviewStatement(statementId, StatementReviewStatus.Rejected, investigator, utc, audit, reason);
            if (!rs.IsSuccess)
            {
                return Result<RowDecision>.Fail(rs.ErrorCode, rs.ErrorMessage);
            }

            if (entry != null && entry.State == CrossCheckState.PendingConfirmation)
            {
                Result<CrossCheckEntry> re = register.Dismiss(statementId, investigator, utc, reason);
                if (!re.IsSuccess)
                {
                    return Result<RowDecision>.Fail(re.ErrorCode, re.ErrorMessage);
                }
            }

            return Result<RowDecision>.Ok(new RowDecision(rs.Value, entry));
        }

        /// <summary>
        /// W5.1 “重新比对”：用当前陈述（当前 Revision）重新跑确定性比对器，结果按台账规则落地——
        /// 未比对 → Submit；已驳回 → Resubmit（理由必填）；过期且待确认 → 先 Dismiss（理由前缀 “陈述已改版 rA→rB”）再 Resubmit。
        /// 未过期的待确认（应直接确认/驳回）与已确认（不可撤销）返回 icmp_recheck_not_allowed；已驳回的陈述返回 icmp_not_reviewable。
        /// Dismiss 成功而 Resubmit 审计失败时条目停在 Dismissed，再次调用会直接 Resubmit。
        /// </summary>
        public static Result<RowDecision> RecheckRow(InterviewRecord record, CrossCheckRegister register, string statementId, IStatementDataSource source,
            string investigator, DateTimeOffset utc, IInvestigationAuditSink audit, string reason = null, StatementCrossChecker checker = null)
        {
            if (source == null)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.InvalidArgument, "数据源不能为空");
            }

            Statement st;
            CrossCheckEntry entry;
            Result<RowDecision>? bad = Precheck(record, register, statementId, investigator, audit, out st, out entry);
            if (bad.HasValue)
            {
                return bad.Value;
            }

            if (st.ReviewStatus == StatementReviewStatus.Rejected)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.NotReviewable, "陈述已驳回，不再比对：" + statementId);
            }

            if (entry != null && string.IsNullOrWhiteSpace(reason))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.InvalidArgument, "已有比对结论，重新比对必须填写理由");
            }

            bool stalePending = entry != null && entry.State == CrossCheckState.PendingConfirmation && entry.IsStale(record);
            if (entry != null && entry.State != CrossCheckState.Dismissed && !stalePending)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.RecheckNotAllowed,
                    entry.State == CrossCheckState.Confirmed ? "比对结论已确认，不可撤销：" + statementId : "比对结论未过期，请直接确认或驳回：" + statementId);
            }

            CrossCheckResult fresh = (checker ?? new StatementCrossChecker()).Check(st, source);
            Result<CrossCheckEntry> r;
            if (entry == null)
            {
                r = register.Submit(fresh, investigator, utc);
            }
            else
            {
                if (stalePending)
                {
                    Result<CrossCheckEntry> d = register.Dismiss(statementId, investigator, utc,
                        "陈述已改版 r" + entry.StatementVersion + "→r" + st.Revision + "；" + reason);
                    if (!d.IsSuccess)
                    {
                        return Result<RowDecision>.Fail(d.ErrorCode, d.ErrorMessage);
                    }
                }

                r = register.Resubmit(fresh, investigator, utc, reason);
            }

            return r.IsSuccess ? Result<RowDecision>.Ok(new RowDecision(st, r.Value)) : Result<RowDecision>.Fail(r.ErrorCode, r.ErrorMessage);
        }

        private static bool IsOpen(Statement st)
        {
            return st.ReviewStatus == StatementReviewStatus.Draft || st.ReviewStatus == StatementReviewStatus.Modified;
        }

        private static Result<RowDecision>? Precheck(InterviewRecord record, CrossCheckRegister register, string statementId, string investigator, IInvestigationAuditSink audit, out Statement st, out CrossCheckEntry entry)
        {
            st = null;
            entry = null;
            if (record == null || register == null || audit == null || string.IsNullOrWhiteSpace(investigator))
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.InvalidArgument, "笔录、登记簿、审计与调查员不能为空");
            }

            st = record.GetStatement(statementId);
            if (st == null)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.StatementNotFound, "笔录中没有该陈述：" + (statementId ?? "(null)"));
            }

            entry = register.Get(statementId);
            if (entry != null && entry.Result.RecordId != record.RecordId)
            {
                return Result<RowDecision>.Fail(InterviewCompareErrors.RecordMismatch, "比对条目属于另一份笔录：" + entry.Result.RecordId);
            }

            return null;
        }
    }
}
