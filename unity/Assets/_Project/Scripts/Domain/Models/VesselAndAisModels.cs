using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;

namespace Mcis.Domain.Models
{
    /// <summary>
    /// 船舶分舱简化模型。
    /// </summary>
    public readonly struct CompartmentSpec
    {
        /// <summary>舱室标识。</summary>
        public string CompartmentId { get; }

        /// <summary>舱室名称。</summary>
        public string Name { get; }

        /// <summary>相对船中心的局部坐标 (m)。</summary>
        public Double3 CenterLocalM { get; }

        /// <summary>舱室长宽高包络 (m)。</summary>
        public Double3 SizeM { get; }

        /// <summary>渗透率 μ。</summary>
        public float Permeability { get; }

        /// <summary>构造舱室参数。</summary>
        public CompartmentSpec(
            string compartmentId,
            string name,
            Double3 centerLocalM,
            Double3 sizeM,
            float permeability)
        {
            CompartmentId = compartmentId;
            Name = name;
            CenterLocalM = centerLocalM;
            SizeM = sizeM;
            Permeability = permeability;
        }
    }

    /// <summary>
    /// 船舶静态尺度、识别信息与操纵参数（覆盖 AIS 消息 5 / 19 / 24 静态字段）。
    /// </summary>
    public sealed class VesselParticulars
    {
        /// <summary>船舶内部标识。</summary>
        public string VesselId { get; }

        /// <summary>英文船名（AIS 20 字符船名）。</summary>
        public string Name { get; }

        /// <summary>中文船名（可选）。</summary>
        public string NameCn { get; }

        /// <summary>9 位水上移动通信业务标识码 MMSI。</summary>
        public string Mmsi { get; }

        /// <summary>IMO 编号。</summary>
        public string ImoNumber { get; }

        /// <summary>呼号（Call Sign）。</summary>
        public string CallSign { get; }

        /// <summary>船旗国。</summary>
        public string FlagState { get; }

        /// <summary>AIS 船型代码数字（如 70=货船, 80=油轮）。</summary>
        public int ShipTypeCodeNumber { get; }

        /// <summary>船型分类标识字符串。</summary>
        public string VesselTypeCode { get; }

        /// <summary>船模预制体资源键。</summary>
        public string ModelPrefabKey { get; }

        /// <summary>总长 LOA (m)。</summary>
        public float LoaM { get; }

        /// <summary>型宽 Beam (m)。</summary>
        public float BeamM { get; }

        /// <summary>首吃水 (m)。</summary>
        public float DraftForeM { get; }

        /// <summary>尾吃水 (m)。</summary>
        public float DraftAftM { get; }

        /// <summary>型深 (m)。</summary>
        public float MoldedDepthM { get; }

        /// <summary>排水量 (t)。</summary>
        public float DisplacementTons { get; }

        /// <summary>载况。</summary>
        public string LoadingCondition { get; }

        /// <summary>AIS 天线距首尾左右舷尺寸偏移 (A, B, C, D)。</summary>
        public AntennaOffset AntennaOffset { get; }

        /// <summary>目的港（AIS 消息 5）。</summary>
        public string Destination { get; }

        /// <summary>驾驶台眼高局部坐标（相对船中心）。</summary>
        public Double3 BridgeEyeLocalM { get; }

        /// <summary>一阶 Nomoto 旋回性指数 K (1/s)。</summary>
        public float NomotoK { get; }

        /// <summary>一阶 Nomoto 追随性指数 T (s)。</summary>
        public float NomotoT { get; }

        /// <summary>分舱列表。</summary>
        public IReadOnlyList<CompartmentSpec> Compartments { get; }

        /// <summary>构造完整船舶静态资料。</summary>
        public VesselParticulars(
            string vesselId,
            string name,
            string nameCn,
            string Mmsi,
            string imoNumber,
            string callSign,
            string flagState,
            string vesselTypeCode,
            string modelPrefabKey,
            float loaM,
            float beamM,
            float draftForeM,
            float draftAftM,
            float moldedDepthM,
            float displacementTons,
            string loadingCondition,
            AntennaOffset antennaOffset,
            Double3 bridgeEyeLocalM,
            float nomotoK,
            float nomotoT,
            IReadOnlyList<CompartmentSpec> compartments = null,
            int shipTypeCodeNumber = 0,
            string destination = null)
        {
            VesselId = vesselId ?? Mmsi ?? string.Empty;
            Name = name ?? string.Empty;
            NameCn = nameCn;
            this.Mmsi = Mmsi ?? string.Empty;
            ImoNumber = imoNumber;
            CallSign = callSign;
            FlagState = flagState ?? string.Empty;
            VesselTypeCode = vesselTypeCode ?? string.Empty;
            ModelPrefabKey = modelPrefabKey ?? string.Empty;
            LoaM = loaM;
            BeamM = beamM;
            DraftForeM = draftForeM;
            DraftAftM = draftAftM;
            MoldedDepthM = moldedDepthM;
            DisplacementTons = displacementTons;
            LoadingCondition = loadingCondition ?? "FullLoad";
            AntennaOffset = antennaOffset;
            BridgeEyeLocalM = bridgeEyeLocalM;
            NomotoK = nomotoK;
            NomotoT = nomotoT;
            Compartments = compartments ?? Array.Empty<CompartmentSpec>();
            ShipTypeCodeNumber = shipTypeCodeNumber;
            Destination = destination ?? string.Empty;
        }
    }

