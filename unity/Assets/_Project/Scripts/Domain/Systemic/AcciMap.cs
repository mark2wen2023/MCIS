using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.HumanFactors;

namespace Mcis.Domain.Systemic
{
    /// <summary>AcciMap 六层，数值越小越“上层”。</summary>
    public enum AcciMapLevel
    {
        /// <summary>政府与法规。</summary>
        Government = 0,

        /// <summary>监管（主管机关 / VTS / 船旗国 / 港口国）。</summary>
        Regulatory = 1,

        /// <summary>公司（船东 / 管理公司 / SMS）。</summary>
        Company = 2,

        /// <summary>船舶管理（船长 / 驾驶台组织 / 值班安排）。</summary>
        ShipManagement = 3,

        /// <summary>船员行为。</summary>
        CrewActs = 4,

        /// <summary>设备与环境（含物理过程与事故事件序列）。</summary>
        EquipmentEnvironment = 5
    }

    public sealed class AcciMapNode : SystemicElement
    {
        /// <summary>层级。经 <see cref="AcciMapModel.UpdateNode"/> 修改（须满足全部相连因果边的方向规则）。</summary>
        public AcciMapLevel Level { get; internal set; }

        internal AcciMapNode(string id, string label, AcciMapLevel level, EvidenceStrength strength, SystemicRefs refs, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            Level = level;
        }
    }

    /// <summary>
    /// AcciMap 社会-技术系统层级图（A3：保持规格的六层）。因果边为“原因 → 结果”，不得成环。
    /// 另有信息流边（A2，如“VTS 向引航员通报”）：只要求端点存在、非自环、不重复，不参与成环判断与层间方向规则。
    /// 层间方向规则（本包假设）：只允许 上层 → 下层 与 同层；
    /// 唯一例外：设备与环境 → 船员行为（物理条件如能见度、横流、设备显示直接影响船员行为），
    /// 由 <see cref="AllowEnvironmentToCrew"/> 控制，默认允许；其余由下往上的边 → sys_level_direction。
    /// </summary>
    public sealed class AcciMapModel
    {
        private readonly List<AcciMapNode> _nodes = new List<AcciMapNode>();
        private readonly Dictionary<string, AcciMapNode> _byId = new Dictionary<string, AcciMapNode>(StringComparer.Ordinal);
        private readonly List<SystemicEdge> _edges = new List<SystemicEdge>();
        private readonly List<SystemicEdge> _infoFlows = new List<SystemicEdge>();
        private Dictionary<string, List<string>> _adj = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        public string Id { get; }
        public string Title { get; }
        public bool AllowEnvironmentToCrew { get; }

        private AcciMapModel(string id, string title, bool allowEnvironmentToCrew)
        {
            Id = id;
            Title = title;
            AllowEnvironmentToCrew = allowEnvironmentToCrew;
        }

        public static Result<AcciMapModel> Create(string id, string title, bool allowEnvironmentToCrew = true)
        {
            if (!SystemicRules.IsValidId(id))
            {
                return Result<AcciMapModel>.Fail(SystemicErrors.InvalidId, "模型 ID 无效：" + id);
            }

            if (string.IsNullOrWhiteSpace(title))
            {
                return Result<AcciMapModel>.Fail(SystemicErrors.InvalidArgument, "标题不能为空");
            }

            return Result<AcciMapModel>.Ok(new AcciMapModel(id, title, allowEnvironmentToCrew));
        }

        /// <summary>层名（中文）。</summary>
        public static string LevelLabel(AcciMapLevel level)
        {
            switch (level)
            {
                case AcciMapLevel.Government: return "政府与法规";
                case AcciMapLevel.Regulatory: return "监管";
                case AcciMapLevel.Company: return "公司";
                case AcciMapLevel.ShipManagement: return "船舶管理";
                case AcciMapLevel.CrewActs: return "船员行为";
                case AcciMapLevel.EquipmentEnvironment: return "设备与环境";
                default: return level.ToString();
            }
        }

        /// <summary>方向规则：to 层不高于 from 层；或（允许时）设备与环境 → 船员行为。</summary>
        public static bool IsDirectionAllowed(AcciMapLevel from, AcciMapLevel to, bool allowEnvironmentToCrew)
        {
            if (to >= from)
            {
                return true;
            }

            return allowEnvironmentToCrew && from == AcciMapLevel.EquipmentEnvironment && to == AcciMapLevel.CrewActs;
        }

