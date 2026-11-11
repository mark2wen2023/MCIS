using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Simulation;
using Xunit;

namespace Mcis.Pure.Tests
{
    public sealed class SimClockTests
    {
        private sealed class DeterministicProbe : ITimeDriven
        {
            public int ExecutionPriority { get; }
            public SimTime LastEvaluatedTime { get; private set; }
            public SimTime LastPreviousTime { get; private set; }
            public bool LastIsSeek { get; private set; }
            public double PurePositionMeters { get; private set; }
            public int EvaluationCount { get; private set; }
            private readonly List<int> _executionOrderLog;

            public DeterministicProbe(int priority, List<int> executionOrderLog = null)
            {
                ExecutionPriority = priority;
                _executionOrderLog = executionOrderLog;
            }

            public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
            {
                LastEvaluatedTime = currentTime;
                LastPreviousTime = previousTime;
                LastIsSeek = isSeek;
                EvaluationCount++;
                // 纯函数状态：f(SimTime) = 5.144444 * t + 0.02 * t^2
                double t = currentTime.Seconds;
                PurePositionMeters = 5.144444 * t + 0.02 * t * t;
                if (_executionOrderLog != null)
                {
                    _executionOrderLog.Add(ExecutionPriority);
                }
            }
        }

        [Fact]
        public void Seek_MatchesContinuousTickFromZero_AcrossManyRandomDeltaSequences()
        {
            float[] rates = new float[] { 0.5f, 1.0f, 2.0f, 4.0f, 8.0f, 16.0f };
            var rng = new Random(20261111);

            for (int trial = 0; trial < 50; trial++)
            {
                float rate = rates[trial % rates.Length];
                double targetSeconds = Math.Round(10.0 + rng.NextDouble() * 500.0, 3);
                long targetTicks = SimClock.SecondsToTicks(targetSeconds);

                var tickClock = new SimClock(0.0, 1000.0);
                var tickProbe = new DeterministicProbe(20);
                tickClock.RegisterTimeDriven(tickProbe);
                tickClock.SetRate(rate);
                tickClock.Play();

                // 使用随机步长序列从 0 连续 Tick 到目标时刻 targetSeconds
                while (tickClock.CurrentTicks < targetTicks)
                {
                    long remainingSimTicks = targetTicks - tickClock.CurrentTicks;
                    long maxStepRealUs = 50_000L; // 1 ~ 50 ms 随机真实帧间隔
                    long randomRealUs = rng.Next(1_000, (int)maxStepRealUs + 1);
                    long stepSimTicks = (long)Math.Round(randomRealUs * (double)rate);

                    double realDeltaSec;
                    if (stepSimTicks >= remainingSimTicks || stepSimTicks <= 0)
                    {
                        realDeltaSec = (remainingSimTicks / (double)SimClock.TicksPerSecond) / rate;
                    }
                    else
                    {
                        realDeltaSec = randomRealUs / (double)SimClock.TicksPerSecond;
                    }

                    tickClock.Tick(realDeltaSec);
                }

                var seekClock = new SimClock(0.0, 1000.0);
                var seekProbe = new DeterministicProbe(20);
                seekClock.RegisterTimeDriven(seekProbe);
                seekClock.SetRate(rate);
                seekClock.Seek(new SimTime(targetSeconds));

                Assert.Equal(targetTicks, tickClock.CurrentTicks);
                Assert.Equal(tickClock.CurrentTicks, seekClock.CurrentTicks);
                Assert.Equal(tickClock.CurrentTime, seekClock.CurrentTime);
                Assert.Equal(
                    BitConverter.DoubleToInt64Bits(tickClock.CurrentTime.Seconds),
                    BitConverter.DoubleToInt64Bits(seekClock.CurrentTime.Seconds));
                Assert.Equal(tickProbe.LastEvaluatedTime, seekProbe.LastEvaluatedTime);
                Assert.Equal(
                    BitConverter.DoubleToInt64Bits(tickProbe.PurePositionMeters),
                    BitConverter.DoubleToInt64Bits(seekProbe.PurePositionMeters));
            }
        }

        [Theory]
        [InlineData(0.5f, 2.0, 1.0)]
        [InlineData(1.0f, 2.0, 2.0)]
        [InlineData(2.0f, 1.5, 3.0)]
        [InlineData(4.0f, 1.25, 5.0)]
        [InlineData(8.0f, 0.5, 4.0)]
        [InlineData(16.0f, 0.25, 4.0)]
        public void PlaybackRates_AdvanceExpectedSimulatedTime(float rate, double realDelta, double expectedSimSeconds)
        {
            var clock = new SimClock(0.0, 100.0);
            clock.SetRate(rate);
            clock.Play();

            clock.Tick(realDelta);

            Assert.Equal(rate, clock.PlaybackRate);
            Assert.Equal(expectedSimSeconds, clock.CurrentTime.Seconds, 9);
        }

        [Fact]
        public void SetRate_RejectsUnsupportedOrInvalidValues()
        {
            var clock = new SimClock(0.0, 100.0);
            Assert.Throws<ArgumentOutOfRangeException>(() => clock.SetRate(0f));
            Assert.Throws<ArgumentOutOfRangeException>(() => clock.SetRate(-1f));
            Assert.Throws<ArgumentOutOfRangeException>(() => clock.SetRate(3.0f));
            Assert.Throws<ArgumentOutOfRangeException>(() => clock.SetRate(float.NaN));
        }

