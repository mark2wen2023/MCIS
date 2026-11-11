using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Models;
using Mcis.Simulation.Damage;
using Mcis.Simulation.WhatIf;
using Mcis.Simulation.WhatIf.Cases;
using Mcis.Simulation.WhatIf.Demo;
using Xunit;
using Xunit.Sdk;

namespace Mcis.Acceptance.W14
{
    /// <summary>W14 独立验收夹具：几何核对、航迹构造、真实案例定位。不改被测代码。</summary>
    internal static class W14AccFixture
    {
        public const double MpsPerKnot = 1852.0 / 3600.0;
        public const double MetersPerNm = 1852.0;
        public const string Disclaimer = "仅供分析参考：本结果基于简化操纵模型的反事实推演，不作责任认定。";

        public static string FindRepoRoot()
        {
            string dir = AppContext.BaseDirectory;
            for (int i = 0; i < 16 && !string.IsNullOrEmpty(dir); i++)
            {
                if (File.Exists(Path.Combine(dir, "ROADMAP.md")) &&
                    Directory.Exists(Path.Combine(dir, "unity")) &&
                    Directory.Exists(Path.Combine(dir, "reports")))
                {
                    return dir;
                }
                DirectoryInfo parent = Directory.GetParent(dir);
                if (parent == null) break;
                dir = parent.FullName;
            }
            throw new XunitException("无法定位仓库根目录（需要 ROADMAP.md + unity/ + reports/）：" + AppContext.BaseDirectory);
        }

        public static string LogsDirectory
        {
            get
            {
                string path = Path.Combine(FindRepoRoot(), "logs");
                Directory.CreateDirectory(path);
                return path;
            }
        }

        public static string Yangze22Directory
        {
            get
            {
                string path = Path.Combine(FindRepoRoot(), "reports", "yangze22");
                if (!Directory.Exists(path))
                {
                    throw new XunitException("未找到真实报告目录：" + path);
                }
                return path;
            }
        }

        public static string[] ReadYangzeTrackLines()
        {
            string path = Path.Combine(Yangze22Directory, "tracks_from_report.csv");
            Assert.True(File.Exists(path), "缺少航迹文件：" + path);
            return File.ReadAllLines(path);
        }

        public static string ReadYangzeCaseJson()
        {
            string path = Path.Combine(Yangze22Directory, "case.json");
            Assert.True(File.Exists(path), "缺少案例文件：" + path);
            return File.ReadAllText(path);
        }

        public static Yangze22Inputs LoadYangzeInputs(
            double endSeconds = 300.0,
            bool truncateAfterReportedCollision = true)
        {
            using JsonDocument document = JsonDocument.Parse(ReadYangzeCaseJson());
            JsonElement root = document.RootElement;

            List<Yangze22VesselInput> vessels = new List<Yangze22VesselInput>();
            int index = 0;
            foreach (JsonElement vessel in root.GetProperty("vessels").EnumerateArray())
            {
                JsonElement fieldSources = vessel.GetProperty("fieldSources");
                string reference =
                    "case.json vessels[" + index + "].fieldSources.loaM/beamM/grossTonnage；" +
                    FormatSource(fieldSources.GetProperty("loaM"));
                vessels.Add(new Yangze22VesselInput(
                    vessel.GetProperty("vesselId").GetString(),
                    vessel.GetProperty("name").GetString(),
                    vessel.GetProperty("loaM").GetDouble(),
                    vessel.GetProperty("beamM").GetDouble(),
                    vessel.GetProperty("grossTonnage").GetDouble(),
                    reference));
                index++;
            }

            List<Yangze22RudderOrder> orders = new List<Yangze22RudderOrder>();
            foreach (JsonElement row in root.GetProperty("rudderOrders").GetProperty("rows").EnumerateArray())
            {
                JsonElement source = row.GetProperty("source");
                orders.Add(new Yangze22RudderOrder(
                    row.GetProperty("id").GetString(),
                    DateTimeOffset.Parse(row.GetProperty("time").GetProperty("beijing").GetString()),
                    GetNullableDouble(row, "headingDeg"),
                    GetNullableString(row, "pilotOrder"),
                    GetNullableDouble(row, "rudderCommandDeg"),
                    GetNullableDouble(row, "rudderFeedbackDeg"),
                    GetNullableBool(row, "reversedVsOrder"),
                    "case.json rudderOrders.rows[" + row.GetProperty("id").GetString() + "]；" +
                    FormatSource(source)));
            }

            JsonElement collision = root.GetProperty("collision");
            JsonElement location = collision.GetProperty("location");
            DateTimeOffset collisionTime = DateTimeOffset.Parse(
                collision.GetProperty("time").GetProperty("beijing").GetString());
            DateTimeOffset epoch = new DateTimeOffset(2024, 12, 30, 21, 58, 30, TimeSpan.FromHours(8.0));
            string collisionReference =
                "case.json collision；" + FormatSource(collision.GetProperty("timeSource")) + "；" +
                FormatSource(collision.GetProperty("angleSource"));

            return new Yangze22Inputs(
                vessels,
                orders,
                new GeoCoord(
                    location.GetProperty("lonDeg").GetDouble(),
                    location.GetProperty("latDeg").GetDouble(),
                    0.0),
                collisionTime,
                epoch,
                collision.GetProperty("collisionAngleDeg").GetDouble(),
                collision.GetProperty("contact").GetString(),
                collisionReference,
                GetNullableDouble(collision, "yangze22HeadingDeg"),
                GetNullableDouble(collision, "vegaDreamHeadingDeg"),
                GetNullableDouble(collision, "yangze22SpeedKn"),
                GetNullableDouble(collision, "vegaDreamSpeedKn"),
                endSeconds,
                truncateAfterReportedCollision);
        }

