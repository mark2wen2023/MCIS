using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.HumanFactors;

namespace Mcis.Domain.Systemic
{
    public enum BowTieElementKind
    {
        Threat = 0,
        PreventionBarrier = 1,
        TopEvent = 2,
        MitigationBarrier = 3,
        Consequence = 4,
        EscalationFactor = 5
    }

    /// <summary>屏障状态：有效 / 失效 / 缺失 / 未知 / 部分有效（D04，追加在末尾以保持既有数值）。</summary>
    public enum BarrierState
    {
        Effective = 0,
        Failed = 1,
        Missing = 2,
        Unknown = 3,
        Degraded = 4
    }

    /// <summary>Bow-tie 节点。屏障带 <see cref="State"/>；升级因素带 <see cref="BarrierId"/>（它削弱的屏障）。</summary>
    public sealed class BowTieElement : SystemicElement
    {
        public BowTieElementKind Kind { get; }

        /// <summary>仅屏障有值。经 <see cref="BowTieModel.SetBarrierState"/> 修改。</summary>
        public BarrierState? State { get; internal set; }

        /// <summary>仅升级因素有值：被削弱的屏障 ID。</summary>
        public string BarrierId { get; }

        internal BowTieElement(string id, string label, BowTieElementKind kind, EvidenceStrength strength, SystemicRefs refs, BarrierState? state, string barrierId, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            Kind = kind;
            State = state;
            BarrierId = barrierId;
        }

        public bool IsBarrier
        {
            get { return Kind == BowTieElementKind.PreventionBarrier || Kind == BowTieElementKind.MitigationBarrier; }
        }
    }

    /// <summary>
    /// Bow-tie（领结图）：威胁 →（预防屏障）→ 顶事件 →（减缓屏障）→ 后果；升级因素挂在屏障上。
    /// 路径用有向边表示，允许的边：
    /// 威胁→威胁（A1 威胁链）/ 威胁→预防屏障 / 威胁→顶事件 / 预防屏障→预防屏障 / 预防屏障→顶事件 /
    /// 顶事件→减缓屏障 / 顶事件→后果 / 减缓屏障→减缓屏障 / 减缓屏障→后果。
    /// 威胁链规则（A1）：一个威胁要么只指向其他威胁（前驱），要么只指向屏障/顶事件（链末威胁），不得两者兼有。
    /// 全图不得成环。整体校验见 <see cref="Validate"/>。
    /// </summary>
    public sealed class BowTieModel
    {
        private readonly List<BowTieElement> _elements = new List<BowTieElement>();
        private readonly Dictionary<string, BowTieElement> _byId = new Dictionary<string, BowTieElement>(StringComparer.Ordinal);
        private readonly List<SystemicEdge> _edges = new List<SystemicEdge>();
        private Dictionary<string, List<string>> _adj = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        public string Id { get; }

        /// <summary>危险源（如“狭窄航道·雾中双向通航”）。</summary>
        public string Hazard { get; }

        public BowTieElement TopEvent { get; }

        private BowTieModel(string id, string hazard, BowTieElement top)
        {
            Id = id;
            Hazard = hazard;
            TopEvent = top;
            _elements.Add(top);
            _byId[top.Id] = top;
        }

        /// <summary>创建模型。顶事件默认强度为 ToBeVerified（A6：Moderate/Strong 需同时给证据引用）。</summary>
        public static Result<BowTieModel> Create(string id, string hazard, string topEventId, string topEventLabel, EvidenceStrength topStrength = EvidenceStrength.ToBeVerified, SystemicRefs topRefs = null, string topActorId = null)
        {
            if (!SystemicRules.IsValidId(id))
            {
                return Result<BowTieModel>.Fail(SystemicErrors.InvalidId, "模型 ID 无效：" + id);
            }

            if (string.IsNullOrWhiteSpace(hazard))
            {
                return Result<BowTieModel>.Fail(SystemicErrors.InvalidArgument, "危险源不能为空");
            }

            Result<bool> ok = SystemicRules.CheckElement(topEventId, topEventLabel, topStrength, topRefs, topActorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<BowTieModel>(ok);
            }

            var top = new BowTieElement(topEventId, topEventLabel, BowTieElementKind.TopEvent, topStrength, topRefs, null, null, topActorId);
            return Result<BowTieModel>.Ok(new BowTieModel(id, hazard, top));
        }

        /// <summary>只读视图（D01）：强转 IList 后修改会抛 NotSupportedException。</summary>
        public IReadOnlyList<BowTieElement> Elements
        {
            get { return _elements.AsReadOnly(); }
        }

