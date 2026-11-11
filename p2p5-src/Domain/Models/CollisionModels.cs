using System;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Models
{
    /// <summary>碰撞事件与接触点评估数据（对应 ARCHITECTURE 4.8 节）。</summary>
    public sealed class CollisionEvent
    {
        public string EventId { get; }
        public SimTime CollisionTime { get; }
        public string StrikingVesselId { get; }
        public string StruckObjectId { get; }
        public bool IsFixedStructure { get; }
        public GeoCoord ContactGeo { get; }
        public EnuPosition ContactEnu { get; }
        public Double3 ContactPointLocalStruck { get; }
        public float IntersectionAngleDeg { get; }
        public float RelativeNormalSpeedMps { get; }
        public double EstimatedEnergyMJ { get; }
        public DamageSeverity Severity { get; }
        public float EstimatedBreachAreaM2 { get; }
        public float BreachDepthBelowWlM { get; }

        public CollisionEvent(
            string eventId,
            SimTime collisionTime,
            string strikingVesselId,
            string struckObjectId,
            bool isFixedStructure,
            GeoCoord contactGeo,
            EnuPosition contactEnu,
            Double3 contactPointLocalStruck,
            float intersectionAngleDeg,
            float relativeNormalSpeedMps,
            double estimatedEnergyMJ,
            DamageSeverity severity,
            float estimatedBreachAreaM2,
            float breachDepthBelowWlM)
        {
            EventId = eventId ?? string.Empty;
            CollisionTime = collisionTime;
            StrikingVesselId = strikingVesselId ?? string.Empty;
            StruckObjectId = struckObjectId ?? string.Empty;
            IsFixedStructure = isFixedStructure;
            ContactGeo = contactGeo;
            ContactEnu = contactEnu;
            ContactPointLocalStruck = contactPointLocalStruck;
            IntersectionAngleDeg = intersectionAngleDeg;
            RelativeNormalSpeedMps = relativeNormalSpeedMps;
            EstimatedEnergyMJ = estimatedEnergyMJ;
            Severity = severity;
            EstimatedBreachAreaM2 = estimatedBreachAreaM2;
            BreachDepthBelowWlM = breachDepthBelowWlM;
        }
    }

    /// <summary>碰撞后单帧物理烘焙记录（10 Hz 采样）。</summary>
    public readonly struct DamageKeyframe
    {
        public SimTime Time { get; }
        public EnuPosition EnuCenter { get; }
        public float HdgDeg { get; }
        public float RollDeg { get; }
        public float PitchDeg { get; }
        public float SinkHeaveM { get; }
        public float FloodedWaterMassTons { get; }

        public DamageKeyframe(
            SimTime time,
            EnuPosition enuCenter,
            float hdgDeg,
            float rollDeg,
            float pitchDeg,
            float sinkHeaveM,
            float floodedWaterMassTons)
        {
            Time = time;
            EnuCenter = enuCenter;
            HdgDeg = hdgDeg;
            RollDeg = rollDeg;
            PitchDeg = pitchDeg;
            SinkHeaveM = sinkHeaveM;
            FloodedWaterMassTons = floodedWaterMassTons;
        }
    }
}
