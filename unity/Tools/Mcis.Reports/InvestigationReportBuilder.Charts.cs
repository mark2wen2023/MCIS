using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Cpa;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Analysis;
using Mcis.Simulation.Cpa;
using Mcis.Simulation.Ecfc;
using PdfSharp.Drawing;

namespace Mcis.Reports
{
    public static partial class InvestigationReportBuilder
    {
        private static readonly XColor LilyColor = XColor.FromArgb(255, 20, 130, 180);
        private static readonly XColor MaryColor = XColor.FromArgb(255, 220, 100, 20);
        private static readonly XColor WarningColor = XColor.FromArgb(255, 200, 130, 0);
        private static readonly XColor DangerColor = XColor.FromArgb(255, 180, 30, 30);
        private static readonly XColor TcColor = XColor.FromArgb(255, 30, 30, 30);
        private static readonly XColor GridColor = XColor.FromArgb(255, 210, 215, 220);
        private static readonly XColor BandWarning = XColor.FromArgb(55, 230, 170, 40);
        private static readonly XColor BandDanger = XColor.FromArgb(55, 210, 50, 50);

        private const double TcpaDisplayMaxMin = 15.0;

        private static void DrawTracks(
            XGraphics gfx,
            IShipTrack lily,
            IShipTrack mary,
            CpaTimeSeries series,
            EncounterAnalysisReport analysis,
            DateTimeOffset epoch,
            SimTime tc)
        {
            var box = new XRect(50, 58, 495, 660);
            gfx.DrawRectangle(new XPen(XColors.SteelBlue, 0.8), XBrushes.White, box);

            var all = new List<EnuPosition>();
            Collect(all, lily);
            Collect(all, mary);
            GetBounds(all, out double minE, out double maxE, out double minN, out double maxN);
            MakeEqualAspect(ref minE, ref maxE, ref minN, ref maxN, 0.12);

            DrawEnuGrid(gfx, box, minE, maxE, minN, maxN);

            DrawTrack(gfx, box, lily, minE, maxE, minN, maxN, LilyColor, tc);
            DrawTrack(gfx, box, mary, minE, maxE, minN, maxN, MaryColor, tc);

            // 碰撞时刻中心连线
            if (lily.TrySampleAt(tc, out TrackSample ls) && mary.TrySampleAt(tc, out TrackSample ms))
            {
                XPoint a = Map(box, ls.EnuCenter.EastM, ls.EnuCenter.NorthM, minE, maxE, minN, maxN);
                XPoint b = Map(box, ms.EnuCenter.EastM, ms.EnuCenter.NorthM, minE, maxE, minN, maxN);
                gfx.DrawLine(new XPen(DangerColor, 1.3), a, b);
            }

            DrawTrackTimeLabels(gfx, box, lily, mary, analysis, epoch, tc, minE, maxE, minN, maxN);
            DrawNorthArrow(gfx, new XPoint(box.X + box.Width - 28, box.Y + 36));
            DrawScaleBar(gfx, box, minE, maxE, minN, maxN);
            DrawTrackLegend(gfx, new XRect(box.X + 8, box.Y + 8, 200, 70));

            var caption = new XFont(NotoSansScFontResolver.FamilyName, 8, XFontStyleEx.Regular);
            gfx.DrawString(
                "北向上、等比例。实线为碰撞前航迹，虚线为碰撞后漂移。时间标签为北京时间（UTC+8）。",
                caption, XBrushes.DimGray, new XPoint(50, 732));
        }

