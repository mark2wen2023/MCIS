using System;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Simulation.Damage
{
    /// <summary>水平面二维定向包围盒（船中心、首向、半长、半宽），用于船体净距计算。</summary>
    public readonly struct OrientedBoundingBox
    {
        public EnuPosition Center { get; }
        public double HeadingDeg { get; }
        public double HalfLengthM { get; }
        public double HalfBeamM { get; }

        public OrientedBoundingBox(EnuPosition center, double headingDeg, double halfLengthM, double halfBeamM)
        {
            Center = center;
            HeadingDeg = headingDeg;
            HalfLengthM = Math.Max(halfLengthM, 0.0);
            HalfBeamM = Math.Max(halfBeamM, 0.0);
        }

        public static OrientedBoundingBox FromVessel(EnuPosition center, double headingDeg, float loaM, float beamM)
        {
            return new OrientedBoundingBox(center, headingDeg, loaM * 0.5, beamM * 0.5);
        }

        /// <summary>船体局部 (forward, starboard) 轴的单位向量（ENU）。</summary>
        public void GetAxes(out Double2 forward, out Double2 starboard)
        {
            double rad = HeadingDeg * Math.PI / 180.0;
            double sin = Math.Sin(rad);
            double cos = Math.Cos(rad);
            forward = new Double2(sin, cos);
            starboard = new Double2(cos, -sin);
        }

        public Double2[] GetCorners()
        {
            Double2 f, s;
            GetAxes(out f, out s);
            var c = new Double2(Center.EastM, Center.NorthM);
            return new[]
            {
                c + f * HalfLengthM + s * HalfBeamM,
                c + f * HalfLengthM - s * HalfBeamM,
                c - f * HalfLengthM - s * HalfBeamM,
                c - f * HalfLengthM + s * HalfBeamM
            };
        }

        /// <summary>
        /// 计算两艘（或船与固定物）OBB 之间的最小净距。正值=分离时两矩形的欧氏最小距离，0=刚好接触，
        /// 负值=穿透深度（沿 SAT 轴的最小平移量）。
        /// 先用二维分离轴定理判定分离/重叠；分离时按「顶点到对方各边」32 次点-线段距离穷举取最小值
        /// （覆盖边对边、点对边与角对角），重叠时保持原约定返回 −最小穿透深度。
        /// </summary>
        public static double Clearance(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            Double2 af, asb, bf, bsb;
            a.GetAxes(out af, out asb);
            b.GetAxes(out bf, out bsb);
            Double2 ca = new Double2(a.Center.EastM, a.Center.NorthM);
            Double2 cb = new Double2(b.Center.EastM, b.Center.NorthM);
            Double2 d = cb - ca;

            Double2[] axes = new[] { af, asb, bf, bsb };
            double minSeparation = double.PositiveInfinity;
            double minPenetration = double.PositiveInfinity;
            bool separated = false;

            for (int i = 0; i < axes.Length; i++)
            {
                Double2 axis = NormalizeOrZero(axes[i]);
                if (axis.LengthSquared < 1e-16)
                {
                    continue;
                }

                double projD = Math.Abs(Double2.Dot(d, axis));
                double ra = a.HalfLengthM * Math.Abs(Double2.Dot(af, axis)) + a.HalfBeamM * Math.Abs(Double2.Dot(asb, axis));
                double rb = b.HalfLengthM * Math.Abs(Double2.Dot(bf, axis)) + b.HalfBeamM * Math.Abs(Double2.Dot(bsb, axis));
                double gap = projD - (ra + rb);
                if (gap > 0.0)
                {
                    separated = true;
                    if (gap < minSeparation)
                    {
                        minSeparation = gap;
                    }
                }
                else
                {
                    double pen = -gap;
                    if (pen < minPenetration)
                    {
                        minPenetration = pen;
                    }
                }
            }

            if (separated)
            {
                double exact = SeparatedDistance(a, b);
                // 分离已由 SAT 判定；精确距离不应小于任一轴间隙（数值上取较大者以保持符号一致）。
                return Math.Max(exact, minSeparation == double.PositiveInfinity ? 0.0 : minSeparation);
            }

            return minPenetration == double.PositiveInfinity ? 0.0 : -minPenetration;
        }

        /// <summary>
        /// 接触点（保留旧名以兼容调用方）：等同于 <see cref="ContactPoint"/>。
        /// W14.1 起不再取两中心中点。
        /// </summary>
        public static EnuPosition ApproximateContact(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            return ContactPoint(a, b);
        }

        /// <summary>
        /// 两 OBB 的接触点：分离或刚好接触时取最近点对的中点；重叠时取两矩形交集（穿透区）多边形的形心。
        /// 交集退化（面积≈0）时退回最近点对中点。Up 分量取两中心 Up 的均值。
        /// </summary>
        public static EnuPosition ContactPoint(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            double up = 0.5 * (a.Center.UpM + b.Center.UpM);
            Double2 p;
            if (Clearance(a, b) <= 0.0)
            {
                Double2 centroid;
                if (TryIntersectionCentroid(a.GetCorners(), b.GetCorners(), out centroid))
                {
                    return new EnuPosition(centroid.X, centroid.Y, up);
                }
            }

            Double2 pa, pb;
            ClosestPoints(a, b, out pa, out pb);
            p = (pa + pb) * 0.5;
            return new EnuPosition(p.X, p.Y, up);
        }

        /// <summary>两 OBB 边界上的最近点对（按顶点-边穷举；重叠时结果仅表示边界上最近的一对特征点）。</summary>
        public static void ClosestPoints(OrientedBoundingBox a, OrientedBoundingBox b, out Double2 pointOnA, out Double2 pointOnB)
        {
            Double2[] ca = a.GetCorners();
            Double2[] cb = b.GetCorners();
            double best = double.PositiveInfinity;
            pointOnA = ca[0];
            pointOnB = cb[0];
            for (int i = 0; i < 4; i++)
            {
                for (int j = 0; j < 4; j++)
                {
                    Double2 q;
                    double d = PointSegmentDistance(ca[i], cb[j], cb[(j + 1) % 4], out q);
                    if (d < best)
                    {
                        best = d;
                        pointOnA = ca[i];
                        pointOnB = q;
                    }

                    d = PointSegmentDistance(cb[i], ca[j], ca[(j + 1) % 4], out q);
                    if (d < best)
                    {
                        best = d;
                        pointOnA = q;
                        pointOnB = cb[i];
                    }
                }
            }
        }

        private static double SeparatedDistance(OrientedBoundingBox a, OrientedBoundingBox b)
        {
            Double2 pa, pb;
            ClosestPoints(a, b, out pa, out pb);
            return (pb - pa).Length;
        }

        private static double PointSegmentDistance(Double2 p, Double2 s0, Double2 s1, out Double2 closest)
        {
            Double2 seg = s1 - s0;
            double len2 = seg.LengthSquared;
            double t = len2 > 1e-18 ? Double2.Dot(p - s0, seg) / len2 : 0.0;
            if (t < 0.0) t = 0.0;
            if (t > 1.0) t = 1.0;
            closest = s0 + seg * t;
            return (p - closest).Length;
        }

        private static bool TryIntersectionCentroid(Double2[] subject, Double2[] clip, out Double2 centroid)
        {
            centroid = Double2.Zero;
            // GetCorners 的顶点顺序在 ENU（东-北）坐标下为顺时针；统一转为逆时针后做 Sutherland–Hodgman 裁剪。
            Double2[] clipCcw = EnsureCounterClockwise(clip);
            var poly = new System.Collections.Generic.List<Double2>(EnsureCounterClockwise(subject));
            for (int e = 0; e < clipCcw.Length && poly.Count > 0; e++)
            {
                Double2 c0 = clipCcw[e];
                Double2 c1 = clipCcw[(e + 1) % clipCcw.Length];
                var input = poly;
                poly = new System.Collections.Generic.List<Double2>(input.Count + 2);
                for (int i = 0; i < input.Count; i++)
                {
                    Double2 cur = input[i];
                    Double2 prev = input[(i + input.Count - 1) % input.Count];
                    double dCur = Cross(c1 - c0, cur - c0);
                    double dPrev = Cross(c1 - c0, prev - c0);
                    bool curIn = dCur >= 0.0;
                    bool prevIn = dPrev >= 0.0;
                    if (curIn)
                    {
                        if (!prevIn)
                        {
                            poly.Add(Lerp(prev, cur, dPrev / (dPrev - dCur)));
                        }

                        poly.Add(cur);
                    }
                    else if (prevIn)
                    {
                        poly.Add(Lerp(prev, cur, dPrev / (dPrev - dCur)));
                    }
                }
            }

            if (poly.Count < 3)
            {
                return false;
            }

            double area2 = 0.0;
            double cx = 0.0;
            double cy = 0.0;
            for (int i = 0; i < poly.Count; i++)
            {
                Double2 p0 = poly[i];
                Double2 p1 = poly[(i + 1) % poly.Count];
                double cr = Cross(p0, p1);
                area2 += cr;
                cx += (p0.X + p1.X) * cr;
                cy += (p0.Y + p1.Y) * cr;
            }

            if (Math.Abs(area2) < 1e-9)
            {
                return false;
            }

            centroid = new Double2(cx / (3.0 * area2), cy / (3.0 * area2));
            return true;
        }

        private static Double2[] EnsureCounterClockwise(Double2[] poly)
        {
            double area2 = 0.0;
            for (int i = 0; i < poly.Length; i++)
            {
                area2 += Cross(poly[i], poly[(i + 1) % poly.Length]);
            }

            if (area2 >= 0.0)
            {
                return poly;
            }

            var reversed = new Double2[poly.Length];
            for (int i = 0; i < poly.Length; i++)
            {
                reversed[i] = poly[poly.Length - 1 - i];
            }

            return reversed;
        }

        private static double Cross(Double2 u, Double2 v)
        {
            return u.X * v.Y - u.Y * v.X;
        }

        private static Double2 Lerp(Double2 p, Double2 q, double t)
        {
            return p + (q - p) * t;
        }

        private static Double2 NormalizeOrZero(Double2 v)
        {
            double len = v.Length;
            if (len < 1e-12)
            {
                return Double2.Zero;
            }

            return v / len;
        }
    }

    /// <summary>船舶在某一时刻用于碰撞检测的运动学快照。</summary>
    public readonly struct CollisionBodyState
    {
        public string Id { get; }
        public EnuPosition Center { get; }
        public double HeadingDeg { get; }
        public Double2 VelocityEnuMps { get; }
        public float LoaM { get; }
        public float BeamM { get; }
        public float DisplacementTons { get; }
        public bool IsFixed { get; }

        public CollisionBodyState(
            string id,
            EnuPosition center,
            double headingDeg,
            Double2 velocityEnuMps,
            float loaM,
            float beamM,
            float displacementTons,
            bool isFixed = false)
        {
            Id = id ?? string.Empty;
            Center = center;
            HeadingDeg = headingDeg;
            VelocityEnuMps = velocityEnuMps;
            LoaM = loaM;
            BeamM = beamM;
            DisplacementTons = displacementTons;
            IsFixed = isFixed;
        }

        public OrientedBoundingBox Obb
        {
            get { return OrientedBoundingBox.FromVessel(Center, HeadingDeg, LoaM, BeamM); }
        }
    }
}
