using System;
using System.Collections.Generic;
using System.Linq;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.Interview
{
    /// <summary>比对结果确认状态。所有结论（一致/矛盾/无法核实）登记后均为草稿，须调查员确认才生效（W3-D01 裁定）。</summary>
    public enum CrossCheckState : byte
    {
        /// <summary>草稿，待调查员确认，尚未生效。</summary>
        PendingConfirmation = 0,
        /// <summary>调查员已确认，生效。</summary>
        Confirmed = 1,
        /// <summary>调查员驳回（不生效，保留记录）。</summary>
        Dismissed = 2,

        /// <summary>
        /// W5.1（DEFECTS/W5.md 21:32）：已驳回的条目被 <see cref="CrossCheckRegister.Resubmit"/> 的新条目取代。
        /// 只留痕、不删除、不生效；与陈述复核的 Rejected 区分。
        /// </summary>
        Superseded = 3,
    }

    /// <summary>登记簿中的一条比对结果及其确认状态。状态只能经 <see cref="CrossCheckRegister"/> 改变。</summary>
    public sealed class CrossCheckEntry
    {
        public CrossCheckResult Result { get; }
        public CrossCheckState State { get; internal set; }
        public string DecidedBy { get; internal set; }
        public DateTimeOffset? DecidedUtc { get; internal set; }
        public string Note { get; internal set; }

        /// <summary>是否已进入分析（仅调查员确认后）。</summary>
        public bool IsEffective
        {
            get { return State == CrossCheckState.Confirmed; }
        }

        /// <summary>是否经批量确认（仅一致项可批量）。</summary>
        public bool ConfirmedInBatch { get; internal set; }

        /// <summary>W5.1：比对时的陈述版本（= Result.StatementVersion）。</summary>
        public int StatementVersion
        {
            get { return Result.StatementVersion; }
        }

        /// <summary>
        /// W5.1 D01：结论是否过期——本条目属于 <paramref name="record"/>、笔录中有该陈述，且陈述当前版本 ≠ 比对时版本。
        /// record 为空、属于别的笔录、或笔录中没有该陈述时无从比较，返回 false。只读，不改状态。
        /// </summary>
        public bool IsStale(InterviewRecord record)
        {
            if (record == null || !string.Equals(record.RecordId, Result.RecordId, StringComparison.Ordinal))
            {
                return false;
            }

            Statement s = record.GetStatement(Result.StatementId);
            return s != null && s.Revision != Result.StatementVersion;
        }

        /// <summary>
        /// 按 contracts/schemas/interview.schema.json 的 crossCheckResult 序列化（camelCase 键、固定顺序）：
        /// statementId, recordId, outcome, delta, deltaUnit, claimedText, observedText, sourceLabel, rule,
        /// state, decidedBy, decidedUtc, note, confirmedInBatch, statementVersion（W5.1）。null 字段写 JSON null。
        /// </summary>
        public string ToJson()
        {
            var sb = new System.Text.StringBuilder(256);
            sb.Append("{\"statementId\":").Append(AuditJson.Quote(Result.StatementId ?? string.Empty));
            sb.Append(",\"recordId\":").Append(AuditJson.Quote(Result.RecordId ?? string.Empty));
            sb.Append(",\"outcome\":").Append(AuditJson.Quote(Result.Outcome.ToString()));
            sb.Append(",\"delta\":").Append(Result.Delta.HasValue && !double.IsNaN(Result.Delta.Value) && !double.IsInfinity(Result.Delta.Value)
                ? Result.Delta.Value.ToString("R", System.Globalization.CultureInfo.InvariantCulture) : "null");
            sb.Append(",\"deltaUnit\":").Append(AuditJson.Quote(Result.DeltaUnit ?? string.Empty));
            sb.Append(",\"claimedText\":").Append(AuditJson.Quote(Result.ClaimedText ?? string.Empty));
            sb.Append(",\"observedText\":").Append(AuditJson.Quote(Result.ObservedText ?? string.Empty));
            sb.Append(",\"sourceLabel\":").Append(AuditJson.Quote(Result.SourceLabel ?? string.Empty));
            sb.Append(",\"rule\":").Append(AuditJson.Quote(Result.Rule ?? string.Empty));
            sb.Append(",\"state\":").Append(AuditJson.Quote(State.ToString()));
            sb.Append(",\"decidedBy\":").Append(DecidedBy == null ? "null" : AuditJson.Quote(DecidedBy));
            sb.Append(",\"decidedUtc\":").Append(DecidedUtc.HasValue
                ? AuditJson.Quote(DecidedUtc.Value.ToUniversalTime().ToString(DecidedUtcFormat, CultureInfo.InvariantCulture)) : "null");
            sb.Append(",\"note\":").Append(AuditJson.Quote(Note ?? string.Empty));
            sb.Append(",\"confirmedInBatch\":").Append(ConfirmedInBatch ? "true" : "false");
            sb.Append(",\"statementVersion\":").Append(Result.StatementVersion.ToString(CultureInfo.InvariantCulture));
            sb.Append('}');
            return sb.ToString();
        }

        /// <summary>W3.2：decidedUtc 序列化格式，带毫秒的 ISO 8601 UTC。</summary>
        public const string DecidedUtcFormat = "yyyy-MM-ddTHH:mm:ss.fffZ";

        internal CrossCheckEntry(CrossCheckResult result, CrossCheckState state)
        {
            Result = result;
            State = state;
        }
    }

    /// <summary>
    /// 比对结果登记簿：所有结论登记后都是草稿，必须由调查员确认后才生效；
    /// 一致项可批量确认，矛盾/无法核实项必须逐条确认；每个确认/驳回动作都写一条审计（audit.jsonl 兼容格式）。
    /// </summary>
    public sealed class CrossCheckRegister
    {
        public const string ErrInvalidArgument = "crosscheck_invalid_argument";
        public const string ErrNotFound = "crosscheck_not_found";
        public const string ErrDuplicate = "crosscheck_duplicate";
        public const string ErrNotPending = "crosscheck_not_pending";
        public const string ErrBatchNotConsistent = "crosscheck_batch_not_consistent";

        /// <summary>W5.1：Resubmit 只能从 Dismissed 发起（待确认 / 已确认 / 已取代均拒绝）。</summary>
        public const string ErrNotDismissed = "crosscheck_not_dismissed";

        /// <summary>W5.1：重新提交（旧条目 → Superseded，新条目待确认）。</summary>
        public const string ActionResubmit = "interview.crosscheck.resubmit";

        public const string ActionSubmit = "interview.crosscheck.submit";
        public const string ActionConfirm = "interview.contradiction.confirm";
        public const string ActionDismiss = "interview.contradiction.dismiss";
        public const string ActionBatchConfirm = "interview.crosscheck.batch_confirm";

        /// <summary>W3-D07：批量确认的审计中途失败，已预写的批量审计作废。</summary>
        public const string ActionBatchAbort = "interview.crosscheck.batch_abort";

        /// <summary>
        /// W3.2：批量确认两阶段提交的提交行。同一 batchId 的全部 batch_confirm 行写完后写这一行（after 为逗号分隔的陈述编号）；
        /// 读取或重放时没有对应提交行的批量行一律作废，见 <see cref="EffectiveAudit"/>。
        /// </summary>
        public const string ActionBatchCommit = "interview.crosscheck.batch_commit";

        /// <summary>W3-D07 / W3.2：审计写入失败（批量整体回滚；单条确认/驳回状态不变）。</summary>
        public const string ErrAuditFailed = "crosscheck_audit_failed";

        private readonly IInvestigationAuditSink _audit;
        private readonly List<CrossCheckEntry> _entries = new List<CrossCheckEntry>();
        private readonly Dictionary<string, CrossCheckEntry> _byStatement = new Dictionary<string, CrossCheckEntry>(StringComparer.Ordinal);

        public CrossCheckRegister(IInvestigationAuditSink audit)
        {
            _audit = audit ?? throw new ArgumentNullException(nameof(audit));
        }

        public IReadOnlyList<CrossCheckEntry> Entries { get { return _entries; } }

        public CrossCheckEntry Get(string statementId)
        {
            return statementId != null && _byStatement.TryGetValue(statementId, out CrossCheckEntry e) ? e : null;
        }

        public IReadOnlyList<CrossCheckEntry> Pending()
        {
            return Filter(e => e.State == CrossCheckState.PendingConfirmation);
        }

        /// <summary>待确认的一致项（可批量确认）。</summary>
        public IReadOnlyList<CrossCheckEntry> PendingConsistent()
        {
            return Filter(e => e.State == CrossCheckState.PendingConfirmation && e.Result.Outcome == CrossCheckOutcome.Consistent);
        }

        /// <summary>已生效（已确认）的全部结论。</summary>
        public IReadOnlyList<CrossCheckEntry> Effective()
        {
            return Filter(e => e.IsEffective);
        }

        /// <summary>已生效的矛盾（已确认）。</summary>
        public IReadOnlyList<CrossCheckEntry> EffectiveContradictions()
        {
            return Filter(e => e.State == CrossCheckState.Confirmed && e.Result.Outcome == CrossCheckOutcome.Contradictory);
        }

        /// <summary>登记比对结果，一律进入待确认；登记动作同样写审计（操作人通常为抽取/比对流程）。</summary>
        public Result<CrossCheckEntry> Submit(CrossCheckResult result, string operatorName, DateTimeOffset utc)
        {
            if (result == null || string.IsNullOrWhiteSpace(result.StatementId) || string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<CrossCheckEntry>.Fail(ErrInvalidArgument, "结果与操作人不能为空");
            }

            if (_byStatement.ContainsKey(result.StatementId))
            {
                return Result<CrossCheckEntry>.Fail(ErrDuplicate, "该陈述已登记比对结果：" + result.StatementId);
            }

            var entry = new CrossCheckEntry(result, CrossCheckState.PendingConfirmation);
            // W5.1（DEFECTS/W3.md 21:32）：与 Confirm/Dismiss 统一——先写审计，失败返回 crosscheck_audit_failed，不登记、不抛异常。
            try
            {
                _audit.Append(new InvestigationAuditEntry(utc, operatorName, ActionSubmit, InvestigationAuditCategories.Interview,
                    "登记比对 " + result.StatementId + "（" + result.RecordId + "）", string.Empty, Summarize(entry)));
            }
            catch (Exception ex)
            {
                return Result<CrossCheckEntry>.Fail(ErrAuditFailed, "审计写入失败，登记未生效：" + ex.Message);
            }

            _entries.Add(entry);
            _byStatement[result.StatementId] = entry;
            return Result<CrossCheckEntry>.Ok(entry);
        }

        /// <summary>
        /// W5.1 D02：对已驳回（Dismissed）的结论重新提交比对结果。新条目进入待确认并成为该陈述的当前条目；
        /// 旧条目改为 <see cref="CrossCheckState.Superseded"/>，保留在 <see cref="Entries"/> 中（驳回人/时间/理由不动）。
        /// 只写一条审计（action = <see cref="ActionResubmit"/>，before = 旧条目摘要，after = 新条目摘要 + 理由），先写审计后改状态：
        /// 审计失败返回 crosscheck_audit_failed，台账不变。待确认 / 已确认 / 已取代的条目返回 crosscheck_not_dismissed；
        /// 结果的笔录号必须与原条目相同；理由必填。
        /// </summary>
        public Result<CrossCheckEntry> Resubmit(CrossCheckResult result, string investigator, DateTimeOffset utc, string reason)
        {
            if (result == null || string.IsNullOrWhiteSpace(result.StatementId) || string.IsNullOrWhiteSpace(investigator) || string.IsNullOrWhiteSpace(reason))
            {
                return Result<CrossCheckEntry>.Fail(ErrInvalidArgument, "结果、调查员与重新提交理由不能为空");
            }

            CrossCheckEntry old = Get(result.StatementId);
            if (old == null)
            {
                return Result<CrossCheckEntry>.Fail(ErrNotFound, "未登记：" + result.StatementId);
            }

            if (old.State != CrossCheckState.Dismissed)
            {
                return Result<CrossCheckEntry>.Fail(ErrNotDismissed, "只有已驳回的结论可重新提交，当前：" + old.State);
            }

            if (!string.Equals(old.Result.RecordId, result.RecordId, StringComparison.Ordinal))
            {
                return Result<CrossCheckEntry>.Fail(ErrInvalidArgument, "重新提交的结果属于另一份笔录：" + result.RecordId + "（原 " + old.Result.RecordId + "）");
            }

            var entry = new CrossCheckEntry(result, CrossCheckState.PendingConfirmation);
            try
            {
                _audit.Append(new InvestigationAuditEntry(utc, investigator, ActionResubmit, InvestigationAuditCategories.Interview,
                    "重新提交比对 " + result.StatementId + "（" + result.RecordId + "，r" + result.StatementVersion.ToString(CultureInfo.InvariantCulture) + "）",
                    Summarize(old), Summarize(entry) + "；理由=" + reason));
            }
            catch (Exception ex)
            {
                return Result<CrossCheckEntry>.Fail(ErrAuditFailed, "审计写入失败，重新提交未生效：" + ex.Message);
            }

            old.State = CrossCheckState.Superseded;
            _entries.Add(entry);
            _byStatement[result.StatementId] = entry;
            return Result<CrossCheckEntry>.Ok(entry);
        }

        /// <summary>逐条确认一条待确认结论（一致/矛盾/无法核实均可），写审计。</summary>
        public Result<CrossCheckEntry> Confirm(string statementId, string investigator, DateTimeOffset utc, string note = null)
        {
            return Decide(statementId, investigator, utc, note, CrossCheckState.Confirmed, ActionConfirm, "确认比对结论 ", false);
        }

        /// <summary>
        /// 批量确认一致项。全有或全无：列表中任一项不存在、非待确认或结论不是“一致”，整批拒绝且不写审计。
        /// 成功时每一项各写一条审计（action = <see cref="ActionBatchConfirm"/>）。矛盾项必须用 <see cref="Confirm"/> 逐条确认。
        /// </summary>
        public Result<IReadOnlyList<CrossCheckEntry>> ConfirmConsistentBatch(IEnumerable<string> statementIds, string investigator, DateTimeOffset utc, string note = null)
        {
            if (string.IsNullOrWhiteSpace(investigator))
            {
                return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrInvalidArgument, "调查员不能为空");
            }

            if (statementIds == null)
            {
                return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrInvalidArgument, "列表不能为空");
            }

            var batch = new List<CrossCheckEntry>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (string id in statementIds)
            {
                CrossCheckEntry e = Get(id);
                if (e == null)
                {
                    return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrNotFound, "未登记：" + (id ?? "(null)"));
                }

                if (!seen.Add(id))
                {
                    continue;
                }

                if (e.State != CrossCheckState.PendingConfirmation)
                {
                    return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrNotPending, "非待确认：" + id + "（" + e.State + "）");
                }

                if (e.Result.Outcome != CrossCheckOutcome.Consistent)
                {
                    return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrBatchNotConsistent, "只有一致项可批量确认，" + id + " 为 " + e.Result.Outcome + "，须逐条确认");
                }

                batch.Add(e);
            }

            if (batch.Count == 0)
            {
                return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrInvalidArgument, "列表不能为空");
            }

            // W3.2 两阶段提交：① 逐条写带 batchId 的 batch_confirm；② 写 batch_commit；③ 全部成功后才一次性改状态（改状态本身不会失败）。
            // 任一步审计写失败：状态一律不动；尽力追加一条带 batchId 的 batch_abort，返回 crosscheck_audit_failed。
            // batch_abort 只是辅助说明：即使它也写失败，没有 batch_commit 的批量行在重放时同样作废。
            string batchId = Guid.NewGuid().ToString("N");
            string tag = " " + BatchTagOpen + batchId + "]";
            string ids = string.Join(",", batch.Select(x => x.Result.StatementId));
            int written = 0;
            try
            {
                for (int i = 0; i < batch.Count; i++)
                {
                    CrossCheckEntry e = batch[i];
                    _audit.Append(new InvestigationAuditEntry(utc, investigator, ActionBatchConfirm, InvestigationAuditCategories.Interview,
                        "批量确认一致 " + e.Result.StatementId + "（" + e.Result.RecordId + "，" + (i + 1) + "/" + batch.Count + "）" + tag, Summarize(e),
                        CrossCheckState.Confirmed + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note), batchId));
                    written++;
                }

                _audit.Append(new InvestigationAuditEntry(utc, investigator, ActionBatchCommit, InvestigationAuditCategories.Interview,
                    "批量确认提交 " + batch.Count + " 条" + tag, string.Empty, ids, batchId));
            }
            catch (Exception ex)
            {
                try
                {
                    _audit.Append(new InvestigationAuditEntry(utc, investigator, ActionBatchAbort, InvestigationAuditCategories.Interview,
                        "批量确认中止，作废已写入的 " + written + "/" + batch.Count + " 条批量确认审计" + tag, ids,
                        CrossCheckState.PendingConfirmation.ToString(), batchId));
                }
                catch (Exception)
                {
                    // 审计不可用时无法补记；状态未改，未提交的批量行重放时作废，调查员可重试。
                }

                string stage = written < batch.Count ? "第 " + (written + 1) + "/" + batch.Count + " 条" : "提交行";
                return Result<IReadOnlyList<CrossCheckEntry>>.Fail(ErrAuditFailed, "审计写入失败（" + stage + "），整批未确认：" + ex.Message);
            }

            foreach (CrossCheckEntry e in batch)
            {
                e.State = CrossCheckState.Confirmed;
                e.DecidedBy = investigator;
                e.DecidedUtc = utc;
                e.Note = note ?? string.Empty;
                e.ConfirmedInBatch = true;
            }

            return Result<IReadOnlyList<CrossCheckEntry>>.Ok(batch);
        }

        /// <summary>驳回结论（如数据源有误）。必须填写理由。</summary>
        public Result<CrossCheckEntry> Dismiss(string statementId, string investigator, DateTimeOffset utc, string reason)
        {
            return Decide(statementId, investigator, utc, reason, CrossCheckState.Dismissed, ActionDismiss, "驳回比对结论 ", true);
        }

        private Result<CrossCheckEntry> Decide(string statementId, string investigator, DateTimeOffset utc, string note, CrossCheckState target, string action, string verb, bool noteRequired)
        {
            if (string.IsNullOrWhiteSpace(investigator))
            {
                return Result<CrossCheckEntry>.Fail(ErrInvalidArgument, "调查员不能为空");
            }

            if (noteRequired && string.IsNullOrWhiteSpace(note))
            {
                return Result<CrossCheckEntry>.Fail(ErrInvalidArgument, "驳回必须填写理由");
            }

            CrossCheckEntry e = Get(statementId);
            if (e == null)
            {
                return Result<CrossCheckEntry>.Fail(ErrNotFound, "未登记：" + (statementId ?? "(null)"));
            }

            if (e.State != CrossCheckState.PendingConfirmation)
            {
                return Result<CrossCheckEntry>.Fail(ErrNotPending, "仅待确认的结论可确认/驳回，当前：" + e.State);
            }

            string before = Summarize(e);
            // 先写审计，再改状态：审计写失败时状态不变，返回 crosscheck_audit_failed（W3.2，与批量一致，不再抛异常）。
            try
            {
                _audit.Append(new InvestigationAuditEntry(utc, investigator, action, InvestigationAuditCategories.Interview,
                    verb + e.Result.StatementId + "（" + e.Result.RecordId + "）", before,
                    target + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            }
            catch (Exception ex)
            {
                return Result<CrossCheckEntry>.Fail(ErrAuditFailed, "审计写入失败，" + verb.Trim() + "未生效：" + ex.Message);
            }

            e.State = target;
            e.DecidedBy = investigator;
            e.DecidedUtc = utc;
            e.Note = note ?? string.Empty;
            return Result<CrossCheckEntry>.Ok(e);
        }

        /// <summary>
        /// 批量审计行（batch_confirm / batch_commit / batch_abort）上的 batchId；其他行或 W3.2 之前的旧批量行返回 null。
        /// W5.1：优先取合同扩展键 x-batchId（<see cref="InvestigationAuditEntry.BatchId"/>，须为 32 位小写十六进制）；
        /// 没有或不合法时退回 command 末尾的 “[batch=…]” 标记（写入方两者都写；只认 7 个标准键的读取方读回时只剩标记）。
        /// </summary>
        public static string BatchIdOf(InvestigationAuditEntry entry)
        {
            if (entry == null || (entry.Action != ActionBatchConfirm && entry.Action != ActionBatchCommit && entry.Action != ActionBatchAbort))
            {
                return null;
            }

            if (IsBatchKey(entry.BatchId))
            {
                return entry.BatchId;
            }

            string c = entry.CommandName;
            int i = c.LastIndexOf(BatchTagOpen, StringComparison.Ordinal);
            if (i < 0 || !c.EndsWith("]", StringComparison.Ordinal))
            {
                return null;
            }

            string id = c.Substring(i + BatchTagOpen.Length, c.Length - i - BatchTagOpen.Length - 1);
            return id.Length == 0 ? null : id;
        }

        /// <summary>
        /// 读取或重放审计时用：去掉未提交的批量确认行，其余行按原顺序保留。
        /// 一条 batch_confirm 行有效，当且仅当它带 batchId，且其后出现同 batchId 的 batch_commit，
        /// 且该提交行列出的陈述数等于提交行之前同 batchId 的 batch_confirm 行数；提交行之后才出现的同 batchId 行不算。没有 batchId 的旧批量行一律作废。
        /// </summary>
        public static IReadOnlyList<InvestigationAuditEntry> EffectiveAudit(IEnumerable<InvestigationAuditEntry> entries)
        {
            var list = entries == null ? new List<InvestigationAuditEntry>() : entries.Where(x => x != null).ToList();
            var rowsBefore = new Dictionary<string, int>(StringComparer.Ordinal);
            var commitAt = new Dictionary<string, int>(StringComparer.Ordinal);
            for (int i = 0; i < list.Count; i++)
            {
                InvestigationAuditEntry a = list[i];
                string id = BatchIdOf(a);
                if (id == null)
                {
                    continue;
                }

                if (a.Action == ActionBatchConfirm)
                {
                    rowsBefore[id] = rowsBefore.TryGetValue(id, out int k) ? k + 1 : 1;
                }
                else if (a.Action == ActionBatchCommit && !commitAt.ContainsKey(id))
                {
                    int listed = a.AfterValueSummary.Length == 0 ? 0 : a.AfterValueSummary.Split(',').Length;
                    if (rowsBefore.TryGetValue(id, out int seen) && seen == listed)
                    {
                        commitAt[id] = i;
                    }
                }
            }

            var result = new List<InvestigationAuditEntry>(list.Count);
            for (int i = 0; i < list.Count; i++)
            {
                InvestigationAuditEntry a = list[i];
                if (a.Action == ActionBatchConfirm)
                {
                    string id = BatchIdOf(a);
                    if (id == null || !commitAt.TryGetValue(id, out int at) || i > at)
                    {
                        continue;
                    }
                }

                result.Add(a);
            }

            return result.AsReadOnly();
        }

        private const string BatchTagOpen = "[batch=";

        private static bool IsBatchKey(string id)
        {
            if (id == null || id.Length != 32)
            {
                return false;
            }

            foreach (char ch in id)
            {
                if (!((ch >= '0' && ch <= '9') || (ch >= 'a' && ch <= 'f')))
                {
                    return false;
                }
            }

            return true;
        }

        private IReadOnlyList<CrossCheckEntry> Filter(Func<CrossCheckEntry, bool> pred)
        {
            var list = new List<CrossCheckEntry>();
            for (int i = 0; i < _entries.Count; i++)
            {
                if (pred(_entries[i]))
                {
                    list.Add(_entries[i]);
                }
            }

            return list;
        }

        private static string Summarize(CrossCheckEntry e)
        {
            CrossCheckResult r = e.Result;
            string delta = r.Delta.HasValue ? r.Delta.Value.ToString("0.###", CultureInfo.InvariantCulture) + " " + r.DeltaUnit : "-";
            return e.State + "；" + r.Outcome + "；陈述=" + r.ClaimedText + "；数据=" + r.ObservedText + "（" + r.SourceLabel + "）；Δ=" + delta + "；规则=" + r.Rule;
        }
    }
}
