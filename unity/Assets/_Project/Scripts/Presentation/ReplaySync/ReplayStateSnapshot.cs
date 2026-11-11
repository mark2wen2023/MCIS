namespace Mcis.Presentation.ReplaySync
{
    /// <summary>Read-only local snapshot. Service supplies UTC/updatedUtc; no publication occurs here.</summary>
    public sealed class ReplayStateSnapshot
    {
        public string CaseId { get; }
        public double SimTimeSec { get; }
        public bool Playing { get; }
        public double Rate { get; }
        public string Source => "unity";
        internal ReplayStateSnapshot(string caseId, double time, bool playing, double rate)
        { CaseId=caseId; SimTimeSec=time; Playing=playing; Rate=rate; }
    }
}