        private static void DrawCpaCurves(
            XGraphics gfx,
            CpaTimeSeries series,
            EncounterAnalysisReport analysis,
            DateTimeOffset epoch,
            SimTime tc)
        {
            if (series == null || series.Samples.Count < 2)
            {
                return;
            }

            double t0 = series.StartTime.Seconds;
            double t1 = series.EndTime.Seconds;
            double maxDist = 0.1;
            double maxDcpa = 1.2;
            for (int i = 0; i < series.Samples.Count; i++)
            {
                CpaResult s = series.Samples[i];
                maxDist = Math.Max(maxDist, s.CurrentDistanceNm);
                if (s.Time.Seconds <= tc.Seconds + 1e-9)
                {
                    maxDcpa = Math.Max(maxDcpa, Math.Abs(s.DcpaNm));
                }
            }

            maxDist = NiceCeiling(maxDist * 1.08, 0.5);
            maxDcpa = NiceCeiling(Math.Max(maxDcpa, 1.2) * 1.08, 0.2);

            const double left = 62;
            const double width = 470;
            const double top = 62;
            const double gap = 36;
            const double totalH = 660;
            double panelH = (totalH - 2 * gap) / 3.0;
            var panels = new[]
            {
                new XRect(left, top, width, panelH),
                new XRect(left, top + panelH + gap, width, panelH),
                new XRect(left, top + 2 * (panelH + gap), width, panelH)
            };

            DrawDistancePanel(gfx, panels[0], series, t0, t1, maxDist, analysis, tc, false);
            DrawDcpaPanel(gfx, panels[1], series, t0, t1, maxDcpa, analysis, tc, false);
            DrawTcpaPanel(gfx, panels[2], series, t0, t1, analysis, tc, true, epoch);

            var legendFont = new XFont(NotoSansScFontResolver.FamilyName, 8, XFontStyleEx.Regular);
            gfx.DrawString(
                "琥珀带：警告阈值（DCPA < 1 nm，0 < TCPA < 12 min）  红带：危险阈值（DCPA < 0.3 nm，0 < TCPA < 6 min）",
                legendFont, XBrushes.DimGray, new XPoint(left, 760));
            gfx.DrawString(
                "竖线：首次警告 / 首次危险 / 首次接触 tc。tc 之后不再绘制 DCPA 与 TCPA。TCPA 显示上限 15 min。时间轴为北京时间（UTC+8）。",
                legendFont, XBrushes.DimGray, new XPoint(left, 774));
        }

        private static void DrawDistancePanel(
            XGraphics gfx, XRect box, CpaTimeSeries series,
            double t0, double t1, double maxY,
            EncounterAnalysisReport analysis, SimTime tc, bool xLabels)
        {
            DrawPanelFrame(gfx, box, "距离", "nm", 0, maxY, t0, t1, xLabels, default, false);
            DrawSeriesInPanel(gfx, box, series, t0, t1, 0, maxY, s => s.CurrentDistanceNm, XColor.FromArgb(255, 30, 90, 160), null, 1.6);
            DrawEventMarkers(gfx, box, t0, t1, analysis, tc, "距离");
        }

        private static void DrawDcpaPanel(
            XGraphics gfx, XRect box, CpaTimeSeries series,
            double t0, double t1, double maxY,
            EncounterAnalysisReport analysis, SimTime tc, bool xLabels)
        {
            DrawPanelFrame(gfx, box, "DCPA", "nm", 0, maxY, t0, t1, xLabels, default, false);
            FillBand(gfx, box, 0, maxY, 0, 0.3, BandDanger);
            FillBand(gfx, box, 0, maxY, 0.3, 1.0, BandWarning);
            DrawSeriesInPanel(gfx, box, series, t0, t1, 0, maxY, s => Math.Abs(s.DcpaNm), XColor.FromArgb(255, 200, 90, 10), tc, 1.6);
            DrawEventMarkers(gfx, box, t0, t1, analysis, tc, "DCPA");
        }

        private static void DrawTcpaPanel(
            XGraphics gfx, XRect box, CpaTimeSeries series,
            double t0, double t1,
            EncounterAnalysisReport analysis, SimTime tc, bool xLabels, DateTimeOffset epoch)
        {
            DrawPanelFrame(gfx, box, "TCPA", "min", 0, TcpaDisplayMaxMin, t0, t1, xLabels, epoch, true);
            FillBand(gfx, box, 0, TcpaDisplayMaxMin, 0, 6.0, BandDanger);
            FillBand(gfx, box, 0, TcpaDisplayMaxMin, 6.0, 12.0, BandWarning);
            DrawSeriesInPanel(gfx, box, series, t0, t1, 0, TcpaDisplayMaxMin, s => Math.Min(Math.Max(s.TcpaMin, 0), TcpaDisplayMaxMin), XColor.FromArgb(255, 30, 130, 80), tc, 1.6);
            DrawEventMarkers(gfx, box, t0, t1, analysis, tc, "TCPA");
        }

        private static void DrawPanelFrame(
            XGraphics gfx, XRect box, string title, string unit,
            double y0, double y1, double t0, double t1, bool xLabels, DateTimeOffset epoch, bool isTimeAxis)
        {
            gfx.DrawRectangle(new XPen(XColors.Gray, 0.7), XBrushes.White, box);
            var titleFont = new XFont(NotoSansScFontResolver.FamilyName, 9, XFontStyleEx.Bold);
            var tickFont = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Regular);

            gfx.Save();
            gfx.TranslateTransform(box.X - 44, box.Y + box.Height / 2);
            gfx.RotateTransform(-90);
            gfx.DrawString(title + "（" + unit + "）", titleFont, XBrushes.Black, new XPoint(0, 0), XStringFormats.Center);
            gfx.Restore();

