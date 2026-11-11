using Mcis.Core;

namespace Mcis.Domain.Colreg
{
    /// <summary>与交换合同同名的船舶状态，用于 R18 责任判断。</summary>
    public enum ColregVesselStatus
    {
        PowerDriven,
        NotUnderCommand,
        RestrictedManoeuvrability,
        ConstrainedByDraught,
        Fishing,
        Sailing,
        Unknown
    }

    /// <summary>船舶状态样本；自该时刻起阶梯保持，首个样本前为 Unknown。</summary>
    public sealed class ColregVesselStatusSample
    {
        public string VesselId { get; }
        public SimTime Time { get; }
        public ColregVesselStatus Status { get; }

        public ColregVesselStatusSample(string vesselId, SimTime time, ColregVesselStatus status)
        {
            VesselId = vesselId;
            Time = time;
            Status = status;
        }
    }

    /// <summary>合同中固定使用的 snake_case 存疑原因。</summary>
    public static class ColregDoubtReasons
    {
        public const string HeadOnDoubt = "head_on_doubt";
        public const string ContradictoryViews = "contradictory_views";
        public const string LockedDuringTurn = "locked_during_turn";
        public const string PendingStableHeading = "pending_stable_heading";
        public const string AxisView = "axis_view";
        public const string VesselStatusReview = "vessel_status_review";
    }

    /// <summary>Domain 到交换合同名称的纯映射，不承担 JSON 序列化。</summary>
    public static class ColregContractNames
    {
        /// <summary>合同映射：CollisionRisk→None，其余同名；会遇类型仍保留在 Situation。</summary>
        public static string DangerStage(ColregDangerStage value)
        {
            return value == ColregDangerStage.CollisionRisk ? "None" : value.ToString();
        }

        /// <summary>合同映射：Satisfied→Complies、NotSatisfied→NotComplied，其余同名；保留需研判和缺证据的区别。</summary>
        public static string Verdict(RuleCheckStatus value)
        {
            if (value == RuleCheckStatus.Satisfied) return "Complies";
            if (value == RuleCheckStatus.NotSatisfied) return "NotComplied";
            return value.ToString();
        }

        /// <summary>合同映射：NoCollisionRisk→NoRisk，其余会遇类型同名，不按危险阶段更改局面。</summary>
        public static string Situation(EncounterSituation value)
        {
            return value == EncounterSituation.NoCollisionRisk ? "NoRisk" : value.ToString();
        }
    }
}
