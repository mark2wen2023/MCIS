using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;

namespace Mcis.Acceptance.W1
{
    /// <summary>
    /// W1 验收夹具。全部航迹为合成虚构数据（示例数据·虚构，"虚构甲船/虚构乙船"），局部 ENU 米、m/s、度。
    /// 船舶以 1 s 步长积分（转向率默认 6°/s），按 outEvery 秒输出 TrackSample，位置/速度/航向自洽。
    /// </summary>
    internal static class Fx
    {
        public const string Own = "虚构甲船";
        public const string Tgt = "虚构乙船";

        public static double Sin(double d) => Math.Sin(d * Math.PI / 180);
        public static double Cos(double d) => Math.Cos(d * Math.PI / 180);
        public static double Norm(double a) => (a % 360 + 360) % 360;
        public static double Delta(double from, double to) => Norm(to - from + 180) - 180;

        public static TrackSample S(double t, double e, double n, double hdg, double spd, float? hdgOverride = null, bool fromCog = false, float? cog = null)
        {
            return new TrackSample(new SimTime(t), new GeoCoord(0, 0), new EnuPosition(e, n),
                new Double2(spd * Sin(hdg), spd * Cos(hdg)), (float)spd, cog ?? (float)Norm(hdg),
                hdgOverride ?? (float)Norm(hdg), 0, SampleProvenance.Presumed, TimeQuality.Estimated, fromCog);
        }

        public static EnvironmentState Env(double t, float vis) =>
            new EnvironmentState(new SimTime(t), "虚构环境", vis, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);

