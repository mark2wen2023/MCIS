using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.Recommendations
{
    /// <summary>安全建议状态：草拟→已发布→已回复→已落实/未采纳/关闭。</summary>
    public enum RecommendationStatus : byte
    {
        Draft = 0,
        Issued = 1,
        Responded = 2,
        Implemented = 3,
        NotAdopted = 4,
        Closed = 5,
    }

    /// <summary>原型看板四栏（screenshots/1440/15-recs）。</summary>
    public enum KanbanColumn : byte
    {
        /// <summary>草拟。</summary>
        Draft = 0,
        /// <summary>已发布。</summary>
        Issued = 1,
        /// <summary>落实中。</summary>
        InProgress = 2,
        /// <summary>已关闭。</summary>
        Closed = 3,
    }

    /// <summary>状态转换记录。</summary>
    public sealed class RecommendationTransition
    {
        public RecommendationStatus From { get; }
        public RecommendationStatus To { get; }
        public string OperatorName { get; }
        public DateTimeOffset Utc { get; }
        public string Note { get; }

        internal RecommendationTransition(RecommendationStatus from, RecommendationStatus to, string op, DateTimeOffset utc, string note)
        {
            From = from;
            To = to;
            OperatorName = op ?? string.Empty;
            Utc = utc;
            Note = note ?? string.Empty;
        }
    }

    /// <summary>被建议对象（或其主管方）的书面回复。</summary>
    public sealed class RecommendationResponse
    {
        public string Party { get; }
        public string Text { get; }
        public DateTimeOffset Utc { get; }

        internal RecommendationResponse(string party, string text, DateTimeOffset utc)
        {
            Party = party ?? string.Empty;
            Text = text ?? string.Empty;
            Utc = utc;
        }
    }

    /// <summary>
    /// 安全建议（⑨）。字段只读，状态只能通过 <see cref="SafetyRecommendationBoard"/> 按状态机改变。
    /// 每条建议至少关联一个原因节点 id（ECFC/HFACS/COLREG 节点），以满足“可回链到原因节点”。
    /// </summary>
    public sealed class SafetyRecommendation
    {
        private readonly List<string> _causeNodeIds;
        internal readonly List<RecommendationTransition> HistoryList = new List<RecommendationTransition>();
        internal readonly List<RecommendationResponse> ResponseList = new List<RecommendationResponse>();

        /// <summary>编号，格式 SR-YYYY-NN（不允许为空）。</summary>
        public string Id { get; }
        public string Title { get; internal set; }
        public string Body { get; internal set; }
        /// <summary>建议对象，如“Mary 轮公司”“星屿 VTS”。</summary>
        public string Addressee { get; internal set; }
        public IReadOnlyList<string> CauseNodeIds { get { return _causeNodeIds; } }
        /// <summary>落实期限。</summary>
        public DateTimeOffset DueUtc { get; internal set; }
        /// <summary>MSC.255 §25.5 临时安全措施。</summary>
        public bool IsInterim { get; internal set; }
        public DateTimeOffset CreatedUtc { get; }
        public RecommendationStatus Status { get; internal set; }
        /// <summary>所属案件号；空串表示未填。</summary>
        public string CaseId { get; }
        /// <summary>落实进度 0–100。仅 Responded 状态可修改；进入 Implemented 时自动置 100。</summary>
        public int ProgressPct { get; internal set; }
        /// <summary>核实说明：最近一次进入 Implemented 或 Closed 时填写的说明。</summary>
        public string VerificationNote { get; internal set; } = string.Empty;
        /// <summary>回复摘要：最近一条回复内容（无回复为空串）。</summary>
        public string ResponseSummary
        {
            get { return ResponseList.Count == 0 ? string.Empty : ResponseList[ResponseList.Count - 1].Text; }
        }

        /// <summary>看板栏位，见 <see cref="SafetyRecommendationBoard.ToKanbanColumn"/>。</summary>
        public KanbanColumn Column { get { return SafetyRecommendationBoard.ToKanbanColumn(Status); } }

        public IReadOnlyList<RecommendationTransition> History { get { return HistoryList; } }
        public IReadOnlyList<RecommendationResponse> Responses { get { return ResponseList; } }

        internal SafetyRecommendation(string id, string title, string body, string addressee, List<string> causeNodeIds, DateTimeOffset dueUtc, bool isInterim, DateTimeOffset createdUtc, string caseId)
        {
            CaseId = caseId ?? string.Empty;
            Id = id;
            Title = title ?? string.Empty;
            Body = body ?? string.Empty;
            Addressee = addressee ?? string.Empty;
            _causeNodeIds = causeNodeIds;
            DueUtc = dueUtc;
            IsInterim = isInterim;
            CreatedUtc = createdUtc;
            Status = RecommendationStatus.Draft;
        }

        internal void ReplaceCauseNodes(List<string> nodes)
        {
            _causeNodeIds.Clear();
            _causeNodeIds.AddRange(nodes);
        }

        public bool IsTerminal { get { return Status == RecommendationStatus.Closed; } }

        /// <summary>未落实前（已发布/已回复）超过期限即逾期。</summary>
        public bool IsOverdue(DateTimeOffset asOfUtc)
        {
            return (Status == RecommendationStatus.Issued || Status == RecommendationStatus.Responded) && asOfUtc > DueUtc;
        }
    }

    /// <summary>安全建议看板：创建、按状态机流转、回复登记、逾期查询；所有变更写审计。</summary>
    public sealed class SafetyRecommendationBoard
    {
        public const string ErrInvalidArgument = "safetyrec_invalid_argument";
        public const string ErrInvalidId = "safetyrec_invalid_id";
        public const string ErrDuplicateId = "safetyrec_duplicate_id";
        public const string ErrNoCauseLink = "safetyrec_no_cause_link";
        public const string ErrNotFound = "safetyrec_not_found";
        public const string ErrIllegalTransition = "safetyrec_illegal_transition";

        /// <summary>W3.1：UpdateDraft 只能用于草稿。</summary>
        public const string ErrNotDraft = "safetyrec_not_draft";

        /// <summary>W3.1：草稿内容修改的审计动作。</summary>
        public const string ActionUpdate = "safetyrec.update";
        public const string ErrInvalidProgress = "safetyrec_invalid_progress";
        public const string ErrInvalidCaseId = "safetyrec_invalid_case_id";

        private static readonly Regex IdPattern = new Regex(@"\ASR-[0-9]{4}-[0-9]{2,}\z", RegexOptions.CultureInvariant); // W3-D09：\d 会匹配非 ASCII 数字

        private static readonly Dictionary<RecommendationStatus, RecommendationStatus[]> Allowed = new Dictionary<RecommendationStatus, RecommendationStatus[]>
        {
            { RecommendationStatus.Draft, new[] { RecommendationStatus.Issued } },
            { RecommendationStatus.Issued, new[] { RecommendationStatus.Responded } },
            { RecommendationStatus.Responded, new[] { RecommendationStatus.Implemented, RecommendationStatus.NotAdopted, RecommendationStatus.Closed } },
            { RecommendationStatus.Implemented, new[] { RecommendationStatus.Closed } },
            { RecommendationStatus.NotAdopted, new[] { RecommendationStatus.Closed } },
            { RecommendationStatus.Closed, new RecommendationStatus[0] },
        };

        private readonly IInvestigationAuditSink _audit;
        private readonly List<SafetyRecommendation> _items = new List<SafetyRecommendation>();
        private readonly Dictionary<string, SafetyRecommendation> _byId = new Dictionary<string, SafetyRecommendation>(StringComparer.Ordinal);

        public SafetyRecommendationBoard(IInvestigationAuditSink audit)
        {
            _audit = audit ?? throw new ArgumentNullException(nameof(audit));
        }

        public IReadOnlyList<SafetyRecommendation> All { get { return _items; } }

        public static bool CanTransition(RecommendationStatus from, RecommendationStatus to)
        {
            return Array.IndexOf(Allowed[from], to) >= 0;
        }

        public static IReadOnlyList<RecommendationStatus> AllowedNext(RecommendationStatus from)
        {
            return (RecommendationStatus[])Allowed[from].Clone();
        }

        /// <summary>
        /// 状态 → 看板四栏：Draft→草拟；Issued→已发布；Responded→落实中；Implemented / NotAdopted / Closed→已关闭。
        /// </summary>
        public static KanbanColumn ToKanbanColumn(RecommendationStatus status)
        {
            switch (status)
            {
                case RecommendationStatus.Draft: return KanbanColumn.Draft;
                case RecommendationStatus.Issued: return KanbanColumn.Issued;
                case RecommendationStatus.Responded: return KanbanColumn.InProgress;
                default: return KanbanColumn.Closed;
            }
        }

        /// <summary>看板栏中文标题。</summary>
        public static string KanbanLabel(KanbanColumn column)
        {
            switch (column)
            {
                case KanbanColumn.Draft: return "草拟";
                case KanbanColumn.Issued: return "已发布";
                case KanbanColumn.InProgress: return "落实中";
                default: return "已关闭";
            }
        }

        public IReadOnlyList<SafetyRecommendation> ByKanbanColumn(KanbanColumn column)
        {
            var list = new List<SafetyRecommendation>();
            for (int i = 0; i < _items.Count; i++)
            {
                if (_items[i].Column == column)
                {
                    list.Add(_items[i]);
                }
            }

            return list;
        }

        /// <summary>更新落实进度（0–100）。仅 Responded（落实中）可改；写审计。</summary>
        public Result<SafetyRecommendation> SetProgress(string id, int progressPct, string operatorName, DateTimeOffset utc, string note = null)
        {
            SafetyRecommendation r = Get(id);
            if (r == null)
            {
                return Result<SafetyRecommendation>.Fail(ErrNotFound, "建议不存在：" + (id ?? "(null)"));
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (progressPct < 0 || progressPct > 100)
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidProgress, "进度须在 0–100：" + progressPct);
            }

            if (r.Status != RecommendationStatus.Responded)
            {
                return Result<SafetyRecommendation>.Fail(ErrIllegalTransition, "仅已回复（落实中）的建议可更新进度，当前：" + r.Status);
            }

            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "safetyrec.progress", InvestigationAuditCategories.SafetyRec,
                "更新落实进度 " + id, r.ProgressPct + "%", progressPct + "%" + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            r.ProgressPct = progressPct;
            return Result<SafetyRecommendation>.Ok(r);
        }

        public static bool IsValidId(string id)
        {
            return id != null && IdPattern.IsMatch(id);
        }

        public SafetyRecommendation Get(string id)
        {
            return id != null && _byId.TryGetValue(id, out SafetyRecommendation r) ? r : null;
        }

        /// <summary>下一个可用编号 SR-{year}-NN（两位起，按该年已有最大序号 +1）。</summary>
        public string NextId(int year)
        {
            string prefix = "SR-" + year.ToString("0000", CultureInfo.InvariantCulture) + "-";
            int max = 0;
            for (int i = 0; i < _items.Count; i++)
            {
                string id = _items[i].Id;
                if (id.StartsWith(prefix, StringComparison.Ordinal) &&
                    int.TryParse(id.Substring(prefix.Length), NumberStyles.None, CultureInfo.InvariantCulture, out int n) && n > max)
                {
                    max = n;
                }
            }

            return prefix + (max + 1).ToString("00", CultureInfo.InvariantCulture);
        }

        public IReadOnlyList<SafetyRecommendation> ByStatus(RecommendationStatus status)
        {
            var list = new List<SafetyRecommendation>();
            for (int i = 0; i < _items.Count; i++)
            {
                if (_items[i].Status == status)
                {
                    list.Add(_items[i]);
                }
            }

            return list;
        }

        public IReadOnlyList<SafetyRecommendation> Overdue(DateTimeOffset asOfUtc)
        {
            var list = new List<SafetyRecommendation>();
            for (int i = 0; i < _items.Count; i++)
            {
                if (_items[i].IsOverdue(asOfUtc))
                {
                    list.Add(_items[i]);
                }
            }

            return list;
        }

        /// <summary>回链查询：关联到某原因节点的全部建议。</summary>
        public IReadOnlyList<SafetyRecommendation> ByCauseNode(string nodeId)
        {
            var list = new List<SafetyRecommendation>();
            for (int i = 0; i < _items.Count; i++)
            {
                for (int k = 0; k < _items[i].CauseNodeIds.Count; k++)
                {
                    if (string.Equals(_items[i].CauseNodeIds[k], nodeId, StringComparison.Ordinal))
                    {
                        list.Add(_items[i]);
                        break;
                    }
                }
            }

            return list;
        }

        public Result<SafetyRecommendation> CreateDraft(
            string id,
            string title,
            string addressee,
            IEnumerable<string> causeNodeIds,
            DateTimeOffset dueUtc,
            string operatorName,
            DateTimeOffset utc,
            string body = null,
            bool isInterim = false,
            string caseId = null)
        {
            if (!IsValidId(id))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidId, "编号须为 SR-YYYY-NN：" + (id ?? "(null)"));
            }

            if (_byId.ContainsKey(id))
            {
                return Result<SafetyRecommendation>.Fail(ErrDuplicateId, "编号已存在：" + id);
            }

            if (!string.IsNullOrEmpty(caseId) && !EvidenceItem.IsValidCaseId(caseId))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidCaseId, "案件号格式不符：" + caseId);
            }

            if (string.IsNullOrWhiteSpace(title) || string.IsNullOrWhiteSpace(addressee) || string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "标题、对象、操作人不能为空");
            }

            var nodes = new List<string>();
            if (causeNodeIds != null)
            {
                foreach (string n in causeNodeIds)
                {
                    if (!string.IsNullOrWhiteSpace(n) && !nodes.Contains(n))
                    {
                        nodes.Add(n);
                    }
                }
            }

            if (nodes.Count == 0)
            {
                return Result<SafetyRecommendation>.Fail(ErrNoCauseLink, "至少关联一个原因节点 id");
            }

            if (dueUtc <= utc)
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "期限必须晚于创建时间");
            }

            var rec = new SafetyRecommendation(id, title, body, addressee, nodes, dueUtc, isInterim, utc, caseId);
            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "safetyrec.create", InvestigationAuditCategories.SafetyRec,
                "新建安全建议 " + id, string.Empty,
                "对象=" + addressee + "；原因节点=" + string.Join(",", nodes) + "；期限=" + AuditJson.FormatIso(dueUtc) + (isInterim ? "；临时措施" : string.Empty)));
            _items.Add(rec);
            _byId[id] = rec;
            return Result<SafetyRecommendation>.Ok(rec);
        }

        /// <summary>
        /// W3.1：修改草稿内容。只有草稿（Draft）可改；参数为 null 表示该字段不变。
        /// 校验同 CreateDraft（标题/对象/操作人非空、至少一个原因节点、期限晚于本次操作时间）；
        /// 必须至少有一个字段实际变化。先写审计 safetyrec.update（含改前/改后），审计成功才落地修改。
        /// </summary>
        public Result<SafetyRecommendation> UpdateDraft(
            string id,
            string operatorName,
            DateTimeOffset utc,
            string title = null,
            string body = null,
            string addressee = null,
            IEnumerable<string> causeNodeIds = null,
            DateTimeOffset? dueUtc = null,
            bool? isInterim = null)
        {
            SafetyRecommendation r = Get(id);
            if (r == null)
            {
                return Result<SafetyRecommendation>.Fail(ErrNotFound, "建议不存在：" + (id ?? "(null)"));
            }

            if (r.Status != RecommendationStatus.Draft)
            {
                return Result<SafetyRecommendation>.Fail(ErrNotDraft, "只有草稿可修改，" + id + " 当前为 " + r.Status);
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if ((title != null && string.IsNullOrWhiteSpace(title)) || (addressee != null && string.IsNullOrWhiteSpace(addressee)))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "标题、对象不能为空");
            }

            List<string> nodes = null;
            if (causeNodeIds != null)
            {
                nodes = new List<string>();
                foreach (string n in causeNodeIds)
                {
                    if (!string.IsNullOrWhiteSpace(n) && !nodes.Contains(n))
                    {
                        nodes.Add(n);
                    }
                }

                if (nodes.Count == 0)
                {
                    return Result<SafetyRecommendation>.Fail(ErrNoCauseLink, "至少关联一个原因节点 id");
                }
            }

            if (dueUtc.HasValue && dueUtc.Value <= utc)
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "期限必须晚于修改时间");
            }

            string newTitle = title ?? r.Title;
            string newBody = body ?? r.Body;
            string newAddressee = addressee ?? r.Addressee;
            List<string> newNodes = nodes ?? new List<string>(r.CauseNodeIds);
            DateTimeOffset newDue = dueUtc ?? r.DueUtc;
            bool newInterim = isInterim ?? r.IsInterim;
            string before = DraftSummary(r.Title, r.Body, r.Addressee, r.CauseNodeIds, r.DueUtc, r.IsInterim);
            string after = DraftSummary(newTitle, newBody, newAddressee, newNodes, newDue, newInterim);
            if (string.Equals(before, after, StringComparison.Ordinal))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "没有任何字段变化");
            }

            _audit.Append(new InvestigationAuditEntry(utc, operatorName, ActionUpdate, InvestigationAuditCategories.SafetyRec,
                "修改安全建议草稿 " + id, before, after));
            r.Title = newTitle;
            r.Body = newBody;
            r.Addressee = newAddressee;
            r.ReplaceCauseNodes(newNodes);
            r.DueUtc = newDue;
            r.IsInterim = newInterim;
            return Result<SafetyRecommendation>.Ok(r);
        }

        private static string DraftSummary(string title, string body, string addressee, IEnumerable<string> nodes, DateTimeOffset due, bool interim)
        {
            return "标题=" + title + "；正文=" + body + "；对象=" + addressee + "；原因节点=" + string.Join(",", nodes) +
                   "；期限=" + AuditJson.FormatIso(due) + "；临时措施=" + (interim ? "是" : "否");
        }

        public Result<SafetyRecommendation> Issue(string id, string operatorName, DateTimeOffset utc, string note = null)
        {
            return Transition(id, RecommendationStatus.Issued, operatorName, utc, note);
        }

        /// <summary>登记回复。已发布→已回复；已回复状态下可追加后续回复（不改变状态）。</summary>
        public Result<SafetyRecommendation> RecordResponse(string id, string party, string text, string operatorName, DateTimeOffset utc)
        {
            SafetyRecommendation r = Get(id);
            if (r == null)
            {
                return Result<SafetyRecommendation>.Fail(ErrNotFound, "建议不存在：" + (id ?? "(null)"));
            }

            if (string.IsNullOrWhiteSpace(party) || string.IsNullOrWhiteSpace(text) || string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "回复方、回复内容、操作人不能为空");
            }

            if (r.Status != RecommendationStatus.Issued && r.Status != RecommendationStatus.Responded)
            {
                return Result<SafetyRecommendation>.Fail(ErrIllegalTransition, "仅已发布/已回复的建议可登记回复，当前：" + r.Status);
            }

            RecommendationStatus before = r.Status;
            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "safetyrec.response", InvestigationAuditCategories.SafetyRec,
                "登记回复 " + id, before.ToString(), RecommendationStatus.Responded + "；回复方=" + party));
            r.ResponseList.Add(new RecommendationResponse(party, text, utc));
            if (before == RecommendationStatus.Issued)
            {
                r.HistoryList.Add(new RecommendationTransition(before, RecommendationStatus.Responded, operatorName, utc, "回复方=" + party));
                r.Status = RecommendationStatus.Responded;
            }

            return Result<SafetyRecommendation>.Ok(r);
        }

        public Result<SafetyRecommendation> MarkImplemented(string id, string operatorName, DateTimeOffset utc, string note = null)
        {
            return Transition(id, RecommendationStatus.Implemented, operatorName, utc, note);
        }

        public Result<SafetyRecommendation> MarkNotAdopted(string id, string operatorName, DateTimeOffset utc, string reason)
        {
            return Transition(id, RecommendationStatus.NotAdopted, operatorName, utc, reason);
        }

        public Result<SafetyRecommendation> Close(string id, string operatorName, DateTimeOffset utc, string note = null)
        {
            return Transition(id, RecommendationStatus.Closed, operatorName, utc, note);
        }

        /// <summary>
        /// 通用状态转换。非法转换返回 <see cref="ErrIllegalTransition"/> 且不写审计、不改状态。
        /// 进入“已回复”必须走 <see cref="RecordResponse"/>；“未采纳”必须写明理由。
        /// </summary>
        public Result<SafetyRecommendation> Transition(string id, RecommendationStatus to, string operatorName, DateTimeOffset utc, string note = null)
        {
            SafetyRecommendation r = Get(id);
            if (r == null)
            {
                return Result<SafetyRecommendation>.Fail(ErrNotFound, "建议不存在：" + (id ?? "(null)"));
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (!CanTransition(r.Status, to))
            {
                return Result<SafetyRecommendation>.Fail(ErrIllegalTransition, "非法状态转换：" + r.Status + " → " + to);
            }

            if (to == RecommendationStatus.Responded)
            {
                return Result<SafetyRecommendation>.Fail(ErrIllegalTransition, "进入已回复须通过 RecordResponse 登记回复内容");
            }

            if (to == RecommendationStatus.NotAdopted && string.IsNullOrWhiteSpace(note))
            {
                return Result<SafetyRecommendation>.Fail(ErrInvalidArgument, "未采纳必须写明理由");
            }

            RecommendationStatus from = r.Status;
            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "safetyrec.transition", InvestigationAuditCategories.SafetyRec,
                "建议状态变更 " + id, from.ToString(), to + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            r.HistoryList.Add(new RecommendationTransition(from, to, operatorName, utc, note));
            r.Status = to;
            if (to == RecommendationStatus.Implemented)
            {
                r.ProgressPct = 100;
            }

            if ((to == RecommendationStatus.Implemented || to == RecommendationStatus.Closed) && !string.IsNullOrEmpty(note))
            {
                r.VerificationNote = note;
            }

            return Result<SafetyRecommendation>.Ok(r);
        }
    }
}
