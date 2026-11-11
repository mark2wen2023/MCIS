using System;

namespace Mcis.Domain.Timeline
{
    /// <summary>
    /// 时间轴轨道的数据种类。同一种类可来自不同数据源（VDR、AIS、人工记录等），
    /// 冲突检测按“同种类、不同来源”进行比较。
    /// </summary>
    public enum TrackKind
    {
        /// <summary>位置（经纬度）轨道，样本值为 NaN，坐标放在 Position 字段。</summary>
        Position = 0,
        /// <summary>对地航速（节）。</summary>
        SpeedOverGround = 1,
        /// <summary>对地航向（度，真北顺时针）。</summary>
        CourseOverGround = 2,
        /// <summary>船首向（度，真北顺时针）。</summary>
        Heading = 3,
        /// <summary>转向角速度（度/分钟）。</summary>
        RateOfTurn = 4,
        /// <summary>舵角（度，右舵为正）。</summary>
        RudderAngle = 5,
        /// <summary>车钟档位（阶跃取值，实际文本放在 TimelineSample.Text）。</summary>
        EngineTelegraph = 6,
        /// <summary>目标距离（海里）。</summary>
        TargetRange = 7,
        /// <summary>目标方位（度，真北顺时针）。</summary>
        TargetBearing = 8,
        /// <summary>目标位置（经纬度）。</summary>
        TargetPosition = 9,
        /// <summary>音频媒体轨道。</summary>
        Audio = 10,
        /// <summary>雷达截图媒体轨道。</summary>
        RadarImage = 11,
        /// <summary>ECDIS 截屏媒体轨道。</summary>
        EcdisImage = 12,
        /// <summary>其他自定义轨道。</summary>
        Other = 13,

        /// <summary>事件时刻（跨源同名事件对齐后的时刻差冲突，裁定 5；合同 trackKind 枚举含此值）。</summary>
        EventTime = 14
    }

    /// <summary>
    /// 轨道种类的判定与默认单位辅助方法。
    /// </summary>
    public static class TrackKindInfo
    {
        /// <summary>
        /// 判断该种类是否为角度量（对地航向、船首向、目标方位），
        /// 插值、冲突比较时需按最短弧处理并归一到 [0,360)。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>角度量返回 true。</returns>
        public static bool IsAngular(TrackKind kind)
        {
            return kind == TrackKind.CourseOverGround ||
                   kind == TrackKind.Heading ||
                   kind == TrackKind.TargetBearing;
        }

        /// <summary>
        /// 判断该种类是否为阶跃量（车钟档位只在变化时刻跳变，不进行线性插值）。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>阶跃量返回 true。</returns>
        public static bool IsStep(TrackKind kind)
        {
            return kind == TrackKind.EngineTelegraph;
        }

        /// <summary>
        /// 判断该种类是否为媒体轨道（音频、雷达截图、ECDIS 截屏）。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>媒体轨道返回 true。</returns>
        public static bool IsMedia(TrackKind kind)
        {
            return kind == TrackKind.Audio ||
                   kind == TrackKind.RadarImage ||
                   kind == TrackKind.EcdisImage;
        }

        /// <summary>
        /// 返回轨道种类的默认单位字符串。
        /// </summary>
        /// <param name="kind">轨道种类。</param>
        /// <returns>单位文本；无单位时返回空字符串。</returns>
        public static string DefaultUnit(TrackKind kind)
        {
            switch (kind)
            {
                case TrackKind.SpeedOverGround:
                    return "kn";
                case TrackKind.CourseOverGround:
                    return "°";
                case TrackKind.Heading:
                    return "°";
                case TrackKind.RateOfTurn:
                    return "°/min";
                case TrackKind.RudderAngle:
                    return "°";
                case TrackKind.TargetRange:
                    return "nm";
                case TrackKind.TargetBearing:
                    return "°";
                case TrackKind.EventTime:
                    return "s";
                default:
                    return string.Empty;
            }
        }
    }
}
