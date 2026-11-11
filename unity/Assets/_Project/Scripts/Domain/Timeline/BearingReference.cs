namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 方位角参考基准。真方位以真北为基准；相对方位以船首向为基准。
    /// W2.1（D09）：缺船首向时相对方位保留原值并标记为 Relative，不得静默换算为真方位。
    /// </summary>
    public enum BearingReference
    {
        /// <summary>真方位（真北顺时针）。</summary>
        True = 0,
        /// <summary>相对方位（船首向顺时针）。</summary>
        Relative = 1
    }
}
