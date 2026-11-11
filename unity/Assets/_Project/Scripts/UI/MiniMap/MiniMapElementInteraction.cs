using System;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using UnityEngine;
using UnityEngine.UIElements;

namespace Mcis.UI.MiniMap
{
    public partial class MiniMapElement
    {
        /// <inheritdoc />
        public void SetFollowOwnVessel(bool follow)
        {
            _isFollowingOwnVessel = follow;
            if (follow && _hasOwnCurrent)
            {
                _centerEnu = _ownCurrent.EnuCenter;
                _autoFitPending = false;
            }
            MarkDirtyRepaint();
        }

        /// <inheritdoc />
        public void PanToEnu(EnuPosition centerEnu)
        {
            _isFollowingOwnVessel = false;
            _autoFitPending = false;
            _centerEnu = centerEnu;
            MarkDirtyRepaint();
        }

        /// <inheritdoc />
        public void SetZoom(float metersPerPixel)
        {
            _autoFitPending = false;
            _metersPerPixel = Mathf.Clamp(metersPerPixel, 0.25f, 500.0f);
            MarkDirtyRepaint();
        }

        /// <inheritdoc />
        public void ZoomToFitAllTracks(float paddingRatio = 0.15f)
        {
            _isFollowingOwnVessel = false;
            _autoFitPaddingRatio = Mathf.Clamp(paddingRatio, 0.02f, 0.45f);
            _autoFitPending = true;
            RecomputeAutoFitBounds(_autoFitPaddingRatio);
            MarkDirtyRepaint();
        }

        /// <inheritdoc />
        public EnuPosition ScreenPointToEnu(Vector2 localPanelPos)
        {
            Rect rect = contentRect;
            float cx = rect.width > 1f ? rect.width * 0.5f : 120f;
            float cy = rect.height > 1f ? rect.height * 0.5f : 85f;
            float scale = Mathf.Max(0.01f, _metersPerPixel);

            double east = _centerEnu.EastM + (localPanelPos.x - cx) * scale;
            double north = _centerEnu.NorthM - (localPanelPos.y - cy) * scale;
            return new EnuPosition(east, north, 0.0);
        }

        /// <inheritdoc />
        public Vector2 EnuToScreenPoint(EnuPosition enu)
        {
            Rect rect = contentRect;
            float cx = rect.width > 1f ? rect.width * 0.5f : 120f;
            float cy = rect.height > 1f ? rect.height * 0.5f : 85f;
            float scale = Mathf.Max(0.01f, _metersPerPixel);

            float x = cx + (float)((enu.EastM - _centerEnu.EastM) / scale);
            float y = cy - (float)((enu.NorthM - _centerEnu.NorthM) / scale);
            return new Vector2(x, y);
        }

        /// <inheritdoc />
        public byte[] RenderHighResSnapshotPng(int widthPx = 2048, int heightPx = 2048)
        {
            // P1 提供接口兼容占位；P5 报告导出阶段通过 RenderTexture + EncodeToPNG 实现离屏高分快照。
            return Array.Empty<byte>();
        }

        private void OnGeometryChanged(GeometryChangedEvent evt)
        {
            if (_autoFitPending)
            {
                RecomputeAutoFitBounds(_autoFitPaddingRatio);
                MarkDirtyRepaint();
            }
        }

        private void RecomputeAutoFitBounds(float paddingRatio)
        {
            double minE = double.PositiveInfinity;
            double maxE = double.NegativeInfinity;
            double minN = double.PositiveInfinity;
            double maxN = double.NegativeInfinity;
            int count = 0;

            AccumulateBounds(_ownTrackSamples, ref minE, ref maxE, ref minN, ref maxN, ref count);
            AccumulateBounds(_targetTrackSamples, ref minE, ref maxE, ref minN, ref maxN, ref count);

            if (_hasOwnCurrent)
            {
                ExpandPoint(_ownCurrent.EnuCenter, ref minE, ref maxE, ref minN, ref maxN, ref count);
            }
            if (_hasTargetCurrent)
            {
                ExpandPoint(_targetCurrent.EnuCenter, ref minE, ref maxE, ref minN, ref maxN, ref count);
            }

            if (count == 0)
            {
                _centerEnu = EnuPosition.Zero;
                _metersPerPixel = 20.0f;
                return;
            }

            _centerEnu = new EnuPosition((minE + maxE) * 0.5, (minN + maxN) * 0.5, 0.0);

            Rect rect = contentRect;
            if (rect.width <= 4f || rect.height <= 4f)
            {
                // 尚未完成首次布局，保持 _autoFitPending = true 等待 GeometryChangedEvent
                return;
            }

            double spanE = Math.Max(200.0, maxE - minE);
            double spanN = Math.Max(200.0, maxN - minN);
            double factor = 1.0 + 2.0 * Math.Max(0.05, paddingRatio);

            float mppX = (float)((spanE * factor) / rect.width);
            float mppY = (float)((spanN * factor) / rect.height);
            _metersPerPixel = Mathf.Clamp(Mathf.Max(mppX, mppY), 0.5f, 500.0f);
            _autoFitPending = false;
        }

