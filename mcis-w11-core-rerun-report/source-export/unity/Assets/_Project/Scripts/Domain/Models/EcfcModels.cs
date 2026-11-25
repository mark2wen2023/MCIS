using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Models
{
    /// <summary>ECFC 事件与原因因素图节点（严格对应论文 2.5 节表 4）。</summary>
    public sealed class EcfcNode
    {
        public string NodeId { get; }
        public EcfcNodeKind Kind { get; }
        public string Text { get; }
        public SimTime? Time { get; }
        public SimTime? EndTime { get; }
        public int Lane { get; }
        public bool IsPrimaryIncident { get; }
        public bool IsPresumptive { get; }
        public string ActorVesselId { get; }
        public GeoCoord? FixedLocation { get; }
        public IReadOnlyDictionary<string, string> Quantities { get; }
        public IReadOnlyList<string> EvidenceIds { get; }
        public Double2? ManualCanvasPos { get; }

        public EcfcNode(
            string nodeId,
            EcfcNodeKind kind,
            string text,
            SimTime? time = null,
            SimTime? endTime = null,
            int lane = 0,
            bool isPrimaryIncident = false,
            bool isPresumptive = false,
            string actorVesselId = null,
            GeoCoord? fixedLocation = null,
            IReadOnlyDictionary<string, string> quantities = null,
            IReadOnlyList<string> evidenceIds = null,
            Double2? manualCanvasPos = null)
        {
            NodeId = nodeId ?? string.Empty;
            Kind = kind;
            Text = text ?? string.Empty;
            Time = time;
            EndTime = endTime;
            Lane = lane;
            IsPrimaryIncident = isPrimaryIncident;
            IsPresumptive = isPresumptive;
            ActorVesselId = actorVesselId;
            FixedLocation = fixedLocation;
            Quantities = quantities ?? new Dictionary<string, string>();
            EvidenceIds = evidenceIds ?? Array.Empty<string>();
            ManualCanvasPos = manualCanvasPos;
        }

        public EcfcNode WithManualCanvasPos(Double2? pos)
        {
            return new EcfcNode(
                NodeId, Kind, Text, Time, EndTime, Lane, IsPrimaryIncident, IsPresumptive,
                ActorVesselId, FixedLocation, Quantities, EvidenceIds, pos);
        }
    }

    /// <summary>ECFC 连线。</summary>
    public sealed class EcfcEdge
    {
        public string EdgeId { get; }
        public string FromNodeId { get; }
        public string ToNodeId { get; }
        public EcfcEdgeKind Kind { get; }
        public bool IsPrimarySequenceBold { get; }

        public EcfcEdge(
            string edgeId,
            string fromNodeId,
            string toNodeId,
            EcfcEdgeKind kind,
            bool isPrimarySequenceBold)
        {
            EdgeId = edgeId ?? string.Empty;
            FromNodeId = fromNodeId ?? string.Empty;
            ToNodeId = toNodeId ?? string.Empty;
            Kind = kind;
            IsPrimarySequenceBold = isPrimarySequenceBold;
        }
    }

    /// <summary>ECFC 校验问题项（由 EcfcValidator 输出）。</summary>
    public readonly struct EcfcValidationIssue
    {
        public string RuleCode { get; }
        public bool IsError { get; }
        public string Message { get; }
        public string RelatedNodeId { get; }
        public string RelatedEdgeId { get; }

        public EcfcValidationIssue(
            string ruleCode,
            bool isError,
            string message,
            string relatedNodeId = null,
            string relatedEdgeId = null)
        {
            RuleCode = ruleCode ?? string.Empty;
            IsError = isError;
            Message = message ?? string.Empty;
            RelatedNodeId = relatedNodeId;
            RelatedEdgeId = relatedEdgeId;
        }
    }
}
