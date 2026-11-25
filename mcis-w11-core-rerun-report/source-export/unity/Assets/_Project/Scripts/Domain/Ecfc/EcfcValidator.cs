using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ecfc
{
    /// <summary>
    /// 按论文 2.5 节表 4（How to draw an Event and casual factors chart，Snorre Sklet, 2002）
    /// 及 ARCHITECTURE 4.9.1 节执行规范性检查。不阻止保存，只输出错误或警告。
    /// </summary>
    public static class EcfcValidator
    {
        // 用于判断事件是否包含“主动动词”的启发式词表（中英对照论文举例 “crane strikes building”）。
        private static readonly string[] ActiveVerbHints = new string[]
        {
            "发生", "转向", "撞击", "碰撞", "下令", "鸣放", "沟通", "出港", "进港", "下沉", "弃船",
            "进水", "会遇", "航行", "卸货", "满载", "抵达", "离开", "避让", "倒车", "右满舵", "左转", "右转",
            "撞击", "触碰", "坐底", "施救", "救起", "失败", "违规", "未达成",
            "strikes", "strike", "collides", "collide", "turns", "turn", "sails", "sail",
            "issues", "orders", "sounds", "hits", "hit", "sinks", "abandons", "floods"
        };

        /// <summary>对给定节点与边集合执行表 4 规则校验。</summary>
        public static IReadOnlyList<EcfcValidationIssue> Validate(
            IReadOnlyList<EcfcNode> nodes,
            IReadOnlyList<EcfcEdge> edges)
        {
            var issues = new List<EcfcValidationIssue>();
            nodes = nodes ?? Array.Empty<EcfcNode>();
            edges = edges ?? Array.Empty<EcfcEdge>();

            var byId = new Dictionary<string, EcfcNode>(StringComparer.Ordinal);
            int primaryIncidentCount = 0;
            for (int i = 0; i < nodes.Count; i++)
            {
                EcfcNode n = nodes[i];
                if (string.IsNullOrWhiteSpace(n.NodeId))
                {
                    issues.Add(new EcfcValidationIssue("ECFC-E09", true, "节点缺少 NodeId。", n.NodeId));
                    continue;
                }

                if (byId.ContainsKey(n.NodeId))
                {
                    issues.Add(new EcfcValidationIssue("ECFC-E09", true, "节点标识重复：" + n.NodeId, n.NodeId));
                }
                else
                {
                    byId[n.NodeId] = n;
                }

                if (n.IsPrimaryIncident)
                {
                    primaryIncidentCount++;
                    if (n.Kind != EcfcNodeKind.Event)
                    {
                        issues.Add(new EcfcValidationIssue("ECFC-E06", true, "核心事故节点必须是事件（矩形）。", n.NodeId));
                    }

                    if (n.Lane != 0)
                    {
                        issues.Add(new EcfcValidationIssue("ECFC-W07", false, "核心事故节点应位于主序列（Lane = 0）。", n.NodeId));
                    }
                }

                ValidateNodeTextAndEvidence(n, issues);
            }

            if (primaryIncidentCount != 1)
            {
                issues.Add(new EcfcValidationIssue(
                    "ECFC-E06",
                    true,
                    "主序列应有且仅有一个核心事故节点（IsPrimaryIncident），当前数量为 " + primaryIncidentCount + "。"));
            }

            var incoming = new Dictionary<string, List<EcfcEdge>>(StringComparer.Ordinal);
            var outgoing = new Dictionary<string, List<EcfcEdge>>(StringComparer.Ordinal);
            for (int i = 0; i < edges.Count; i++)
            {
                EcfcEdge e = edges[i];
                if (!byId.ContainsKey(e.FromNodeId) || !byId.ContainsKey(e.ToNodeId))
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-E07",
                        true,
                        "连线引用了不存在的节点：" + e.FromNodeId + " → " + e.ToNodeId,
                        null,
                        e.EdgeId));
                    continue;
                }

                EcfcNode from = byId[e.FromNodeId];
                EcfcNode to = byId[e.ToNodeId];
                ValidateEdgeKind(e, from, to, issues);
                AddEdge(incoming, e.ToNodeId, e);
                AddEdge(outgoing, e.FromNodeId, e);
            }

            // 条件应关联到对应事件（表 4：Conditions are associated with the corresponding event）
            for (int i = 0; i < nodes.Count; i++)
            {
                EcfcNode n = nodes[i];
                if (n.Kind != EcfcNodeKind.Condition)
                {
                    continue;
                }

                if (!IsAssociatedWithEvent(n.NodeId, byId, incoming, outgoing))
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W04",
                        false,
                        "条件应关联到对应的事件（表 4：associated with the corresponding event）。",
                        n.NodeId));
                }
            }

            // 主序列事件应在水平一线，相邻主序列事件用加粗实线箭头连接
            var primaryEvents = new List<EcfcNode>();
            for (int i = 0; i < nodes.Count; i++)
            {
                if (nodes[i].Kind == EcfcNodeKind.Event && nodes[i].Lane == 0)
                {
                    primaryEvents.Add(nodes[i]);
                }
            }

            primaryEvents.Sort(CompareByTimeThenId);
            for (int i = 0; i < primaryEvents.Count - 1; i++)
            {
                EcfcNode a = primaryEvents[i];
                EcfcNode b = primaryEvents[i + 1];
                EcfcEdge edge = FindEdge(edges, a.NodeId, b.NodeId);
                if (edge == null)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-E05",
                        true,
                        "主序列相邻事件应由加粗实线箭头连接（表 4：primary sequence … bold printed connecting arrows）："
                        + a.NodeId + " → " + b.NodeId,
                        a.NodeId));
                    continue;
                }

                if (edge.Kind != EcfcEdgeKind.Sequence || !edge.IsPrimarySequenceBold)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-E05",
                        true,
                        "主序列事件之间的连线必须是加粗实线箭头。",
                        a.NodeId,
                        edge.EdgeId));
                }
            }

            // 次序列事件不应占据主序列泳道
            for (int i = 0; i < nodes.Count; i++)
            {
                EcfcNode n = nodes[i];
                if (n.Kind == EcfcNodeKind.Event && n.Lane != 0 && n.IsPrimaryIncident)
                {
                    issues.Add(new EcfcValidationIssue("ECFC-W06", false, "次序列事件不应同时标为核心事故。", n.NodeId));
                }
            }

            return issues;
        }

        /// <summary>按表 4 符号规则由起止节点类型推导连线种类：事件→事件为实线，条件出发为虚线。</summary>
        public static ResultDerive DeriveEdgeKind(EcfcNode from, EcfcNode to)
        {
            if (from == null || to == null)
            {
                return ResultDerive.Fail("起止节点不能为空");
            }

            if (from.Kind == EcfcNodeKind.Event && to.Kind == EcfcNodeKind.Event)
            {
                bool bold = from.Lane == 0 && to.Lane == 0;
                return ResultDerive.Ok(EcfcEdgeKind.Sequence, bold);
            }

            if (from.Kind == EcfcNodeKind.Condition &&
                (to.Kind == EcfcNodeKind.Event || to.Kind == EcfcNodeKind.Condition))
            {
                return ResultDerive.Ok(EcfcEdgeKind.Influence, false);
            }

            // 事件 → 条件：表 4 未给出实线路径，禁止
            return ResultDerive.Fail("禁止将事件连接到条件（表 4：Events should be connected by solid arrows；Conditions connect to events or conditions by dashed arrows）。");
        }

        public readonly struct ResultDerive
        {
            public bool IsSuccess { get; }
            public EcfcEdgeKind Kind { get; }
            public bool IsPrimarySequenceBold { get; }
            public string Error { get; }

            private ResultDerive(bool ok, EcfcEdgeKind kind, bool bold, string error)
            {
                IsSuccess = ok;
                Kind = kind;
                IsPrimarySequenceBold = bold;
                Error = error;
            }

            public static ResultDerive Ok(EcfcEdgeKind kind, bool bold)
            {
                return new ResultDerive(true, kind, bold, null);
            }

            public static ResultDerive Fail(string error)
            {
                return new ResultDerive(false, EcfcEdgeKind.Sequence, false, error);
            }
        }

        private static void ValidateNodeTextAndEvidence(EcfcNode n, List<EcfcValidationIssue> issues)
        {
            // 表 4：Each events and condition be based upon valid factual evidence or be clearly indicated as presumptive
            bool hasEvidence = n.EvidenceIds != null && n.EvidenceIds.Count > 0;
            if (!hasEvidence && !n.IsPresumptive)
            {
                issues.Add(new EcfcValidationIssue(
                    "ECFC-E08",
                    true,
                    "节点必须基于有效事实证据，或明确标为推定（虚线框，IsPresumptive = true）。",
                    n.NodeId));
            }

            if (n.Kind == EcfcNodeKind.Event)
            {
                // Events should be stated using one noun and one active verb
                if (!LooksLikeNounPlusActiveVerb(n.Text))
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W01",
                        false,
                        "事件应使用“一个名词 + 一个主动动词”表述（表 4：one noun and one active verb）。",
                        n.NodeId));
                }

                // Should be quantified as much as possible
                if (n.Quantities == null || n.Quantities.Count == 0)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W02",
                        false,
                        "事件应尽量量化（表 4：Should be quantified as much as possible）。",
                        n.NodeId));
                }

                // Should indicate the date and time, when they are known
                if (!n.Time.HasValue)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W03",
                        false,
                        "事件在时间已知时应标明日期与时刻（表 4：indicate the date and time, when they are known）。",
                        n.NodeId));
                }
            }
            else
            {
                // Conditions are passive; as practical, should be quantified; should indicate date and time if practical
                if (n.Quantities == null || n.Quantities.Count == 0)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W05",
                        false,
                        "条件在可行时应予以量化（表 4：As practical, should be quantified）。",
                        n.NodeId));
                }

                if (!n.Time.HasValue)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-W03",
                        false,
                        "条件在可行/适用时应标明日期与时刻。",
                        n.NodeId));
                }
            }
        }

        private static void ValidateEdgeKind(EcfcEdge e, EcfcNode from, EcfcNode to, List<EcfcValidationIssue> issues)
        {
            ResultDerive derived = DeriveEdgeKind(from, to);
            if (!derived.IsSuccess)
            {
                issues.Add(new EcfcValidationIssue("ECFC-E03", true, derived.Error, from.NodeId, e.EdgeId));
                return;
            }

            if (e.Kind != derived.Kind)
            {
                if (derived.Kind == EcfcEdgeKind.Sequence)
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-E01",
                        true,
                        "事件之间必须用实线箭头连接（表 4：Events should be connected by solid arrows）。",
                        from.NodeId,
                        e.EdgeId));
                }
                else
                {
                    issues.Add(new EcfcValidationIssue(
                        "ECFC-E02",
                        true,
                        "条件指向事件或条件必须用虚线箭头（表 4：Conditions should be connected … by dashed arrows）。",
                        from.NodeId,
                        e.EdgeId));
                }
            }
        }

        public static bool LooksLikeNounPlusActiveVerb(string text)
        {
            if (string.IsNullOrWhiteSpace(text))
            {
                return false;
            }

            string t = text.Trim();
            if (t.Length < 4)
            {
                return false;
            }

            for (int i = 0; i < ActiveVerbHints.Length; i++)
            {
                if (t.IndexOf(ActiveVerbHints[i], StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return true;
                }
            }

            // 英文：至少两个词，且含一个常见动词形态
            if (Regex.IsMatch(t, @"^[A-Za-z].*\s+.*[A-Za-z]"))
            {
                return Regex.IsMatch(t, @"\b\w+(ed|ing|s)\b", RegexOptions.IgnoreCase);
            }

            return false;
        }

        private static bool IsAssociatedWithEvent(
            string nodeId,
            Dictionary<string, EcfcNode> byId,
            Dictionary<string, List<EcfcEdge>> incoming,
            Dictionary<string, List<EcfcEdge>> outgoing)
        {
            List<EcfcEdge> inc;
            if (incoming.TryGetValue(nodeId, out inc))
            {
                for (int i = 0; i < inc.Count; i++)
                {
                    if (byId[inc[i].FromNodeId].Kind == EcfcNodeKind.Event)
                    {
                        return true;
                    }
                }
            }

            List<EcfcEdge> outg;
            if (outgoing.TryGetValue(nodeId, out outg))
            {
                for (int i = 0; i < outg.Count; i++)
                {
                    if (byId[outg[i].ToNodeId].Kind == EcfcNodeKind.Event)
                    {
                        return true;
                    }

                    // 条件→条件，沿虚线再看一步是否接到事件
                    if (byId[outg[i].ToNodeId].Kind == EcfcNodeKind.Condition &&
                        IsDirectlyConnectedToEvent(outg[i].ToNodeId, byId, outgoing))
                    {
                        return true;
                    }
                }
            }

            return false;
        }

        private static bool IsDirectlyConnectedToEvent(
            string nodeId,
            Dictionary<string, EcfcNode> byId,
            Dictionary<string, List<EcfcEdge>> outgoing)
        {
            List<EcfcEdge> outg;
            if (!outgoing.TryGetValue(nodeId, out outg))
            {
                return false;
            }

            for (int i = 0; i < outg.Count; i++)
            {
                if (byId[outg[i].ToNodeId].Kind == EcfcNodeKind.Event)
                {
                    return true;
                }
            }

            return false;
        }

        private static void AddEdge(Dictionary<string, List<EcfcEdge>> map, string key, EcfcEdge edge)
        {
            List<EcfcEdge> list;
            if (!map.TryGetValue(key, out list))
            {
                list = new List<EcfcEdge>();
                map[key] = list;
            }

            list.Add(edge);
        }

        private static EcfcEdge FindEdge(IReadOnlyList<EcfcEdge> edges, string from, string to)
        {
            for (int i = 0; i < edges.Count; i++)
            {
                if (edges[i].FromNodeId == from && edges[i].ToNodeId == to)
                {
                    return edges[i];
                }
            }

            return null;
        }

        private static int CompareByTimeThenId(EcfcNode a, EcfcNode b)
        {
            if (a.Time.HasValue && b.Time.HasValue)
            {
                int c = a.Time.Value.CompareTo(b.Time.Value);
                if (c != 0)
                {
                    return c;
                }
            }
            else if (a.Time.HasValue)
            {
                return -1;
            }
            else if (b.Time.HasValue)
            {
                return 1;
            }

            return string.CompareOrdinal(a.NodeId, b.NodeId);
        }
    }
}
