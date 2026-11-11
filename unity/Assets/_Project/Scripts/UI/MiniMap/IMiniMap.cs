using System;
using Mcis.Domain.Common;
using UnityEngine;

namespace Mcis.UI.MiniMap
{
    /// <summary>
    /// 2D 小地图图层可见性位掩码（对应 ARCHITECTURE.md 5.3.11 节）。
    /// </summary>
    [Flags]
    public enum MiniMapLayers : uint
    {
        /// <summary>无图层。</summary>
        None = 0,
        /// <summary>岸线与航道边界。</summary>
        CoastlineAndChannel = 1 << 0,
        /// <summary>经纬/米制网格线。</summary>
        LatLonGrid = 1 << 1,
        /// <summary>双船完整航迹线。</summary>
        FullTracks = 1 << 2,
        /// <summary>时间缺口虚线段。</summary>
        TimeGapDashed = 1 << 3,
        /// <summary>船舶船首向三角图标与速度矢量线。</summary>
        VesselIconsAndVectors = 1 << 4,
        /// <summary>DCPA/TCPA 预测点与风险连线。</summary>
        CpaConnectors = 1 << 5,
        /// <summary>ECFC 事件位置标记。</summary>
        EcfcMarkers = 1 << 6,
        /// <summary>三维摄像机视锥朝向。</summary>
        CameraFrustum = 1 << 7,
        /// <summary>全部图层。</summary>
        All = 0xFFFFFFFF
    }

    /// <summary>
    /// 基于 UI Toolkit <see cref="UnityEngine.UIElements.Painter2D"/> 的 ECDIS 风格 2D 矢量小地图接口（对应 ARCHITECTURE.md 5.3.11 节）。
    /// </summary>
    public interface IMiniMap
    {
        /// <summary>当前视口中心对应的局部 ENU 坐标（米）。</summary>
        EnuPosition CenterEnu { get; }

        /// <summary>当前缩放比例（每像素对应的米数）。</summary>
        float MetersPerPixel { get; }

        /// <summary>是否自动跟随本船位置居中。</summary>
        bool IsFollowingOwnVessel { get; }

        /// <summary>当前启用显示的图层掩码。</summary>
        MiniMapLayers VisibleLayers { get; set; }

        /// <summary>设置是否跟随本船。</summary>
        void SetFollowOwnVessel(bool follow);

        /// <summary>平移视口中心至指定 ENU 坐标。</summary>
        void PanToEnu(EnuPosition centerEnu);

        /// <summary>设置缩放比例（米/像素）。</summary>
        void SetZoom(float metersPerPixel);

        /// <summary>自适应缩放并居中以完整容纳全部船舶航迹。</summary>
        void ZoomToFitAllTracks(float paddingRatio = 0.15f);

        /// <summary>将元素局部像素坐标转换为局部 ENU 坐标。</summary>
        EnuPosition ScreenPointToEnu(Vector2 localPanelPos);

        /// <summary>将局部 ENU 坐标转换为元素局部像素坐标。</summary>
        Vector2 EnuToScreenPoint(EnuPosition enu);

        /// <summary>离屏渲染高分辨率航迹态势快照（PNG 字节流）。</summary>
        byte[] RenderHighResSnapshotPng(int widthPx = 2048, int heightPx = 2048);
    }
}
