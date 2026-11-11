using System;
using System.Globalization;

namespace Mcis.Domain.Common
{
    /// <summary>
    /// 局部切平面东-北-天坐标（单位：米，双精度）。
    /// </summary>
    public readonly struct EnuPosition : IEquatable<EnuPosition>
    {
        /// <summary>原点零位置。</summary>
        public static readonly EnuPosition Zero = new EnuPosition(0.0, 0.0, 0.0);

        /// <summary>东向距离（米）。</summary>
        public double EastM { get; }

        /// <summary>北向距离（米）。</summary>
        public double NorthM { get; }

        /// <summary>天向高度（米）。</summary>
        public double UpM { get; }

        /// <summary>构造局部切平面 ENU 坐标。</summary>
        public EnuPosition(double eastM, double northM, double upM = 0.0)
        {
            EastM = eastM;
            NorthM = northM;
            UpM = upM;
        }

        /// <summary>水平面二维分量 (East, North)。</summary>
        public Double2 Horizontal
        {
            get { return new Double2(EastM, NorthM); }
        }

        /// <summary>转换为三维双精度向量 (East, North, Up)。</summary>
        public Double3 ToDouble3()
        {
            return new Double3(EastM, NorthM, UpM);
        }

        /// <summary>计算与另一 ENU 点的水平欧氏距离（米）。</summary>
        public double HorizontalDistanceTo(EnuPosition other)
        {
            double de = other.EastM - EastM;
            double dn = other.NorthM - NorthM;
            return Math.Sqrt(de * de + dn * dn);
        }

        /// <inheritdoc />
        public bool Equals(EnuPosition other)
        {
            return EastM.Equals(other.EastM) && NorthM.Equals(other.NorthM) && UpM.Equals(other.UpM);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is EnuPosition other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = EastM.GetHashCode();
                hash = (hash * 397) ^ NorthM.GetHashCode();
                hash = (hash * 397) ^ UpM.GetHashCode();
                return hash;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(CultureInfo.InvariantCulture, "ENU({0:F3}m, {1:F3}m, {2:F3}m)", EastM, NorthM, UpM);
        }
    }

