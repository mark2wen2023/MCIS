using System;
namespace Mcis.Presentation.ReplaySync
{
    /// <summary>Immutable local representation of the service command. No transport or persistence.</summary>
    public sealed class ReplayCommand : IEquatable<ReplayCommand>
    {
        public long Seq { get; }
        public string CaseId { get; }
        public string Type { get; }
        public double? SimTimeSec { get; }
        public double? Rate { get; }
        public string VesselId { get; }
        public string Reason { get; }
        public string CreatedUtc { get; }
        public string IssuedBy { get; }
        public ReplayCommand(long seq, string caseId, string type, double? simTimeSec = null,
            double? rate = null, string vesselId = null, string reason = null,
            string createdUtc = null, string issuedBy = null)
        {
            Seq=seq; CaseId=caseId; Type=type; SimTimeSec=simTimeSec; Rate=rate;
            VesselId=vesselId; Reason=reason; CreatedUtc=createdUtc; IssuedBy=issuedBy;
        }
        public bool Equals(ReplayCommand o) => o != null && Seq==o.Seq && CaseId==o.CaseId &&
            Type==o.Type && SimTimeSec==o.SimTimeSec && Rate==o.Rate && VesselId==o.VesselId &&
            Reason==o.Reason && CreatedUtc==o.CreatedUtc && IssuedBy==o.IssuedBy;
        public override bool Equals(object o) => Equals(o as ReplayCommand);
        public override int GetHashCode() => Seq.GetHashCode();
    }
    public enum ReplayApplyStatus { Applied, Duplicate, Rejected, FailedUnknown }
    public sealed class ReplayApplyResult
    {
        public long Seq { get; }
        public ReplayApplyStatus Status { get; }
        public string Code { get; }
        internal ReplayApplyResult(long seq, ReplayApplyStatus status, string code)
        { Seq=seq; Status=status; Code=code; }
    }
}
