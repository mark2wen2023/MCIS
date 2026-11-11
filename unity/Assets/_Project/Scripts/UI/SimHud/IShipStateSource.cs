using System;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;

namespace Mcis.UI.SimHud
{
    /// <summary>
    /// 船舶运动学状态只读数据源接口。
    /// 用于将 Mcis.UI 与并行开发的 Ships 模块解耦，可直接包装 IShipTrack 或自定义船舶控制器。
    /// </summary>
    public interface IShipStateSource
    {
        /// <summary>船舶唯一标识。</summary>
        string VesselId { get; }

        /// <summary>HUD 显示船名（如 "LILY 轮"）。</summary>
        string DisplayName { get; }

        /// <summary>角色或船型副标题（如 "本船 / 散货船"）。</summary>
        string SubtitleRole { get; }

        /// <summary>状态徽章文本（如 "压载出港"、"满载进港"）。</summary>
        string StatusBadgeText { get; }

        /// <summary>船舶静态尺度参数（可选）。</summary>
        VesselParticulars Particulars { get; }

        /// <summary>底层完整航迹（供 2D 小地图绘制全时段轨迹与缺口，可选）。</summary>
        IShipTrack Track { get; }

        /// <summary>查询指定仿真时刻的船舶运动学样本。</summary>
        TrackSample SampleStateAt(SimTime time);
    }

    /// <summary>
    /// 基于领域层 <see cref="IShipTrack"/> 或采样委托的默认船舶状态数据源实现。
    /// </summary>
    public sealed class ShipTrackStateSource : IShipStateSource
    {
        private readonly Func<SimTime, TrackSample> _sampler;

        /// <inheritdoc />
        public string VesselId { get; }

        /// <inheritdoc />
        public string DisplayName { get; }

        /// <inheritdoc />
        public string SubtitleRole { get; }

        /// <inheritdoc />
        public string StatusBadgeText { get; set; }

        /// <inheritdoc />
        public VesselParticulars Particulars { get; }

        /// <inheritdoc />
        public IShipTrack Track { get; }

        /// <summary>使用 <see cref="IShipTrack"/> 构造船舶状态数据源。</summary>
        public ShipTrackStateSource(
            IShipTrack track,
            string displayName = null,
            string subtitleRole = null,
            string statusBadgeText = null,
            VesselParticulars particulars = null)
        {
            if (track == null) throw new ArgumentNullException(nameof(track));
            Track = track;
            Particulars = particulars;
            VesselId = track.VesselId ?? (particulars != null ? particulars.VesselId : "Vessel");
            DisplayName = !string.IsNullOrEmpty(displayName)
                ? displayName
                : (particulars != null && !string.IsNullOrEmpty(particulars.Name) ? particulars.Name : VesselId);
            SubtitleRole = subtitleRole ?? (particulars != null ? particulars.VesselTypeCode : string.Empty);
            StatusBadgeText = statusBadgeText ?? (particulars != null ? particulars.LoadingCondition : "在航");
            _sampler = track.SampleAt;
        }

        /// <summary>使用纯采样函数构造船舶状态数据源。</summary>
        public ShipTrackStateSource(
            string vesselId,
            Func<SimTime, TrackSample> sampler,
            string displayName = null,
            string subtitleRole = null,
            string statusBadgeText = null,
            VesselParticulars particulars = null,
            IShipTrack optionalTrack = null)
        {
            if (sampler == null) throw new ArgumentNullException(nameof(sampler));
            VesselId = vesselId ?? "Vessel";
            _sampler = sampler;
            Track = optionalTrack;
            Particulars = particulars;
            DisplayName = !string.IsNullOrEmpty(displayName) ? displayName : VesselId;
            SubtitleRole = subtitleRole ?? string.Empty;
            StatusBadgeText = statusBadgeText ?? "在航";
        }

        /// <inheritdoc />
        public TrackSample SampleStateAt(SimTime time)
        {
            return _sampler(time);
        }
    }

    /// <summary>
    /// 航海仪表盘（HUD / 时间轴）等宽数值格式化工具，统一使用 <see cref="CultureInfo.InvariantCulture"/>。
    /// </summary>
    public static class HudFormatters
    {
        /// <summary>1 节对应的米/秒（1852 / 3600）。</summary>
        public const double MetersPerSecondPerKnot = 1852.0 / 3600.0;

        /// <summary>将纬度（十进制度）格式化为航海度分格式，如 21°47.82'N。</summary>
        public static string FormatLatDegMin(double latDeg)
        {
            if (double.IsNaN(latDeg) || Math.Abs(latDeg) > 90.0)
            {
                return "--°--.--'N";
            }

            char hemi = latDeg >= 0.0 ? 'N' : 'S';
            double abs = Math.Abs(latDeg);
            int deg = (int)Math.Floor(abs);
            double min = (abs - deg) * 60.0;
            if (min >= 59.995)
            {
                deg += 1;
                min = 0.0;
            }
            return string.Format(CultureInfo.InvariantCulture, "{0:D2}°{1:00.00}'{2}", deg, min, hemi);
        }

        /// <summary>将经度（十进制度）格式化为航海度分格式，如 113°42.00'E。</summary>
        public static string FormatLonDegMin(double lonDeg)
        {
            if (double.IsNaN(lonDeg) || Math.Abs(lonDeg) > 180.0)
            {
                return "---°--.--'E";
            }

            char hemi = lonDeg >= 0.0 ? 'E' : 'W';
            double abs = Math.Abs(lonDeg);
            int deg = (int)Math.Floor(abs);
            double min = (abs - deg) * 60.0;
            if (min >= 59.995)
            {
                deg += 1;
                min = 0.0;
            }
            return string.Format(CultureInfo.InvariantCulture, "{0:D3}°{1:00.00}'{2}", deg, min, hemi);
        }

        /// <summary>将 WGS84 坐标格式化为“纬度 经度”度分字符串。</summary>
        public static string FormatGeoDegMin(GeoCoord geo)
        {
            return string.Concat(FormatLatDegMin(geo.LatDeg), " ", FormatLonDegMin(geo.LonDeg));
        }

        /// <summary>将米/秒航速转换为节并格式化（如 "10.5 kn"）。</summary>
        public static string FormatSogKnots(float sogMps)
        {
            double kn = sogMps / MetersPerSecondPerKnot;
            return string.Format(CultureInfo.InvariantCulture, "{0:0.0} kn", kn);
        }

        /// <summary>格式化航向/船首向角度（000.0°）。</summary>
        public static string FormatAngleDeg(double deg)
        {
            if (double.IsNaN(deg)) return "---.-°";
            double norm = deg % 360.0;
            if (norm < 0.0) norm += 360.0;
            return string.Format(CultureInfo.InvariantCulture, "{0:000.0}°", norm);
        }

        /// <summary>格式化相对仿真时长 MM:SS.d。</summary>
        public static string FormatElapsedMinSec(double seconds)
        {
            if (double.IsNaN(seconds) || seconds < 0.0) seconds = 0.0;
            int totalMin = (int)(seconds / 60.0);
            double remSec = seconds - totalMin * 60.0;
            return string.Format(CultureInfo.InvariantCulture, "{0:D2}:{1:00.0}", totalMin, remSec);
        }
    }
}
