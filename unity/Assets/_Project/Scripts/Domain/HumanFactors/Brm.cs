using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.HumanFactors
{
    /// <summary>BRM 核查项评估结果。</summary>
    public enum BrmResult
    {
        /// <summary>未评估。</summary>
        NotAssessed = 0,

        /// <summary>符合。</summary>
        Pass = 1,

        /// <summary>部分符合。</summary>
        Partial = 2,

        /// <summary>不符合。</summary>
        Fail = 3,

        /// <summary>不适用（如未装 ARPA 的船）。</summary>
        NotApplicable = 4
    }

    /// <summary>BRM 评估版本的复核状态（W18-B6）。</summary>
    public enum BrmReviewStatus
    {
        /// <summary>草稿：SetResult 新建的评估版本，待调查员确认。</summary>
        Draft = 0,

        /// <summary>已确认（生效）。</summary>
        Confirmed = 1,

        /// <summary>已驳回（必须写理由），不计入统计。</summary>
        Rejected = 2,

        /// <summary>初始“未评估”基线（版本 0），无可复核内容。</summary>
        NotSubmitted = 3
    }

    /// <summary>驾驶台资源管理核查项的一个评估版本（不可变；重新评估/复核即生成新实例，历史见 BrmChecklist.History）。</summary>
    public sealed class BrmItem
    {
        public string Id { get; }
        public string Text { get; }
        public string Category { get; }
        public BrmResult Result { get; }

        /// <summary>支撑证据编号（保管链登记过的）。</summary>
        public IReadOnlyList<string> EvidenceIds { get; }

        /// <summary>评估人。</summary>
        public string Assessor { get; }

        /// <summary>备注。</summary>
        public string Note { get; }

        /// <summary>版本号：0 = 初始未评估；每次 SetResult +1。</summary>
        public int Version { get; }

        /// <summary>复核状态。</summary>
        public BrmReviewStatus ReviewStatus { get; }

        /// <summary>确认/驳回人；未复核为 null。</summary>
        public string ReviewedBy { get; }

        /// <summary>确认/驳回时刻；未复核为 null。</summary>
        public DateTimeOffset? ReviewedUtc { get; }

        /// <summary>复核备注（驳回理由）。</summary>
        public string ReviewNote { get; }

        public BrmItem(string id, string text, string category)
            : this(id, text, category, BrmResult.NotAssessed, new string[0], string.Empty, string.Empty)
        {
        }

        public BrmItem(string id, string text, string category, BrmResult result, IReadOnlyList<string> evidenceIds, string assessor, string note)
            : this(id, text, category, result, evidenceIds, assessor, note, 0, BrmReviewStatus.NotSubmitted, null, null, null)
        {
        }

        public BrmItem(
            string id,
            string text,
            string category,
            BrmResult result,
            IReadOnlyList<string> evidenceIds,
            string assessor,
            string note,
            int version,
            BrmReviewStatus reviewStatus,
            string reviewedBy,
            DateTimeOffset? reviewedUtc,
            string reviewNote)
        {
            Version = version;
            ReviewStatus = reviewStatus;
            ReviewedBy = reviewedBy;
            ReviewedUtc = reviewedUtc;
            ReviewNote = reviewNote ?? string.Empty;
            Id = id ?? string.Empty;
            Text = text ?? string.Empty;
            Category = category ?? string.Empty;
            Result = result;
            EvidenceIds = evidenceIds ?? new string[0];
            Assessor = assessor ?? string.Empty;
            Note = note ?? string.Empty;
        }
    }

    /// <summary>
    /// 一次针对某对象（班组/船）的 BRM（驾驶台资源管理）核查。只追加条目、评估可覆盖。
    /// 默认核查单参考 STCW A-II/1（船长与驾驶员最低适任标准）与 STCW Section B-VIII/2
    /// （值班安排与值班指导，含驾驶台程序）。
    /// </summary>
    public sealed class BrmChecklist
    {
        public const string ErrDuplicateItem = "hf_duplicate_item";
        public const string ErrUnknownItem = "hf_unknown_item";
        public const string ErrInvalidArgument = "hf_invalid_argument";
        public const string ErrMissingEvidence = "hf_missing_evidence";
        public const string ErrUnknownEvidence = "hf_unknown_evidence";

        public const string ErrInvalidState = "hf_invalid_state";
        public const string ActionConfirm = "hf.brm.confirm";
        public const string ActionReject = "hf.brm.reject";

        private readonly List<BrmItem> _items = new List<BrmItem>();
        private readonly Dictionary<string, List<BrmItem>> _history = new Dictionary<string, List<BrmItem>>(StringComparer.Ordinal);
        private readonly HashSet<string> _ids = new HashSet<string>(StringComparer.Ordinal);

        /// <summary>核查对象（如当值班组 / 船名）。</summary>
        public string Subject { get; }

        public BrmChecklist(string subject)
            : this(subject, null)
        {
        }

        /// <summary>audit 为 null 时用内部 <see cref="InMemoryInvestigationAuditSink"/>。</summary>
        public BrmChecklist(string subject, IInvestigationAuditSink audit)
        {
            Subject = subject ?? string.Empty;
            Audit = audit ?? new InMemoryInvestigationAuditSink();
        }

        /// <summary>确认/驳回的审计去向。</summary>
        public IInvestigationAuditSink Audit { get; }

        /// <summary>
        /// 默认核查单（6 条）：
        /// 1. 船长上驾驶台（STCW A-II/1；B-VIII/2 第 3-1 部分——受限水域/能见度不良时船长到岗）；
        /// 2. 瞭望：视觉+听觉连续有效瞭望（STCW A-VIII/2 第 4 部分；COLREG 规则 5）；
        /// 3. ARPA 系统标绘（STCW A-II/1 §3——雷达/ARPA 使用）；
        /// 4. 舵令复述 / 闭环沟通（STCW B-VIII/2——驾驶台程序与沟通）；
        /// 5. VTS 报告与守听（SOLAS 第 V 章第 12 条；港口 VTS 规定）；
        /// 6. 雷达双机运行（STCW B-VIII/2——设备可用性管理）。
        /// </summary>
        public static BrmChecklist CreateDefault(string subject)
        {
            return CreateDefault(subject, null);
        }

        /// <summary>同 <see cref="CreateDefault(string)"/>，指定审计去向。</summary>
        public static BrmChecklist CreateDefault(string subject, IInvestigationAuditSink audit)
        {
            var c = new BrmChecklist(subject, audit);
            c.AddItem("HF-CAP-01", "船长上驾驶台（受限水域/能见度不良/交通密集时到岗）", "指挥");
            c.AddItem("HF-LOOK-01", "瞭望：视觉+听觉连续有效瞭望，且不因其他任务中断", "瞭望");
            c.AddItem("HF-ARPA-01", "ARPA 系统标绘：目标捕获、CPA/TCPA 设置与持续标绘", "航行设备");
            c.AddItem("HF-HELM-01", "舵令复述/闭环沟通：车钟与舵令逐令复诵确认", "沟通");
            c.AddItem("HF-VTS-01", "VTS 报告与守听：按时向 VTS 报告并守听指定频道", "对外沟通");
            c.AddItem("HF-RADAR-02", "雷达双机运行：主/备雷达同时开机并互核目标", "航行设备");
            return c;
        }

        /// <summary>已录入核查项（录入顺序）。</summary>
        public IReadOnlyList<BrmItem> Items
        {
            get { return new List<BrmItem>(_items).AsReadOnly(); } // W18.1 / D07：只读副本，不暴露内部 List
        }

        /// <summary>追加核查项；id 重复 → hf_duplicate_item。</summary>
        public Result<BrmItem> AddItem(string id, string text, string category)
        {
            if (string.IsNullOrWhiteSpace(id) || string.IsNullOrWhiteSpace(text))
            {
                return Result<BrmItem>.Fail(ErrInvalidArgument, "核查项编号与内容不能为空");
            }

            if (_ids.Contains(id))
            {
                return Result<BrmItem>.Fail(ErrDuplicateItem, "核查项编号重复：" + id);
            }

            var item = new BrmItem(id, text, category);
            _items.Add(item);
            _history[id] = new List<BrmItem> { item };
            _ids.Add(id);
            return Result<BrmItem>.Ok(item);
        }

        /// <summary>
        /// 设置核查项结果。未知条目 → hf_unknown_item；assessor 为空 → hf_invalid_argument；
        /// Fail/Partial 必须至少 1 条证据 → hf_missing_evidence；
        /// ledger 不为空时证据必须已登记 → hf_unknown_evidence。
        /// </summary>
        public Result<BrmItem> SetResult(
            string itemId,
            BrmResult result,
            IEnumerable<string> evidenceIds,
            string assessor,
            string note = null,
            CustodyLedger ledger = null)
        {
            int index = IndexOf(itemId);
            if (index < 0)
            {
                return Result<BrmItem>.Fail(ErrUnknownItem, "未知核查项：" + itemId);
            }

            if (string.IsNullOrWhiteSpace(assessor))
            {
                return Result<BrmItem>.Fail(ErrInvalidArgument, "评估人不能为空");
            }

            if (!Enum.IsDefined(typeof(BrmResult), result))
            {
                return Result<BrmItem>.Fail(ErrInvalidArgument, "未知结果值：" + (int)result);
            }

            var evList = evidenceIds == null ? new List<string>() : evidenceIds.Where(x => !string.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).ToList();
            if ((result == BrmResult.Fail || result == BrmResult.Partial) && evList.Count == 0)
            {
                return Result<BrmItem>.Fail(ErrMissingEvidence, "Fail/Partial 结论至少需要 1 条证据");
            }

            // 传 ledger 时，凡给出的证据 id 都必须已登记（不论结果）。
            if (ledger != null)
            {
                for (int i = 0; i < evList.Count; i++)
                {
                    if (ledger.Get(evList[i]) == null)
                    {
                        return Result<BrmItem>.Fail(ErrUnknownEvidence, "证据未登记：" + evList[i]);
                    }
                }
            }

            // B6：每次评估追加一个 Draft 新版本（保留历史），待 ConfirmResult/RejectResult。
            BrmItem old = _items[index];
            var updated = new BrmItem(old.Id, old.Text, old.Category, result, evList, assessor, note, old.Version + 1, BrmReviewStatus.Draft, null, null, null);
            _items[index] = updated;
            _history[old.Id].Add(updated);
            return Result<BrmItem>.Ok(updated);
        }

        /// <summary>确认当前 Draft 评估版本（B6）。先写审计 hf.brm.confirm，审计成功才改状态。</summary>
        public Result<BrmItem> ConfirmResult(string itemId, string investigator, DateTimeOffset utc, string note = null)
        {
            return Review(itemId, investigator, utc, note, BrmReviewStatus.Confirmed);
        }

        /// <summary>驳回当前 Draft 评估版本（B6）；理由必填。先写审计 hf.brm.reject。</summary>
        public Result<BrmItem> RejectResult(string itemId, string investigator, DateTimeOffset utc, string note)
        {
            return Review(itemId, investigator, utc, note, BrmReviewStatus.Rejected);
        }

        /// <summary>某核查项的全部评估版本（版本 0 = 初始未评估），按版本升序。</summary>
        public IReadOnlyList<BrmItem> History(string itemId)
        {
            List<BrmItem> h;
            return itemId != null && _history.TryGetValue(itemId, out h) ? h.ToList() : new List<BrmItem>();
        }

        /// <summary>
        /// 各结果计数（含草稿视图）：每项取最新一个未被驳回的版本；全被驳回 → NotAssessed。
        /// 生效视图见 <see cref="ConfirmedSummary"/>。
        /// </summary>
        public IReadOnlyDictionary<BrmResult, int> Summary()
        {
            return Tally(v => v.ReviewStatus != BrmReviewStatus.Rejected);
        }

        /// <summary>只计已确认的评估：每项取最新一个 Confirmed 版本；没有 → NotAssessed。</summary>
        public IReadOnlyDictionary<BrmResult, int> ConfirmedSummary()
        {
            return Tally(v => v.ReviewStatus == BrmReviewStatus.Confirmed);
        }

        private IReadOnlyDictionary<BrmResult, int> Tally(Func<BrmItem, bool> eligible)
        {
            var d = new Dictionary<BrmResult, int>();
            foreach (BrmResult r in Enum.GetValues(typeof(BrmResult)))
            {
                d[r] = 0;
            }

            for (int i = 0; i < _items.Count; i++)
            {
                List<BrmItem> h = _history[_items[i].Id];
                BrmResult result = BrmResult.NotAssessed;
                for (int k = h.Count - 1; k >= 1; k--)
                {
                    if (eligible(h[k]))
                    {
                        result = h[k].Result;
                        break;
                    }
                }

                d[result]++;
            }

            return d;
        }

        private Result<BrmItem> Review(string itemId, string investigator, DateTimeOffset utc, string note, BrmReviewStatus to)
        {
            int index = IndexOf(itemId);
            if (index < 0)
            {
                return Result<BrmItem>.Fail(ErrUnknownItem, "未知核查项：" + itemId);
            }

            if (string.IsNullOrWhiteSpace(investigator))
            {
                return Result<BrmItem>.Fail(ErrInvalidArgument, "调查员不能为空");
            }

            if (to == BrmReviewStatus.Rejected && string.IsNullOrWhiteSpace(note))
            {
                return Result<BrmItem>.Fail(ErrInvalidArgument, "驳回必须写理由");
            }

            BrmItem cur = _items[index];
            if (cur.ReviewStatus != BrmReviewStatus.Draft)
            {
                return Result<BrmItem>.Fail(ErrInvalidState, "只有草稿评估可确认/驳回，" + cur.Id + " 当前为 " + cur.ReviewStatus);
            }

            Audit.Append(new InvestigationAuditEntry(utc, investigator, to == BrmReviewStatus.Confirmed ? ActionConfirm : ActionReject, HumanFactorsAudit.Category,
                (to == BrmReviewStatus.Confirmed ? "确认" : "驳回") + " BRM 评估 " + cur.Id + " v" + cur.Version + "（" + Subject + "）",
                cur.Result + "；" + cur.ReviewStatus + "；评估人=" + cur.Assessor,
                cur.Result + "；" + to + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            var reviewed = new BrmItem(cur.Id, cur.Text, cur.Category, cur.Result, cur.EvidenceIds, cur.Assessor, cur.Note, cur.Version, to, investigator, utc, note);
            _items[index] = reviewed;
            List<BrmItem> h = _history[cur.Id];
            h[h.Count - 1] = reviewed;
            return Result<BrmItem>.Ok(reviewed);
        }

        private int IndexOf(string itemId)
        {
            if (itemId == null)
            {
                return -1;
            }

            for (int i = 0; i < _items.Count; i++)
            {
                if (string.Equals(_items[i].Id, itemId, StringComparison.Ordinal))
                {
                    return i;
                }
            }

            return -1;
        }
    }
}
