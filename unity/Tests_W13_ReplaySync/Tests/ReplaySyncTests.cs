using System;
using System.Collections.Generic;
using System.Text.Json;
using Mcis.Core;
using Mcis.Simulation;
using Mcis.Presentation.ReplaySync;
using Xunit;
public class ReplaySyncTests
{
    private sealed class Driven : ITimeDriven
    {
        public int ExecutionPriority=>20;
        public readonly List<(double,double,bool)> Calls=new List<(double,double,bool)>();
        public void EvaluateTime(SimTime c,SimTime p,bool seek)=>Calls.Add((c.Seconds,p.Seconds,seek));
    }
    private static ReplayCommand C(long seq,string type="seek",double? time=10,double? rate=null,string vessel=null,string id="case") =>
        new ReplayCommand(seq,id,type,time,rate,vessel);
    [Theory][InlineData(0)][InlineData(10.1234564)][InlineData(100)]
    public void SeekRealClock(double t)
    {
        var clock=new SimClock(0,100); var d=new Driven(); clock.RegisterTimeDriven(d);
        var a=new ReplayCommandAdapter("case",clock);
        Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(1,time:t)).Status);
        Assert.InRange(Math.Abs(clock.CurrentTime.Seconds-t),0,0.000001);
        Assert.True(d.Calls[0].Item3); Assert.Equal(d.Calls[0].Item1,d.Calls[0].Item2);
        Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(2,time:t)).Status); Assert.Equal(2,d.Calls.Count);
    }
    [Theory][InlineData(.25)][InlineData(.5)][InlineData(1)][InlineData(2)][InlineData(4)][InlineData(8)][InlineData(16)][InlineData(32)]
    public void PlayRatePause(double rate)
    {
        var clock=new SimClock(0,100);var a=new ReplayCommandAdapter("case",clock);
        a.Apply(C(1,"setRate",rate:rate));a.Apply(C(2,"play"));clock.Tick(1);
        Assert.Equal(rate,clock.CurrentTime.Seconds);a.Apply(C(3,"pause"));clock.Tick(1);
        var snapshot=a.CaptureState();Assert.False(snapshot.Playing);Assert.Equal(rate,snapshot.Rate);
        Assert.Equal(rate,snapshot.SimTimeSec);Assert.Equal("case",snapshot.CaseId);Assert.Equal("unity",snapshot.Source);
    }
    [Theory][InlineData(-1)][InlineData(100.0000001)][InlineData(double.NaN)][InlineData(double.PositiveInfinity)][InlineData(double.MaxValue)]
    public void InvalidSeekNoEffect(double t)
    { var clock=new SimClock(0,100);var a=new ReplayCommandAdapter("case",clock);Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,time:t)).Status);Assert.Equal(0,a.LastAppliedSeq);Assert.Equal(0,clock.CurrentTicks); }
    [Theory][InlineData(null)][InlineData(3.0)][InlineData(double.NaN)][InlineData(1.0000001)]
    public void InvalidRateNoEffect(double? rate)
    {var clock=new SimClock(0,100);var a=new ReplayCommandAdapter("case",clock);Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,"setRate",rate:rate)).Status);Assert.Equal(1,clock.PlaybackRate);Assert.Equal(0,a.LastAppliedSeq);}
    [Fact] public void CaseBeforeDedupAndPayloadConflict()
    {
        var clock=new SimClock(0,100);var a=new ReplayCommandAdapter("case",clock);a.Apply(C(1));
        Assert.Equal(ReplayApplyStatus.Duplicate,a.Apply(C(1)).Status);
        Assert.Equal("CASE_MISMATCH",a.Apply(C(1,id:"other")).Code);
        Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,time:11)).Status);
        Assert.Equal(10,clock.CurrentTime.Seconds);
    }
    [Fact] public void SortedBatchAndGap()
    {
        var a=new ReplayCommandAdapter("case",new SimClock(0,100));
        var r=a.ApplyBatch(new[]{C(2),C(1),C(1),C(4)});
        Assert.Equal(3,r.Count);Assert.Equal(2,a.LastAppliedSeq);Assert.Equal("SEQUENCE_GAP",r[2].Code);
        Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(3)).Status);
    }
    [Fact] public void ConflictingBatchPreflight()
    {var clock=new SimClock(0,100);var a=new ReplayCommandAdapter("case",clock);var r=a.ApplyBatch(new[]{C(1),C(2),C(2,time:11)});Assert.Equal("BATCH_PAYLOAD_CONFLICT",r[0].Code);Assert.Equal(0,a.LastAppliedSeq);Assert.Equal(0,clock.CurrentTicks);}
    [Fact] public void BadParameterInLaterCommandPreflight()
    {var a=new ReplayCommandAdapter("case",new SimClock(0,100));a.ApplyBatch(new[]{C(1),C(2,time:double.NaN)});Assert.Equal(0,a.LastAppliedSeq);}
    [Fact] public void ConfirmedCursorAndLifecycle()
    {var a=new ReplayCommandAdapter("case",new SimClock(0,100),confirmedSeq:10);Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(10)).Status);Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(11)).Status);}
    [Fact] public void FocusIntentDedup()
    {int n=0;var a=new ReplayCommandAdapter("case",new SimClock(0,100),v=>{Assert.Equal("v1",v);n++;});var c=C(1,"focusVessel",vessel:"v1");a.Apply(c);a.Apply(c);Assert.Equal(1,n);}
    [Fact] public void FailedFocusIsUncertainAndBlocked()
    {int n=0;var a=new ReplayCommandAdapter("case",new SimClock(0,100),v=>{n++;throw new Exception();});var c=C(1,"focusVessel",vessel:"v1");Assert.Equal(ReplayApplyStatus.FailedUnknown,a.Apply(c).Status);Assert.Equal(ReplayApplyStatus.FailedUnknown,a.Apply(c).Status);Assert.True(a.OutcomeUnknown);Assert.Equal(0,a.LastAppliedSeq);Assert.Equal(1,n);}
    [Fact] public void ClockEventMayThrowAfterSideEffect()
    {var clock=new SimClock(0,100);clock.TimeChanged+=t=>throw new Exception();var a=new ReplayCommandAdapter("case",clock);Assert.Equal(ReplayApplyStatus.FailedUnknown,a.Apply(C(1)).Status);Assert.Equal(10,clock.CurrentTime.Seconds);Assert.Equal(0,a.LastAppliedSeq);}
    [Theory][InlineData("unknown")][InlineData("focusVessel")][InlineData("seek")]
    public void MissingOrUnknownRejected(string type)
    {var a=new ReplayCommandAdapter("case",new SimClock(0,100));Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,type,time:null)).Status);}
    [Fact] public void ServiceWireFieldsMappedInTestOnly()
    {
        using var json=JsonDocument.Parse("{\"seq\":1,\"caseId\":\"case\",\"type\":\"seek\",\"simTimeSec\":12.3,\"rate\":null,\"vesselId\":null,\"reason\":\"evidence\",\"createdUtc\":\"2026-11-12T00:00:00Z\",\"issuedBy\":\"tester\"}");
        var j=json.RootElement;
        var c=new ReplayCommand(j.GetProperty("seq").GetInt64(),j.GetProperty("caseId").GetString(),j.GetProperty("type").GetString(),j.GetProperty("simTimeSec").GetDouble(),reason:j.GetProperty("reason").GetString(),createdUtc:j.GetProperty("createdUtc").GetString(),issuedBy:j.GetProperty("issuedBy").GetString());
        var a=new ReplayCommandAdapter("case",new SimClock(0,100));Assert.Equal(ReplayApplyStatus.Applied,a.Apply(c).Status);Assert.Equal(12.3,a.CaptureState().SimTimeSec);
    }
    [Fact] public void ReentrantCallbackCannotAdvanceCursor()
    {
        ReplayCommandAdapter a=null;ReplayApplyResult nested=null;
        a=new ReplayCommandAdapter("case",new SimClock(0,100),v=>nested=a.Apply(C(1,"play")));
        Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(1,"focusVessel",vessel:"v")).Status);
        Assert.Equal("REENTRANT_CALL",nested.Code);Assert.Equal(1,a.LastAppliedSeq);
    }
    [Fact] public void SameTimeSeekEvaluatesWithoutTimeChanged()
    {
        var clock=new SimClock(0,100);int n=0;clock.TimeChanged+=t=>n++;
        var d=new Driven();clock.RegisterTimeDriven(d);var a=new ReplayCommandAdapter("case",clock);
        a.Apply(C(1,time:0));Assert.Single(d.Calls);Assert.Equal(0,n);
    }
    [Fact] public void SnapshotDoesNotEvaluateOrMutate()
    {
        var clock=new SimClock(0,100);var d=new Driven();clock.RegisterTimeDriven(d);
        var a=new ReplayCommandAdapter("case",clock);a.CaptureState();a.CaptureState();Assert.Empty(d.Calls);Assert.Equal(0,a.LastAppliedSeq);
    }
}
