using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Recommendations;

namespace Mcis.Domain.Systemic
{
    /// <summary>W15 系统分析错误码（全部 sys_ 前缀）。</summary>
    public static class SystemicErrors
    {
        public const string InvalidArgument = "sys_invalid_argument";
        public const string InvalidId = "sys_invalid_id";
        public const string DuplicateId = "sys_duplicate_id";
        public const string DuplicateEdge = "sys_duplicate_edge";
        public const string UnknownNode = "sys_unknown_node";
        public const string UnknownEdge = "sys_unknown_edge";
        public const string InvalidEdge = "sys_invalid_edge";
        public const string Cycle = "sys_cycle";
        public const string LevelDirection = "sys_level_direction";
        public const string OrphanThreat = "sys_orphan_threat";
        public const string OrphanConsequence = "sys_orphan_consequence";
        public const string OrphanBarrier = "sys_orphan_barrier";
        public const string IsolatedNode = "sys_isolated_node";
        public const string IsolatedController = "sys_isolated_controller";
        public const string MissingFeedback = "sys_missing_feedback";
        public const string EmptyModel = "sys_empty_model";
        public const string StrongWithoutEvidence = "sys_strong_without_evidence";
        public const string ModerateWithoutEvidence = "sys_moderate_without_evidence";
        public const string EvidenceUnreliable = "sys_evidence_unreliable";
        public const string EvidenceNeedsReview = "sys_evidence_needs_review";
        public const string UnknownEvidence = "sys_unknown_evidence";
        public const string UnknownEcfc = "sys_unknown_ecfc";
        public const string UnknownHfacs = "sys_unknown_hfacs";
        public const string UnknownRecommendation = "sys_unknown_recommendation";
        public const string UnknownRef = "sys_unknown_ref";
        public const string UnregisteredRefKind = "sys_unregistered_ref_kind";

        /// <summary>W15.2 / D05：引用未核对（未传入来源或未注册校验器），Info 级，每种 kind 汇总一条。21:25 裁定改名为 sys_ref_not_checked（统一 sys_ 前缀）。</summary>
        public const string RefNotChecked = "sys_ref_not_checked";
        public const string JsonInvalid = "sys_json_invalid";
        public const string JsonUnsupportedSchema = "sys_json_unsupported_schema";
    }

    /// <summary>引用种类（A5）。前 4 种为内置校验种类；其余可经 <see cref="SystemicRefContext.RegisterValidator"/> 注册校验器。</summary>
    public static class SystemicRefKinds
    {
        public const string Evidence = "Evidence";
        public const string Ecfc = "Ecfc";
        public const string Hfacs = "Hfacs";
        public const string Recommendation = "Recommendation";
        public const string Statement = "Statement";
        public const string ColregCheck = "ColregCheck";
        public const string DamageTrack = "DamageTrack";

        private static readonly Regex KindPattern = new Regex(@"\A[A-Z][A-Za-z0-9]{0,31}\z", RegexOptions.CultureInvariant);

        /// <summary>种类名：大写字母开头的 ASCII 字母数字，最长 32。</summary>
        public static bool IsValidKind(string kind)
        {
            return kind != null && KindPattern.IsMatch(kind);
        }

        /// <summary>内置校验种类（证据 / ECFC / HFACS / 安全建议）：上下文传了对应来源才校验，不传不报。</summary>
        public static bool IsBuiltIn(string kind)
        {
            return kind == Evidence || kind == Ecfc || kind == Hfacs || kind == Recommendation;
        }
    }

    /// <summary>带类型的引用 {Kind, Id}（A5）。</summary>
    public sealed class SystemicRef : IEquatable<SystemicRef>
    {
        public string Kind { get; }
        public string Id { get; }

        /// <summary>kind 必须满足 <see cref="SystemicRefKinds.IsValidKind"/>，id 不能为空白（去首尾空白）。否则抛 ArgumentException。</summary>
        public SystemicRef(string kind, string id)
        {
            if (!SystemicRefKinds.IsValidKind(kind))
            {
                throw new ArgumentException("引用种类无效：" + kind, nameof(kind));
            }

            if (string.IsNullOrWhiteSpace(id))
            {
                throw new ArgumentException("引用 ID 不能为空", nameof(id));
            }

            Kind = kind;
            Id = id.Trim();
        }

