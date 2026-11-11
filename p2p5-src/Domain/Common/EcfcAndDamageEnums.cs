using System;

namespace Mcis.Domain.Common
{
    /// <summary>碰撞结构损伤分级（示意级，对应 ARCHITECTURE 4.8 节）。</summary>
    public enum DamageSeverity : byte
    {
        /// <summary>无损伤。</summary>
        None = 0,
        /// <summary>擦碰。</summary>
        Glancing = 1,
        /// <summary>轻微变形（水线以上）。</summary>
        Minor = 2,
        /// <summary>水线附近破损进水。</summary>
        HullBreach = 3,
        /// <summary>水线以下严重破口、快速进水下沉。</summary>
        SevereFlooding = 4
    }

    /// <summary>ECFC 节点类型（对应论文 2.5 节表 4）。</summary>
    public enum EcfcNodeKind : byte
    {
        /// <summary>事件：矩形，主动事项（一个名词 + 一个主动动词）。</summary>
        Event = 0,
        /// <summary>条件：椭圆，被动状态或环境条件。</summary>
        Condition = 1
    }

    /// <summary>ECFC 连线类型（由起止节点类型自动推导）。</summary>
    public enum EcfcEdgeKind : byte
    {
        /// <summary>事件 -&gt; 事件：实线箭头（主序列加粗）。</summary>
        Sequence = 0,
        /// <summary>条件 -&gt; 事件 或 条件 -&gt; 条件：虚线箭头。</summary>
        Influence = 1
    }
}