            int yTicks = 5;
            for (int i = 0; i <= yTicks; i++)
            {
                double v = y0 + (y1 - y0) * i / yTicks;
                double y = YOf(box, v, y0, y1);
                var gridPen = new XPen(GridColor, 0.4);
                gfx.DrawLine(gridPen, box.X, y, box.X + box.Width, y);
                string label = v == Math.Floor(v) || Math.Abs(v - Math.Round(v)) < 1e-6
                    ? string.Format(CultureInfo.InvariantCulture, "{0:0}", v)
                    : string.Format(CultureInfo.InvariantCulture, "{0:0.0}", v);
                gfx.DrawString(label, tickFont, XBrushes.DimGray, new XRect(box.X - 36, y - 6, 32, 12), XStringFormats.CenterRight);
            }

            // 垂直时间网格：每 2 分钟
            for (double t = Math.Ceiling(t0 / 120.0) * 120.0; t <= t1 + 1e-6; t += 120.0)
            {
                double x = XOf(box, t, t0, t1);
                gfx.DrawLine(new XPen(GridColor, 0.4), x, box.Y, x, box.Y + box.Height);
                if (xLabels)
                {
                    string clock = epoch.AddSeconds(t).ToOffset(TimeSpan.FromHours(8)).ToString("HH:mm", CultureInfo.InvariantCulture);
                    gfx.DrawString(clock, tickFont, XBrushes.DimGray, new XRect(x - 18, box.Y + box.Height + 3, 36, 10), XStringFormats.TopCenter);
                    gfx.DrawString(string.Format(CultureInfo.InvariantCulture, "+{0:0} min", t / 60.0), tickFont, XBrushes.Gray,
                        new XRect(x - 22, box.Y + box.Height + 13, 44, 10), XStringFormats.TopCenter);
                }
            }

            if (xLabels)
            {
                // 刻度已同时给出北京时间与相对分钟，不再另写轴名以免重叠。
            }
        }

        private static void FillBand(XGraphics gfx, XRect box, double y0, double y1, double lo, double hi, XColor color)
        {
            double a = Math.Max(y0, Math.Min(y1, lo));
            double b = Math.Max(y0, Math.Min(y1, hi));
            if (b <= a)
            {
                return;
            }

            double yTop = YOf(box, b, y0, y1);
            double yBot = YOf(box, a, y0, y1);
            gfx.DrawRectangle(new XSolidBrush(color), new XRect(box.X, yTop, box.Width, Math.Max(0.5, yBot - yTop)));
        }

        private static void DrawSeriesInPanel(
            XGraphics gfx, XRect box, CpaTimeSeries series,
            double t0, double t1, double y0, double y1,
            Func<CpaResult, double> sel, XColor color, SimTime? clipAt, double width)
        {
            var pen = new XPen(color, width);
            XPoint? prev = null;
            for (int i = 0; i < series.Samples.Count; i++)
            {
                CpaResult s = series.Samples[i];
                if (clipAt.HasValue && s.Time.Seconds > clipAt.Value.Seconds + 1e-9)
                {
                    break;
                }

                var pt = new XPoint(XOf(box, s.Time.Seconds, t0, t1), YOf(box, sel(s), y0, y1));
                if (prev.HasValue)
                {
                    gfx.DrawLine(pen, prev.Value, pt);
                }

                prev = pt;
            }
        }