        public bool Equals(SystemicRef other)
        {
            return other != null && other.Kind == Kind && other.Id == Id;
        }

        public override bool Equals(object obj)
        {
            return Equals(obj as SystemicRef);
        }

        public override int GetHashCode()
        {
            return StringComparer.Ordinal.GetHashCode(Kind) * 397 ^ StringComparer.Ordinal.GetHashCode(Id);
        }

        public override string ToString()
        {
            return Kind + ":" + Id;
        }
    }

    /// <summary>
    /// 节点对外部对象的只读引用集合（A5：带类型的 {Kind, Id}）。
    /// 内置种类：证据（W3 保管链）、ECFC 节点、HFACS 发现（W18）、安全建议（W3）；
    /// 另支持询问记录陈述、COLREG 检查、损伤轨迹等任意已命名种类。
    /// 构造时去空白、去重（保持顺序）。只保存 ID，不持有、不修改被引用对象。集合对外只读（D01）。
    /// </summary>
    public sealed class SystemicRefs
    {
        public static readonly SystemicRefs None = new SystemicRefs();

        private readonly ReadOnlyCollection<SystemicRef> _all;

        public IReadOnlyList<string> EvidenceIds { get; }
        public IReadOnlyList<string> EcfcNodeIds { get; }
        public IReadOnlyList<string> HfacsFindingIds { get; }
        public IReadOnlyList<string> RecommendationIds { get; }

        /// <summary>兼容构造：四类内置引用。</summary>
        public SystemicRefs(
            IEnumerable<string> evidenceIds = null,
            IEnumerable<string> ecfcNodeIds = null,
            IEnumerable<string> hfacsFindingIds = null,
            IEnumerable<string> recommendationIds = null)
            : this(Typed(SystemicRefKinds.Evidence, evidenceIds)
                .Concat(Typed(SystemicRefKinds.Ecfc, ecfcNodeIds))
                .Concat(Typed(SystemicRefKinds.Hfacs, hfacsFindingIds))
                .Concat(Typed(SystemicRefKinds.Recommendation, recommendationIds)))
        {
        }

        /// <summary>带类型构造：null 项忽略，按 (Kind, Id) 去重并保持首次出现顺序。</summary>
        public SystemicRefs(IEnumerable<SystemicRef> refs)
        {
            var list = new List<SystemicRef>();
            var seen = new HashSet<SystemicRef>();
            foreach (SystemicRef r in refs ?? Enumerable.Empty<SystemicRef>())
            {
                if (r != null && seen.Add(r))
                {
                    list.Add(r);
                }
            }

            _all = list.AsReadOnly();
            EvidenceIds = Ids(SystemicRefKinds.Evidence);
            EcfcNodeIds = Ids(SystemicRefKinds.Ecfc);
            HfacsFindingIds = Ids(SystemicRefKinds.Hfacs);
            RecommendationIds = Ids(SystemicRefKinds.Recommendation);
        }

        /// <summary>便捷工厂：同一种类的一组 ID（空白忽略）。</summary>
        public static SystemicRefs Of(string kind, params string[] ids)
        {
            return new SystemicRefs(Typed(kind, ids));
        }

        /// <summary>全部引用（只读视图）。</summary>
        public IReadOnlyList<SystemicRef> All
        {
            get { return _all; }
        }

        /// <summary>出现过的种类（按首次出现顺序）。</summary>
        public IReadOnlyList<string> Kinds
        {
            get { return _all.Select(r => r.Kind).Distinct(StringComparer.Ordinal).ToList().AsReadOnly(); }
        }

        /// <summary>某一种类的全部 ID（只读视图）。</summary>
        public IReadOnlyList<string> Ids(string kind)
        {
            return _all.Where(r => r.Kind == kind).Select(r => r.Id).ToList().AsReadOnly();
        }

        public bool IsEmpty
        {
            get { return _all.Count == 0; }
        }

