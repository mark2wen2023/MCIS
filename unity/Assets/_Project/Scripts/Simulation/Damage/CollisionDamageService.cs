using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Damage
{
    /// <summary>船舶或固定物的采样委托与尺度资料。</summary>
    public sealed class CollisionParticipant
    {
        public string Id { get; }
        public bool IsFixed { get; }
        public VesselParticulars Particulars { get; }
        public Func<double, CollisionBodyState> Sampler { get; }

        public CollisionParticipant(string id, VesselParticulars particulars, Func<double, CollisionBodyState> sampler, bool isFixed = false)
        {
            Id = id ?? string.Empty;
            Particulars = particulars;
            Sampler = sampler ?? throw new ArgumentNullException(nameof(sampler));
            IsFixed = isFixed;
        }
    }

    public interface ICollisionDamage : ITimeDriven, ITimelineMarkerProvider
    {
        IReadOnlyList<CollisionEvent> DetectedCollisions { get; }
        bool HasValidBake { get; }

        IReadOnlyList<CollisionEvent> DetectCollisionsOffline(double searchPrecisionSec = 0.05);
        Task<Result<IDamageBakeTrack>> BakePostCollisionAsync(CollisionEvent collision, CancellationToken ct = default);
        void ApplyScriptedSink(ScriptedSinkProfile profile);
        void InvalidateBake(string vesselId = null);
        IDamageBakeTrack GetBakeTrack(string vesselId);
    }

    /// <summary>离线碰撞检测、损伤评估与 10 Hz 烘焙服务（纯逻辑，不依赖 UnityEngine）。</summary>
    public sealed class CollisionDamageService : ICollisionDamage
    {
        private readonly List<CollisionParticipant> _participants = new List<CollisionParticipant>();
        private readonly List<CollisionEvent> _collisions = new List<CollisionEvent>();
        private readonly Dictionary<string, IDamageBakeTrack> _bakes = new Dictionary<string, IDamageBakeTrack>(StringComparer.Ordinal);
        private readonly IGeoConverter _geo;
        private readonly SimTime _rangeStart;
        private readonly SimTime _rangeEnd;

        public int ExecutionPriority { get { return 40; } }
        public IReadOnlyList<CollisionEvent> DetectedCollisions { get { return _collisions; } }
        public bool HasValidBake { get { return _bakes.Count > 0; } }
        public event Action MarkersChanged;

        public CollisionDamageService(IGeoConverter geo, SimTime rangeStart, SimTime rangeEnd)
        {
            _geo = geo;
            _rangeStart = rangeStart;
            _rangeEnd = rangeEnd;
        }

        public void AddParticipant(CollisionParticipant participant)
        {
            if (participant == null)
            {
                return;
            }

            _participants.RemoveAll(p => p.Id == participant.Id);
            _participants.Add(participant);
        }

        public IReadOnlyList<CollisionEvent> DetectCollisionsOffline(double searchPrecisionSec = 0.05)
        {
            _collisions.Clear();
            for (int i = 0; i < _participants.Count; i++)
            {
                for (int j = i + 1; j < _participants.Count; j++)
                {
                    CollisionParticipant a = _participants[i];
                    CollisionParticipant b = _participants[j];
                    if (a.IsFixed && b.IsFixed)
                    {
                        continue;
                    }

                    SimTime? tc = CollisionDetector.FindFirstContactTime(
                        t => a.Sampler(t),
                        t => b.Sampler(t),
                        _rangeStart,
                        _rangeEnd,
                        searchPrecisionSec);
                    if (!tc.HasValue)
                    {
                        continue;
                    }

                    CollisionBodyState sa = a.Sampler(tc.Value.Seconds);
                    CollisionBodyState sb = b.Sampler(tc.Value.Seconds);
                    CollisionBodyState striking = sa;
                    CollisionBodyState struck = sb;
                    // 相对法向速度较大者视为撞击船；固定物永远是被撞方
                    if (a.IsFixed)
                    {
                        striking = sb;
                        struck = sa;
                    }
                    else if (b.IsFixed)
                    {
                        striking = sa;
                        struck = sb;
                    }

                    DamageAssessment assess = DamageModel.Assess(striking, struck);
                    _collisions.Add(CollisionDetector.BuildEvent(tc.Value, striking, struck, _geo, assess));
                }
            }

            RaiseMarkers();
            return _collisions;
        }

        public Task<Result<IDamageBakeTrack>> BakePostCollisionAsync(CollisionEvent collision, CancellationToken ct = default)
        {
            return Task.Run(() => BakePostCollision(collision), ct);
        }

        public Result<IDamageBakeTrack> BakePostCollision(CollisionEvent collision)
        {
            if (collision == null)
            {
                return Result<IDamageBakeTrack>.Fail("COL-E01", "碰撞事件为空");
            }

            string struckId = collision.StruckObjectId;
            CollisionParticipant struck = Find(struckId);
            if (struck == null || struck.IsFixed)
            {
                // 对撞击船也可烘焙（被撞为固定物时）
                struck = Find(collision.StrikingVesselId);
            }

            if (struck == null || struck.Particulars == null)
            {
                return Result<IDamageBakeTrack>.Fail("COL-E02", "找不到可用于烘焙的船舶资料");
            }

            CollisionBodyState state = struck.Sampler(collision.CollisionTime.Seconds);
            DamageBakeTrack track = DamageBakeTrack.BakeFlooding(
                struck.Id,
                collision,
                struck.Particulars,
                state,
                _rangeEnd,
                DamageBakeTrack.DefaultSampleHz,
                FloodingModel.DefaultDischargeCoeff,
                struck.Sampler);
            _bakes[struck.Id] = track;
            return Result<IDamageBakeTrack>.Ok(track);
        }

        public void ApplyScriptedSink(ScriptedSinkProfile profile)
        {
            if (profile == null)
            {
                return;
            }

            CollisionParticipant p = Find(profile.VesselId);
            CollisionBodyState state = p != null
                ? p.Sampler(profile.StartTime.Seconds)
                : new CollisionBodyState(profile.VesselId, EnuPosition.Zero, 0.0, Double2.Zero, 0f, 0f, 0f, false);
            _bakes[profile.VesselId] = DamageBakeTrack.BakeScripted(profile, state);
        }

        public void InvalidateBake(string vesselId = null)
        {
            if (string.IsNullOrEmpty(vesselId))
            {
                _bakes.Clear();
            }
            else
            {
                _bakes.Remove(vesselId);
            }
        }

        public IDamageBakeTrack GetBakeTrack(string vesselId)
        {
            IDamageBakeTrack track;
            return _bakes.TryGetValue(vesselId, out track) ? track : null;
        }

        public void EvaluateTime(SimTime currentTime, SimTime previousTime, bool isSeek)
        {
            // 纯逻辑服务在求值时无需副作用；烘焙由显式调用触发。
        }

        public IReadOnlyList<TimelineMarker> GetMarkers()
        {
            var list = new List<TimelineMarker>();
            for (int i = 0; i < _collisions.Count; i++)
            {
                CollisionEvent c = _collisions[i];
                list.Add(new TimelineMarker(
                    "collision-" + c.EventId,
                    c.CollisionTime,
                    "Collision",
                    "碰撞 " + c.StrikingVesselId + " / " + c.StruckObjectId,
                    RiskLevel.Danger,
                    c.StruckObjectId));
            }

            return list;
        }

        private CollisionParticipant Find(string id)
        {
            for (int i = 0; i < _participants.Count; i++)
            {
                if (_participants[i].Id == id)
                {
                    return _participants[i];
                }
            }

            return null;
        }

        private void RaiseMarkers()
        {
            Action h = MarkersChanged;
            if (h != null)
            {
                h();
            }
        }
    }
}