        /// <summary>只读视图（D01）。</summary>
        public IReadOnlyList<SystemicEdge> Edges
        {
            get { return _edges.AsReadOnly(); }
        }

        public BowTieElement Get(string id)
        {
            BowTieElement e;
            return id != null && _byId.TryGetValue(id, out e) ? e : null;
        }

        public IReadOnlyList<BowTieElement> OfKind(BowTieElementKind kind)
        {
            return _elements.Where(e => e.Kind == kind).ToList().AsReadOnly();
        }

        public Result<BowTieElement> AddThreat(string id, string label, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            return Add(id, label, BowTieElementKind.Threat, strength, refs, null, null, actorId);
        }

        public Result<BowTieElement> AddConsequence(string id, string label, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            return Add(id, label, BowTieElementKind.Consequence, strength, refs, null, null, actorId);
        }

        /// <summary>添加屏障。kind 只能是 PreventionBarrier / MitigationBarrier。</summary>
        public Result<BowTieElement> AddBarrier(string id, string label, BowTieElementKind kind, BarrierState state, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            if (kind != BowTieElementKind.PreventionBarrier && kind != BowTieElementKind.MitigationBarrier)
            {
                return Result<BowTieElement>.Fail(SystemicErrors.InvalidArgument, "屏障种类只能是预防或减缓：" + kind);
            }

            if (!Enum.IsDefined(typeof(BarrierState), state))
            {
                return Result<BowTieElement>.Fail(SystemicErrors.InvalidArgument, "未知屏障状态：" + (int)state);
            }

            return Add(id, label, kind, strength, refs, state, null, actorId);
        }

        /// <summary>添加升级因素（削弱某个屏障的条件）。barrierId 不存在 → sys_unknown_node；不是屏障 → sys_invalid_edge。</summary>
        public Result<BowTieElement> AddEscalationFactor(string id, string label, string barrierId, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            BowTieElement b = Get(barrierId);
            if (b == null)
            {
                return Result<BowTieElement>.Fail(SystemicErrors.UnknownNode, "升级因素指向的屏障不存在：" + barrierId);
            }

            if (!b.IsBarrier)
            {
                return Result<BowTieElement>.Fail(SystemicErrors.InvalidEdge, "升级因素只能挂在屏障上：" + barrierId);
            }

            return Add(id, label, BowTieElementKind.EscalationFactor, strength, refs, null, barrierId, actorId);
        }

        /// <summary>连接路径边。端点不存在 → sys_unknown_node；不允许的种类组合或违反威胁链规则 → sys_invalid_edge；重复 → sys_duplicate_edge；成环 → sys_cycle。</summary>
        public Result<SystemicEdge> Connect(string fromId, string toId)
        {
            BowTieElement from = Get(fromId);
            BowTieElement to = Get(toId);
            if (from == null || to == null)
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.UnknownNode, "边的端点不存在：" + fromId + " → " + toId);
            }

