using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.MiniMap
{
    public partial class MiniMapElement
    {
        private static readonly Color SeaBgColor = new Color(0.016f, 0.051f, 0.098f, 0.96f);
        private static readonly Color GridLineColor = new Color(0.231f, 0.890f, 1.000f, 0.09f);
        private static readonly Color GridAxisColor = new Color(0.231f, 0.890f, 1.000f, 0.20f);

        private static readonly Color OwnPastColor = new Color(0.231f, 0.890f, 1.000f, 0.92f);     // #3be3ff
        private static readonly Color OwnFutureColor = new Color(0.231f, 0.890f, 1.000f, 0.28f);
        private static readonly Color TargetPastColor = new Color(1.000f, 0.690f, 0.125f, 0.92f);  // #ffb020
        private static readonly Color TargetFutureColor = new Color(1.000f, 0.690f, 0.125f, 0.28f);

        private static readonly Color SafeRiskColor = new Color(0.231f, 0.890f, 1.000f, 0.85f);    // #3be3ff
        private static readonly Color WarningRiskColor = new Color(1.000f, 0.690f, 0.125f, 0.90f); // #ffb020
        private static readonly Color DangerRiskColor = new Color(1.000f, 0.302f, 0.369f, 0.95f);  // #ff4d5e

        private void OnGenerateVisualContent(MeshGenerationContext mgc)
        {
            Rect rect = contentRect;
            if (rect.width <= 2f || rect.height <= 2f)
            {
                return;
            }

            Painter2D painter = mgc.painter2D;
            painter.lineCap = LineCap.Round;
            painter.lineJoin = LineJoin.Round;

            // 1. 绘制深海背景
            DrawBackground(painter, rect);

            // 2. 绘制自适应米制/海图网格
            if ((_visibleLayers & MiniMapLayers.LatLonGrid) != 0)
            {
                DrawGrid(painter, rect);
            }

            // 3. 绘制双船完整航迹（已过航段实线高亮、未来航段半透明、缺口虚线）
            if ((_visibleLayers & MiniMapLayers.FullTracks) != 0)
            {
                DrawVesselTrack(painter, _ownTrackSamples, _ownTimeGaps, OwnPastColor, OwnFutureColor);
                DrawVesselTrack(painter, _targetTrackSamples, _targetTimeGaps, TargetPastColor, TargetFutureColor);
            }

            // 4. 绘制 CPA 预测位置与会遇风险连线
            if ((_visibleLayers & MiniMapLayers.CpaConnectors) != 0 && _currentCpa.HasValue)
            {
                DrawCpaOverlay(painter, _currentCpa.Value);
            }

            // 5. 绘制两船当前位置、船首向三角形与速度矢量线
            if ((_visibleLayers & MiniMapLayers.VesselIconsAndVectors) != 0)
            {
                if (_hasOwnCurrent)
                {
                    DrawVesselTriangleAndVector(painter, _ownCurrent, OwnPastColor);
                }
                if (_hasTargetCurrent)
                {
                    DrawVesselTriangleAndVector(painter, _targetCurrent, TargetPastColor);
                }
            }
        }

        private static void DrawBackground(Painter2D painter, Rect rect)
        {
            painter.fillColor = SeaBgColor;
            painter.BeginPath();
            painter.MoveTo(new Vector2(0f, 0f));
            painter.LineTo(new Vector2(rect.width, 0f));
            painter.LineTo(new Vector2(rect.width, rect.height));
            painter.LineTo(new Vector2(0f, rect.height));
            painter.ClosePath();
            painter.Fill();
        }

        private void DrawGrid(Painter2D painter, Rect rect)
        {
            float targetStepMeters = Mathf.Max(50f, _metersPerPixel * 42f);
            float gridStepM = SelectCleanGridStep(targetStepMeters);

            EnuPosition topLeftEnu = ScreenPointToEnu(new Vector2(0f, 0f));
            EnuPosition bottomRightEnu = ScreenPointToEnu(new Vector2(rect.width, rect.height));

            double startEast = Math.Floor(topLeftEnu.EastM / gridStepM) * gridStepM;
            double endEast = bottomRightEnu.EastM;

            painter.lineWidth = 1.0f;
            painter.strokeColor = GridLineColor;
            painter.BeginPath();

            int safety = 0;
            for (double e = startEast; e <= endEast && safety < 64; e += gridStepM, safety++)
            {
                float x = EnuToScreenPoint(new EnuPosition(e, 0.0)).x;
                painter.MoveTo(new Vector2(x, 0f));
                painter.LineTo(new Vector2(x, rect.height));
            }

            double startNorth = Math.Floor(bottomRightEnu.NorthM / gridStepM) * gridStepM;
            double endNorth = topLeftEnu.NorthM;
            safety = 0;
            for (double n = startNorth; n <= endNorth && safety < 64; n += gridStepM, safety++)
            {
                float y = EnuToScreenPoint(new EnuPosition(0.0, n)).y;
                painter.MoveTo(new Vector2(0f, y));
                painter.LineTo(new Vector2(rect.width, y));
            }
            painter.Stroke();

            // 视口中心十字准星与指北标
            Vector2 centerPx = new Vector2(rect.width * 0.5f, rect.height * 0.5f);
            painter.strokeColor = GridAxisColor;
            painter.BeginPath();
            painter.MoveTo(new Vector2(centerPx.x - 6f, centerPx.y));
            painter.LineTo(new Vector2(centerPx.x + 6f, centerPx.y));
            painter.MoveTo(new Vector2(centerPx.x, centerPx.y - 6f));
            painter.LineTo(new Vector2(centerPx.x, centerPx.y + 6f));
            painter.Stroke();
        }

        private static float SelectCleanGridStep(float rawStepM)
        {
            float[] steps = new float[] { 50f, 100f, 250f, 500f, 1000f, 1852f, 3704f, 5000f, 10000f };
            for (int i = 0; i < steps.Length; i++)
            {
                if (steps[i] >= rawStepM) return steps[i];
            }
            return 10000f;
        }
    }
}
