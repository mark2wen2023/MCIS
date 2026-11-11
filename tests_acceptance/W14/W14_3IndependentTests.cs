using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Xunit;

namespace Mcis.Acceptance.W14
{
    public class W14_3IndependentTests
    {
        [Theory]
        [InlineData(6.21)] [InlineData(6.25)] [InlineData(6.29)] [InlineData(6.35)]
        public void PhaseShiftedNarrowValleysMatchIndependentHundredthSecondScan(double center)
        {
            var a = new List<KinematicState>(); var b = new List<KinematicState>();
            for (int i=0; i<=200; i++) {
                double t=i*0.1, dip=55*Math.Max(0,1-Math.Abs(t-center)/0.12);
                a.Add(new KinematicState(t,0,0,0,0));
                b.Add(new KinematicState(t,50-dip,200-8*t,180,8));
            }
            var own=WhatIfVessel.FromStates("Own",ManeuverParams.Default(200,20,8000),a);
            var target=WhatIfVessel.FromStates("Target",ManeuverParams.Default(80,16,5000),b);
            var result=ScenarioEvaluator.Evaluate(W14AccFixture.TwoShipSetup(own,target,0,20,0.1),WhatIfScenario.Original());
            double truth=double.PositiveInfinity;
            for(int i=0;i<=2000;i++) {
                double t=i*0.01;
                truth=Math.Min(truth,OrientedBoundingBox.Clearance(Box(result.Tracks["Own"],t),Box(result.Tracks["Target"],t)));
            }
            Assert.False(result.Collision);
            Assert.True(truth<25);
            Assert.InRange(Math.Abs(result.MinClearanceM-truth),0,0.1);
        }
        private static OrientedBoundingBox Box(CounterfactualTrack track,double t) {
            var s=track.SampleAt(t);
            return OrientedBoundingBox.FromVessel(new EnuPosition(s.EastM,s.NorthM,0),s.HeadingDeg,(float)track.LoaM,(float)track.BeamM);
        }
        [Theory]
        [InlineData(0)] [InlineData(1)] [InlineData(2)] [InlineData(3)]
        public void EndpointPlateauAndSeparateValleysRetainGlobalMinimum(int mode) {
            Func<double,double> f=mode==0 ? t=>2+t : mode==1 ? t=>3-t : mode==2 ? t=>7 :
                t=>Math.Min(3+100*(t-0.23)*(t-0.23),2+100*(t-0.78)*(t-0.78));
            double at; double actual=ScenarioEvaluator.GlobalMinimum(0,1,f,0.1,0.01,out at);
            double brute=double.PositiveInfinity;
            for(int i=0;i<=100;i++) brute=Math.Min(brute,f(i*0.01));
            Assert.InRange(Math.Abs(actual-brute),0,0.1);
            Assert.InRange(at,0,1);
        }
        [Fact]
        public void HighTurnWithoutRotRefinesHiddenSubstepValley() {
            var start=new KinematicState(0,0,0,359.96,0);
            var end=new KinematicState(0.1,0,0,0.04,0);
            Func<double,double> f=t=>50-t-10*Math.Max(0,1-Math.Abs(t-0.05)/0.02);
            double at;
            double value=ScenarioEvaluator.MinimumOnGrid(new[]{0.0,0.1,0.2},f,0.01,
                (a,b)=>a<0.1 && ScenarioEvaluator.HighTurnInterval(start,end),out at);
            double brute=double.PositiveInfinity;
            for(int i=0;i<=20;i++) brute=Math.Min(brute,f(i*0.01));
            Assert.InRange(Math.Abs(value-brute),0,0.1);
            Assert.InRange(at,0.049,0.051);
        }
        [Theory]
        [InlineData(359.97,0.04,true)] [InlineData(0.04,359.97,true)]
        [InlineData(359.98,0.02,false)]
        public void HeadingWrapWithUnspecifiedRotUsesActualAngularMotion(double a,double b,bool expected) {
            var start=new KinematicState(0,0,0,a,0);
            var end=new KinematicState(0.1,0,0,b,0);
            Assert.Equal(0,start.RotDegPerSec); Assert.Equal(0,end.RotDegPerSec);
            Assert.Equal(expected,ScenarioEvaluator.HighTurnInterval(start,end));
        }
    }
}
