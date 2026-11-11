using System;
using System.Linq;
using Mcis.Core;
using Mcis.Simulation;
using Mcis.Presentation.ReplaySync;
using Xunit;

namespace Mcis.Acceptance.W13 {
 public class ReplayAcceptanceTests {
  const string Case="CASE-ACCEPTANCE";
  static SimClock Clock() { var c=new SimClock();c.ConfigureRange(new SimTime(0),new SimTime(100));return c; }
  static ReplayCommand C(long seq,string type="seek",double? time=10,double? rate=null,string vessel=null,string caseId=Case)
   =>new ReplayCommand(seq,caseId,type,time,rate,vessel);
  [Fact] public void RealClockSeekPlayRatePauseAndImmutableSnapshot() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(1,time:12.345678)).Status);
   Assert.True(Math.Abs(c.CurrentTime.Seconds-12.345678)<0.1);
   var snap=a.CaptureState();
   Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(2,"setRate",null,4)).Status);
   a.Apply(C(3,"play",null));c.Tick(.25);Assert.Equal(13.345678,c.CurrentTime.Seconds,6);
   a.Apply(C(4,"pause",null));c.Tick(10);Assert.Equal(13.345678,c.CurrentTime.Seconds,6);
   Assert.Equal(12.345678,snap.SimTimeSec,6);Assert.False(snap.Playing);Assert.Equal(1,snap.Rate);
   Assert.All(typeof(ReplayStateSnapshot).GetProperties(),p=>Assert.Null(p.SetMethod));
   Assert.Equal(Case,snap.CaseId);Assert.Equal("unity",snap.Source);
  }
  [Fact] public void CaseMismatchCannotMasqueradeAsDuplicate() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);a.Apply(C(1));
   Assert.Equal("CASE_MISMATCH",a.Apply(C(1,caseId:"OTHER")).Code);
   Assert.Equal(ReplayApplyStatus.Duplicate,a.Apply(C(1)).Status);
   Assert.Equal(10,c.CurrentTime.Seconds);Assert.Equal(1,a.LastAppliedSeq);
  }
  [Fact] public void OutOfOrderBatchSortsAndCoalescesExactDuplicate() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   var r=a.ApplyBatch(new[]{C(3,time:30),C(1),C(2,time:20),C(1)});
   Assert.Equal(3,r.Count);Assert.All(r,x=>Assert.Equal(ReplayApplyStatus.Applied,x.Status));
   Assert.Equal(30,c.CurrentTime.Seconds);Assert.Equal(3,a.LastAppliedSeq);
  }
  [Fact] public void GapStopsAtLastContiguousSuccessAndMayResumeExplicitly() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   var r=a.ApplyBatch(new[]{C(1),C(3,time:30)});
   Assert.Equal("SEQUENCE_GAP",r.Last().Code);Assert.Equal(1,a.LastAppliedSeq);Assert.Equal(10,c.CurrentTime.Seconds);
   Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(2,time:20)).Status);
  }
  [Fact] public void ConflictingBatchPayloadHasNoEarlierSideEffect() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   Assert.Equal("BATCH_PAYLOAD_CONFLICT",Assert.Single(a.ApplyBatch(new[]{C(1),C(2),C(2,time:40)})).Code);
   Assert.Equal(0,c.CurrentTime.Seconds);Assert.Equal(0,a.LastAppliedSeq);
  }
  [Fact] public void AppliedSequencePayloadConflictDoesNotReplay() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);a.Apply(C(1));
   Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,time:11)).Status);Assert.Equal(10,c.CurrentTime.Seconds);
  }
  [Theory] [InlineData(-.0000001)] [InlineData(100.0000001)] [InlineData(double.NaN)] [InlineData(double.PositiveInfinity)]
  public void InvalidSeekRejectedBeforeClockOrCursorMutation(double time) {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);int calls=0;c.TimeChanged+=_=>calls++;
   Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,time:time)).Status);
   Assert.Equal(0,calls);Assert.Equal(0,a.LastAppliedSeq);Assert.Equal(0,c.CurrentTime.Seconds);
  }
  [Theory] [InlineData(0)] [InlineData(3)] [InlineData(256)] [InlineData(1.0000001)] [InlineData(double.NaN)]
  public void UnsupportedRateRejectedBeforeMutation(double rate) {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   Assert.Equal(ReplayApplyStatus.Rejected,a.Apply(C(1,"setRate",null,rate)).Status);
   Assert.Equal(1,c.PlaybackRate);Assert.Equal(0,a.LastAppliedSeq);
  }
  [Fact] public void InvalidBatchMemberPreventsAllEffects() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);
   a.ApplyBatch(new[]{C(1),C(2,"focusVessel",null,vessel:" ")});
   Assert.Equal(0,a.LastAppliedSeq);Assert.Equal(0,c.CurrentTime.Seconds);
  }
  [Fact] public void RealSeekSubscriberFailureHasAlreadyChangedClockAndLocksRetry() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c);int n=0;
   c.TimeChanged+=_=>{n++;throw new InvalidOperationException("after mutation");};
   Assert.Equal(ReplayApplyStatus.FailedUnknown,a.Apply(C(1)).Status);
   Assert.Equal(10,c.CurrentTime.Seconds);Assert.Equal(0,a.LastAppliedSeq);Assert.True(a.OutcomeUnknown);
   Assert.Equal("INSTANCE_BLOCKED",a.Apply(C(1)).Code);
   Assert.Equal("INSTANCE_BLOCKED",a.Apply(C(2,"play",null)).Code);Assert.Equal(1,n);Assert.False(c.IsPlaying);
  }
  [Fact] public void FocusIntentFailureLocksWithoutClaimingCameraCompletion() {
   int calls=0;var a=new ReplayCommandAdapter(Case,Clock(),v=>{calls++;throw new Exception();});
   Assert.Equal(ReplayApplyStatus.FailedUnknown,a.Apply(C(1,"focusVessel",null,vessel:"VESSEL-A")).Status);
   a.Apply(C(1,"focusVessel",null,vessel:"VESSEL-A"));Assert.Equal(1,calls);Assert.Equal(0,a.LastAppliedSeq);
  }
  [Fact] public void ExplicitCheckpointCannotVerifyHistoricPayloadAndDoesNotPersistClock() {
   var c=Clock();var a=new ReplayCommandAdapter(Case,c,confirmedSeq:7);
   Assert.Equal("PAYLOAD_CONFLICT_OR_UNVERIFIABLE_HISTORY",a.Apply(C(7)).Code);
   Assert.Equal(0,c.CurrentTime.Seconds);Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(8)).Status);
   var fresh=new ReplayCommandAdapter(Case,Clock());Assert.Equal("SEQUENCE_GAP",fresh.Apply(C(8)).Code);
  }
  [Fact] public void ReentrantCallbackCannotApplySecondCommandDuringFirst() {
   var c=Clock();ReplayCommandAdapter a=null;ReplayApplyResult nested=null;
   a=new ReplayCommandAdapter(Case,c,v=>nested=a.Apply(C(2,"play",null)));
   Assert.Equal(ReplayApplyStatus.Applied,a.Apply(C(1,"focusVessel",null,vessel:"V1")).Status);
   Assert.Equal("REENTRANT_CALL",nested.Code);Assert.Equal(1,a.LastAppliedSeq);Assert.False(c.IsPlaying);
  }
 }
}
