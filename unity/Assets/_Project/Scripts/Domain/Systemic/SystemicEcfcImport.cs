using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.Common;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Models;

namespace Mcis.Domain.Systemic
{
    /// <summary>由 ECFC 节点转换得到的待建节点（纯数据，不属于任何模型）。由调用方决定放入哪个模型、哪一层。</summary>
    public sealed class SystemicNodeDraft
    {
        public string Id { get; }
        public string Label { get; }
        public EvidenceStrength Strength { get; }
        public SystemicRefs Refs { get; }
        public string ActorId { get; }
        public string SourceEcfcNodeId { get; }
        public EcfcNodeKind SourceKind { get; }

        internal SystemicNodeDraft(string id, string label, EvidenceStrength strength, SystemicRefs refs, string actorId, string sourceEcfcNodeId, EcfcNodeKind sourceKind)
        {
            Id = id;
            Label = label;
            Strength = strength;
            Refs = refs;
            ActorId = actorId;
            SourceEcfcNodeId = sourceEcfcNodeId;
            SourceKind = sourceKind;
        }
    }

    /// <summary>ECFC 导入结果：可建节点、两端都已导入的连线、被跳过的节点及原因。集合只读。</summary>
    public sealed class EcfcImportResult
    {
        public IReadOnlyList<SystemicNodeDraft> Nodes { get; }
        public IReadOnlyList<SystemicEdge> Edges { get; }
        public IReadOnlyList<SystemicIssue> Skipped { get; }

        internal EcfcImportResult(List<SystemicNodeDraft> nodes, List<SystemicEdge> edges, List<SystemicIssue> skipped)
        {
            Nodes = nodes.AsReadOnly();
            Edges = edges.AsReadOnly();
            Skipped = skipped.AsReadOnly();
        }
    }

    /// <summary>
    /// “从 ECFC 导入节点”的纯转换函数（A9；按钮属界面包）。确定性、无副作用、不修改输入。规则：
    /// ID = idPrefix + ECFC 节点 ID（不合法 → 跳过 sys_invalid_id；重复 → 跳过 sys_duplicate_id）；标签 = 节点文本（空 → 跳过 sys_invalid_argument）；
    /// 引用 = Ecfc:[节点 ID] + Evidence:节点证据 ID；
    /// 强度：推定节点或无证据 → ToBeVerified，否则 Moderate（从不自动给 Strong，由调查员确认后再改）；
    /// actorId = ActorVesselId（不合法则置空并记一条警告）；连线只保留两端都导入成功的，统一为因果边。
    /// </summary>
    public static class SystemicEcfcImport
    {
        public static EcfcImportResult Convert(IEnumerable<EcfcNode> nodes, IEnumerable<EcfcEdge> edges = null, string idPrefix = "")
        {
            var drafts = new List<SystemicNodeDraft>();
            var skipped = new List<SystemicIssue>();
            var map = new Dictionary<string, string>(StringComparer.Ordinal);
            string prefix = idPrefix ?? string.Empty;
            foreach (EcfcNode n in nodes ?? Enumerable.Empty<EcfcNode>())
            {
                if (n == null)
                {
                    continue;
                }

                string id = prefix + n.NodeId;
                if (!SystemicRules.IsValidId(id))
                {
                    skipped.Add(new SystemicIssue(SystemicErrors.InvalidId, n.NodeId, "ECFC 节点 ID 无法作为系统分析节点 ID：" + id));
                    continue;
                }

                if (map.ContainsKey(n.NodeId) || drafts.Any(d => d.Id == id))
                {
                    skipped.Add(new SystemicIssue(SystemicErrors.DuplicateId, n.NodeId, "ECFC 节点重复：" + n.NodeId));
                    continue;
                }

                if (string.IsNullOrWhiteSpace(n.Text))
                {
                    skipped.Add(new SystemicIssue(SystemicErrors.InvalidArgument, n.NodeId, "ECFC 节点文本为空"));
                    continue;
                }

                var refs = new SystemicRefs(n.EvidenceIds, new[] { n.NodeId });
                EvidenceStrength strength = n.IsPresumptive || refs.EvidenceIds.Count == 0 ? EvidenceStrength.ToBeVerified : EvidenceStrength.Moderate;
                string actor = n.ActorVesselId;
                if (actor != null && !SystemicRules.IsValidId(actor))
                {
                    skipped.Add(new SystemicIssue(SystemicErrors.InvalidId, n.NodeId, "actorId 不合法，已置空：" + actor, SystemicIssueSeverity.Warning));
                    actor = null;
                }

                drafts.Add(new SystemicNodeDraft(id, n.Text.Trim(), strength, refs, actor, n.NodeId, n.Kind));
                map[n.NodeId] = id;
            }

            var outEdges = new List<SystemicEdge>();
            foreach (EcfcEdge e in edges ?? Enumerable.Empty<EcfcEdge>())
            {
                string from, to;
                if (e != null && map.TryGetValue(e.FromNodeId, out from) && map.TryGetValue(e.ToNodeId, out to)
                    && from != to && !outEdges.Any(x => x.FromId == from && x.ToId == to))
                {
                    outEdges.Add(new SystemicEdge(from, to));
                }
            }

            return new EcfcImportResult(drafts, outEdges, skipped);
        }
    }
}