            if (!IsAllowed(from.Kind, to.Kind))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.InvalidEdge, "Bow-tie 不允许的边：" + from.Kind + " → " + to.Kind);
            }

            if (fromId == toId || SystemicRules.Reaches(_adj, toId, fromId))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.Cycle, "路径成环：" + fromId + " → " + toId);
            }

            if (_edges.Any(e => e.FromId == fromId && e.ToId == toId))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.DuplicateEdge, "重复的边：" + fromId + " → " + toId);
            }

            if (from.Kind == BowTieElementKind.Threat)
            {
                bool toThreat = to.Kind == BowTieElementKind.Threat;
                bool conflict = _edges.Any(e => e.FromId == fromId && (Get(e.ToId).Kind == BowTieElementKind.Threat) != toThreat);
                if (conflict)
                {
                    return Result<SystemicEdge>.Fail(
                        SystemicErrors.InvalidEdge,
                        "威胁链中只有最末一个威胁连向屏障/顶事件（A1）：" + fromId + " → " + toId);
                }
            }

            var edge = new SystemicEdge(fromId, toId);
            _edges.Add(edge);
            SystemicRules.AddEdge(_adj, fromId, toId);
            return Result<SystemicEdge>.Ok(edge);
        }

        /// <summary>删除一条边（A9）。不存在 → sys_unknown_edge。</summary>
        public Result<bool> Disconnect(string fromId, string toId)
        {
            int i = _edges.FindIndex(e => e.FromId == fromId && e.ToId == toId);
            if (i < 0)
            {
                return Result<bool>.Fail(SystemicErrors.UnknownEdge, "边不存在：" + fromId + " → " + toId);
            }

            _edges.RemoveAt(i);
            _adj = SystemicRules.BuildAdj(_edges);
            return Result<bool>.Ok(true);
        }

        /// <summary>
        /// 删除节点（A9）：同时删除其全部边；删除屏障时一并删除挂在其上的升级因素。顶事件不可删 → sys_invalid_argument；
        /// 不存在 → sys_unknown_node。返回实际删除的节点 ID（本节点在首位）。
        /// </summary>
        public Result<IReadOnlyList<string>> RemoveElement(string id)
        {
            BowTieElement e = Get(id);
            if (e == null)
            {
                return Result<IReadOnlyList<string>>.Fail(SystemicErrors.UnknownNode, "节点不存在：" + id);
            }

            if (e.Kind == BowTieElementKind.TopEvent)
            {
                return Result<IReadOnlyList<string>>.Fail(SystemicErrors.InvalidArgument, "顶事件不能删除");
            }

            var removed = new List<string> { id };
            removed.AddRange(_elements.Where(x => x.Kind == BowTieElementKind.EscalationFactor && x.BarrierId == id).Select(x => x.Id));
            var set = new HashSet<string>(removed, StringComparer.Ordinal);
            _elements.RemoveAll(x => set.Contains(x.Id));
            foreach (string r in removed)
            {
                _byId.Remove(r);
            }

            _edges.RemoveAll(x => set.Contains(x.FromId) || set.Contains(x.ToId));
            _adj = SystemicRules.BuildAdj(_edges);
            return Result<IReadOnlyList<string>>.Ok(removed.AsReadOnly());
        }

        /// <summary>
        /// 修改节点公共字段（A9）：给出的字段才改；修改后仍须满足新增时的全部规则（含 A6 证据要求）。
        /// clearActor = true 清除责任方。不存在 → sys_unknown_node。
        /// </summary>
        public Result<BowTieElement> UpdateElement(string id, string label = null, EvidenceStrength? strength = null, SystemicRefs refs = null, string actorId = null, bool clearActor = false)
        {
            BowTieElement e = Get(id);
            if (e == null)
            {
                return Result<BowTieElement>.Fail(SystemicErrors.UnknownNode, "节点不存在：" + id);
            }

            Result<bool> ok = SystemicRules.ApplyUpdate(e, label, strength, refs, actorId, clearActor);
            return ok.IsSuccess ? Result<BowTieElement>.Ok(e) : SystemicRules.Fail<BowTieElement>(ok);
        }

        /// <summary>修改屏障状态（A9）。不是屏障 → sys_invalid_argument；未知状态 → sys_invalid_argument。</summary>
        public Result<BowTieElement> SetBarrierState(string id, BarrierState state)
        {
            BowTieElement e = Get(id);
            if (e == null)
            {
                return Result<BowTieElement>.Fail(SystemicErrors.UnknownNode, "节点不存在：" + id);
            }

            if (!e.IsBarrier || !Enum.IsDefined(typeof(BarrierState), state))
            {
                return Result<BowTieElement>.Fail(SystemicErrors.InvalidArgument, "只能为屏障设置已知状态：" + id);
            }

            e.State = state;
            return Result<BowTieElement>.Ok(e);
        }

        /// <summary>允许的边种类组合（见类注释）。</summary>
        public static bool IsAllowed(BowTieElementKind from, BowTieElementKind to)
        {
            switch (from)
            {
                case BowTieElementKind.Threat:
                    return to == BowTieElementKind.Threat || to == BowTieElementKind.PreventionBarrier || to == BowTieElementKind.TopEvent;
                case BowTieElementKind.PreventionBarrier:
                    return to == BowTieElementKind.PreventionBarrier || to == BowTieElementKind.TopEvent;
                case BowTieElementKind.TopEvent:
                case BowTieElementKind.MitigationBarrier:
                    return to == BowTieElementKind.MitigationBarrier || to == BowTieElementKind.Consequence;
                default:
                    return false;
            }
        }

        /// <summary>各屏障状态计数（每种状态都有键，含 Degraded）。</summary>
        public IReadOnlyDictionary<BarrierState, int> BarrierStats()
        {
            var d = new Dictionary<BarrierState, int>();
            foreach (BarrierState s in Enum.GetValues(typeof(BarrierState)))
            {
                d[s] = 0;
            }

            foreach (BowTieElement e in _elements.Where(x => x.IsBarrier))
            {
                d[e.State.Value]++;
            }

            return d;
        }

        /// <summary>
        /// 整体校验：
        /// 无威胁或无后果 → sys_empty_model；
        /// 威胁没有任何路径到达顶事件 → sys_orphan_threat（威胁链上的前驱威胁经链末威胁到达即可）；
        /// 后果不能从顶事件到达 → sys_orphan_consequence；
        /// 屏障不在任何“威胁→顶事件”或“顶事件→后果”路径上 → sys_orphan_barrier；
        /// 另按 ctx 校验引用存在性、Strong/Moderate 必须有证据。
        /// </summary>
        public SystemicValidation Validate(SystemicRefContext ctx = null)
        {
            var issues = new List<SystemicIssue>();
            var threats = OfKind(BowTieElementKind.Threat);
            var consequences = OfKind(BowTieElementKind.Consequence);
            if (threats.Count == 0 || consequences.Count == 0)
            {
                issues.Add(new SystemicIssue(SystemicErrors.EmptyModel, Id, "Bow-tie 至少需要 1 个威胁和 1 个后果"));
            }

            var rev = SystemicRules.Reverse(_adj);
            HashSet<string> reachTop = SystemicRules.ReachableFrom(rev, new[] { TopEvent.Id });     // 能到达顶事件的节点
            HashSet<string> fromTop = SystemicRules.ReachableFrom(_adj, new[] { TopEvent.Id });     // 顶事件可达的节点
            HashSet<string> fromThreats = SystemicRules.ReachableFrom(_adj, threats.Select(t => t.Id));
            HashSet<string> reachCons = SystemicRules.ReachableFrom(rev, consequences.Select(c => c.Id));

            foreach (BowTieElement t in threats.Where(t => !reachTop.Contains(t.Id)))
            {
                issues.Add(new SystemicIssue(SystemicErrors.OrphanThreat, t.Id, "威胁没有路径到达顶事件：" + t.Label));
            }

            foreach (BowTieElement c in consequences.Where(c => !fromTop.Contains(c.Id)))
            {
                issues.Add(new SystemicIssue(SystemicErrors.OrphanConsequence, c.Id, "后果不能从顶事件到达：" + c.Label));
            }

            foreach (BowTieElement b in _elements.Where(x => x.IsBarrier))
            {
                bool onPath = b.Kind == BowTieElementKind.PreventionBarrier
                    ? fromThreats.Contains(b.Id) && reachTop.Contains(b.Id)
                    : fromTop.Contains(b.Id) && reachCons.Contains(b.Id);
                if (!onPath)
                {
                    issues.Add(new SystemicIssue(SystemicErrors.OrphanBarrier, b.Id, "屏障不在任何完整路径上：" + b.Label));
                }
            }

            var notChecked = new Dictionary<string, int>(StringComparer.Ordinal);
            SystemicRules.CheckElements(_elements, ctx, issues, notChecked);
            return new SystemicValidation(issues, notChecked);
        }

        /// <summary>按给定 ID 顺序重排节点（顶事件始终在首位；未列出的保持相对顺序排在后面）。供两遍加载恢复文件顺序。</summary>
        internal void RestoreOrder(IList<string> orderedIds)
        {
            var rank = new Dictionary<string, int>(StringComparer.Ordinal);
            for (int i = 0; i < orderedIds.Count; i++)
            {
                rank[orderedIds[i]] = i;
            }

            var top = _elements[0];
            var rest = _elements.Skip(1)
                .Select((e, i) => new { e, i })
                .OrderBy(x => rank.TryGetValue(x.e.Id, out int r) ? r : int.MaxValue)
                .ThenBy(x => x.i)
                .Select(x => x.e)
                .ToList();
            _elements.Clear();
            _elements.Add(top);
            _elements.AddRange(rest);
        }

        private Result<BowTieElement> Add(string id, string label, BowTieElementKind kind, EvidenceStrength strength, SystemicRefs refs, BarrierState? state, string barrierId, string actorId)
        {
            Result<bool> ok = SystemicRules.CheckElement(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<BowTieElement>(ok);
            }

            if (_byId.ContainsKey(id))
            {
                return Result<BowTieElement>.Fail(SystemicErrors.DuplicateId, "ID 重复：" + id);
            }

            var e = new BowTieElement(id, label, kind, strength, refs, state, barrierId, actorId);
            _elements.Add(e);
            _byId[id] = e;
            return Result<BowTieElement>.Ok(e);
        }
    }
}
