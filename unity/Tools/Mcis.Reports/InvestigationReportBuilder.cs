using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using Mcis.Core;
using Mcis.Data.CasePackage;
using Mcis.Domain.Cpa;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Fixtures;
using Mcis.Simulation.Analysis;
using Mcis.Simulation.Cpa;
using Mcis.Simulation.Damage;
using Mcis.Simulation.Ecfc;
using MigraDoc.DocumentObjectModel;
using MigraDoc.Rendering;
using PdfSharp.Drawing;
using PdfSharp.Fonts;
using PdfSharp.Pdf;

namespace Mcis.Reports
{
    /// <summary>基于 PDFsharp + MigraDoc 生成中文海事调查报告（含矢量航迹图、CPA 曲线、ECFC 图与 SHA-256 证据清单）。</summary>
    public static partial class InvestigationReportBuilder
    {
        public const string WatermarkText = "示例数据 / 虚构案例（仅供演示）";
        public const string SoftwareVersion = "MCIS-Unity6-0.9.0";

        public static ReportBuildResult BuildLilyMarySample(string outputPdfPath, string fontPath)
        {
            if (GlobalFontSettings.FontResolver == null)
            {
                GlobalFontSettings.UseWindowsFontsUnderWindows = false;
                GlobalFontSettings.FontResolver = new NotoSansScFontResolver(fontPath);
            }

            var geo = LilyMaryDemo.CreateGeo();
            var lily = LilyMaryDemo.BuildLilyTrack(geo);
            var mary = LilyMaryDemo.BuildMaryTrack(geo);
            var cpa = new CpaService(lily, mary, 1.0, RiskThresholds.Default);
            CpaTimeSeries series = cpa.PrecomputeSeries(LilyMaryDemo.LilyId, LilyMaryDemo.MaryId, 1.0);
            var ecfc = new EcfcService(8.0);
            LilyMaryDemo.PopulateEcfc(ecfc);
            SimTime tc = LilyMaryDemo.CollisionTime;
            VesselParticulars lilyP = LilyMaryDemo.CreateLily();
            VesselParticulars maryP = LilyMaryDemo.CreateMary();
            SimTime? foundTc = CollisionDetector.FindFirstContactTime(
                time => ToBody(lily, lilyP, time),
                time => ToBody(mary, maryP, time),
                SimTime.Zero,
                LilyMaryDemo.SimulationEnd,
                0.05,
                1.0);
            if (foundTc.HasValue)
            {
                tc = foundTc.Value;
            }

            EncounterAnalysisReport analysis = EncounterAnalyzer.Analyze(
                series, tc, new IShipTrack[] { lily, mary });

            string tempDir = Path.Combine(Path.GetTempPath(), "mcis-report-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(tempDir);
            string mcase = Path.Combine(tempDir, "Demo_LilyMary.mcase");
            var repo = new CaseRepository(Path.Combine(tempDir, "recent.txt"), "演示调查员");
            var created = repo.CreateNew(LilyMaryDemo.CreateMetadata(), mcase);
            if (!created.IsSuccess)
            {
                throw new InvalidOperationException(created.ErrorMessage);
            }

            repo.AddWorkspaceFile("raw/ais/lily_shore_station.nmea", System.Text.Encoding.UTF8.GetBytes("!AIVDM,DEMO,FICTIONAL LILY\n"));
            repo.AddWorkspaceFile("raw/ais/mary_ais_export.csv", System.Text.Encoding.UTF8.GetBytes("time,lat,lon,sog,cog\n# 虚构示例数据\n"));
            repo.AddWorkspaceFile("evidence/E01_lily_master_statement.txt", System.Text.Encoding.UTF8.GetBytes("虚构船长陈述（仅供演示）"));
            repo.Save();
            PackageManifest manifest = PackageManifest.FromJson(
                File.ReadAllText(CasePackageLayout.Combine(repo.ActiveWorkspaceDirectory, CasePackageLayout.ManifestFileName)));
            string packageHash = Sha256Util.ComputeFileHex(mcase);
            CaseMetadata meta = created.Value;

            var document = BuildDocument(meta, lily, mary, series, analysis, ecfc, manifest, packageHash);
            var renderer = new DocumentRenderer(document);
            renderer.PrepareDocument();

            var pdf = new PdfDocument();
            pdf.Info.Title = meta.Title;
            pdf.Info.Author = meta.AgencyName;
            pdf.Info.Subject = WatermarkText;
            int count = renderer.FormattedDocument.PageCount;
            for (int i = 1; i <= count; i++)
            {
                PdfPage page = pdf.AddPage();
                page.Size = PdfSharp.PageSize.A4;
                using (XGraphics gfx = XGraphics.FromPdfPage(page))
                {
                    renderer.RenderPage(gfx, i);
                    DrawWatermark(gfx, page, meta.IsFictionalDemo);
                }
            }

            AddChartPage(pdf, "航迹态势图（矢量）", g => DrawTracks(g, lily, mary, series, analysis, meta.CaseEpochUtc, tc), meta.IsFictionalDemo);
            AddChartPage(pdf, "距离 / DCPA / TCPA 曲线（矢量）", g => DrawCpaCurves(g, series, analysis, meta.CaseEpochUtc, tc), meta.IsFictionalDemo);
            AddChartPage(pdf, "ECFC 事件与原因因素图（矢量）", g => DrawEcfc(g, ecfc), meta.IsFictionalDemo);

            string dir = Path.GetDirectoryName(outputPdfPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            int pageCount = pdf.PageCount;
            pdf.Save(outputPdfPath);
            string sha = Sha256Util.ComputeFileHex(outputPdfPath);
            try { Directory.Delete(tempDir, true); } catch (IOException) { }

            return new ReportBuildResult(outputPdfPath, sha, pageCount, packageHash);
        }

        public sealed class ReportBuildResult
        {
            public string PdfPath { get; }
            public string PdfSha256 { get; }
            public int PageCount { get; }
            public string PackageSha256 { get; }

            public ReportBuildResult(string pdfPath, string pdfSha256, int pageCount, string packageSha256)
            {
                PdfPath = pdfPath;
                PdfSha256 = pdfSha256;
                PageCount = pageCount;
                PackageSha256 = packageSha256;
            }
        }

        private static Document BuildDocument(
            CaseMetadata meta,
            IShipTrack lily,
            IShipTrack mary,
            CpaTimeSeries series,
            EncounterAnalysisReport analysis,
            EcfcService ecfc,
            PackageManifest manifest,
            string packageHash)
        {
            var doc = new Document();
            doc.Info.Title = meta.Title;
            doc.Info.Author = meta.LeadInvestigator;
            Style normal = doc.Styles["Normal"];
            normal.Font.Name = NotoSansScFontResolver.FamilyName;
            normal.Font.Size = 10.5;
            Style heading1 = doc.Styles["Heading1"];
            heading1.Font.Name = NotoSansScFontResolver.FamilyName;
            heading1.Font.Size = 18;
            heading1.Font.Bold = true;
            heading1.ParagraphFormat.SpaceBefore = "6pt";
            heading1.ParagraphFormat.SpaceAfter = "4pt";
            Style heading2 = doc.Styles["Heading2"];
            heading2.Font.Name = NotoSansScFontResolver.FamilyName;
            heading2.Font.Size = 13;
            heading2.Font.Bold = true;
            heading2.ParagraphFormat.SpaceBefore = "6pt";
            heading2.ParagraphFormat.SpaceAfter = "3pt";

            Section s = doc.AddSection();
            s.PageSetup.PageFormat = PageFormat.A4;
            s.PageSetup.TopMargin = "16mm";
            s.PageSetup.BottomMargin = "20mm";
            s.PageSetup.LeftMargin = "18mm";
            s.PageSetup.RightMargin = "18mm";
            var footer = s.Footers.Primary.AddParagraph();
            footer.AddText("MCIS 调查报告  ·  " + SoftwareVersion + "  ·  第 ");
            footer.AddPageField();
            footer.AddText(" 页");
            footer.Format.Font.Size = 8;
            footer.Format.Alignment = ParagraphAlignment.Center;

            // 封面
            Paragraph p = s.AddParagraph("海事事故调查三维仿真系统");
            p.Format.Alignment = ParagraphAlignment.Center;
            p.Format.Font.Size = 14;
            p.Format.SpaceBefore = "8mm";
            p = s.AddParagraph("调查报告");
            p.Format.Alignment = ParagraphAlignment.Center;
            p.Format.Font.Size = 26;
            p.Format.Font.Bold = true;
            p.Format.SpaceAfter = "8mm";
            p = s.AddParagraph(meta.Title);
            p.Format.Alignment = ParagraphAlignment.Center;
            p.Format.Font.Size = 14;
            p.Format.SpaceAfter = "10mm";
            AddKv(s, "案件编号", meta.CaseId);
            AddKv(s, "事故类型 / 等级", meta.AccidentType + " / " + meta.AccidentGrade);
            AddKv(s, "调查员 / 机构", meta.LeadInvestigator + " / " + meta.AgencyName);
            AddKv(s, "生成时间（UTC+8）", DateTimeOffset.UtcNow.ToOffset(TimeSpan.FromHours(8)).ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture) + "  Asia/Shanghai");
            AddKv(s, "软件版本", SoftwareVersion);
            AddKv(s, "案件包 SHA-256", packageHash);
            if (meta.IsFictionalDemo)
            {
                p = s.AddParagraph(WatermarkText);
                p.Format.Alignment = ParagraphAlignment.Center;
                p.Format.Font.Size = 16;
                p.Format.Font.Bold = true;
                p.Format.Font.Color = Colors.DarkRed;
                p.Format.SpaceBefore = "8mm";
            }

            s.AddParagraph("一、事故概况").Style = "Heading1";
            s.AddParagraph(meta.SummaryNotes);
            s.AddParagraph(string.Format(
                CultureInfo.InvariantCulture,
                "事故水域参考原点：东经 {0:F6}°，北纬 {1:F6}°。案件纪元时间为 {2:yyyy-MM-dd HH:mm} UTC（北京时间 {3:HH:mm}）。仿真总时长 15 分钟。",
                meta.IncidentLocation.LonDeg, meta.IncidentLocation.LatDeg, meta.CaseEpochUtc,
                meta.CaseEpochUtc.ToOffset(TimeSpan.FromHours(8))));

            var env = LilyMaryDemo.CreateEnvironment(SimTime.Zero);
            s.AddParagraph("二、环境条件").Style = "Heading1";
            s.AddParagraph(string.Format(
                CultureInfo.InvariantCulture,
                "傍晚薄雾，水平能见度 {0:F1} n mile；风向（来向）{1:F0}°，风速 {2:F1} m/s；有效波高 Hs={3:F1} m，周期 Tp={4:F1} s；涨潮流向（去向）{5:F0}°，流速 {6:F1} kn。",
                env.VisibilityNm, env.WindFromDirDeg, env.WindSpeedMps, env.WaveSignificantHeightM,
                env.WavePeakPeriodSec, env.CurrentToDirDeg, env.CurrentSpeedKn));

            s.AddParagraph("三、船舶资料").Style = "Heading1";
            AppendVessel(s, LilyMaryDemo.CreateLily());
            AppendVessel(s, LilyMaryDemo.CreateMary());

            s.AddParagraph("四、关键时刻").Style = "Heading1";
            if (analysis.FirstWarning.HasValue)
                AddKv(s, "首次警告", FormatMoment(analysis.FirstWarning.Value, meta.CaseEpochUtc));
            if (analysis.FirstDanger.HasValue)
                AddKv(s, "首次危险", FormatMoment(analysis.FirstDanger.Value, meta.CaseEpochUtc));
            if (analysis.MinDistance.HasValue)
                AddKv(s, "最近距离", FormatMoment(analysis.MinDistance.Value, meta.CaseEpochUtc));
            if (analysis.Collision.HasValue)
                AddKv(s, "首次接触 tc", FormatMoment(analysis.Collision.Value, meta.CaseEpochUtc));
            s.AddParagraph(string.Format(CultureInfo.InvariantCulture,
                "全时段预计算样本 {0} 个（步长 1 s）。航迹图、CPA 曲线与 ECFC 图见后续矢量附图。",
                series.Samples.Count));
            s.AddParagraph(
                "会遇过程（虚构）：两船起初在窄航道内计划左对左通过，t = 0 时 DCPA 大于 1 nm，风险为“安全”。约数分钟后 Mary 轮违规向左转向，DCPA 降至 1 nm 以下进入警告，随后进入危险；Lily 轮向右转向并倒车已来不及，约 10 分钟时两船发生碰撞。碰撞后不再用 DCPA/TCPA 描述会遇几何。");

            s.AddParagraph("五、剔除点统计").Style = "Heading1";
            s.AddParagraph(string.Format(CultureInfo.InvariantCulture,
                "清洗后有效样本 {0} 个，剔除 {1} 个，人工恢复 {2} 个。本演示航迹由手绘关键点按航速分配时间生成，故剔除点为 0。",
                analysis.RejectedStats.TotalCleaned, analysis.RejectedStats.TotalRejected, analysis.RejectedStats.ManuallyRestored));

            s.AddParagraph("六、SHA-256 证据清单").Style = "Heading1";
            int listed = 0;
            for (int i = 0; i < manifest.Files.Count; i++)
            {
                ManifestFileEntry e = manifest.Files[i];
                string name = System.IO.Path.GetFileName(e.RelativePath.Replace('\\', '/'));
                if (name == ".keep" || e.SizeBytes == 0)
                {
                    continue;
                }

                listed++;
                s.AddParagraph(string.Format(CultureInfo.InvariantCulture,
                    "{0}  [{1}]  {2} 字节  SHA-256={3}", e.RelativePath, e.Role, e.SizeBytes, e.Sha256));
            }

            s.AddParagraph(string.Format(CultureInfo.InvariantCulture,
                "以上为有内容的证据与案件定义文件；清单共 {0} 条（另含用于保持空目录的占位文件，未逐条列出）。",
                manifest.Files.Count));

            s.AddParagraph("七、方法学声明").Style = "Heading1";
            s.AddParagraph(
                "本报告中的航迹由关键点经三次 Hermite / Catmull-Rom 样条并按航速分配时间生成；DCPA/TCPA 采用向量法（r = P_t−P_o，v = V_t−V_o，TCPA = −(r·v)/|v|²，DCPA = |r + v·TCPA|），并与论文 3.4 节矢量三角形公式交叉验证。风险分级采用 DCPA < 0.3 n mile 且 0 < TCPA < 6 min 为危险、DCPA < 1 n mile 且 0 < TCPA < 12 min 为警告，并施加 1 s 正向滞回。碰撞时刻 tc 由两船 OBB 净距离线二分搜索得到（精度 0.05 s）。进水流量采用 Q = Cd·A·√(2gh)，Cd 默认 0.60。碰撞动能与破口面积为示意级估算，不得替代结构有限元或法定检验。原始证据入包后计算 SHA-256 并与清单核对，派生数据可重算。");
            s.AddParagraph(
                "免责声明：内置 Lily / Mary 案例全部为虚构演示数据（IsFictionalDemo = true），船名、MMSI、IMO、坐标与时间戳均不对应任何真实海事事故，仅用于软件功能验证与培训。本报告每一页均印有“示例数据 / 虚构案例（仅供演示）”水印。");

            s.AddParagraph("八、ECFC 节点摘要").Style = "Heading1";
            for (int i = 0; i < ecfc.Nodes.Count; i++)
            {
                EcfcNode n = ecfc.Nodes[i];
                string time = n.Time.HasValue ? n.Time.Value.ToString() : "—";
                s.AddParagraph(string.Format("{0} ({1}, t={2}{3})  {4}",
                    n.NodeId, n.Kind == EcfcNodeKind.Event ? "事件" : "条件", time,
                    n.IsPresumptive ? "，推定" : "", n.Text));
            }

            return doc;
        }

        private static void AppendVessel(Section s, VesselParticulars v)
        {
            s.AddParagraph(v.Name + "（" + (v.NameCn ?? "") + "）").Style = "Heading2";
            AddKv(s, "识别号", "MMSI " + v.Mmsi + " / " + (v.ImoNumber ?? "") + " / 呼号 " + (v.CallSign ?? ""));
            AddKv(s, "船型 / 载况", v.VesselTypeCode + " / " + v.LoadingCondition);
            AddKv(s, "尺度", string.Format(CultureInfo.InvariantCulture,
                "Loa {0:F1} m，型宽 {1:F1} m，型深 {2:F1} m，吃水 {3:F1}/{4:F1} m，排水量 {5:F0} t",
                v.LoaM, v.BeamM, v.MoldedDepthM, v.DraftForeM, v.DraftAftM, v.DisplacementTons));
        }

        private static void AddKv(Section s, string k, string v, bool keepWithNext = false)
        {
            Paragraph p = s.AddParagraph();
            p.AddFormattedText(k + "：", TextFormat.Bold);
            p.AddText(v ?? string.Empty);
            if (keepWithNext)
            {
                p.Format.KeepWithNext = true;
            }
        }

        private static string FormatMoment(AnalysisKeyMoment m, DateTimeOffset epoch)
        {
            string utc8 = epoch.AddSeconds(m.Time.Seconds).ToOffset(TimeSpan.FromHours(8)).ToString("HH:mm:ss", CultureInfo.InvariantCulture);
            string extra = "";
            if (m.Sample.HasValue)
            {
                CpaResult s = m.Sample.Value;
                extra = string.Format(CultureInfo.InvariantCulture, "，距离 {0:F3} nm，DCPA {1:F3} nm，{2}",
                    s.CurrentDistanceNm, s.DcpaNm, FormatTcpa(s.TcpaMin));
            }

            return string.Format(CultureInfo.InvariantCulture, "t = {0:F1} s（北京时间 {1}）{2}", m.Time.Seconds, utc8, extra);
        }

        private static string FormatTcpa(double tcpaMin)
        {
            if (tcpaMin > 0.05)
            {
                return string.Format(CultureInfo.InvariantCulture, "TCPA {0:F2} min", tcpaMin);
            }

            if (tcpaMin >= -0.05)
            {
                return "TCPA ≈ 0";
            }

            return "已过最近会遇点";
        }

        private static CollisionBodyState ToBody(IShipTrack track, VesselParticulars vessel, double timeSec)
        {
            TrackSample s = track.SampleAt(new SimTime(timeSec));
            return new CollisionBodyState(
                vessel.VesselId,
                s.EnuCenter,
                s.HdgDeg,
                s.VelocityEnuMps,
                vessel.LoaM,
                vessel.BeamM,
                vessel.DisplacementTons);
        }

        private static void AddChartPage(PdfDocument pdf, string title, Action<XGraphics> draw, bool watermark)
        {
            PdfPage page = pdf.AddPage();
            page.Size = PdfSharp.PageSize.A4;
            using (XGraphics gfx = XGraphics.FromPdfPage(page))
            {
                var font = new XFont(NotoSansScFontResolver.FamilyName, 14, XFontStyleEx.Bold);
                gfx.DrawString(title, font, XBrushes.Black, new XPoint(50, 40));
                draw(gfx);
                if (watermark)
                {
                    DrawWatermark(gfx, page, true);
                }
            }
        }

        private static void DrawWatermark(XGraphics gfx, PdfPage page, bool enabled)
        {
            if (!enabled)
            {
                return;
            }

            var font = new XFont(NotoSansScFontResolver.FamilyName, 22, XFontStyleEx.Bold);
            gfx.Save();
            gfx.TranslateTransform(page.Width.Point / 2, page.Height.Point / 2);
            gfx.RotateTransform(-32);
            var brush = new XSolidBrush(XColor.FromArgb(40, 160, 20, 20));
            gfx.DrawString(WatermarkText, font, brush, new XPoint(0, 0), XStringFormats.Center);
            gfx.Restore();
        }
    }
}
