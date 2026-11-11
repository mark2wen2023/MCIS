using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Simulation;
namespace Mcis.Presentation.ReplaySync
{
    /// <summary>Single-threaded executor for already-authorized, deserialized commands. Not authentication or HTTP.
    /// Caller configures the clock case range and owns field mapping, main-thread scheduling and durable acknowledgments.
    /// A callback exception may follow a side effect: this instance is then permanently blocked.</summary>
    public sealed class ReplayCommandAdapter
    {
        private readonly ISimClock _clock;
        private readonly Action<string> _focus;
        private readonly Dictionary<long, ReplayCommand> _applied = new Dictionary<long, ReplayCommand>();
        private bool _executing;
        public string CaseId { get; }
        public long LastAppliedSeq { get; private set; }
        public bool OutcomeUnknown { get; private set; }
        public ReplayCommandAdapter(string caseId, ISimClock clock, Action<string> focus = null, long confirmedSeq = 0)
        {
            if (string.IsNullOrWhiteSpace(caseId)) throw new ArgumentException("Case required", nameof(caseId));
            if (confirmedSeq < 0) throw new ArgumentOutOfRangeException(nameof(confirmedSeq));
            CaseId=caseId; _clock=clock ?? throw new ArgumentNullException(nameof(clock));
            _focus=focus; LastAppliedSeq=confirmedSeq;
        }
        private static bool Finite(double v) => !double.IsNaN(v) && !double.IsInfinity(v);
        private string Validate(ReplayCommand c)
        {
            if (c==null) return "NULL_COMMAND";
            if (c.CaseId!=CaseId) return "CASE_MISMATCH";
            if (c.Seq<=0) return "INVALID_SEQ";
            if ((c.SimTimeSec.HasValue && !Finite(c.SimTimeSec.Value)) ||
                (c.Rate.HasValue && !Finite(c.Rate.Value))) return "NONFINITE_PARAMETER";
            switch(c.Type)
            {
                case "seek": return c.SimTimeSec.HasValue && c.SimTimeSec.Value>=0 &&
                    c.SimTimeSec.Value>=_clock.StartTime.Seconds && c.SimTimeSec.Value<=_clock.EndTime.Seconds ? null : "INVALID_SEEK";
                case "play": case "pause": return null;
                case "setRate":
                    if (!c.Rate.HasValue) return "RATE_REQUIRED";
                    // Exact wire values for eight supported rates; no narrowing-cast tolerance surprises.
                    double r=c.Rate.Value;
                    return r==.25 || r==.5 || r==1 || r==2 || r==4 || r==8 || r==16 || r==32 ? null : "UNSUPPORTED_RATE";
                case "focusVessel": return string.IsNullOrWhiteSpace(c.VesselId) ? "VESSEL_REQUIRED" :
                    _focus==null ? "FOCUS_UNAVAILABLE" : null;
                default: return "UNKNOWN_TYPE";
            }
        }
        private static ReplayApplyResult Result(ReplayCommand c, ReplayApplyStatus s, string code) =>
            new ReplayApplyResult(c?.Seq ?? 0, s, code);
        public ReplayApplyResult Apply(ReplayCommand command)
        {
            string error=Validate(command);
            if(error!=null) return Result(command, ReplayApplyStatus.Rejected, error);
            if(OutcomeUnknown) return Result(command, ReplayApplyStatus.FailedUnknown, "INSTANCE_BLOCKED");
            if(_executing) return Result(command, ReplayApplyStatus.Rejected, "REENTRANT_CALL");
            if(command.Seq<=LastAppliedSeq)
                return _applied.TryGetValue(command.Seq, out var prior) && prior.Equals(command)
                    ? Result(command,ReplayApplyStatus.Duplicate,"ALREADY_APPLIED")
                    : Result(command,ReplayApplyStatus.Rejected,"PAYLOAD_CONFLICT_OR_UNVERIFIABLE_HISTORY");
            if(LastAppliedSeq==long.MaxValue || command.Seq!=LastAppliedSeq+1)
                return Result(command,ReplayApplyStatus.Rejected,"SEQUENCE_GAP");
            _executing=true;
            try
            {
                switch(command.Type)
                {
                    case "seek":
                        _clock.Seek(new SimTime(command.SimTimeSec.Value)); break;
                    case "play": _clock.Play(); break;
                    case "pause": _clock.Pause(); break;
                    case "setRate": _clock.SetRate((float)command.Rate.Value); break;
                    case "focusVessel": _focus(command.VesselId); break;
                }
                _applied.Add(command.Seq,command); LastAppliedSeq=command.Seq;
                return Result(command,ReplayApplyStatus.Applied,"APPLIED");
            }
            catch(Exception)
            {
                OutcomeUnknown=true;
                return Result(command,ReplayApplyStatus.FailedUnknown,"SIDE_EFFECT_OUTCOME_UNKNOWN");
            }
            finally { _executing=false; }
        }
        public IReadOnlyList<ReplayApplyResult> ApplyBatch(IEnumerable<ReplayCommand> commands)
        {
            if(commands==null) throw new ArgumentNullException(nameof(commands));
            var sorted=new SortedDictionary<long,ReplayCommand>();
            var results=new List<ReplayApplyResult>();
            // Entire batch validation before side effects; conflicting repeated payloads never win by ordering.
            foreach(var c in commands)
            {
                string error=Validate(c);
                if(error!=null) { results.Add(Result(c,ReplayApplyStatus.Rejected,error)); return results; }
                if(sorted.TryGetValue(c.Seq,out var existing) && !existing.Equals(c))
                { results.Add(Result(c,ReplayApplyStatus.Rejected,"BATCH_PAYLOAD_CONFLICT")); return results; }
                if(_applied.TryGetValue(c.Seq,out existing) && !existing.Equals(c))
                { results.Add(Result(c,ReplayApplyStatus.Rejected,"PAYLOAD_CONFLICT")); return results; }
                sorted[c.Seq]=c;
            }
            foreach(var c in sorted.Values)
            {
                var r=Apply(c); results.Add(r);
                if(r.Status==ReplayApplyStatus.Rejected || r.Status==ReplayApplyStatus.FailedUnknown) break;
            }
            return results;
        }
        public ReplayStateSnapshot CaptureState() => new ReplayStateSnapshot(CaseId,
            _clock.CurrentTime.Seconds,_clock.IsPlaying,_clock.PlaybackRate);
    }
}