        /// <summary>
        /// 全程扫描两航迹的真实 OBB 最小净距：先按 coarseStep 粗扫，再在每个局部极小处按 fineStep 细化。
        /// 与实施方“最近会遇 ±2 s”不同，用于核对裁定 7b。
        /// </summary>
        public static void ScanGlobalMinClearance(
            CounterfactualTrack own,
            CounterfactualTrack target,
            double startSeconds,
            double endSeconds,
            out double bestClearanceM,
            out double bestTimeSeconds,
            double coarseStep = 0.5,
            double fineStep = 0.02)
        {
            if (own == null) throw new ArgumentNullException(nameof(own));
            if (target == null) throw new ArgumentNullException(nameof(target));
            List<double> times = new List<double>();
            List<double> values = new List<double>();
            for (double t = startSeconds; t <= endSeconds + 1e-9; t += coarseStep)
            {
                times.Add(t);
                values.Add(OrientedBoundingBox.Clearance(
                    BoxOf(own.SampleAt(t), own.LoaM, own.BeamM),
                    BoxOf(target.SampleAt(t), target.LoaM, target.BeamM)));
            }
            if (times.Count == 0 || times[times.Count - 1] < endSeconds - 1e-9)
            {
                times.Add(endSeconds);
                values.Add(OrientedBoundingBox.Clearance(
                    BoxOf(own.SampleAt(endSeconds), own.LoaM, own.BeamM),
                    BoxOf(target.SampleAt(endSeconds), target.LoaM, target.BeamM)));
            }

            List<double> candidates = new List<double>();
            for (int i = 0; i < values.Count; i++)
            {
                double left = i > 0 ? values[i - 1] : values[i] + 1.0;
                double right = i < values.Count - 1 ? values[i + 1] : values[i] + 1.0;
                if (values[i] <= left && values[i] <= right)
                {
                    candidates.Add(times[i]);
                }
            }

            bestClearanceM = double.PositiveInfinity;
            bestTimeSeconds = startSeconds;
            for (int c = 0; c < candidates.Count; c++)
            {
                double from = Math.Max(startSeconds, candidates[c] - coarseStep);
                double to = Math.Min(endSeconds, candidates[c] + coarseStep);
                for (double t = from; t <= to + 1e-9; t += fineStep)
                {
                    double clearance = OrientedBoundingBox.Clearance(
                        BoxOf(own.SampleAt(t), own.LoaM, own.BeamM),
                        BoxOf(target.SampleAt(t), target.LoaM, target.BeamM));
                    if (clearance < bestClearanceM)
                    {
                        bestClearanceM = clearance;
                        bestTimeSeconds = t;
                    }
                }
            }
        }