    /// <summary>
    /// AIS 消息 5 / 24 尺寸参数（GPS 天线距离船首 A、船尾 B、左舷 C、右舷 D，单位：米）。
    /// 用于将天线定位点修正至船舶几何中心。
    /// </summary>
    public readonly struct AntennaOffset : IEquatable<AntennaOffset>
    {
        /// <summary>零偏移。</summary>
        public static readonly AntennaOffset Zero = new AntennaOffset(0f, 0f, 0f, 0f);

        /// <summary>天线距船首距离 A（米）。</summary>
        public float ToBowA { get; }

        /// <summary>天线距船尾距离 B（米）。</summary>
        public float ToSternB { get; }

        /// <summary>天线距左舷距离 C（米）。</summary>
        public float ToPortC { get; }

        /// <summary>天线距右舷距离 D（米）。</summary>
        public float ToStarboardD { get; }

        /// <summary>构造天线偏移参数。</summary>
        public AntennaOffset(float toBowA, float toSternB, float toPortC, float toStarboardD)
        {
            ToBowA = toBowA;
            ToSternB = toSternB;
            ToPortC = toPortC;
            ToStarboardD = toStarboardD;
        }

        /// <summary>船舶总长 LOA = A + B（米）。</summary>
        public float LoaM
        {
            get { return ToBowA + ToSternB; }
        }

        /// <summary>船舶型宽 Beam = C + D（米）。</summary>
        public float BeamM
        {
            get { return ToPortC + ToStarboardD; }
        }

        /// <summary>
        /// 船中心相对于天线的船体局部偏移（X=横向右舷为正 (C-D)/2 或 (D-C)/2，Y=纵向船首为正 (A-B)/2，单位：米）。
        /// 按 ARCHITECTURE 4.2.5：纵向 Δx = (A - B)/2（前向为正），横向 Δy = (C - D)/2（右舷为正：天线偏左时 C&lt;D，中心在右舷正方向 (D-C)/2；若天线距左舷 C、距右舷 D，船宽中心距左舷 (C+D)/2，故相对天线向右舷偏移为 (D-C)/2，向前偏移为 (A-B)/2）。
        /// 返回 Double2(StarboardOffset, ForwardOffset)。
        /// </summary>
        public Double2 CenterOffsetFromAntenna
        {
            get
            {
                return new Double2(
                    (ToStarboardD - ToPortC) * 0.5,
                    (ToBowA - ToSternB) * 0.5);
            }
        }

        /// <summary>根据船首向（真北顺时针角度）将船体中心相对天线的偏移转换为 ENU 位移增量（米）。</summary>
        public Double2 ToEnuOffset(double headingDeg)
        {
            double rad = headingDeg * (Math.PI / 180.0);
            double sinH = Math.Sin(rad);
            double cosH = Math.Cos(rad);
            double forward = (ToBowA - ToSternB) * 0.5;
            double starboard = (ToStarboardD - ToPortC) * 0.5;
            double dEast = forward * sinH + starboard * cosH;
            double dNorth = forward * cosH - starboard * sinH;
            return new Double2(dEast, dNorth);
        }

        /// <inheritdoc />
        public bool Equals(AntennaOffset other)
        {
            return ToBowA.Equals(other.ToBowA) &&
                   ToSternB.Equals(other.ToSternB) &&
                   ToPortC.Equals(other.ToPortC) &&
                   ToStarboardD.Equals(other.ToStarboardD);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is AntennaOffset other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = ToBowA.GetHashCode();
                hash = (hash * 397) ^ ToSternB.GetHashCode();
                hash = (hash * 397) ^ ToPortC.GetHashCode();
                hash = (hash * 397) ^ ToStarboardD.GetHashCode();
                return hash;
            }
        }
    }

    /// <summary>运动学样本来源标记（贯穿清洗、插值、HUD 显示与报告审计）。</summary>
    public enum SampleProvenance : byte
    {
        /// <summary>原始传感器实测（AIS / VDR GPS）。</summary>
        Measured = 0,
        /// <summary>正常间隔内插值（线性 / Hermite）。</summary>
        Interpolated = 1,
        /// <summary>时间缺口（TimeGap）跨越插值。</summary>
        LowConfidence = 2,
        /// <summary>航位推算外推（DR）。</summary>
        DeadReckoned = 3,
        /// <summary>调查员手绘关键点样条。</summary>
        ManualDrawn = 4,
        /// <summary>操纵模型假设推演或人工推定。</summary>
        Presumed = 5,
        /// <summary>已被异常检测剔除。</summary>
        Rejected = 6
    }

    /// <summary>时间戳质量等级。</summary>
    public enum TimeQuality : byte
    {
        /// <summary>岸基 AIS Tag Block UNIX 秒时间戳或 VDR $GPZDA。</summary>
        ExactTagBlock = 0,
        /// <summary>接收软件日志行前缀时间。</summary>
        LogPrefix = 1,
        /// <summary>利用 AIS 秒字段修正后的就近分钟对齐时间。</summary>
        MinuteAligned = 2,
        /// <summary>无绝对时间，按起始时间与接收顺序推算。</summary>
        Estimated = 3
    }

    /// <summary>AIS 异常点剔除或告警原因代码（兼容 ARCHITECTURE 5.1 与 P1_TASK_A 命名）。</summary>
    public enum RejectReason : byte
    {
        /// <summary>无异常。</summary>
        None = 0,
        /// <summary>NMEA 异或校验和失败。</summary>
        ChecksumError = 1,
        /// <summary>字段非法或不可用值（如 Lon=181, Lat=91）。</summary>
        InvalidField = 2,
        /// <summary>不可用值（同 InvalidField 细分）。</summary>
        Unavailable = 9,
        /// <summary>经纬度或航速数值越界。</summary>
        OutOfRange = 10,
        /// <summary>同 MMSI 时间戳重复。</summary>
        Duplicate = 3,
        /// <summary>时间戳重复（同 Duplicate）。</summary>
        DuplicateTimestamp = 3,
        /// <summary>时间倒序且重排后仍冲突。</summary>
        TimeReversal = 4,
        /// <summary>乱序（同 TimeReversal）。</summary>
        OutOfOrder = 4,
        /// <summary>相邻点隐含航速超过船型物理门限。</summary>
        SpeedGate = 5,
        /// <summary>位置跳变 / 隐含航速超阈（同 SpeedGate）。</summary>
        PositionJump = 5,
        /// <summary>报告 SOG 航速突变超限。</summary>
        SpeedJump = 11,
        /// <summary>航向突变或与位移严重不符。</summary>
        CourseJump = 12,
        /// <summary>前后双向航位推算残差均超限。</summary>
        DrResidual = 6,
        /// <summary>滑动窗口 Hampel 离群滤波剔除。</summary>
        Hampel = 7,
        /// <summary>字段不一致（如 SOG≈0 但位置持续漂移，仅标记不剔除）。</summary>
        Inconsistent = 8
    }

    /// <summary>船舶运动控制模式。</summary>
    public enum ControlMode : byte
    {
        /// <summary>严格按清洗插值后的 AIS 航迹回放。</summary>
        AisReplay = 0,
        /// <summary>调查员海图手绘样条轨迹。</summary>
        DrawnPath = 1,
        /// <summary>Nomoto 操纵模型推演。</summary>
        ManeuverModel = 2,
        /// <summary>碰撞后物理驱动。</summary>
        PhysicsDriven = 3
    }

    /// <summary>航迹插值算法模式。</summary>
    public enum InterpolationMode : byte
    {
        /// <summary>线性插值。</summary>
        Linear = 0,
        /// <summary>三次 Hermite 插值。</summary>
        CubicHermite = 1,
        /// <summary>Catmull-Rom 样条插值。</summary>
        CatmullRom = 2
    }

    /// <summary>时间缺口处理策略。</summary>
    public enum GapPolicy : byte
    {
        /// <summary>Hermite/线性连接但标记 LowConfidence（虚线显示）。</summary>
        ConnectDashed = 0,
        /// <summary>按缺口前最后有效 SOG/COG 航位推算。</summary>
        DeadReckon = 1,
        /// <summary>缺口时段隐藏船舶 / 拒绝外推。</summary>
        HideVessel = 2
    }

    /// <summary>碰撞风险等级。</summary>
    public enum RiskLevel : byte
    {
        /// <summary>安全（青/绿色）。</summary>
        Safe = 0,
        /// <summary>警告（琥珀色）。</summary>
        Warning = 1,
        /// <summary>危险（红色）。</summary>
        Danger = 2
    }
}