        private static void DrawEventMarkers(XGraphics gfx, XRect box, double t0, double t1, EncounterAnalysisReport analysis, SimTime tc, string panelTitle)
        {
            var font = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Regular);
            DrawMarker(gfx, box, t0, t1, analysis != null && analysis.FirstWarning.HasValue ? analysis.FirstWarning.Value.Time.Seconds : double.NaN, WarningColor, panelTitle == "距离" ? "首次警告" : null, font);
            DrawMarker(gfx, box, t0, t1, analysis != null && analysis.FirstDanger.HasValue ? analysis.FirstDanger.Value.Time.Seconds : double.NaN, DangerColor, panelTitle == "距离" ? "首次危险" : null, font);
            DrawMarker(gfx, box, t0, t1, tc.Seconds, TcColor, panelTitle == "距离" ? "tc" : null, font);
        }

        private static void DrawMarker(XGraphics gfx, XRect box, double t0, double t1, double t, XColor color, string label, XFont font)
        {
            if (double.IsNaN(t) || t < t0 || t > t1)
            {
                return;
            }

            double x = XOf(box, t, t0, t1);
            var pen = new XPen(color, label == "tc" || (label != null && label.Contains("tc")) ? 1.2 : 0.9);
            pen.DashStyle = string.IsNullOrEmpty(label) || label == "tc" ? XDashStyle.Solid : XDashStyle.Dash;
            if (label == "首次警告" || label == "首次危险")
            {
                pen.DashStyle = XDashStyle.Dash;
            }

            if (label == "tc")
            {
                pen.DashStyle = XDashStyle.Solid;
                pen.Width = 1.3;
            }

            gfx.DrawLine(pen, x, box.Y, x, box.Y + box.Height);
            if (!string.IsNullOrEmpty(label))
            {
                gfx.DrawString(label, font, new XSolidBrush(color), new XPoint(x + 2, box.Y + 8));
            }
        }

        private static void DrawEcfc(XGraphics gfx, EcfcService ecfc)
        {
            // 报告专用两行排布，避免自动布局把 9 个事件挤成过窄矩形。
            var events = new List<EcfcNode>();
            var conditions = new List<EcfcNode>();
            for (int i = 0; i < ecfc.Nodes.Count; i++)
            {
                if (ecfc.Nodes[i].Kind == EcfcNodeKind.Event)
                {
                    events.Add(ecfc.Nodes[i]);
                }
                else
                {
                    conditions.Add(ecfc.Nodes[i]);
                }
            }

            events.Sort((a, b) =>
            {
                int c = Comparer<double>.Default.Compare(a.Time.HasValue ? a.Time.Value.Seconds : 0, b.Time.HasValue ? b.Time.Value.Seconds : 0);
                return c != 0 ? c : string.CompareOrdinal(a.NodeId, b.NodeId);
            });

            // 主序列（Lane==0）按时间一行最多 5 个，其余事件放侧道。
            var primary = new List<EcfcNode>();
            var side = new List<EcfcNode>();
            for (int i = 0; i < events.Count; i++)
            {
                if (events[i].Lane == 0)
                {
                    primary.Add(events[i]);
                }
                else
                {
                    side.Add(events[i]);
                }
            }

            const double boxW = 108;
            const double boxH = 56;
            const double gapX = 18;
            const double rowY1 = 280;
            const double rowY2 = 430;
            const double startX = 48;
            int firstRow = Math.Min(4, primary.Count);
            var pos = new Dictionary<string, XRect>(StringComparer.Ordinal);

            for (int i = 0; i < primary.Count; i++)
            {
                int row = i < firstRow ? 0 : 1;
                int col = i < firstRow ? i : i - firstRow;
                double x = startX + col * (boxW + gapX);
                double y = row == 0 ? rowY1 : rowY2;
                pos[primary[i].NodeId] = new XRect(x, y, boxW, boxH);
            }

            // 侧道事件（如 E4）放在第一行下方、对应时间附近
            for (int i = 0; i < side.Count; i++)
            {
                EcfcNode n = side[i];
                double x = startX;
                if (n.Time.HasValue)
                {
                    EcfcNode nearest = null;
                    double best = double.MaxValue;
                    for (int j = 0; j < primary.Count; j++)
                    {
                        if (!primary[j].Time.HasValue) continue;
                        double d = Math.Abs(primary[j].Time.Value.Seconds - n.Time.Value.Seconds);
                        if (d < best) { best = d; nearest = primary[j]; }
                    }

                    if (nearest != null && pos.ContainsKey(nearest.NodeId))
                    {
                        x = pos[nearest.NodeId].X;
                    }
                }

                pos[n.NodeId] = new XRect(x, 560, boxW, boxH);
            }

            // 条件：C 节点在关联事件上方或下方
            for (int i = 0; i < conditions.Count; i++)
            {
                EcfcNode c = conditions[i];
                string anchorId = null;
                for (int e = 0; e < ecfc.Edges.Count; e++)
                {
                    if (ecfc.Edges[e].FromNodeId == c.NodeId && pos.ContainsKey(ecfc.Edges[e].ToNodeId))
                    {
                        anchorId = ecfc.Edges[e].ToNodeId;
                        break;
                    }
                }

                XRect anchor = !string.IsNullOrEmpty(anchorId) ? pos[anchorId] : new XRect(startX + i * 140, rowY1, boxW, boxH);
                bool above = c.Lane >= 0;
                double y = above ? Math.Max(70, anchor.Y - 100) : Math.Min(660, anchor.Y + 90);
                double x = anchor.X + (i % 3 - 1) * 16;
                x = Math.Max(40, Math.Min(455, x));
                var cr = new XRect(x, y, 120, 52);
                cr = NudgeAway(pos, cr);
                pos[c.NodeId] = cr;
            }

            var font = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Regular);
            var timeFont = new XFont(NotoSansScFontResolver.FamilyName, 6.5, XFontStyleEx.Regular);
            var idFont = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Bold);

            // 先画边
            for (int i = 0; i < ecfc.Edges.Count; i++)
            {
                EcfcEdge e = ecfc.Edges[i];
                if (!pos.ContainsKey(e.FromNodeId) || !pos.ContainsKey(e.ToNodeId))
                {
                    continue;
                }

                XPoint a = RectOut(pos[e.FromNodeId], pos[e.ToNodeId]);
                XPoint b = RectOut(pos[e.ToNodeId], pos[e.FromNodeId]);
                var pen = new XPen(XColors.Black, e.IsPrimarySequenceBold ? 1.8 : 0.8);
                if (e.Kind == EcfcEdgeKind.Influence)
                {
                    pen.DashStyle = XDashStyle.Dash;
                }

                gfx.DrawLine(pen, a, b);
                DrawArrowHead(gfx, pen, a, b);
            }

            DateTimeOffset epoch = Mcis.Fixtures.LilyMaryDemo.CaseEpochUtc;
            for (int i = 0; i < ecfc.Nodes.Count; i++)
            {
                EcfcNode n = ecfc.Nodes[i];
                if (!pos.ContainsKey(n.NodeId))
                {
                    continue;
                }

                XRect r = pos[n.NodeId];
                var pen = new XPen(XColors.Black, n.IsPrimaryIncident ? 1.8 : 0.8);
                if (n.IsPresumptive)
                {
                    pen.DashStyle = XDashStyle.Dash;
                }

                if (n.Kind == EcfcNodeKind.Event)
                {
                    gfx.DrawRectangle(pen, XBrushes.White, r);
                }
                else
                {
                    gfx.DrawEllipse(pen, XBrushes.White, r);
                }

                gfx.DrawString(n.NodeId, idFont, XBrushes.Black, new XRect(r.X + 2, r.Y + 2, r.Width - 4, 10), XStringFormats.TopLeft);
                if (n.Time.HasValue)
                {
                    string clock = epoch.AddSeconds(n.Time.Value.Seconds).ToOffset(TimeSpan.FromHours(8)).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
                    gfx.DrawString(clock, timeFont, XBrushes.DimGray, new XRect(r.X + 2, r.Y + r.Height - 11, r.Width - 4, 10), XStringFormats.BottomRight);
                }

                string text = n.Text ?? "";
                if (n.IsPresumptive)
                {
                    text += "（推定）";
                }

                DrawWrapped(gfx, text, font, XBrushes.Black, new XRect(r.X + 4, r.Y + 13, r.Width - 8, r.Height - 24));
            }

            var legend = new XFont(NotoSansScFontResolver.FamilyName, 8, XFontStyleEx.Regular);
            gfx.DrawString("图例：矩形＝事件　　椭圆＝条件　　实线箭头＝事件顺序　　虚线箭头＝条件影响　　粗框＝主要事故　　虚框＝推定", legend, XBrushes.DimGray, new XPoint(48, 755));
            gfx.DrawString("节点右下角时间为北京时间（UTC+8）。本图按论文 2.5 节表 4 符号规则绘制。", legend, XBrushes.DimGray, new XPoint(48, 770));
        }

        private static void DrawTrack(
            XGraphics gfx, XRect box, IShipTrack track,
            double minE, double maxE, double minN, double maxN, XColor color, SimTime tc)
        {
            var solid = new XPen(color, 1.6);
            var dashed = new XPen(color, 1.1) { DashStyle = XDashStyle.Dash };
            XPoint? prev = null;
            bool after = false;
            for (int i = 0; i < track.CleanedSamples.Count; i++)
            {
                TrackSample s = track.CleanedSamples[i];
                XPoint pt = Map(box, s.EnuCenter.EastM, s.EnuCenter.NorthM, minE, maxE, minN, maxN);
                bool nowAfter = s.Time.Seconds > tc.Seconds + 1e-9;
                if (prev.HasValue)
                {
                    gfx.DrawLine(nowAfter || after ? dashed : solid, prev.Value, pt);
                }

                after = nowAfter;
                prev = pt;
            }
        }

        private static void DrawTrackTimeLabels(
            XGraphics gfx, XRect box, IShipTrack lily, IShipTrack mary,
            EncounterAnalysisReport analysis, DateTimeOffset epoch, SimTime tc,
            double minE, double maxE, double minN, double maxN)
        {
            var font = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Regular);
            var marks = new List<(double T, string Label)>
            {
                (360, null),
                (480, null),
                (tc.Seconds, "tc")
            };
            if (analysis != null)
            {
                if (analysis.FirstWarning.HasValue)
                {
                    marks.Add((analysis.FirstWarning.Value.Time.Seconds, "警告"));
                }

                if (analysis.FirstDanger.HasValue)
                {
                    marks.Add((analysis.FirstDanger.Value.Time.Seconds, "危险"));
                }
            }

            marks.Sort((a, b) => a.T.CompareTo(b.T));
            // 去掉与事件标签过近的普通时刻，避免 18:03 重复
            var times = new List<(double T, string Label)>();
            for (int i = 0; i < marks.Count; i++)
            {
                bool nearEvent = false;
                for (int j = 0; j < marks.Count; j++)
                {
                    if (i == j) continue;
                    if (!string.IsNullOrEmpty(marks[j].Label) && string.IsNullOrEmpty(marks[i].Label)
                        && Math.Abs(marks[i].T - marks[j].T) < 90)
                    {
                        nearEvent = true;
                        break;
                    }
                }

                if (!nearEvent)
                {
                    times.Add(marks[i]);
                }
            }

            var used = new List<XPoint>();
            LabelShipStart(gfx, box, lily, "Lily", font, minE, maxE, minN, maxN, epoch, used);
            LabelShipStart(gfx, box, mary, "Mary", font, minE, maxE, minN, maxN, epoch, used);

            for (int i = 0; i < times.Count; i++)
            {
                double tt = times[i].T;
                if (tt <= 0)
                {
                    continue;
                }

                if (lily.TrySampleAt(new SimTime(tt), out TrackSample s))
                {
                    XPoint p = Map(box, s.EnuCenter.EastM, s.EnuCenter.NorthM, minE, maxE, minN, maxN);
                    gfx.DrawEllipse(new XSolidBrush(LilyColor), p.X - 1.7, p.Y - 1.7, 3.4, 3.4);
                    string text = Beijing(epoch, tt);
                    if (!string.IsNullOrEmpty(times[i].Label))
                    {
                        text += "  " + times[i].Label;
                    }

                    PlaceLabel(gfx, font, text, p, used, 8, -8);
                }

                if (mary.TrySampleAt(new SimTime(tt), out TrackSample sm))
                {
                    XPoint p = Map(box, sm.EnuCenter.EastM, sm.EnuCenter.NorthM, minE, maxE, minN, maxN);
                    gfx.DrawEllipse(new XSolidBrush(MaryColor), p.X - 1.7, p.Y - 1.7, 3.4, 3.4);
                }
            }
        }

        private static void LabelShipStart(
            XGraphics gfx, XRect box, IShipTrack track, string name, XFont font,
            double minE, double maxE, double minN, double maxN, DateTimeOffset epoch, List<XPoint> used)
        {
            if (track.CleanedSamples == null || track.CleanedSamples.Count == 0)
            {
                return;
            }

            TrackSample s = track.CleanedSamples[0];
            XPoint p = Map(box, s.EnuCenter.EastM, s.EnuCenter.NorthM, minE, maxE, minN, maxN);
            gfx.DrawEllipse(new XPen(XColors.Black, 0.6), new XSolidBrush(name == "Lily" ? LilyColor : MaryColor), p.X - 3, p.Y - 3, 6, 6);
            PlaceLabel(gfx, font, name + "  " + Beijing(epoch, s.Time.Seconds), p, used, 8, name == "Lily" ? -12 : 8);
        }

        private static void PlaceLabel(XGraphics gfx, XFont font, string text, XPoint p, List<XPoint> used, double dx, double dy)
        {
            var at = new XPoint(p.X + dx, p.Y + dy);
            for (int k = 0; k < used.Count; k++)
            {
                if (Math.Abs(used[k].X - at.X) < 36 && Math.Abs(used[k].Y - at.Y) < 10)
                {
                    at = new XPoint(at.X, at.Y + 11);
                }
            }

            gfx.DrawString(text, font, XBrushes.Black, at);
            used.Add(at);
        }

        private static void DrawNorthArrow(XGraphics gfx, XPoint tip)
        {
            var pen = new XPen(XColors.Black, 0.9);
            gfx.DrawLine(pen, tip.X, tip.Y + 22, tip.X, tip.Y);
            gfx.DrawLine(pen, tip.X, tip.Y, tip.X - 4, tip.Y + 8);
            gfx.DrawLine(pen, tip.X, tip.Y, tip.X + 4, tip.Y + 8);
            var font = new XFont(NotoSansScFontResolver.FamilyName, 8, XFontStyleEx.Bold);
            gfx.DrawString("N", font, XBrushes.Black, new XPoint(tip.X, tip.Y - 10), XStringFormats.Center);
        }

        private static void DrawScaleBar(XGraphics gfx, XRect box, double minE, double maxE, double minN, double maxN)
        {
            double spanM = Math.Max(maxE - minE, maxN - minN);
            double barM;
            string label;
            if (spanM >= 3500)
            {
                barM = 1852 * 0.5;
                label = "0.5 nm";
            }
            else if (spanM >= 1500)
            {
                barM = 500;
                label = "500 m";
            }
            else
            {
                barM = 200;
                label = "200 m";
            }

            double barPx = barM / Math.Max(maxE - minE, 1e-6) * box.Width;
            double x = box.X + 16;
            double y = box.Y + box.Height - 22;
            var pen = new XPen(XColors.Black, 1.2);
            gfx.DrawLine(pen, x, y, x + barPx, y);
            gfx.DrawLine(pen, x, y - 4, x, y + 4);
            gfx.DrawLine(pen, x + barPx, y - 4, x + barPx, y + 4);
            var font = new XFont(NotoSansScFontResolver.FamilyName, 7, XFontStyleEx.Regular);
            gfx.DrawString(label, font, XBrushes.Black, new XPoint(x + barPx / 2, y - 8), XStringFormats.Center);
        }

        private static void DrawTrackLegend(XGraphics gfx, XRect r)
        {
            var font = new XFont(NotoSansScFontResolver.FamilyName, 8, XFontStyleEx.Regular);
            gfx.DrawLine(new XPen(LilyColor, 2), r.X, r.Y + 8, r.X + 22, r.Y + 8);
            gfx.DrawString("Lily（虚构，南下出港）", font, XBrushes.Black, new XPoint(r.X + 26, r.Y + 4));
            gfx.DrawLine(new XPen(MaryColor, 2), r.X, r.Y + 22, r.X + 22, r.Y + 22);
            gfx.DrawString("Mary（虚构，北上进港）", font, XBrushes.Black, new XPoint(r.X + 26, r.Y + 18));
            gfx.DrawLine(new XPen(DangerColor, 1.3), r.X, r.Y + 36, r.X + 22, r.Y + 36);
            gfx.DrawString("碰撞时刻中心连线", font, XBrushes.Black, new XPoint(r.X + 26, r.Y + 32));
            gfx.DrawLine(new XPen(LilyColor, 1.1) { DashStyle = XDashStyle.Dash }, r.X, r.Y + 50, r.X + 22, r.Y + 50);
            gfx.DrawString("碰撞后漂移（虚线）", font, XBrushes.Black, new XPoint(r.X + 26, r.Y + 46));
        }

        private static void DrawEnuGrid(XGraphics gfx, XRect box, double minE, double maxE, double minN, double maxN)
        {
            double span = Math.Max(maxE - minE, maxN - minN);
            double step = span > 4000 ? 1000 : span > 2000 ? 500 : 200;
            var pen = new XPen(XColor.FromArgb(255, 230, 232, 235), 0.4);
            double e0 = Math.Ceiling(minE / step) * step;
            for (double e = e0; e <= maxE; e += step)
            {
                XPoint a = Map(box, e, minN, minE, maxE, minN, maxN);
                XPoint b = Map(box, e, maxN, minE, maxE, minN, maxN);
                gfx.DrawLine(pen, a, b);
            }

            double n0 = Math.Ceiling(minN / step) * step;
            for (double n = n0; n <= maxN; n += step)
            {
                XPoint a = Map(box, minE, n, minE, maxE, minN, maxN);
                XPoint b = Map(box, maxE, n, minE, maxE, minN, maxN);
                gfx.DrawLine(pen, a, b);
            }
        }

        private static void Collect(List<EnuPosition> all, IShipTrack track)
        {
            for (int i = 0; i < track.CleanedSamples.Count; i++)
            {
                all.Add(track.CleanedSamples[i].EnuCenter);
            }
        }

        private static void GetBounds(List<EnuPosition> pts, out double minE, out double maxE, out double minN, out double maxN)
        {
            minE = maxE = pts[0].EastM;
            minN = maxN = pts[0].NorthM;
            for (int i = 1; i < pts.Count; i++)
            {
                minE = Math.Min(minE, pts[i].EastM);
                maxE = Math.Max(maxE, pts[i].EastM);
                minN = Math.Min(minN, pts[i].NorthM);
                maxN = Math.Max(maxN, pts[i].NorthM);
            }
        }

        private static void MakeEqualAspect(ref double minE, ref double maxE, ref double minN, ref double maxN, double padFrac)
        {
            double de = Math.Max(maxE - minE, 50);
            double dn = Math.Max(maxN - minN, 50);
            double span = Math.Max(de, dn);
            double cE = 0.5 * (minE + maxE);
            double cN = 0.5 * (minN + maxN);
            span *= (1.0 + padFrac);
            minE = cE - 0.5 * span;
            maxE = cE + 0.5 * span;
            minN = cN - 0.5 * span;
            maxN = cN + 0.5 * span;
        }

        private static XPoint Map(XRect box, double x, double y, double minX, double maxX, double minY, double maxY)
        {
            double nx = (x - minX) / Math.Max(maxX - minX, 1e-6);
            double ny = (y - minY) / Math.Max(maxY - minY, 1e-6);
            return new XPoint(box.X + nx * box.Width, box.Y + box.Height - ny * box.Height);
        }

        private static double XOf(XRect box, double t, double t0, double t1)
        {
            return box.X + (t - t0) / Math.Max(t1 - t0, 1e-6) * box.Width;
        }

        private static double YOf(XRect box, double v, double y0, double y1)
        {
            double ny = (v - y0) / Math.Max(y1 - y0, 1e-6);
            ny = Math.Max(0, Math.Min(1, ny));
            return box.Y + box.Height - ny * box.Height;
        }

        private static double NiceCeiling(double v, double step)
        {
            if (step <= 0) step = 0.5;
            return Math.Ceiling(v / step) * step;
        }

        private static string Beijing(DateTimeOffset epoch, double seconds)
        {
            return epoch.AddSeconds(seconds).ToOffset(TimeSpan.FromHours(8)).ToString("HH:mm", CultureInfo.InvariantCulture);
        }

        private static XPoint RectOut(XRect from, XRect to)
        {
            var a = new XPoint(from.X + from.Width / 2, from.Y + from.Height / 2);
            var b = new XPoint(to.X + to.Width / 2, to.Y + to.Height / 2);
            double dx = b.X - a.X;
            double dy = b.Y - a.Y;
            // 与矩形边界相交
            double px = from.Width / 2 / Math.Max(Math.Abs(dx), 1e-6);
            double py = from.Height / 2 / Math.Max(Math.Abs(dy), 1e-6);
            double t = Math.Min(px, py);
            t = Math.Min(t, 1.0);
            return new XPoint(a.X + dx * t, a.Y + dy * t);
        }

        private static void DrawArrowHead(XGraphics gfx, XPen pen, XPoint from, XPoint to)
        {
            double dx = to.X - from.X;
            double dy = to.Y - from.Y;
            double len = Math.Sqrt(dx * dx + dy * dy);
            if (len < 4)
            {
                return;
            }

            dx /= len;
            dy /= len;
            const double size = 6;
            var l = new XPoint(to.X - dx * size + dy * size * 0.4, to.Y - dy * size - dx * size * 0.4);
            var r = new XPoint(to.X - dx * size - dy * size * 0.4, to.Y - dy * size + dx * size * 0.4);
            gfx.DrawLine(pen, to, l);
            gfx.DrawLine(pen, to, r);
        }


        private static XRect NudgeAway(Dictionary<string, XRect> pos, XRect rect)
        {
            for (int pass = 0; pass < 12; pass++)
            {
                bool hit = false;
                foreach (var kv in pos)
                {
                    if (!RectsOverlap(kv.Value, rect, 8))
                    {
                        continue;
                    }

                    hit = true;
                    // 优先下移进入行间空隙，其次右移
                    rect = new XRect(rect.X, rect.Y + 18, rect.Width, rect.Height);
                    if (rect.Y + rect.Height > 700)
                    {
                        rect = new XRect(Math.Min(455, rect.X + 24), Math.Max(70, rect.Y - 80), rect.Width, rect.Height);
                    }

                    break;
                }

                if (!hit)
                {
                    break;
                }
            }

            return rect;
        }

        private static bool RectsOverlap(XRect a, XRect b, double pad)
        {
            return a.X < b.X + b.Width + pad && a.X + a.Width + pad > b.X
                && a.Y < b.Y + b.Height + pad && a.Y + a.Height + pad > b.Y;
        }

        private static void DrawWrapped(XGraphics gfx, string text, XFont font, XBrush brush, XRect rect)
        {
            if (string.IsNullOrEmpty(text))
            {
                return;
            }

            var lines = new List<string>();
            var current = "";
            for (int i = 0; i < text.Length; i++)
            {
                string trial = current + text[i];
                double w = gfx.MeasureString(trial, font).Width;
                if (w > rect.Width && current.Length > 0)
                {
                    lines.Add(current);
                    current = text[i].ToString();
                }
                else
                {
                    current = trial;
                }
            }

            if (current.Length > 0)
            {
                lines.Add(current);
            }

            const double lineH = 9.5;
            double y = rect.Y;
            int maxLines = Math.Max(1, (int)(rect.Height / lineH));
            for (int i = 0; i < lines.Count && i < maxLines; i++)
            {
                string line = lines[i];
                if (i == maxLines - 1 && lines.Count > maxLines)
                {
                    line = line.Length > 1 ? line.Substring(0, Math.Max(1, line.Length - 1)) + "…" : "…";
                }

                gfx.DrawString(line, font, brush, new XRect(rect.X, y, rect.Width, lineH), XStringFormats.TopLeft);
                y += lineH;
            }
        }
    }
}
