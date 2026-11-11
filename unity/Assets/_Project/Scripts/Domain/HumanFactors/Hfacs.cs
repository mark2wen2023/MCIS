using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.HumanFactors
{
    /// <summary>HFACS-MA 四层 + 外部因素层（Chauvin 2013 / Celik &amp; Cebi 2009 体系，海上 adapted）。</summary>
    public enum HfacsLayer
    {
        /// <summary>不安全行为（L1）。</summary>
        UnsafeActs = 0,

        /// <summary>不安全行为的前提条件（L2）。</summary>
        Preconditions = 1,

        /// <summary>不安全的监督（L3）。</summary>
        UnsafeSupervision = 2,

        /// <summary>组织影响（L4）。</summary>
        OrganizationalInfluences = 3,

        /// <summary>外部因素（船级社/设计/航道/助航/经济压力等，HFACS-MA 扩展层）。</summary>
        ExternalFactors = 4
    }

    /// <summary>HFACS 分类节点。</summary>
    public sealed class HfacsCategory
    {
        /// <summary>分类码，如 UA-ERR-DEC。</summary>
        public string Code { get; }

        /// <summary>显示名（中文）。</summary>
        public string Name { get; }

        /// <summary>所属层。</summary>
        public HfacsLayer Layer { get; }

        /// <summary>父分类码；层根节点为 null。</summary>
        public string ParentCode { get; }

        public HfacsCategory(string code, string name, HfacsLayer layer, string parentCode)
        {
            Code = code ?? string.Empty;
            Name = name ?? string.Empty;
            Layer = layer;
            ParentCode = parentCode;
        }
    }

    /// <summary>证据强度。</summary>
    public enum EvidenceStrength
    {
        /// <summary>强：有客观记录（VDR/AIS/日志）直接支撑。</summary>
        Strong = 0,

        /// <summary>中等：有多方陈述或间接记录支撑。</summary>
        Moderate = 1,

        /// <summary>待核实：仅单一来源或推断，尚无证据链接。</summary>
        ToBeVerified = 2
    }

    /// <summary>HFACS 结论复核状态（W18-D05）。只有 Confirmed 计入 ByLayer/CountByLayer。</summary>
    public enum HfacsReviewStatus
    {
        /// <summary>草稿：智能体/调查员提出，尚未人工确认，不生效。</summary>
        Draft = 0,

        /// <summary>已确认：调查员确认，生效。</summary>
        Confirmed = 1,

        /// <summary>已驳回（必须写理由），不计入任何统计。</summary>
        Rejected = 2
    }

    /// <summary>HFACS 结论来源。</summary>
    public enum HfacsOrigin
    {
        /// <summary>人员/作业智能体给出的分类建议。</summary>
        Agent = 0,

        /// <summary>调查员手工录入。</summary>
        Investigator = 1
    }

    /// <summary>人为因素模块的审计类别与动作名。</summary>
    public static class HumanFactorsAudit
    {
        /// <summary>审计类别（audit-event.schema.json 的 category 为自由字符串）。</summary>
        public const string Category = "HumanFactors";
    }

    /// <summary>一条 HFACS 分析结论。</summary>
    public sealed class HfacsFinding
    {
        /// <summary>结论编号（分析内唯一）。</summary>
        public string Id { get; }

        /// <summary>分类码。</summary>
        public string CategoryCode { get; }

        /// <summary>所属层。</summary>
        public HfacsLayer Layer { get; }

        /// <summary>描述。</summary>
        public string Description { get; }

        /// <summary>证据强度。</summary>
        public EvidenceStrength Strength { get; }

        /// <summary>支撑证据编号（保管链登记过的）。</summary>
        public IReadOnlyList<string> EvidenceIds { get; }

        /// <summary>关联的 ECFC 因果图节点编号。</summary>
        public IReadOnlyList<string> EcfcNodeIds { get; }

        /// <summary>复核状态（新结论一律 Draft）。</summary>
        public HfacsReviewStatus ReviewStatus { get; internal set; }

        /// <summary>来源（智能体 / 调查员）。</summary>
        public HfacsOrigin Origin { get; }

        /// <summary>确认/驳回人；未复核为 null。</summary>
        public string ReviewedBy { get; internal set; }

        /// <summary>确认/驳回时刻；未复核为 null。</summary>
        public DateTimeOffset? ReviewedUtc { get; internal set; }

        /// <summary>复核备注（驳回理由必填）。</summary>
        public string ReviewNote { get; internal set; }

        /// <summary>B3：保管链状态为 Mismatch/NeedsReview 的证据 id（仅 Moderate/ToBeVerified 可带；Strong 不允许）。</summary>
        public IReadOnlyList<string> EvidenceWarnings { get; }

        public HfacsFinding(
            string id,
            string categoryCode,
            HfacsLayer layer,
            string description,
            EvidenceStrength strength,
            IReadOnlyList<string> evidenceIds,
            IReadOnlyList<string> ecfcNodeIds)
        {
            Id = id ?? string.Empty;
            CategoryCode = categoryCode ?? string.Empty;
            Layer = layer;
            Description = description ?? string.Empty;
            Strength = strength;
            EvidenceIds = evidenceIds ?? new string[0];
            EcfcNodeIds = ecfcNodeIds ?? new string[0];
            ReviewStatus = HfacsReviewStatus.Draft;
            Origin = HfacsOrigin.Agent;
            ReviewNote = string.Empty;
            EvidenceWarnings = new string[0];
        }

        public HfacsFinding(
            string id,
            string categoryCode,
            HfacsLayer layer,
            string description,
            EvidenceStrength strength,
            IReadOnlyList<string> evidenceIds,
            IReadOnlyList<string> ecfcNodeIds,
            HfacsOrigin origin,
            IReadOnlyList<string> evidenceWarnings)
            : this(id, categoryCode, layer, description, strength, evidenceIds, ecfcNodeIds)
        {
            Origin = origin;
            EvidenceWarnings = evidenceWarnings ?? new string[0];
        }
    }

    /// <summary>
    /// HFACS-MA 只读分类树。体系参照 Chauvin et al. 2013（HFACS-MA）与 Celik &amp; Cebi 2009；
    /// 分类码为本项目自定（UA/PC/US/OI/EF 前缀 + 层内分组）。示例数据均为虚构。
    /// </summary>
    public static class HfacsMaTaxonomy
    {
        private static readonly List<HfacsCategory> AllList = Build();
        private static readonly Dictionary<string, HfacsCategory> ByCode = BuildIndex();
        private static readonly Dictionary<string, List<HfacsCategory>> Children = BuildChildren();

        /// <summary>全部分类节点（定义顺序）。</summary>
        public static IReadOnlyList<HfacsCategory> All
        {
            get { return AllList; }
        }

        /// <summary>按分类码取节点；未知返回 null。</summary>
        public static HfacsCategory Get(string code)
        {
            if (code == null)
            {
                return null;
            }

            HfacsCategory c;
            return ByCode.TryGetValue(code, out c) ? c : null;
        }

        /// <summary>某分类码的直接子节点；未知或无子返回空表。</summary>
        public static IReadOnlyList<HfacsCategory> ChildrenOf(string code)
        {
            if (code == null)
            {
                return new HfacsCategory[0];
            }

            List<HfacsCategory> list;
            return Children.TryGetValue(code, out list) ? (IReadOnlyList<HfacsCategory>)list : new HfacsCategory[0];
        }

        /// <summary>分类码所属层；未知返回 null。</summary>
        public static HfacsLayer? LayerOf(string code)
        {
            HfacsCategory c = Get(code);
            return c == null ? (HfacsLayer?)null : c.Layer;
        }

        private static List<HfacsCategory> Build()
        {
            var l = new List<HfacsCategory>();
            // L1 不安全行为
            l.Add(new HfacsCategory("UA", "不安全行为", HfacsLayer.UnsafeActs, null));
            l.Add(new HfacsCategory("UA-ERR", "差错", HfacsLayer.UnsafeActs, "UA"));
            l.Add(new HfacsCategory("UA-ERR-DEC", "决策差错", HfacsLayer.UnsafeActs, "UA-ERR"));
            l.Add(new HfacsCategory("UA-ERR-SKL", "技能差错", HfacsLayer.UnsafeActs, "UA-ERR"));
            l.Add(new HfacsCategory("UA-ERR-PER", "感知差错", HfacsLayer.UnsafeActs, "UA-ERR"));
            l.Add(new HfacsCategory("UA-VIO", "违规", HfacsLayer.UnsafeActs, "UA"));
            l.Add(new HfacsCategory("UA-VIO-ROU", "习惯性违规", HfacsLayer.UnsafeActs, "UA-VIO"));
            l.Add(new HfacsCategory("UA-VIO-EXC", "偶然违规", HfacsLayer.UnsafeActs, "UA-VIO"));
            // L2 前提条件
            l.Add(new HfacsCategory("PC", "不安全行为的前提条件", HfacsLayer.Preconditions, null));
            l.Add(new HfacsCategory("PC-ENV", "环境条件", HfacsLayer.Preconditions, "PC"));
            l.Add(new HfacsCategory("PC-ENV-PHY", "物理环境", HfacsLayer.Preconditions, "PC-ENV"));
            l.Add(new HfacsCategory("PC-ENV-TEC", "技术环境", HfacsLayer.Preconditions, "PC-ENV"));
            l.Add(new HfacsCategory("PC-OPR", "操作者条件", HfacsLayer.Preconditions, "PC"));
            l.Add(new HfacsCategory("PC-OPR-MEN", "心理状态", HfacsLayer.Preconditions, "PC-OPR"));
            l.Add(new HfacsCategory("PC-OPR-PHY", "生理状态", HfacsLayer.Preconditions, "PC-OPR"));
            l.Add(new HfacsCategory("PC-OPR-LIM", "身体/能力局限", HfacsLayer.Preconditions, "PC-OPR"));
            l.Add(new HfacsCategory("PC-PER", "人员因素", HfacsLayer.Preconditions, "PC"));
            l.Add(new HfacsCategory("PC-PER-BRM", "驾驶台资源管理 / 班组协作缺陷", HfacsLayer.Preconditions, "PC-PER"));
            l.Add(new HfacsCategory("PC-PER-RDY", "准备状态不足", HfacsLayer.Preconditions, "PC-PER"));
            // L3 不安全的监督
            l.Add(new HfacsCategory("US", "不安全的监督", HfacsLayer.UnsafeSupervision, null));
            l.Add(new HfacsCategory("US-INADEQ", "监督不充分", HfacsLayer.UnsafeSupervision, "US"));
            l.Add(new HfacsCategory("US-PLAN", "计划/配员不当", HfacsLayer.UnsafeSupervision, "US"));
            l.Add(new HfacsCategory("US-FAIL-CORR", "未纠正已发现问题", HfacsLayer.UnsafeSupervision, "US"));
            l.Add(new HfacsCategory("US-VIO", "监督违规", HfacsLayer.UnsafeSupervision, "US"));
            // L4 组织影响
            l.Add(new HfacsCategory("OI", "组织影响", HfacsLayer.OrganizationalInfluences, null));
            l.Add(new HfacsCategory("OI-RES", "资源管理", HfacsLayer.OrganizationalInfluences, "OI"));
            l.Add(new HfacsCategory("OI-CLIM", "组织氛围", HfacsLayer.OrganizationalInfluences, "OI"));
            l.Add(new HfacsCategory("OI-PROC", "组织过程", HfacsLayer.OrganizationalInfluences, "OI"));
            // L5 外部因素（HFACS-MA 扩展）
            l.Add(new HfacsCategory("EF", "外部因素", HfacsLayer.ExternalFactors, null));
            l.Add(new HfacsCategory("EF-REG", "法规/监管（港口国、船旗国检查缺口）", HfacsLayer.ExternalFactors, "EF"));
            l.Add(new HfacsCategory("EF-DES", "设计/航道/助航设施", HfacsLayer.ExternalFactors, "EF"));
            l.Add(new HfacsCategory("EF-ECO", "经济与商业压力", HfacsLayer.ExternalFactors, "EF"));
            return l;
        }

        private static Dictionary<string, HfacsCategory> BuildIndex()
        {
            var d = new Dictionary<string, HfacsCategory>(StringComparer.Ordinal);
            for (int i = 0; i < AllList.Count; i++)
            {
                d[AllList[i].Code] = AllList[i];
            }

            return d;
        }

        private static Dictionary<string, List<HfacsCategory>> BuildChildren()
        {
            var d = new Dictionary<string, List<HfacsCategory>>(StringComparer.Ordinal);
            for (int i = 0; i < AllList.Count; i++)
            {
                HfacsCategory c = AllList[i];
                if (c.ParentCode == null)
                {
                    continue;
                }

                List<HfacsCategory> list;
                if (!d.TryGetValue(c.ParentCode, out list))
                {
                    list = new List<HfacsCategory>();
                    d[c.ParentCode] = list;
                }

                list.Add(c);
            }

            return d;
        }
    }

    /// <summary>
    /// 一次针对某对象（船员/班组/船）的 HFACS 分析。只追加；校验见 <see cref="AddFinding"/>。
    /// </summary>
    public sealed class HfacsAnalysis
    {
        public const string ErrUnknownCategory = "hf_unknown_category";
        public const string ErrMissingEvidence = "hf_missing_evidence";
        public const string ErrMissingEcfcLink = "hf_missing_ecfc_link";
        public const string ErrUnknownEvidence = "hf_unknown_evidence";
        public const string ErrDuplicateFinding = "hf_duplicate_finding";
        public const string ErrInvalidArgument = "hf_invalid_argument";

        /// <summary>B4：Strong/Moderate 结论挂在层根或中间分组码上。</summary>
        public const string ErrNonLeafCategory = "hf_non_leaf_category";

        /// <summary>B3：Strong 结论引用了保管链状态为 Mismatch/NeedsReview 的证据。</summary>
        public const string ErrEvidenceUnreliable = "hf_evidence_unreliable";

        /// <summary>D05：确认/驳回的结论不存在。</summary>
        public const string ErrUnknownFinding = "hf_unknown_finding";

        /// <summary>D05：只有 Draft 可确认/驳回。</summary>
        public const string ErrInvalidState = "hf_invalid_state";

        public const string ActionConfirm = "hf.finding.confirm";
        public const string ActionReject = "hf.finding.reject";

        private readonly List<HfacsFinding> _findings = new List<HfacsFinding>();
        private readonly HashSet<string> _ids = new HashSet<string>(StringComparer.Ordinal);

        /// <summary>分析对象（如值班驾驶员姓名）。</summary>
        public string Subject { get; }

        public HfacsAnalysis(string subject)
            : this(subject, null)
        {
        }

        /// <summary>audit 为 null 时用内部 <see cref="InMemoryInvestigationAuditSink"/>（经 <see cref="Audit"/> 取出落盘）。</summary>
        public HfacsAnalysis(string subject, IInvestigationAuditSink audit)
        {
            Subject = subject ?? string.Empty;
            Audit = audit ?? new InMemoryInvestigationAuditSink();
        }

        /// <summary>确认/驳回的审计去向。</summary>
        public IInvestigationAuditSink Audit { get; }

        /// <summary>已录入结论（录入顺序）。</summary>
        public IReadOnlyList<HfacsFinding> Findings
        {
            get { return new List<HfacsFinding>(_findings).AsReadOnly(); } // W18.1 / D07：只读副本，不暴露内部 List
        }

        /// <summary>
        /// 追加一条结论。规则：
        /// 分类码必须为已知分类（未知 → <see cref="ErrUnknownCategory"/>）；
        /// Strong/Moderate 必须至少 1 条证据 id 与至少 1 个 ECFC 节点 id
        /// （<see cref="ErrMissingEvidence"/> / <see cref="ErrMissingEcfcLink"/>）；
        /// ToBeVerified 两者均可为空；传 ledger 时证据 id 必须已登记（<see cref="ErrUnknownEvidence"/>）；
        /// id 重复（<see cref="ErrDuplicateFinding"/>）。
        /// </summary>
        public Result<HfacsFinding> AddFinding(
            string id,
            string categoryCode,
            string description,
            EvidenceStrength strength,
            IEnumerable<string> evidenceIds,
            IEnumerable<string> ecfcNodeIds,
            CustodyLedger ledger = null,
            HfacsOrigin origin = HfacsOrigin.Agent)
        {
            if (string.IsNullOrWhiteSpace(id))
            {
                return Result<HfacsFinding>.Fail(ErrInvalidArgument, "结论编号不能为空");
            }

            if (!Enum.IsDefined(typeof(EvidenceStrength), strength) || !Enum.IsDefined(typeof(HfacsOrigin), origin))
            {
                return Result<HfacsFinding>.Fail(ErrInvalidArgument, "未知证据强度/来源：" + (int)strength + "/" + (int)origin); // W18-D04
            }

            if (_ids.Contains(id))
            {
                return Result<HfacsFinding>.Fail(ErrDuplicateFinding, "结论编号重复：" + id);
            }

            HfacsCategory cat = HfacsMaTaxonomy.Get(categoryCode);
            if (cat == null)
            {
                return Result<HfacsFinding>.Fail(ErrUnknownCategory, "未知 HFACS 分类码：" + categoryCode);
            }

            // B4：Strong/Moderate 必须挂叶子类码；层根/分组码只允许 ToBeVerified（Weak：假设/草稿）。
            if (strength != EvidenceStrength.ToBeVerified && HfacsMaTaxonomy.ChildrenOf(categoryCode).Count > 0)
            {
                return Result<HfacsFinding>.Fail(ErrNonLeafCategory, "Strong/Moderate 结论须挂叶子类码，" + categoryCode + " 为分组码");
            }

            // 空白 id 视为未提供；去重保持顺序。
            var evList = evidenceIds == null ? new List<string>() : evidenceIds.Where(x => !string.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).ToList();
            var nodeList = ecfcNodeIds == null ? new List<string>() : ecfcNodeIds.Where(x => !string.IsNullOrWhiteSpace(x)).Distinct(StringComparer.Ordinal).ToList();

            if (strength != EvidenceStrength.ToBeVerified)
            {
                if (evList.Count == 0)
                {
                    return Result<HfacsFinding>.Fail(ErrMissingEvidence, "Strong/Moderate 结论至少需要 1 条证据");
                }

                if (nodeList.Count == 0)
                {
                    return Result<HfacsFinding>.Fail(ErrMissingEcfcLink, "Strong/Moderate 结论至少需要 1 个 ECFC 节点链接");
                }

            }

            // 传 ledger 时，凡给出的证据 id（含 ToBeVerified）都必须已登记。
            var warnings = new List<string>();
            if (ledger != null)
            {
                for (int i = 0; i < evList.Count; i++)
                {
                    if (ledger.Get(evList[i]) == null)
                    {
                        return Result<HfacsFinding>.Fail(ErrUnknownEvidence, "证据未登记：" + evList[i]);
                    }
                }

                // B3：Strong 的证据不得 Mismatch/NeedsReview；Moderate/ToBeVerified 可用但记入 EvidenceWarnings。
                string unreliable = FirstUnreliable(evList, ledger, warnings);
                if (strength == EvidenceStrength.Strong && unreliable != null)
                {
                    return Result<HfacsFinding>.Fail(ErrEvidenceUnreliable, "Strong 结论的证据保管链状态异常（" + ledger.StatusOf(unreliable) + "）：" + unreliable);
                }
            }

            var finding = new HfacsFinding(id, categoryCode, cat.Layer, description, strength, evList, nodeList, origin, warnings);
            _findings.Add(finding);
            _ids.Add(id);
            return Result<HfacsFinding>.Ok(finding);
        }

        /// <summary>
        /// 确认一条 Draft 结论（D05）。先写审计 hf.finding.confirm，审计成功才改状态。
        /// 传 ledger 时对 Strong 结论重新检查证据（B3），异常 → hf_evidence_unreliable。
        /// </summary>
        public Result<HfacsFinding> Confirm(string findingId, string investigator, DateTimeOffset utc, string note = null, CustodyLedger ledger = null)
        {
            Result<HfacsFinding> pre = PrepareReview(findingId, investigator);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            HfacsFinding f = pre.Value;
            if (ledger != null)
            {
                for (int i = 0; i < f.EvidenceIds.Count; i++)
                {
                    if (ledger.Get(f.EvidenceIds[i]) == null)
                    {
                        return Result<HfacsFinding>.Fail(ErrUnknownEvidence, "证据未登记：" + f.EvidenceIds[i]);
                    }
                }

                string unreliable = FirstUnreliable(f.EvidenceIds, ledger, null);
                if (f.Strength == EvidenceStrength.Strong && unreliable != null)
                {
                    return Result<HfacsFinding>.Fail(ErrEvidenceUnreliable, "Strong 结论的证据保管链状态异常（" + ledger.StatusOf(unreliable) + "）：" + unreliable);
                }
            }

            return ApplyReview(f, HfacsReviewStatus.Confirmed, ActionConfirm, investigator, utc, note);
        }

        /// <summary>驳回一条 Draft 结论（D05）；理由必填。先写审计 hf.finding.reject。</summary>
        public Result<HfacsFinding> Reject(string findingId, string investigator, DateTimeOffset utc, string note)
        {
            Result<HfacsFinding> pre = PrepareReview(findingId, investigator);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            if (string.IsNullOrWhiteSpace(note))
            {
                return Result<HfacsFinding>.Fail(ErrInvalidArgument, "驳回必须写理由");
            }

            return ApplyReview(pre.Value, HfacsReviewStatus.Rejected, ActionReject, investigator, utc, note);
        }

        /// <summary>待确认（Draft）结论，录入顺序。</summary>
        public IReadOnlyList<HfacsFinding> Pending()
        {
            return _findings.Where(f => f.ReviewStatus == HfacsReviewStatus.Draft).ToList();
        }

        /// <summary>按层过滤，只含已确认（Confirmed）结论。</summary>
        public IReadOnlyList<HfacsFinding> ByLayer(HfacsLayer layer)
        {
            return Filter(layer, false);
        }

        /// <summary>按层过滤，含草稿（Draft + Confirmed，不含 Rejected）。</summary>
        public IReadOnlyList<HfacsFinding> ByLayerIncludingDrafts(HfacsLayer layer)
        {
            return Filter(layer, true);
        }

        /// <summary>各层计数，只计已确认（Confirmed）结论。</summary>
        public IReadOnlyDictionary<HfacsLayer, int> CountByLayer()
        {
            return Count(false);
        }

        /// <summary>各层计数，含草稿（Draft + Confirmed，不含 Rejected）。</summary>
        public IReadOnlyDictionary<HfacsLayer, int> CountByLayerIncludingDrafts()
        {
            return Count(true);
        }

        private static bool Counts(HfacsFinding f, bool includeDrafts)
        {
            return f.ReviewStatus == HfacsReviewStatus.Confirmed || (includeDrafts && f.ReviewStatus == HfacsReviewStatus.Draft);
        }

        private IReadOnlyList<HfacsFinding> Filter(HfacsLayer layer, bool includeDrafts)
        {
            var list = new List<HfacsFinding>();
            for (int i = 0; i < _findings.Count; i++)
            {
                if (_findings[i].Layer == layer && Counts(_findings[i], includeDrafts))
                {
                    list.Add(_findings[i]);
                }
            }

            return list;
        }

        private IReadOnlyDictionary<HfacsLayer, int> Count(bool includeDrafts)
        {
            var d = new Dictionary<HfacsLayer, int>();
            foreach (HfacsLayer layer in Enum.GetValues(typeof(HfacsLayer)))
            {
                d[layer] = 0;
            }

            for (int i = 0; i < _findings.Count; i++)
            {
                if (Counts(_findings[i], includeDrafts))
                {
                    d[_findings[i].Layer]++;
                }
            }

            return d;
        }

        private Result<HfacsFinding> PrepareReview(string findingId, string investigator)
        {
            HfacsFinding f = findingId == null ? null : _findings.FirstOrDefault(x => string.Equals(x.Id, findingId, StringComparison.Ordinal));
            if (f == null)
            {
                return Result<HfacsFinding>.Fail(ErrUnknownFinding, "结论不存在：" + (findingId ?? "(null)"));
            }

            if (string.IsNullOrWhiteSpace(investigator))
            {
                return Result<HfacsFinding>.Fail(ErrInvalidArgument, "调查员不能为空");
            }

            if (f.ReviewStatus != HfacsReviewStatus.Draft)
            {
                return Result<HfacsFinding>.Fail(ErrInvalidState, "只有草稿可确认/驳回，" + f.Id + " 当前为 " + f.ReviewStatus);
            }

            return Result<HfacsFinding>.Ok(f);
        }

        private Result<HfacsFinding> ApplyReview(HfacsFinding f, HfacsReviewStatus to, string action, string investigator, DateTimeOffset utc, string note)
        {
            Audit.Append(new InvestigationAuditEntry(utc, investigator, action, HumanFactorsAudit.Category,
                (to == HfacsReviewStatus.Confirmed ? "确认" : "驳回") + " HFACS 结论 " + f.Id + "（" + f.CategoryCode + "，" + f.Strength + "，" + Subject + "）",
                f.ReviewStatus.ToString(),
                to + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            f.ReviewStatus = to;
            f.ReviewedBy = investigator;
            f.ReviewedUtc = utc;
            f.ReviewNote = note ?? string.Empty;
            return Result<HfacsFinding>.Ok(f);
        }

        /// <summary>首个 Mismatch/NeedsReview 证据 id（无则 null）；warnings 非 null 时收集全部异常 id。</summary>
        private static string FirstUnreliable(IReadOnlyList<string> evidenceIds, CustodyLedger ledger, List<string> warnings)
        {
            string first = null;
            for (int i = 0; i < evidenceIds.Count; i++)
            {
                EvidenceStatus? st = ledger.StatusOf(evidenceIds[i]);
                if (st == EvidenceStatus.Mismatch || st == EvidenceStatus.NeedsReview)
                {
                    if (first == null)
                    {
                        first = evidenceIds[i];
                    }

                    if (warnings != null)
                    {
                        warnings.Add(evidenceIds[i]);
                    }
                }
            }

            return first;
        }
    }
}