        /// <summary>只读视图（D01）。</summary>
        public IReadOnlyList<AcciMapNode> Nodes
        {
            get { return _nodes.AsReadOnly(); }
        }

        /// <summary>因果边（只读视图，D01）。</summary>
        public IReadOnlyList<SystemicEdge> Edges
        {
            get { return _edges.AsReadOnly(); }
        }

        /// <summary>信息流边（A2，只读视图）。</summary>
        public IReadOnlyList<SystemicEdge> InformationFlows
        {
            get { return _infoFlows.AsReadOnly(); }
        }

        public AcciMapNode Get(string id)
        {
            AcciMapNode n;
            return id != null && _byId.TryGetValue(id, out n) ? n : null;
        }

        public IReadOnlyList<AcciMapNode> ByLevel(AcciMapLevel level)
        {
            return _nodes.Where(n => n.Level == level).ToList().AsReadOnly();
        }

        public Result<AcciMapNode> AddNode(string id, string label, AcciMapLevel level, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            if (!Enum.IsDefined(typeof(AcciMapLevel), level))
            {
                return Result<AcciMapNode>.Fail(SystemicErrors.InvalidArgument, "未知层级：" + (int)level);
            }

            Result<bool> ok = SystemicRules.CheckElement(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<AcciMapNode>(ok);
            }

            if (_byId.ContainsKey(id))
            {
                return Result<AcciMapNode>.Fail(SystemicErrors.DuplicateId, "ID 重复：" + id);
            }

            var n = new AcciMapNode(id, label, level, strength, refs, actorId);
            _nodes.Add(n);
            _byId[id] = n;
            return Result<AcciMapNode>.Ok(n);
        }

        /// <summary>添加因果边 cause → effect。不存在 → sys_unknown_node；方向违规 → sys_level_direction；成环（含自环）→ sys_cycle；重复 → sys_duplicate_edge。</summary>
        public Result<SystemicEdge> Connect(string causeId, string effectId)
        {
            AcciMapNode from = Get(causeId);
            AcciMapNode to = Get(effectId);
            if (from == null || to == null)
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.UnknownNode, "边的端点不存在：" + causeId + " → " + effectId);
            }

            if (!IsDirectionAllowed(from.Level, to.Level, AllowEnvironmentToCrew))
            {
                return Result<SystemicEdge>.Fail(
                    SystemicErrors.LevelDirection,
                    "层间方向违规：" + LevelLabel(from.Level) + " → " + LevelLabel(to.Level) + "（" + causeId + " → " + effectId + "）");
            }

