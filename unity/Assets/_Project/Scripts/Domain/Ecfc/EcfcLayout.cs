using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ecfc
{
    /// <summary>
    /// ECFC 自动布局：主序列水平居中一线，次序列分上下泳道，条件就近避让（ARCHITECTURE 4.9.2）。
    /// 坐标单位为画布逻辑像素，原点在主序列左端。
    /// </summary>
    public static class EcfcLayout
    {
        public const double NodeWidth = 200.0;
        public const double NodeHeight = 80.0;
        public const double HorizontalGap = 80.0;
        public const double LaneHeight = 140.0;
        public const double ConditionOffsetY = 70.0;
        public const double ConditionOffsetX = 0.0;

        public static IReadOnlyDictionary<string, Double2> Compute(
            IReadOnlyList<EcfcNode> nodes,
            IReadOnlyList<EcfcEdge> edges)
        {
            var positions = new Dictionary<string, Double2>(StringComparer.Ordinal);
            nodes = nodes ?? Array.Empty<EcfcNode>();
            edges = edges ?? Array.Empty<EcfcEdge>();

            var eventsByLane = new Dictionary<int, List<EcfcNode>>();
            var conditions = new List<EcfcNode>();
            for (int i = 0; i < nodes.Count; i++)
            {
                EcfcNode n = nodes[i];
                if (n.ManualCanvasPos.HasValue)
                {
                    positions[n.NodeId] = n.ManualCanvasPos.Value;
                    continue;
                }

                if (n.Kind == EcfcNodeKind.Condition)
                {
                    conditions.Add(n);
                    continue;
                }

                List<EcfcNode> lane;
                if (!eventsByLane.TryGetValue(n.Lane, out lane))
                {
                    lane = new List<EcfcNode>();
                    eventsByLane[n.Lane] = lane;
                }

                lane.Add(n);
            }

            foreach (KeyValuePair<int, List<EcfcNode>> kv in eventsByLane)
            {
                kv.Value.Sort(CompareByTimeThenId);
                double x = 0.0;
                double y = -kv.Key * LaneHeight;
                for (int i = 0; i < kv.Value.Count; i++)
                {
                    EcfcNode n = kv.Value[i];
                    if (!positions.ContainsKey(n.NodeId))
                    {
                        positions[n.NodeId] = new Double2(x, y);
                    }

                    x += NodeWidth + HorizontalGap;
                }
            }

            // 条件就近其关联事件（优先出边指向的事件，其次入边来源事件）
            for (int i = 0; i < conditions.Count; i++)
            {
                EcfcNode c = conditions[i];
                if (positions.ContainsKey(c.NodeId))
                {
                    continue;
                }

                EcfcNode anchor = FindAssociatedEvent(c, nodes, edges);
                Double2 basePos = anchor != null && positions.ContainsKey(anchor.NodeId)
                    ? positions[anchor.NodeId]
                    : new Double2(i * (NodeWidth + HorizontalGap), LaneHeight);
                int side = c.Lane != 0 ? Math.Sign(c.Lane) : ((i % 2 == 0) ? 1 : -1);
                if (side == 0)
                {
                    side = 1;
                }

                double x = basePos.X + ConditionOffsetX + (i % 3 - 1) * 24.0;
                double y = basePos.Y + side * ConditionOffsetY;
                // 简单避让：若与已有节点过近则沿 Y 再偏移
                y = NudgeY(positions, x, y);
                positions[c.NodeId] = new Double2(x, y);
            }

            return positions;
        }

        private static double NudgeY(Dictionary<string, Double2> positions, double x, double y)
        {
            const double minDx = 90.0;
            const double minDy = 60.0;
            for (int pass = 0; pass < 8; pass++)
            {
                bool collided = false;
                foreach (KeyValuePair<string, Double2> kv in positions)
                {
                    double dx = Math.Abs(kv.Value.X - x);
                    double dy = Math.Abs(kv.Value.Y - y);
                    if (dx < minDx && dy < minDy)
                    {
                        y += Math.Sign(y) * minDy;
                        if (Math.Abs(y) < 1.0)
                        {
                            y = minDy;
                        }

                        collided = true;
                        break;
                    }
                }

                if (!collided)
                {
                    break;
                }
            }

            return y;
        }

        private static EcfcNode FindAssociatedEvent(EcfcNode condition, IReadOnlyList<EcfcNode> nodes, IReadOnlyList<EcfcEdge> edges)
        {
            for (int i = 0; i < edges.Count; i++)
            {
                if (edges[i].FromNodeId == condition.NodeId)
                {
                    EcfcNode to = Find(nodes, edges[i].ToNodeId);
                    if (to != null && to.Kind == EcfcNodeKind.Event)
                    {
                        return to;
                    }
                }
            }

            for (int i = 0; i < edges.Count; i++)
            {
                if (edges[i].ToNodeId == condition.NodeId)
                {
                    EcfcNode from = Find(nodes, edges[i].FromNodeId);
                    if (from != null && from.Kind == EcfcNodeKind.Event)
                    {
                        return from;
                    }
                }
            }

            return null;
        }

        private static EcfcNode Find(IReadOnlyList<EcfcNode> nodes, string id)
        {
            for (int i = 0; i < nodes.Count; i++)
            {
                if (nodes[i].NodeId == id)
                {
                    return nodes[i];
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