        /// <summary>船首到接触点的“船首对船首”阈值：max(10 m, 0.05 L)。</summary>
        public static double BowToBowThresholdM(double loaM)
        {
            return Math.Max(10.0, 0.05 * loaM);
        }

        /// <summary>构造匀速直线航迹的船舶（用于边界与精度用例）。</summary>
        public static WhatIfVessel StraightVessel(
            string id,
            double east0,
            double north0,
            double headingDeg,
            double speedKn,
            double loaM,
            double beamM,
            double start = 0.0,
            double end = 600.0,
            ManeuverParams parameters = null)
        {
            ManeuverParams p = parameters ?? ManeuverParams.Default(loaM, beamM, 8000.0);
            List<KinematicState> states = new List<KinematicState>();
            double rad = headingDeg * Math.PI / 180.0;
            double speedMps = speedKn * MpsPerKnot;
            for (double t = start; t <= end + 1e-9; t += 1.0)
            {
                double d = speedMps * (t - start);
                states.Add(new KinematicState(
                    t,
                    east0 + d * Math.Sin(rad),
                    north0 + d * Math.Cos(rad),
                    headingDeg,
                    speedKn,
                    0.0,
                    0.0));
            }
            return WhatIfVessel.FromStates(id, p, states, id);
        }

        public static WhatIfSetup TwoShipSetup(
            WhatIfVessel own,
            WhatIfVessel target,
            double start,
            double end,
            double safeNm = 0.1)
        {
            return new WhatIfSetup(
                new[] { own, target },
                own.Id,
                target.Id,
                start,
                end,
                1.0,
                0.05,
                0.5,
                safeNm);
        }

        /// <summary>两凸多边形（OBB 角点）的真实最小距离；重叠时返回 0。</summary>
        public static double TrueObbDistance(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            if (OrientedBoundingBox.Clearance(a, b) <= 0.0)
            {
                return 0.0;
            }
            Double2[] ca = ToPoints(a.GetCorners());
            Double2[] cb = ToPoints(b.GetCorners());
            double min = double.PositiveInfinity;
            for (int i = 0; i < 4; i++)
            {
                for (int j = 0; j < 4; j++)
                {
                    min = Math.Min(min, PointSegmentDistance(ca[i], cb[j], cb[(j + 1) % 4]));
                    min = Math.Min(min, PointSegmentDistance(cb[i], ca[j], ca[(j + 1) % 4]));
                }
            }
            return min;
        }

        /// <summary>两 OBB 的一对最近点中点（独立接触点估计）。</summary>
        public static EnuPosition ClosestPointContact(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            Double2[] ca = ToPoints(a.GetCorners());
            Double2[] cb = ToPoints(b.GetCorners());
            double best = double.PositiveInfinity;
            Double2 pa = ca[0];
            Double2 pb = cb[0];
            for (int i = 0; i < 4; i++)
            {
                for (int j = 0; j < 4; j++)
                {
                    Double2 q;
                    double d = PointSegmentDistance(ca[i], cb[j], cb[(j + 1) % 4], out q);
                    if (d < best)
                    {
                        best = d;
                        pa = ca[i];
                        pb = q;
                    }
                    d = PointSegmentDistance(cb[i], ca[j], ca[(j + 1) % 4], out q);
                    if (d < best)
                    {
                        best = d;
                        pa = q;
                        pb = cb[i];
                    }
                }
            }
            return new EnuPosition(0.5 * (pa.X + pb.X), 0.5 * (pa.Y + pb.Y), 0.0);
        }

        public static double AcuteHeadingAngleDeg(double headingA, double headingB)
        {
            double delta = Math.Abs(KinematicState.NormalizeDeg180(headingA - headingB));
            if (delta > 90.0) delta = 180.0 - delta;
            return delta;
        }

        public static string IndependentStruckSide(KinematicState struck, EnuPosition contact)
        {
            double rad = struck.HeadingDeg * Math.PI / 180.0;
            double starboardEast = Math.Cos(rad);
            double starboardNorth = -Math.Sin(rad);
            double sideDot = (contact.EastM - struck.EastM) * starboardEast +
                             (contact.NorthM - struck.NorthM) * starboardNorth;
            return sideDot >= 0.0 ? "右舷" : "左舷";
        }