    /// <summary>
    /// 单条清洗前的 AIS 解码原始记录。
    /// </summary>
    public readonly struct AisDecodedRecord
    {
        /// <summary>原始文件行号（从 1 开始）。</summary>
        public int SourceLineNumber { get; }

        /// <summary>原始 NMEA 或 CSV 行文本。</summary>
        public string RawSentence { get; }

        /// <summary>AIS 消息类型（1, 2, 3, 5, 18, 19, 24；CSV 导入为 0）。</summary>
        public int MessageType { get; }

        /// <summary>9 位 MMSI 字符串。</summary>
        public string Mmsi { get; }

        /// <summary>UTC 时间戳。</summary>
        public DateTimeOffset TimestampUtc { get; }

        /// <summary>时间质量标记。</summary>
        public TimeQuality TimeQuality { get; }

        /// <summary>经度（十进制度，181.0 表示不可用）。</summary>
        public double LonDeg { get; }

        /// <summary>纬度（十进制度，91.0 表示不可用）。</summary>
        public double LatDeg { get; }

        /// <summary>对地航速 SOG（节，102.3f 表示不可用）。</summary>
        public float SogKn { get; }

        /// <summary>对地航向 COG（度，360.0f 表示不可用）。</summary>
        public float CogDeg { get; }

        /// <summary>真船首向 HDG（度，511f 表示不可用）。</summary>
        public float HdgDeg { get; }

        /// <summary>转向率 ROT（度/分钟，float.NaN 表示不可用）。</summary>
        public float RotDegPerMin { get; }

        /// <summary>原始 AIS ROT 字段整数值（-128 表示不可用）。</summary>
        public sbyte RawRot { get; }

        /// <summary>航行状态（0..15）。</summary>
        public byte NavStatus { get; }

        /// <summary>时间戳秒字段（0..59，60+ 表示不可用）。</summary>
        public byte TimestampSecond { get; }

        /// <summary>经度是否可用（|Lon| &lt;= 180）。</summary>
        public bool IsPositionValid
        {
            get { return LonDeg >= -180.0 && LonDeg <= 180.0 && LatDeg >= -90.0 && LatDeg <= 90.0; }
        }

        /// <summary>SOG 是否有效（&lt; 102.25 kn 且 &gt;= 0）。</summary>
        public bool IsSogValid
        {
            get { return !float.IsNaN(SogKn) && SogKn >= 0f && SogKn < 102.25f; }
        }

        /// <summary>COG 是否有效（[0, 360)）。</summary>
        public bool IsCogValid
        {
            get { return !float.IsNaN(CogDeg) && CogDeg >= 0f && CogDeg < 360.0f; }
        }

        /// <summary>HDG 是否有效（[0, 360)）。</summary>
        public bool IsHdgValid
        {
            get { return !float.IsNaN(HdgDeg) && HdgDeg >= 0f && HdgDeg < 360.0f; }
        }

        /// <summary>构造 AIS 解码记录。</summary>
        public AisDecodedRecord(
            int sourceLineNumber,
            string rawSentence,
            int messageType,
            string mmsi,
            DateTimeOffset timestampUtc,
            TimeQuality timeQuality,
            double lonDeg,
            double latDeg,
            float sogKn,
            float cogDeg,
            float hdgDeg,
            float rotDegPerMin,
            byte navStatus,
            sbyte rawRot = -128,
            byte timestampSecond = 60)
        {
            SourceLineNumber = sourceLineNumber;
            RawSentence = rawSentence ?? string.Empty;
            MessageType = messageType;
            Mmsi = mmsi ?? string.Empty;
            TimestampUtc = timestampUtc;
            TimeQuality = timeQuality;
            LonDeg = lonDeg;
            LatDeg = latDeg;
            SogKn = sogKn;
            CogDeg = cogDeg;
            HdgDeg = hdgDeg;
            RotDegPerMin = rotDegPerMin;
            NavStatus = navStatus;
            RawRot = rawRot;
            TimestampSecond = timestampSecond;
        }
    }
}