            if (causeId == effectId || SystemicRules.Reaches(_adj, effectId, causeId))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.Cycle, "因果边成环：" + causeId + " → " + effectId);
            }

            if (_edges.Any(e => e.FromId == causeId && e.ToId == effectId))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.DuplicateEdge, "重复的边：" + causeId + " → " + effectId);
            }

            var edge = new SystemicEdge(causeId, effectId);
            _edges.Add(edge);
            SystemicRules.AddEdge(_adj, causeId, effectId);
            return Result<SystemicEdge>.Ok(edge);
        }

        /// <summary>添加信息流边（A2）。端点不存在 → sys_unknown_node；自环 → sys_invalid_edge；重复 → sys_duplicate_edge。不查成环与层间方向。</summary>
        public Result<SystemicEdge> ConnectInformationFlow(string fromId, string toId)
        {
            if (Get(fromId) == null || Get(toId) == null)
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.UnknownNode, "信息流端点不存在：" + fromId + " → " + toId);
            }

            if (fromId == toId)
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.InvalidEdge, "信息流不能自环：" + fromId);
            }

            if (_infoFlows.Any(e => e.FromId == fromId && e.ToId == toId))
            {
                return Result<SystemicEdge>.Fail(SystemicErrors.DuplicateEdge, "重复的信息流：" + fromId + " → " + toId);
            }

            var edge = new SystemicEdge(fromId, toId, SystemicEdgeKind.InformationFlow);
            _infoFlows.Add(edge);
            return Result<SystemicEdge>.Ok(edge);
        }

        /// <summary>删除因果边（A9）。不存在 → sys_unknown_edge。</summary>
        public Result<bool> Disconnect(string causeId, string effectId)
        {
            int i = _edges.FindIndex(e => e.FromId == causeId && e.ToId == effectId);
            if (i < 0)
            {
                return Result<bool>.Fail(SystemicErrors.UnknownEdge, "边不存在：" + causeId + " → " + effectId);
            }

            _edges.RemoveAt(i);
            _adj = SystemicRules.BuildAdj(_edges);
            return Result<bool>.Ok(true);
        }

        /// <summary>删除信息流边（A9）。不存在 → sys_unknown_edge。</summary>
        public Result<bool> DisconnectInformationFlow(string fromId, string toId)
        {
            int i = _infoFlows.FindIndex(e => e.FromId == fromId && e.ToId == toId);
            if (i < 0)
            {
                return Result<bool>.Fail(SystemicErrors.UnknownEdge, "信息流不存在：" + fromId + " → " + toId);
            }

            _infoFlows.RemoveAt(i);
            return Result<bool>.Ok(true);
        }

        /// <summary>删除节点及其全部因果边与信息流（A9）。不存在 → sys_unknown_node。</summary>
        public Result<bool> RemoveNode(string id)
        {
            AcciMapNode n = Get(id);
            if (n == null)
            {
                return Result<bool>.Fail(SystemicErrors.UnknownNode, "节点不存在：" + id);
            }

            _nodes.Remove(n);
            _byId.Remove(id);
            _edges.RemoveAll(e => e.FromId == id || e.ToId == id);
            _infoFlows.RemoveAll(e => e.FromId == id || e.ToId == id);
            _adj = SystemicRules.BuildAdj(_edges);
            return Result<bool>.Ok(true);
        }

        /// <summary>
        /// 修改节点（A9）：给出的字段才改。改层级时，全部相连因果边须仍满足方向规则，否则 sys_level_direction 且不做任何修改；
        /// 其余字段按新增规则校验（含 A6）。clearActor = true 清除责任方。
        /// </summary>
        public Result<AcciMapNode> UpdateNode(string id, string label = null, AcciMapLevel? level = null, EvidenceStrength? strength = null, SystemicRefs refs = null, string actorId = null, bool clearActor = false)
        {
            AcciMapNode n = Get(id);
            if (n == null)
            {
                return Result<AcciMapNode>.Fail(SystemicErrors.UnknownNode, "节点不存在：" + id);
            }

            AcciMapLevel newLevel = level ?? n.Level;
            if (!Enum.IsDefined(typeof(AcciMapLevel), newLevel))
            {
                return Result<AcciMapNode>.Fail(SystemicErrors.InvalidArgument, "未知层级：" + (int)newLevel);
            }

            foreach (SystemicEdge e in _edges.Where(e => e.FromId == id || e.ToId == id))
            {
                AcciMapLevel from = e.FromId == id ? newLevel : Get(e.FromId).Level;
                AcciMapLevel to = e.ToId == id ? newLevel : Get(e.ToId).Level;
                if (!IsDirectionAllowed(from, to, AllowEnvironmentToCrew))
                {
                    return Result<AcciMapNode>.Fail(SystemicErrors.LevelDirection, "改层级后因果边方向违规：" + e.FromId + " → " + e.ToId);
                }
            }

            Result<bool> ok = SystemicRules.ApplyUpdate(n, label, strength, refs, actorId, clearActor);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<AcciMapNode>(ok);
            }

            n.Level = newLevel;
            return Result<AcciMapNode>.Ok(n);
        }

        /// <summary>
        /// 整体校验：无节点 → sys_empty_model；既无因果边也无信息流相连的孤立节点 → sys_isolated_node；
        /// 另按 ctx 校验引用、Strong 必须有证据。（成环与方向在 Connect 时已拒绝。）
        /// </summary>
        public SystemicValidation Validate(SystemicRefContext ctx = null)
        {
            var issues = new List<SystemicIssue>();
            if (_nodes.Count == 0)
            {
                issues.Add(new SystemicIssue(SystemicErrors.EmptyModel, Id, "AcciMap 没有节点"));
            }

            var linked = new HashSet<string>(_edges.Concat(_infoFlows).SelectMany(e => new[] { e.FromId, e.ToId }), StringComparer.Ordinal);
            foreach (AcciMapNode n in _nodes.Where(n => !linked.Contains(n.Id)))
            {
                issues.Add(new SystemicIssue(SystemicErrors.IsolatedNode, n.Id, "节点没有任何因果边或信息流：" + n.Label));
            }

            var notChecked = new Dictionary<string, int>(StringComparer.Ordinal);
            SystemicRules.CheckElements(_nodes, ctx, issues, notChecked);
            return new SystemicValidation(issues, notChecked);
        }
    }
}