        public static double IndependentContactFromBowM(KinematicState struck, double loaM, EnuPosition contact)
        {
            double rad = struck.HeadingDeg * Math.PI / 180.0;
            double projection = (contact.EastM - struck.EastM) * Math.Sin(rad) +
                                (contact.NorthM - struck.NorthM) * Math.Cos(rad);
            double fromBow = loaM * 0.5 - projection;
            if (fromBow < 0.0) fromBow = 0.0;
            if (fromBow > loaM) fromBow = loaM;
            return fromBow;
        }

        public static EnuPosition BowPoint(KinematicState state, double loaM)
        {
            double rad = state.HeadingDeg * Math.PI / 180.0;
            return new EnuPosition(
                state.EastM + Math.Sin(rad) * loaM * 0.5,
                state.NorthM + Math.Cos(rad) * loaM * 0.5,
                0.0);
        }

        public static OrientedBoundingBox BoxOf(KinematicState state, double loaM, double beamM)
        {
            return OrientedBoundingBox.FromVessel(
                new EnuPosition(state.EastM, state.NorthM, 0.0),
                state.HeadingDeg,
                (float)loaM,
                (float)beamM);
        }

        public static void AssertBitwiseEqual(KinematicState a, KinematicState b)
        {
            Assert.True(a.Equals(b), "状态不完全相等：A=" + a + " B=" + b);
        }

        public static KinematicState ShiftAntennaToCenter(
            KinematicState antenna,
            double antennaForwardOfCenterM,
            double antennaStarboardOfCenterM)
        {
            double rad = antenna.HeadingDeg * Math.PI / 180.0;
            double east = antenna.EastM
                - antennaForwardOfCenterM * Math.Sin(rad)
                - antennaStarboardOfCenterM * Math.Cos(rad);
            double north = antenna.NorthM
                - antennaForwardOfCenterM * Math.Cos(rad)
                + antennaStarboardOfCenterM * Math.Sin(rad);
            return new KinematicState(
                antenna.TimeSeconds, east, north, antenna.HeadingDeg,
                antenna.SpeedKn, antenna.RotDegPerSec, antenna.RudderDeg);
        }

        private static Double2[] ToPoints(Double2[] corners)
        {
            return corners;
        }

        private static double PointSegmentDistance(Double2 p, Double2 a, Double2 b)
        {
            Double2 q;
            return PointSegmentDistance(p, a, b, out q);
        }

        private static double PointSegmentDistance(Double2 p, Double2 a, Double2 b, out Double2 closest)
        {
            double abx = b.X - a.X;
            double aby = b.Y - a.Y;
            double len2 = abx * abx + aby * aby;
            double t = 0.0;
            if (len2 > 1e-18)
            {
                t = ((p.X - a.X) * abx + (p.Y - a.Y) * aby) / len2;
                if (t < 0.0) t = 0.0;
                if (t > 1.0) t = 1.0;
            }
            closest = new Double2(a.X + t * abx, a.Y + t * aby);
            double dx = p.X - closest.X;
            double dy = p.Y - closest.Y;
            return Math.Sqrt(dx * dx + dy * dy);
        }

        private static string FormatSource(JsonElement source)
        {
            string page = source.TryGetProperty("page", out JsonElement pageElement) ? pageElement.ToString() : "—";
            string pdfPage = source.TryGetProperty("pdfPage", out JsonElement pdfElement) ? pdfElement.ToString() : "—";
            string line = source.TryGetProperty("line", out JsonElement lineElement) ? lineElement.ToString() : "—";
            return "报告第" + page + "页（PDF 第" + pdfPage + "页，line " + line + "）";
        }

        private static double? GetNullableDouble(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetDouble();
        }

        private static string GetNullableString(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetString();
        }

        private static bool? GetNullableBool(JsonElement element, string name)
        {
            if (!element.TryGetProperty(name, out JsonElement value) || value.ValueKind == JsonValueKind.Null)
            {
                return null;
            }
            return value.GetBoolean();
        }
    }
}
