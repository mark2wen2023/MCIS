using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// What-if 反事实仿真的公共模型假设与免责声明。
    /// </summary>
    public static class WhatIfAssumptions
    {
        /// <summary>固定免责声明。</summary>
        public const string DisclaimerText =
            "仅供分析参考：本结果基于简化操纵模型的反事实推演，不作责任认定。";

        private static readonly ReadOnlyCollection<string> DefaultList =
            new ReadOnlyCollection<string>(new List<string>
            {
                "采用一阶 Nomoto K-T 操纵响应模型：T·dr/dt + r = K·(u/u_ref)·δ，K 随航速按 u/u_ref 线性缩放。",
                "航速采用一阶响应；常规变速、停车与全速后退使用不同时间常数，后退响应更快。",
                "舵机按固定速率限制趋近指令舵角，舵角受最大舵角约束。",
                "不计风、流、浪、浅水、岸壁效应与船间相互作用；无流时 COG=船首向。",
                "偏离时刻之前完全沿原航迹；偏离后由固定步长确定性积分生成，不含随机数与系统时钟。",
                "碰撞判定使用矩形 OBB 分离轴定理；分离时净距取两矩形真实最小距离（顶点-边穷举），重叠时为负的最小穿透深度；首次接触时刻用二分细化，精度 0.05 s；接触点取 OBB 最近点对中点或穿透区形心。",
                "最小净距取全程全局最小 OBB 真实距离：先以 0.5 s 步长粗扫全时段，再在每个局部极小处 ±0.5 s 内以 0.02 s 细扫并黄金分割收敛到 1e-3 s；最小 DCPA 同时给出全时段值与偏离后最小值（全时段值在干预前各情景相同）。",
                "撞击船判定：两船船首到接触点的距离都小于各自 max(10 m, 0.05L) 时判为“船首对船首”，不指定单一撞击船；其余情况取船首离接触点更近的一方为撞击船（不按排水量裁定）。",
                "对比表“临界”：未碰撞且最小净距离安全线（setup 配置，默认 0.1 nm = 185.2 m）不到 5 m，或敏感性区间跨越安全线时标“临界”，并列出敏感性区间。",
                "应急抛锚模型（如使用）：松锚后经过 LetGoToBiteSec 才产生附加恒定减速度与单锚偏转；单锚偏转方向按抛锚舷（右舷向右、左舷向左，双锚为 0）；超过 MaxEffectiveSpeedKn 后减速度按 MaxEffectiveSpeedKn/u 折减；单锚转首率随航速线性衰减，低于 FullYawSpeedKn 时按 (u−MinSpeed)/(FullYawSpeedKn−MinSpeed) 折减，停船后为 0；不计锚链动力学、底质与锚抓力变化，锚参数均为估计。"
            });

        /// <summary>默认中文模型假设列表（只读）。</summary>
        public static IReadOnlyList<string> Default
        {
            get { return DefaultList; }
        }

        /// <summary>创建默认假设列表的可变副本。</summary>
        public static List<string> CreateDefaultList()
        {
            return new List<string>(DefaultList);
        }
    }

    /// <summary>
    /// 情景评价结论。
    /// </summary>
    public enum ScenarioVerdict
    {
        /// <summary>发生碰撞。</summary>
        Collision = 0,
        /// <summary>未碰撞但最小净距小于安全距离。</summary>
        NearMiss = 1,
        /// <summary>未碰撞且净距满足安全距离。</summary>
        Avoided = 2
    }

    /// <summary>
    /// 反事实评价的公共设定：船舶、本船/目标船、时间范围、CPA 与碰撞计算精度、安全距离与案件当地时间基准。
    /// </summary>
    public sealed class WhatIfSetup
    {
        private readonly ReadOnlyCollection<WhatIfVessel> _vessels;

        /// <summary>参与评价的船舶列表。</summary>
        public IReadOnlyList<WhatIfVessel> Vessels
        {
            get { return _vessels; }
        }

        /// <summary>本船标识（CPA 配对中的 Own）。</summary>
        public string OwnVesselId { get; }

        /// <summary>目标船标识（CPA 配对中的 Target）。</summary>
        public string TargetVesselId { get; }

        /// <summary>评价起始仿真时间（秒）。</summary>
        public double StartSeconds { get; }

        /// <summary>评价结束仿真时间（秒）。</summary>
        public double EndSeconds { get; }

        /// <summary>CPA 预计算步长（秒，默认 1.0）。</summary>
        public double CpaStepSeconds { get; }

        /// <summary>碰撞首次接触二分精度（秒，默认 0.05）。</summary>
        public double CollisionPrecisionSec { get; }

        /// <summary>碰撞粗扫描步长（秒，默认 0.5）。</summary>
        public double CollisionCoarseStepSec { get; }

        /// <summary>安全净距（海里，默认 0.1 nm）。</summary>
        public double SafeDistanceNm { get; }

        /// <summary>CPA 风险分级阈值；null 表示使用默认值。</summary>
        public RiskThresholds? Thresholds { get; }

        /// <summary>案件当地时间基准（含时区偏移）；null 表示不输出当地时间。</summary>
        public DateTimeOffset? CaseEpochLocal { get; }

        /// <summary>情景 ENU 坐标原点（经纬度）；给出时碰撞几何输出接触点经纬度。</summary>
        public GeoCoord? EnuOrigin { get; }

        /// <summary>情景共用的输入参数及来源。</summary>
        public IReadOnlyList<SourcedValue> Inputs { get; }

        /// <summary>案例特有假设（如真实案例的航迹截断点、天线改正），评价时追加到每条结果的 Assumptions。</summary>
        public IReadOnlyList<string> CaseAssumptions { get; }

        /// <summary>构造反事实评价设定。</summary>
        public WhatIfSetup(
            IReadOnlyList<WhatIfVessel> vessels,
            string ownVesselId,
            string targetVesselId,
            double startSeconds,
            double endSeconds,
            double cpaStepSeconds = 1.0,
            double collisionPrecisionSec = 0.05,
            double collisionCoarseStepSec = 0.5,
            double safeDistanceNm = 0.1,
            RiskThresholds? thresholds = null,
            DateTimeOffset? caseEpochLocal = null,
            GeoCoord? enuOrigin = null,
            IReadOnlyList<SourcedValue> inputs = null,
            IReadOnlyList<string> caseAssumptions = null)
        {
            if (vessels == null)
            {
                throw new ArgumentNullException(nameof(vessels));
            }
            if (vessels.Count == 0)
            {
                throw new ArgumentException("船舶列表不能为空。", nameof(vessels));
            }
            if (string.IsNullOrWhiteSpace(ownVesselId))
            {
                throw new ArgumentException("本船标识不能为空。", nameof(ownVesselId));
            }
            if (string.IsNullOrWhiteSpace(targetVesselId))
            {
                throw new ArgumentException("目标船标识不能为空。", nameof(targetVesselId));
            }
            if (string.Equals(ownVesselId, targetVesselId, StringComparison.Ordinal))
            {
                throw new ArgumentException("本船与目标船不能相同。", nameof(targetVesselId));
            }
            if (double.IsNaN(startSeconds) || double.IsInfinity(startSeconds) ||
                double.IsNaN(endSeconds) || double.IsInfinity(endSeconds) ||
                endSeconds <= startSeconds)
            {
                throw new ArgumentException("评价时间范围必须为有限值且结束时间大于起始时间。", nameof(endSeconds));
            }
            if (!IsFinitePositive(cpaStepSeconds)) throw new ArgumentOutOfRangeException(nameof(cpaStepSeconds), "CPA 步长必须为有限正数。");
            if (!IsFinitePositive(collisionPrecisionSec)) throw new ArgumentOutOfRangeException(nameof(collisionPrecisionSec), "碰撞精度必须为有限正数。");
            if (!IsFinitePositive(collisionCoarseStepSec)) throw new ArgumentOutOfRangeException(nameof(collisionCoarseStepSec), "碰撞粗扫描步长必须为有限正数。");
            if (double.IsNaN(safeDistanceNm) || double.IsInfinity(safeDistanceNm) || safeDistanceNm < 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(safeDistanceNm), "安全距离必须为非负有限数。");
            }

            _vessels = new ReadOnlyCollection<WhatIfVessel>(new List<WhatIfVessel>(vessels));
            OwnVesselId = ownVesselId;
            TargetVesselId = targetVesselId;
            StartSeconds = startSeconds;
            EndSeconds = endSeconds;
            CpaStepSeconds = cpaStepSeconds;
            CollisionPrecisionSec = collisionPrecisionSec;
            CollisionCoarseStepSec = collisionCoarseStepSec;
            SafeDistanceNm = safeDistanceNm;
            Thresholds = thresholds;
            CaseEpochLocal = caseEpochLocal;
            EnuOrigin = enuOrigin;
            Inputs = new ReadOnlyCollection<SourcedValue>(
                inputs != null ? new List<SourcedValue>(inputs) : new List<SourcedValue>());
            CaseAssumptions = new ReadOnlyCollection<string>(
                caseAssumptions != null ? new List<string>(caseAssumptions) : new List<string>());

            if (FindVessel(ownVesselId) == null)
            {
                throw new ArgumentException("船舶列表中未找到本船：" + ownVesselId, nameof(ownVesselId));
            }
            if (FindVessel(targetVesselId) == null)
            {
                throw new ArgumentException("船舶列表中未找到目标船：" + targetVesselId, nameof(targetVesselId));
            }
        }

        /// <summary>按标识查找船舶；未找到返回 null。</summary>
        public WhatIfVessel FindVessel(string vesselId)
        {
            for (int i = 0; i < _vessels.Count; i++)
            {
                if (string.Equals(_vessels[i].Id, vesselId, StringComparison.Ordinal))
                {
                    return _vessels[i];
                }
            }
            return null;
        }

        /// <summary>安全净距对应的米数。</summary>
        public double SafeDistanceM
        {
            get { return SafeDistanceNm * 1852.0; }
        }

        /// <summary>按当地时间基准格式化仿真秒为 HH:mm:ss.ff。</summary>
        public string FormatLocalTime(double timeSeconds)
        {
            if (!CaseEpochLocal.HasValue)
            {
                return "T+" + timeSeconds.ToString("F2", CultureInfo.InvariantCulture) + "s";
            }
            return CaseEpochLocal.Value
                .AddSeconds(timeSeconds)
                .ToString("HH:mm:ss.ff", CultureInfo.InvariantCulture);
        }

        private static bool IsFinitePositive(double value)
        {
            return !double.IsNaN(value) && !double.IsInfinity(value) && value > 0.0;
        }
    }
}
