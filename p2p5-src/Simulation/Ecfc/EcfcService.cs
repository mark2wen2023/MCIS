using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Ecfc;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Ecfc
{
    /// <summary>管理 ECFC 图的增删改查、规则校验、自动布局及按 SimTime 查询当前可见卡片集合。</summary>
    public interface IEcfcService : ITimeDriven, ITimelineMarkerProvider
    {
        IReadOnlyList<EcfcNode> Nodes { get; }
        IReadOnlyList<EcfcEdge> Edges { get; }
        IReadOnlyList<EcfcNode> ActiveRuntimeCards { get; }
        double DefaultCardDisplayDurationSec { get; set; }

        Result<EcfcNode> UpsertNode(EcfcNode node);
        Result<bool> RemoveNode(string nodeId);
        Result<EcfcEdge> ConnectNodes(string fromNodeId, string toNodeId);
        Result<bool> RemoveEdge(string edgeId);
        IReadOnlyList<EcfcValidationIssue> ValidateGraph();
        IReadOnlyDictionary<string, Double2> ComputeAutoLayout();
        IReadOnlyList<EcfcNode> GetVisibleCardsAt(SimTime time);
    }

    /// <summary>ECFC 服务纯逻辑实现（不依赖 UnityEngine）。</summary>
    public sealed class EcfcService : IEcfcService
    {
        private readonly List<EcfcNode> _nodes = new List<EcfcNode>();
        private readonly List<EcfcEdge> _edges = new List<EcfcEdge>();
        private readonly List<EcfcNode> _active = new List<EcfcNode>();
        private int _edgeSerial;

        public int ExecutionPriority { get { return 50; } }
        public IReadOnlyList<EcfcNode> Nodes { get { return _nodes; } }
        public IReadOnlyList<EcfcEdge> Edges { get { return _edges; } }
        public IReadOnlyList<EcfcNode> ActiveRuntimeCards { get { return _active; } }
        public double DefaultCardDisplayDurationSec { get; set; }

        public event Action MarkersChanged;

        public EcfcService(double defaultCardDisplayDurationSec = 8.0)
        {
            DefaultCardDisplayDurationSec = defaultCardDisplayDurationSec > 0.0 ? defaultCardDisplayDurationSec : 8.0;
        }

        public Result<EcfcNode> UpsertNode(EcfcNode node)
        {
            if (node == null || string.IsNullOrWhiteSpace(node.NodeId))
            {
                return Result<EcfcNode>.Fail("ECFC-E10", "节点或 NodeId 不能为空");
            }

            for (int i = 0; i < _nodes.Count; i++)
            {
                if (_nodes[i].NodeId == node.NodeId)
                {
                    _nodes[i] = node;
                    RaiseMarkers();
                    return Result<EcfcNode>.Ok(node);
                }
            }

            _nodes.Add(node);
            RaiseMarkers();
            return Result<EcfcNode>.Ok(node);
        }

        public Result<bool> RemoveNode(string nodeId)
        {
            int removed = _nodes.RemoveAll(n => n.NodeId == nodeId);
            _edges.RemoveAll(e => e.FromNodeId == nodeId || e.ToNodeId == nodeId);
            if (removed == 0)
            {
                return Result<bool>.Fail("ECFC-E11", "找不到节点：" + nodeId);
            }

            RaiseMarkers();
            return Result<bool>.Ok(true);
        }

        public Result<EcfcEdge> ConnectNodes(string fromNodeId, string toNodeId)
        {
            EcfcNode from = FindNode(fromNodeId);
            EcfcNode to = FindNode(toNodeId);
            if (from == null || to == null)
            {
                return Result<EcfcEdge>.Fail("ECFC-E07", "连线引用了不存在的节点");
            }

            EcfcValidator.ResultDerive derived = EcfcValidator.DeriveEdgeKind(from, to);
            if (!derived.IsSuccess)
            {
                return Result<EcfcEdge>.Fail("ECFC-E03", derived.Error);
            }

            for (int i = 0; i < _edges.Count; i++)
            {
                if (_edges[i].FromNodeId == fromNodeId && _edges[i].ToNodeId == toNodeId)
                {
                    var updated = new EcfcEdge(_edges[i].EdgeId, fromNodeId, toNodeId, derived.Kind, derived.IsPrimarySequenceBold);
                    _edges[i] = updated;
                    return Result<EcfcEdge>.Ok(updated);
                }
            }

            _edgeSerial++;
            var edge = new EcfcEdge("edge-" + _edgeSerial.ToString("D3"), fromNodeId, toNodeId, derived.Kind, derived.IsPrimarySequenceBold);
            _edges.Add(edge);
            return Result<EcfcEdge>.Ok(edge);
        }

        public Result<bool> RemoveEdge(string edgeId)
        {
            int n = _edges.RemoveAll(e => e.EdgeId == edgeId);
            return n > 0 ? Result<bool>.Ok(true) : Result<bool>.Fail("ECFC-E12", "找不到连线：" + edgeId);
        }

        public IReadOnlyList<EcfcValidationIssue> ValidateGraph()
        {
            return EcfcValidator.Validate(_nodes, _edges);
        }

        public IReadOnlyDictionary<string, Double2> ComputeAutoLayout()
        {
            return EcfcLayout.Compute(_nodes, _edges);
        }

        public IReadOnlyList<EcfcNode> GetVisibleCardsAt(SimTime time)
        {
            var visible = new List<EcfcNode>();
            double duration = DefaultCardDisplayDurationSec;
            for (int i = 0; i < _nodes.Count; i++)
            {
                if (IsVisible(_nodes[i], time, duration))
                {
                    visible.Add(_nodes[i]);
                }
            }

            visible.Sort((a, b) =>
            {
                double ta = a.Time.HasValue ? a.Time.Value.Seconds : double.NegativeInfinity;
                double tb = b.Time.HasValue ? b.Time.Value.Seconds : double.NegativeInfinity;
                int c = ta.CompareTo(tb);
                return c != 0 ? c : string.CompareOrdinal(a.NodeId, b.NodeId);
            });
            return visible;
        }

        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            _active.Clear();
            _active.AddRange(GetVisibleCardsAt(currentTime));
        }

        public IReadOnlyList<TimelineMarker> GetMarkers()
        {
            var markers = new List<TimelineMarker>();
            for (int i = 0; i < _nodes.Count; i++)
            {
                EcfcNode n = _nodes[i];
                if (!n.Time.HasValue)
                {
                    continue;
                }

                markers.Add(new TimelineMarker(
                    "ecfc-" + n.NodeId,
                    n.Time.Value,
                    "ECFC",
                    n.Text,
                    n.IsPrimaryIncident ? RiskLevel.Danger : RiskLevel.Safe,
                    n.ActorVesselId));
            }

            return markers;
        }

        public void Clear()
        {
            _nodes.Clear();
            _edges.Clear();
            _active.Clear();
            RaiseMarkers();
        }

        public static bool IsVisible(EcfcNode node, SimTime time, double defaultDurationSec)
        {
            if (node == null || !node.Time.HasValue)
            {
                return false;
            }

            double t = time.Seconds;
            double start = node.Time.Value.Seconds;
            double end = node.EndTime.HasValue
                ? node.EndTime.Value.Seconds
                : start + Math.Max(defaultDurationSec, 0.0);
            if (end < start)
            {
                end = start + Math.Max(defaultDurationSec, 0.0);
            }

            return t + 1e-9 >= start && t < end + 1e-9;
        }

        private EcfcNode FindNode(string id)
        {
            for (int i = 0; i < _nodes.Count; i++)
            {
                if (_nodes[i].NodeId == id)
                {
                    return _nodes[i];
                }
            }

            return null;
        }

        private void RaiseMarkers()
        {
            Action handler = MarkersChanged;
            if (handler != null)
            {
                handler();
            }
        }
    }
}
