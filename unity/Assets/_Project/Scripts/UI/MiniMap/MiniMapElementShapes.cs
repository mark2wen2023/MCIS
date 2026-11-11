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
        private void DrawVesselTrack(
            Painter2D painter,
            List<TrackSample> samples,
            List<TimeGapSpan> gaps,
            Color pastColor,
            Color futureColor)
        {
            if (samples == null || samples.Count < 2)
            {
                return;
            }

            // 1. 未来航迹（半透明细线）
            painter.lineWidth = 1.25f;
            painter.strokeColor = futureColor;
            painter.BeginPath();
            for (int i = 0; i < samples.Count; i++)
            {
                Vector2 pt = EnuToScreenPoint(samples[i].EnuCenter);
                if (i == 0) painter.MoveTo(pt);
                else painter.LineTo(pt);
            }
            painter.Stroke();

            // 2. 已驶过航迹（高亮实线）
            painter.lineWidth = 2.1f;
            painter.strokeColor = pastColor;
            painter.BeginPath();
            bool startedPast = false;
            for (int i = 0; i < samples.Count; i++)
            {
                if (samples[i].Time > _currentTime)
                {
                    break;
                }
                Vector2 pt = EnuToScreenPoint(samples[i].EnuCenter);
                if (!startedPast)
                {
                    painter.MoveTo(pt);
                    startedPast = true;
                }
                else
                {
                    painter.LineTo(pt);
                }
            }
            if (startedPast)
            {
                painter.Stroke();
            }

            // 3. 时间缺口虚线标记
            if ((_visibleLayers & MiniMapLayers.TimeGapDashed) != 0 && gaps != null && gaps.Count > 0)
            {
                painter.lineWidth = 1.5f;
                painter.strokeColor = WarningRiskColor;
                for (int i = 0; i < gaps.Count; i++)
                {
                    Vector2 a = EnuToScreenPoint(gaps[i].StartEnu);
                    Vector2 b = EnuToScreenPoint(gaps[i].EndEnu);
                    DrawDashedSegment(painter, a, b, 4f, 4f);
                }
            }
        }

        private void DrawCpaOverlay(Painter2D painter, CpaResult cpa)
        {
            Color riskColor = GetRiskColor(cpa.RiskLevel);

            if (_hasOwnCurrent && _hasTargetCurrent)
            {
                Vector2 ownNow = EnuToScreenPoint(_ownCurrent.EnuCenter);
                Vector2 tgtNow = EnuToScreenPoint(_targetCurrent.EnuCenter);

                // 当前两船间距连线（细虚线）
                painter.lineWidth = 1.1f;
                painter.strokeColor = new Color(riskColor.r, riskColor.g, riskColor.b, 0.45f);
                DrawDashedSegment(painter, ownNow, tgtNow, 3f, 3f);

                // 若尚未经过最近会遇点，绘制预测 CPA 位置与连线
                if (!cpa.IsDiverging && !cpa.IsDegenerate && cpa.TcpaSec > 0.0)
                {
                    Vector2 ownCpaPt = EnuToScreenPoint(cpa.OwnCpaEnu);
                    Vector2 tgtCpaPt = EnuToScreenPoint(cpa.TargetCpaEnu);

                    painter.lineWidth = 1.2f;
                    painter.strokeColor = new Color(OwnPastColor.r, OwnPastColor.g, OwnPastColor.b, 0.55f);
                    DrawDashedSegment(painter, ownNow, ownCpaPt, 4f, 3f);

                    painter.strokeColor = new Color(TargetPastColor.r, TargetPastColor.g, TargetPastColor.b, 0.55f);
                    DrawDashedSegment(painter, tgtNow, tgtCpaPt, 4f, 3f);

                    // CPA 最近会遇点之间的告警连线
                    painter.lineWidth = 1.8f;
                    painter.strokeColor = riskColor;
                    painter.BeginPath();
                    painter.MoveTo(ownCpaPt);
                    painter.LineTo(tgtCpaPt);
                    painter.Stroke();

                    DrawCircleMarker(painter, ownCpaPt, 3.2f, riskColor);
                    DrawCircleMarker(painter, tgtCpaPt, 3.2f, riskColor);
                }
            }
        }

        private void DrawVesselTriangleAndVector(Painter2D painter, TrackSample sample, Color vesselColor)
        {
            Vector2 center = EnuToScreenPoint(sample.EnuCenter);

            // 速度矢量预测线（真北顺时针 COG）
            if (sample.SogMps > 0.1f)
            {
                double cogRad = sample.CogDeg * (Math.PI / 180.0);
                Vector2 velDir = new Vector2((float)Math.Sin(cogRad), -(float)Math.Cos(cogRad));
                float vecLenPx = Mathf.Clamp(sample.SogMps * 3.2f, 10f, 32f);

                painter.lineWidth = 1.3f;
                painter.strokeColor = new Color(vesselColor.r, vesselColor.g, vesselColor.b, 0.75f);
                painter.BeginPath();
                painter.MoveTo(center);
                painter.LineTo(center + velDir * vecLenPx);
                painter.Stroke();
            }

            // 船首向等腰三角形（真北顺时针 HDG：0° 朝屏幕上方 -Y，90° 朝屏幕右方 +X）
            double hdgRad = sample.HdgDeg * (Math.PI / 180.0);
            Vector2 fwd = new Vector2((float)Math.Sin(hdgRad), -(float)Math.Cos(hdgRad));
            Vector2 right = new Vector2(-fwd.y, fwd.x);

            const float bowLen = 7.5f;
            const float sternLen = 5.0f;
            const float halfBeam = 4.2f;

            Vector2 bow = center + fwd * bowLen;
            Vector2 sternPort = center - fwd * sternLen - right * halfBeam;
            Vector2 sternStbd = center - fwd * sternLen + right * halfBeam;

            painter.fillColor = vesselColor;
            painter.strokeColor = new Color(0.02f, 0.06f, 0.12f, 0.95f);
            painter.lineWidth = 1.2f;

            painter.BeginPath();
            painter.MoveTo(bow);
            painter.LineTo(sternStbd);
            painter.LineTo(sternPort);
            painter.ClosePath();
            painter.Fill();
            painter.Stroke();
        }

        private static void DrawCircleMarker(Painter2D painter, Vector2 center, float radius, Color color)
        {
            painter.fillColor = color;
            painter.BeginPath();
            painter.Arc(center, radius, Angle.Degrees(0f), Angle.Degrees(360f));
            painter.ClosePath();
            painter.Fill();
        }

        private static void DrawDashedSegment(Painter2D painter, Vector2 a, Vector2 b, float dashPx, float gapPx)
        {
            Vector2 delta = b - a;
            float totalLen = delta.magnitude;
            if (totalLen <= 0.5f) return;

            Vector2 dir = delta / totalLen;
            float step = Mathf.Max(2f, dashPx + gapPx);

            painter.BeginPath();
            for (float d = 0f; d < totalLen; d += step)
            {
                float end = Mathf.Min(d + dashPx, totalLen);
                painter.MoveTo(a + dir * d);
                painter.LineTo(a + dir * end);
            }
            painter.Stroke();
        }

        private static Color GetRiskColor(RiskLevel level)
        {
            switch (level)
            {
                case RiskLevel.Danger:
                    return DangerRiskColor;
                case RiskLevel.Warning:
                    return WarningRiskColor;
                default:
                    return SafeRiskColor;
            }
        }
    }
}