        private static void AccumulateBounds(
            List<TrackSample> samples,
            ref double minE, ref double maxE,
            ref double minN, ref double maxN,
            ref int count)
        {
            for (int i = 0; i < samples.Count; i++)
            {
                ExpandPoint(samples[i].EnuCenter, ref minE, ref maxE, ref minN, ref maxN, ref count);
            }
        }

        private static void ExpandPoint(
            EnuPosition p,
            ref double minE, ref double maxE,
            ref double minN, ref double maxN,
            ref int count)
        {
            if (p.EastM < minE) minE = p.EastM;
            if (p.EastM > maxE) maxE = p.EastM;
            if (p.NorthM < minN) minN = p.NorthM;
            if (p.NorthM > maxN) maxN = p.NorthM;
            count++;
        }

        private void OnWheelZoom(WheelEvent evt)
        {
            float factor = evt.delta.y > 0f ? 1.15f : 0.87f;
            SetZoom(_metersPerPixel * factor);
            evt.StopPropagation();
        }

        private void OnPointerDown(PointerDownEvent evt)
        {
            if (evt.button != 0) return;
            _isDragging = true;
            _dragStartPos = evt.localPosition;
            _dragStartCenterEnu = _centerEnu;
            this.CapturePointer(evt.pointerId);
            evt.StopPropagation();
        }

        private void OnPointerMove(PointerMoveEvent evt)
        {
            if (!_isDragging || !this.HasPointerCapture(evt.pointerId)) return;
            Vector2 delta = (Vector2)evt.localPosition - _dragStartPos;
            if (delta.sqrMagnitude > 9.0f)
            {
                _isFollowingOwnVessel = false;
                _autoFitPending = false;
                double dEast = -delta.x * _metersPerPixel;
                double dNorth = delta.y * _metersPerPixel;
                _centerEnu = new EnuPosition(_dragStartCenterEnu.EastM + dEast, _dragStartCenterEnu.NorthM + dNorth, 0.0);
                MarkDirtyRepaint();
            }
        }

        private void OnPointerUp(PointerUpEvent evt)
        {
            if (!_isDragging) return;
            _isDragging = false;
            if (this.HasPointerCapture(evt.pointerId))
            {
                this.ReleasePointer(evt.pointerId);
            }

            Vector2 delta = (Vector2)evt.localPosition - _dragStartPos;
            if (delta.sqrMagnitude <= 9.0f)
            {
                TrySeekNearestTrackSample(evt.localPosition);
            }
        }

        private void TrySeekNearestTrackSample(Vector2 clickPos)
        {
            EnuPosition clickEnu = ScreenPointToEnu(clickPos);
            double bestDistSq = double.PositiveInfinity;
            SimTime? bestTime = null;

            FindClosestSample(_ownTrackSamples, clickEnu, ref bestDistSq, ref bestTime);
            FindClosestSample(_targetTrackSamples, clickEnu, ref bestDistSq, ref bestTime);

            if (bestTime.HasValue)
            {
                TrackTimeClicked?.Invoke(bestTime.Value);
            }
        }

        private static void FindClosestSample(
            List<TrackSample> samples,
            EnuPosition targetEnu,
            ref double bestDistSq,
            ref SimTime? bestTime)
        {
            for (int i = 0; i < samples.Count; i++)
            {
                EnuPosition p = samples[i].EnuCenter;
                double de = p.EastM - targetEnu.EastM;
                double dn = p.NorthM - targetEnu.NorthM;
                double d2 = de * de + dn * dn;
                if (d2 < bestDistSq)
                {
                    bestDistSq = d2;
                    bestTime = samples[i].Time;
                }
            }
        }
    }
}