        public static Result<ColregAnalysisReport> Run(IReadOnlyList<TrackSample> own, IReadOnlyList<TrackSample> tgt,
            ColregThresholds th = null, double? vis = 8, bool? inSight = true, bool narrow = false,
            IReadOnlyList<EnvironmentState> env = null)
        {
            return new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Tgt, own, tgt, th, env, vis, inSight, narrow));
        }

        public static ColregAnalysisReport Ok(IReadOnlyList<TrackSample> own, IReadOnlyList<TrackSample> tgt,
            ColregThresholds th = null, double? vis = 8, bool? inSight = true, bool narrow = false,
            IReadOnlyList<EnvironmentState> env = null)
        {
            var r = Run(own, tgt, th, vis, inSight, narrow, env);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static ColregTimeBand BandAt(ColregAnalysisReport r, double t)
        {
            ColregTimeBand hit = null;
            foreach (var b in r.TimeBands)
                if (b.StartTime.Seconds <= t + 1e-9 && t <= b.EndTime.Seconds + 1e-9) hit = b; // 边界归后一带
            Assert.NotNull(hit);
            return hit;
        }

        public static IEnumerable<ColregRuleCheck> Checks(ColregAnalysisReport r, ColregRuleId id, string vessel) =>
            r.RuleChecks.Where(c => c.RuleId == id && c.VesselId == vessel);

        public static string Describe(ColregAnalysisReport r)
        {
            var sb = new StringBuilder();
            foreach (var b in r.TimeBands)
                sb.AppendFormat(CultureInfo.InvariantCulture, "[{0:F1}-{1:F1}] {2} own={3} tgt={4} rules={5}\n",
                    b.StartTime.Seconds, b.EndTime.Seconds, b.Situation, b.OwnRole, b.TargetRole, string.Join(",", b.ApplicableRules));
            foreach (var c in r.RuleChecks)
                sb.AppendFormat(CultureInfo.InvariantCulture, "  {0:F1}-{1:F1} {2} {3} {4} {5} hdgΔ={6:F2} spdΔ={7:F2} turn={8} | {9}\n",
                    c.StartTime.Seconds, c.EndTime.Seconds, c.RuleId, c.Clause, c.VesselId, c.Status,
                    c.ActualAction.HeadingChangeDeg, c.ActualAction.SpeedChangeMps, c.ActualAction.Turn, c.Explanation);
            return sb.ToString();
        }

        /// <summary>完整序列化（含数值），用于确定性比较。</summary>
        public static string Fingerprint(ColregAnalysisReport r)
        {
            var sb = new StringBuilder(Describe(r));
            foreach (var c in r.RuleChecks)
            {
                var e = c.Evidence;
                sb.Append(string.Join("|", new[] { e.RelativeBearingDeg, e.HeadingDifferenceDeg, e.DcpaM, e.TcpaSeconds, e.HeadingChangeDeg,
                    e.SpeedChangeMps, e.VisibilityNm, e.DistanceM, e.EndDcpaM, e.MinimumObservedDistanceM, e.EndTcpaSeconds,
                    e.EndDistanceM, e.EarlyActionRemainingTcpaSeconds, e.EarlyActionDistanceM }.Select(v => v.ToString("R", CultureInfo.InvariantCulture))));
                sb.Append(c.ExpectedAction).Append('\n');
            }
            sb.Append(string.Join("\n", r.Assumptions));
            return sb.ToString();
        }

        /// <summary>
        /// 本船位于原点、航向 0°、航速 ownSpeed；他船在相对方位 relBearing、距离 dist 处，以恒定航向航速于 T 秒后与本船相遇（DCPA=0，方位不变）。
        /// </summary>
        public static Ship CollisionTarget(double relBearing, double dist, double T, double ownSpeed = 5)
        {
            double e0 = dist * Sin(relBearing), n0 = dist * Cos(relBearing);
            double pe = 0, pn = ownSpeed * T;
            double ve = (pe - e0) / T, vn = (pn - n0) / T;
            double hdg = Norm(Math.Atan2(ve, vn) * 180 / Math.PI);
            return new Ship(e0, n0, hdg, Math.Sqrt(ve * ve + vn * vn));
        }
    }

    /// <summary>简单运动学船：1 s 积分，定转向率，瞬时变速（可设加速度）。</summary>
    internal sealed class Ship
    {
        private readonly double _e, _n, _h, _v;
        private readonly List<(double t, double hdg, double spd)> _orders = new List<(double, double, double)>();
        public double TurnRate = 6.0;
        public double Accel = 0.5;

        public Ship(double e, double n, double hdg, double spd) { _e = e; _n = n; _h = hdg; _v = spd; }
        public double Heading => _h;
        public double Speed => _v;

        /// <summary>自 t 秒起转向至 hdg（沿最短方向，若 viaStarboard 指定则按该方向），航速改为 spd（空=不变）。</summary>
        public Ship Order(double t, double hdg, double? spd = null)
        {
            _orders.Add((t, hdg, spd ?? double.NaN));
            return this;
        }

        public TrackSample[] Run(double duration, double outEvery = 10, double t0 = 0, double dt = 1)
        {
            var list = new List<TrackSample>();
            double e = _e, n = _n, h = _h, v = _v, cmdH = _h, cmdV = _v;
            var orders = _orders.OrderBy(o => o.t).ToList();
            int oi = 0;
            int steps = (int)Math.Round(duration / dt);
            int outStride = Math.Max(1, (int)Math.Round(outEvery / dt));
            for (int k = 0; k <= steps; k++)
            {
                double t = k * dt;
                while (oi < orders.Count && orders[oi].t <= t + 1e-9)
                {
                    cmdH = orders[oi].hdg;
                    if (!double.IsNaN(orders[oi].spd)) cmdV = orders[oi].spd;
                    oi++;
                }
                if (k % outStride == 0 || k == steps) list.Add(Fx.S(t0 + t, e, n, h, v));
                double d = Fx.Delta(h, cmdH);
                double step = Math.Min(Math.Abs(d), TurnRate * dt) * Math.Sign(d);
                double dv = cmdV - v;
                double vstep = Math.Min(Math.Abs(dv), Accel * dt) * Math.Sign(dv);
                double hNew = Fx.Norm(h + step), vNew = v + vstep;
                // 中点积分
                double hm = h + step / 2, vm = (v + vNew) / 2;
                e += vm * Fx.Sin(hm) * dt; n += vm * Fx.Cos(hm) * dt;
                h = hNew; v = vNew;
            }
            return list.ToArray();
        }
    }
}