        [Fact]
        public void PausedAndStoppedClock_DoNotAdvanceOnTick()
        {
            var clock = new SimClock(0.0, 60.0);
            Assert.Equal(SimClockState.Paused, clock.State);

            clock.Tick(1.0);
            Assert.Equal(0.0, clock.CurrentTime.Seconds);

            clock.Play();
            clock.Tick(2.0);
            Assert.Equal(2.0, clock.CurrentTime.Seconds);

            clock.Pause();
            clock.Tick(5.0);
            Assert.Equal(2.0, clock.CurrentTime.Seconds);

            clock.Stop();
            Assert.Equal(SimClockState.Stopped, clock.State);
            Assert.Equal(0.0, clock.CurrentTime.Seconds);
            clock.Tick(5.0);
            Assert.Equal(0.0, clock.CurrentTime.Seconds);
        }

        [Fact]
        public void StepForwardAndStepBackward_AndStepFrames_WorkAndPauseIfPlaying()
        {
            var clock = new SimClock(0.0, 20.0);
            clock.Play();

            clock.StepForward(2.5);
            Assert.Equal(SimClockState.Paused, clock.State);
            Assert.Equal(2.5, clock.CurrentTime.Seconds, 6);

            clock.StepForward(); // default 1.0s
            Assert.Equal(3.5, clock.CurrentTime.Seconds, 6);

            clock.StepBackward(1.25);
            Assert.Equal(2.25, clock.CurrentTime.Seconds, 6);

            clock.StepFrames(15, 30); // +0.5s
            Assert.Equal(2.75, clock.CurrentTime.Seconds, 6);

            clock.StepFrames(-30, 30); // -1.0s
            Assert.Equal(1.75, clock.CurrentTime.Seconds, 6);
        }

        [Fact]
        public void RangeClamping_ClampsTickSeekAndStepWithinBounds()
        {
            var clock = new SimClock(10.0, 30.0);
            Assert.Equal(10.0, clock.CurrentTime.Seconds);

            clock.Seek(5.0);
            Assert.Equal(10.0, clock.CurrentTime.Seconds);

            clock.StepBackward(5.0);
            Assert.Equal(10.0, clock.CurrentTime.Seconds);

            clock.Seek(50.0);
            Assert.Equal(30.0, clock.CurrentTime.Seconds);

            clock.StepForward(5.0);
            Assert.Equal(30.0, clock.CurrentTime.Seconds);

            clock.Seek(28.0);
            clock.Play();
            clock.Tick(5.0);
            Assert.Equal(30.0, clock.CurrentTime.Seconds);

            clock.ConfigureRange(12.0, 25.0);
            Assert.Equal(25.0, clock.CurrentTime.Seconds);
        }

        [Fact]
        public void EventCounts_AndTimeDrivenPriorityOrder_AreExact()
        {
            var clock = new SimClock(0.0, 10.0);
            int timeChangedCount = 0;
            int stateChangedCount = 0;
            clock.TimeChanged += _ => timeChangedCount++;
            clock.StateChanged += _ => stateChangedCount++;

            var order = new List<int>();
            clock.RegisterTimeDriven(new DeterministicProbe(50, order));
            clock.RegisterTimeDriven(new DeterministicProbe(10, order));
            clock.RegisterTimeDriven(new DeterministicProbe(30, order));

            clock.Pause(); // already Paused -> 0
            Assert.Equal(0, stateChangedCount);

            clock.Play(); // Paused -> Playing (1)
            clock.Play(); // already Playing (1)
            Assert.Equal(1, stateChangedCount);

            clock.Tick(3.0); // 0 -> 3 (timeChanged: 1)
            Assert.Equal(new int[] { 10, 30, 50 }, order.ToArray());

            clock.Tick(4.0); // 3 -> 7 (timeChanged: 2)
            clock.Tick(5.0); // 7 -> 10 clamped (timeChanged: 3)
            clock.Tick(2.0); // already at 10 -> no change (timeChanged: 3)
            Assert.Equal(3, timeChangedCount);

            clock.Seek(10.0); // unchanged time -> no TimeChanged event (timeChanged: 3)
            Assert.Equal(3, timeChangedCount);

            clock.Seek(4.0); // 10 -> 4 (timeChanged: 4)
            Assert.Equal(4, timeChangedCount);

            clock.Pause(); // Playing -> Paused (2)
            clock.Stop();  // Paused -> Stopped (3), 4 -> 0 (timeChanged: 5)
            Assert.Equal(3, stateChangedCount);
            Assert.Equal(5, timeChangedCount);
        }

        [Fact]
        public void Looping_Scrubbing_AndMarkerJumps_WorkAsExpected()
        {
            var clock = new SimClock(0.0, 10.0) { IsLooping = true };
            clock.Play();
            clock.Tick(12.5);
            Assert.Equal(2.5, clock.CurrentTime.Seconds, 6);

            clock.BeginScrub();
            Assert.Equal(SimClockState.Scrubbing, clock.State);
            clock.Tick(3.0);
            Assert.Equal(2.5, clock.CurrentTime.Seconds, 6);
            clock.EndScrub();
            Assert.Equal(SimClockState.Paused, clock.State);

            clock.SetMarkers(new TimelineMarker[]
            {
                new TimelineMarker("m1", new SimTime(1.0), "ECFC", "Event 1", RiskLevel.Safe),
                new TimelineMarker("m2", new SimTime(5.0), "CPA_Danger", "Danger", RiskLevel.Danger),
                new TimelineMarker("m3", new SimTime(8.5), "Collision", "Impact", RiskLevel.Danger)
            });

            clock.JumpToNextMarker();
            Assert.Equal(5.0, clock.CurrentTime.Seconds, 6);

            clock.JumpToNextMarker("Collision");
            Assert.Equal(8.5, clock.CurrentTime.Seconds, 6);

            clock.JumpToPreviousMarker("ECFC");
            Assert.Equal(1.0, clock.CurrentTime.Seconds, 6);
        }
    }
}