        /// <summary>返回追加了 extra 的新集合（原集合不变）。</summary>
        public SystemicRefs With(IEnumerable<SystemicRef> extra)
        {
            return new SystemicRefs(_all.Concat(extra ?? Enumerable.Empty<SystemicRef>()));
        }

        private static IEnumerable<SystemicRef> Typed(string kind, IEnumerable<string> ids)
        {
            if (ids == null)
            {
                return Enumerable.Empty<SystemicRef>();
            }

            return ids.Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => new SystemicRef(kind, x)).ToArray();
        }
    }

    /// <summary>三种模型共用的节点基类：ID、标签、证据强度、引用、可选责任方。字段只能经所属模型的 Update 方法修改（A9）。</summary>
    public abstract class SystemicElement
    {
        public string Id { get; }
        public string Label { get; internal set; }

        /// <summary>结论强度（复用 W18 的 <see cref="EvidenceStrength"/>）。Strong 与 Moderate 都必须至少引用 1 个证据 ID（A6）。</summary>
        public EvidenceStrength Strength { get; internal set; }

        public SystemicRefs Refs { get; internal set; }

        /// <summary>可选责任方 / 主体 ID（A4，如船舶、公司、机构），null 表示未指定。格式同节点 ID。</summary>
        public string ActorId { get; internal set; }

        protected SystemicElement(string id, string label, EvidenceStrength strength, SystemicRefs refs, string actorId = null)
        {
            Id = id;
            Label = label;
            Strength = strength;
            Refs = refs ?? SystemicRefs.None;
            ActorId = actorId;
        }
    }

    /// <summary>边的语义：因果（参与成环与方向规则）/ 信息流（A2，不参与成环与层间方向）。</summary>
    public enum SystemicEdgeKind
    {
        Causal = 0,
        InformationFlow = 1
    }

    /// <summary>有向边（AcciMap 为“原因→结果”，Bow-tie 为路径方向）。</summary>
    public sealed class SystemicEdge
    {
        public string FromId { get; }
        public string ToId { get; }
        public SystemicEdgeKind Kind { get; }

        public SystemicEdge(string fromId, string toId)
            : this(fromId, toId, SystemicEdgeKind.Causal)
        {
        }

        public SystemicEdge(string fromId, string toId, SystemicEdgeKind kind)
        {
            FromId = fromId;
            ToId = toId;
            Kind = kind;
        }
    }

    /// <summary>问题级别：Error 使模型不合规；Warning 只提示，不影响 <see cref="SystemicValidation.IsValid"/>。</summary>
    public enum SystemicIssueSeverity
    {
        Error = 0,
        Warning = 1,

        /// <summary>提示（W15.2）：留痕用，不影响 IsValid，也不计入 Warnings。</summary>
        Info = 2
    }

    /// <summary>一条校验问题。</summary>
    public sealed class SystemicIssue
    {
        public string Code { get; }
        public string ElementId { get; }
        public string Message { get; }
        public SystemicIssueSeverity Severity { get; }

        public SystemicIssue(string code, string elementId, string message)
            : this(code, elementId, message, SystemicIssueSeverity.Error)
        {
        }

        public SystemicIssue(string code, string elementId, string message, SystemicIssueSeverity severity)
        {
            Code = code;
            ElementId = elementId ?? string.Empty;
            Message = message ?? string.Empty;
            Severity = severity;
        }

        public bool IsWarning
        {
            get { return Severity == SystemicIssueSeverity.Warning; }
        }

        public override string ToString()
        {
            return (IsWarning ? "[警告] " : string.Empty) + Code + " [" + ElementId + "] " + Message;
        }
    }

    /// <summary>模型整体校验结果（收集全部问题，不在第一个问题处停止）。</summary>
    public sealed class SystemicValidation
    {
        public IReadOnlyList<SystemicIssue> Issues { get; }

        private static readonly IReadOnlyDictionary<string, int> NoTally = new ReadOnlyDictionary<string, int>(new Dictionary<string, int>());

        public SystemicValidation(IReadOnlyList<SystemicIssue> issues)
        {
            Issues = (issues ?? new SystemicIssue[0]).ToList().AsReadOnly();
            NotCheckedByKind = NoTally;
        }

        /// <summary>
        /// W15.2：附带“未核对引用”计数（kind → 引用次数）。每个计数 &gt; 0 的 kind 追加一条 Info 级 <see cref="SystemicErrors.RefNotChecked"/>，
        /// ElementId 为 kind，顺序：内置四类（证据、ECFC、HFACS、建议）在前，其余按序数排序。
        /// </summary>
        public SystemicValidation(IReadOnlyList<SystemicIssue> issues, IReadOnlyDictionary<string, int> notCheckedByKind)
        {
            var list = (issues ?? new SystemicIssue[0]).ToList();
            var tally = new Dictionary<string, int>(StringComparer.Ordinal);
            if (notCheckedByKind != null)
            {
                foreach (var kv in notCheckedByKind.Where(kv => kv.Value > 0))
                {
                    tally[kv.Key] = kv.Value;
                }
            }

            foreach (string kind in tally.Keys.OrderBy(KindOrder).ThenBy(k => k, StringComparer.Ordinal))
            {
                list.Add(new SystemicIssue(SystemicErrors.RefNotChecked, kind,
                    "未核对：" + kind + " 引用 " + tally[kind] + " 处（未传入来源或未注册校验器）", SystemicIssueSeverity.Info));
            }

            Issues = list.AsReadOnly();
            NotCheckedByKind = new ReadOnlyDictionary<string, int>(tally);
        }

        /// <summary>未核对的引用总次数（W15.2 / D05）。</summary>
        public int NotCheckedRefCount
        {
            get { return NotCheckedByKind.Values.Sum(); }
        }

        /// <summary>各 kind 未核对的引用次数（只读）。</summary>
        public IReadOnlyDictionary<string, int> NotCheckedByKind { get; }

        public IReadOnlyList<SystemicIssue> Infos
        {
            get { return Issues.Where(i => i.Severity == SystemicIssueSeverity.Info).ToList().AsReadOnly(); }
        }

        private static int KindOrder(string kind)
        {
            switch (kind)
            {
                case SystemicRefKinds.Evidence: return 0;
                case SystemicRefKinds.Ecfc: return 1;
                case SystemicRefKinds.Hfacs: return 2;
                case SystemicRefKinds.Recommendation: return 3;
                default: return 4;
            }
        }

        /// <summary>没有 Error 级问题即合规（警告不影响）。</summary>
        public bool IsValid
        {
            get { return !Issues.Any(i => i.Severity == SystemicIssueSeverity.Error); }
        }

        public IReadOnlyList<SystemicIssue> Errors
        {
            get { return Issues.Where(i => i.Severity == SystemicIssueSeverity.Error).ToList().AsReadOnly(); }
        }

        public IReadOnlyList<SystemicIssue> Warnings
        {
            get { return Issues.Where(i => i.Severity == SystemicIssueSeverity.Warning).ToList().AsReadOnly(); }
        }

        public bool Has(string code)
        {
            return Issues.Any(i => i.Code == code);
        }

        public IReadOnlyList<SystemicIssue> Of(string code)
        {
            return Issues.Where(i => i.Code == code).ToList().AsReadOnly();
        }

        /// <summary>合规 → Ok(true)；否则以第一条 Error 的错误码失败。</summary>
        public Result<bool> ToResult()
        {
            if (IsValid)
            {
                return Result<bool>.Ok(true);
            }

            var errors = Errors;
            return Result<bool>.Fail(errors[0].Code, string.Join("；", errors.Select(i => i.ToString())));
        }
    }

    /// <summary>
    /// 可选的引用校验上下文：传入哪个就校验哪类引用是否存在（只读查询，不修改）。
    /// 证据 → <see cref="CustodyLedger"/>（另查可靠性：Strong 引用 Mismatch/NeedsReview 证据报错，Moderate 报警告）；
    /// HFACS 发现 → <see cref="HfacsAnalysis"/>（校验时实时查询，D02）；
    /// 安全建议 → <see cref="SafetyRecommendationBoard"/>；ECFC 节点 → 已知节点 ID 集合（去首尾空白）。
    /// 其他种类（陈述 / COLREG 检查 / 损伤轨迹 / 自定义）经 <see cref="RegisterValidator"/> 注册；
    /// 节点引用了未注册的非内置种类 → 警告 sys_unregistered_ref_kind。
    /// </summary>
    public sealed class SystemicRefContext
    {
        private readonly CustodyLedger _ledger;
        private readonly HfacsAnalysis _hfacs;
        private readonly SafetyRecommendationBoard _board;
        private readonly HashSet<string> _ecfc;
        private readonly Dictionary<string, Func<string, bool>> _validators = new Dictionary<string, Func<string, bool>>(StringComparer.Ordinal);

        public SystemicRefContext(
            CustodyLedger ledger = null,
            HfacsAnalysis hfacs = null,
            SafetyRecommendationBoard recommendations = null,
            IEnumerable<string> knownEcfcNodeIds = null)
        {
            _ledger = ledger;
            _hfacs = hfacs;
            _board = recommendations;
            _ecfc = knownEcfcNodeIds == null
                ? null
                : new HashSet<string>(knownEcfcNodeIds.Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => x.Trim()), StringComparer.Ordinal);
        }

        /// <summary>
        /// 为非内置种类注册存在性校验器（只读查询）。同一种类再次注册会替换。
        /// 种类名无效、为内置种类或 exists 为 null → sys_invalid_argument。
        /// </summary>
        public Result<bool> RegisterValidator(string kind, Func<string, bool> exists)
        {
            if (!SystemicRefKinds.IsValidKind(kind) || SystemicRefKinds.IsBuiltIn(kind) || exists == null)
            {
                return Result<bool>.Fail(SystemicErrors.InvalidArgument, "无法注册引用校验器：" + kind);
            }

            _validators[kind] = exists;
            return Result<bool>.Ok(true);
        }

        public bool HasValidator(string kind)
        {
            return kind != null && _validators.ContainsKey(kind);
        }

        internal void Check(SystemicElement e, List<SystemicIssue> issues, Dictionary<string, int> notChecked)
        {
            SystemicRefs r = e.Refs;
            if (_ledger == null)
            {
                SystemicRules.Tally(notChecked, SystemicRefKinds.Evidence, r.EvidenceIds.Count);
            }
            else
            {
                foreach (string id in r.EvidenceIds)
                {
                    EvidenceStatus? status = _ledger.StatusOf(id);
                    if (status == null)
                    {
                        issues.Add(new SystemicIssue(SystemicErrors.UnknownEvidence, e.Id, "证据未在保管链登记：" + id));
                    }
                    else if (status == EvidenceStatus.Mismatch || status == EvidenceStatus.NeedsReview)
                    {
                        if (e.Strength == EvidenceStrength.Strong)
                        {
                            issues.Add(new SystemicIssue(SystemicErrors.EvidenceUnreliable, e.Id, "Strong 结论引用了不可靠证据（" + status + "）：" + id));
                        }
                        else if (e.Strength == EvidenceStrength.Moderate)
                        {
                            issues.Add(new SystemicIssue(SystemicErrors.EvidenceNeedsReview, e.Id, "Moderate 结论引用了待复核证据（" + status + "）：" + id, SystemicIssueSeverity.Warning));
                        }
                    }
                }
            }

            if (_ecfc == null)
            {
                SystemicRules.Tally(notChecked, SystemicRefKinds.Ecfc, r.EcfcNodeIds.Count);
            }
            else
            {
                foreach (string id in r.EcfcNodeIds.Where(id => !_ecfc.Contains(id)))
                {
                    issues.Add(new SystemicIssue(SystemicErrors.UnknownEcfc, e.Id, "ECFC 节点不存在：" + id));
                }
            }

            if (_hfacs == null)
            {
                SystemicRules.Tally(notChecked, SystemicRefKinds.Hfacs, r.HfacsFindingIds.Count);
            }
            else
            {
                foreach (string id in r.HfacsFindingIds.Where(id => !_hfacs.Findings.Any(f => f.Id == id)))
                {
                    issues.Add(new SystemicIssue(SystemicErrors.UnknownHfacs, e.Id, "HFACS 发现不存在：" + id));
                }
            }

            if (_board == null)
            {
                SystemicRules.Tally(notChecked, SystemicRefKinds.Recommendation, r.RecommendationIds.Count);
            }
            else
            {
                foreach (string id in r.RecommendationIds.Where(id => _board.Get(id) == null))
                {
                    issues.Add(new SystemicIssue(SystemicErrors.UnknownRecommendation, e.Id, "安全建议不存在：" + id));
                }
            }

            foreach (string kind in r.Kinds.Where(k => !SystemicRefKinds.IsBuiltIn(k)))
            {
                Func<string, bool> exists;
                if (_validators.TryGetValue(kind, out exists))
                {
                    foreach (string id in r.Ids(kind).Where(id => !exists(id)))
                    {
                        issues.Add(new SystemicIssue(SystemicErrors.UnknownRef, e.Id, kind + " 引用不存在：" + id));
                    }
                }
                else
                {
                    issues.Add(new SystemicIssue(SystemicErrors.UnregisteredRefKind, e.Id, "引用种类未注册校验器，未核对：" + kind, SystemicIssueSeverity.Warning));
                    SystemicRules.Tally(notChecked, kind, r.Ids(kind).Count);
                }
            }
        }
    }

    /// <summary>ID/元素校验与图算法的内部工具。</summary>
    internal static class SystemicRules
    {
        private static readonly Regex IdPattern = new Regex(@"\A[A-Za-z0-9][A-Za-z0-9._-]{0,63}\z", RegexOptions.CultureInvariant); // \z：拒绝末尾换行（.NET 的 $ 会放过 "x\n"）；显式 ASCII 字符类，不用 \d（会匹配非 ASCII 数字）

        public static bool IsValidId(string id)
        {
            return id != null && IdPattern.IsMatch(id);
        }

        /// <summary>新增 / 修改节点的公共校验：ID 格式、标签非空、强度枚举有效、Strong 与 Moderate 必须有证据（A6）、责任方 ID 格式（A4）。</summary>
        public static Result<bool> CheckElement(string id, string label, EvidenceStrength strength, SystemicRefs refs, string actorId = null)
        {
            if (!IsValidId(id))
            {
                return Result<bool>.Fail(SystemicErrors.InvalidId, "ID 无效（字母数字开头，可含 . _ -，最长 64）：" + id);
            }

            if (string.IsNullOrWhiteSpace(label))
            {
                return Result<bool>.Fail(SystemicErrors.InvalidArgument, "标签不能为空：" + id);
            }

            if (!Enum.IsDefined(typeof(EvidenceStrength), strength))
            {
                return Result<bool>.Fail(SystemicErrors.InvalidArgument, "未知证据强度：" + (int)strength);
            }

            string evidenceCode = EvidenceRuleCode(strength, refs);
            if (evidenceCode != null)
            {
                return Result<bool>.Fail(evidenceCode, strength + " 结论必须至少引用 1 个证据 ID：" + id);
            }

            if (actorId != null && !IsValidId(actorId))
            {
                return Result<bool>.Fail(SystemicErrors.InvalidId, "责任方 ID 无效：" + actorId);
            }

            return Result<bool>.Ok(true);
        }

        /// <summary>Strong/Moderate 无证据时返回对应错误码，否则 null。</summary>
        public static string EvidenceRuleCode(EvidenceStrength strength, SystemicRefs refs)
        {
            bool noEvidence = refs == null || refs.EvidenceIds.Count == 0;
            if (!noEvidence)
            {
                return null;
            }

            if (strength == EvidenceStrength.Strong)
            {
                return SystemicErrors.StrongWithoutEvidence;
            }

            return strength == EvidenceStrength.Moderate ? SystemicErrors.ModerateWithoutEvidence : null;
        }

        /// <summary>按 A9 更新节点公共字段：未给出的字段保持原值；校验通过才写入。</summary>
        public static Result<bool> ApplyUpdate(SystemicElement e, string label, EvidenceStrength? strength, SystemicRefs refs, string actorId, bool clearActor)
        {
            string newLabel = label ?? e.Label;
            EvidenceStrength newStrength = strength ?? e.Strength;
            SystemicRefs newRefs = refs ?? e.Refs;
            string newActor = clearActor ? null : (actorId ?? e.ActorId);
            Result<bool> ok = CheckElement(e.Id, newLabel, newStrength, newRefs, newActor);
            if (!ok.IsSuccess)
            {
                return ok;
            }

            e.Label = newLabel;
            e.Strength = newStrength;
            e.Refs = newRefs;
            e.ActorId = newActor;
            return Result<bool>.Ok(true);
        }

        public static Result<T> Fail<T>(Result<bool> r)
        {
            return Result<T>.Fail(r.ErrorCode, r.ErrorMessage);
        }

        /// <summary>邻接表上从 from 出发能否到达 to（含 from == to）。</summary>
        public static bool Reaches(IReadOnlyDictionary<string, List<string>> adj, string from, string to)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            var stack = new Stack<string>();
            stack.Push(from);
            while (stack.Count > 0)
            {
                string n = stack.Pop();
                if (n == to)
                {
                    return true;
                }

                if (!seen.Add(n))
                {
                    continue;
                }

                List<string> next;
                if (adj.TryGetValue(n, out next))
                {
                    foreach (string m in next)
                    {
                        stack.Push(m);
                    }
                }
            }

            return false;
        }

        /// <summary>从 start 出发可达的全部节点（含 start）。</summary>
        public static HashSet<string> ReachableFrom(IReadOnlyDictionary<string, List<string>> adj, IEnumerable<string> starts)
        {
            var seen = new HashSet<string>(StringComparer.Ordinal);
            var stack = new Stack<string>(starts);
            while (stack.Count > 0)
            {
                string n = stack.Pop();
                if (!seen.Add(n))
                {
                    continue;
                }

                List<string> next;
                if (adj.TryGetValue(n, out next))
                {
                    foreach (string m in next)
                    {
                        stack.Push(m);
                    }
                }
            }

            return seen;
        }

        public static Dictionary<string, List<string>> BuildAdj(IEnumerable<SystemicEdge> edges)
        {
            var adj = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            foreach (SystemicEdge e in edges)
            {
                AddEdge(adj, e.FromId, e.ToId);
            }

            return adj;
        }

        public static void AddEdge(Dictionary<string, List<string>> adj, string from, string to)
        {
            List<string> list;
            if (!adj.TryGetValue(from, out list))
            {
                list = new List<string>();
                adj[from] = list;
            }

            list.Add(to);
        }

        public static Dictionary<string, List<string>> Reverse(IReadOnlyDictionary<string, List<string>> adj)
        {
            var rev = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            foreach (var kv in adj)
            {
                foreach (string to in kv.Value)
                {
                    AddEdge(rev, to, kv.Key);
                }
            }

            return rev;
        }

        /// <summary>累加未核对引用次数。</summary>
        public static void Tally(Dictionary<string, int> notChecked, string kind, int count)
        {
            if (count > 0)
            {
                int n;
                notChecked.TryGetValue(kind, out n);
                notChecked[kind] = n + count;
            }
        }

        /// <summary>逐元素校验证据规则与引用；ctx 为 null 时不核对引用，全部计入未核对（W15.2）。</summary>
        public static void CheckElements(IEnumerable<SystemicElement> elements, SystemicRefContext ctx, List<SystemicIssue> issues, Dictionary<string, int> notChecked)
        {
            foreach (SystemicElement e in elements)
            {
                // 防御：反序列化或子类绕过时再查一次 Strong / Moderate 证据规则（A6）。
                string code = EvidenceRuleCode(e.Strength, e.Refs);
                if (code != null)
                {
                    issues.Add(new SystemicIssue(code, e.Id, e.Strength + " 结论没有证据"));
                }

                if (ctx != null)
                {
                    ctx.Check(e, issues, notChecked);
                }
                else
                {
                    foreach (string kind in e.Refs.Kinds)
                    {
                        Tally(notChecked, kind, e.Refs.Ids(kind).Count);
                    }
                }
            }
        }
    }
}
