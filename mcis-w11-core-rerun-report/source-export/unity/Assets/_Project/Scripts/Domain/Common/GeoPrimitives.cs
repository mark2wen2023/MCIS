using System;
using System.Globalization;

namespace Mcis.Domain.Common
{
    /// <summary>
    /// 纯 C# 双精度二维向量（替代 Unity.Mathematics.double2，用于水平面东/北速度与位移计算）。
    /// </summary>
    public readonly struct Double2 : IEquatable<Double2>
    {
        /// <summary>零向量。</summary>
        public static readonly Double2 Zero = new Double2(0.0, 0.0);

        /// <summary>X 分量（通常对应东向 East）。</summary>
        public double X { get; }

        /// <summary>Y 分量（通常对应北向 North）。</summary>
        public double Y { get; }

        /// <summary>构造二维双精度向量。</summary>
        public Double2(double x, double y)
        {
            X = x;
            Y = y;
        }

        /// <summary>向量模长平方。</summary>
        public double LengthSquared
        {
            get { return X * X + Y * Y; }
        }

        /// <summary>向量模长。</summary>
        public double Length
        {
            get { return Math.Sqrt(X * X + Y * Y); }
        }

        /// <summary>二维向量点积。</summary>
        public static double Dot(Double2 a, Double2 b)
        {
            return a.X * b.X + a.Y * b.Y;
        }

        /// <summary>二维向量叉积标量（a.X * b.Y - a.Y * b.X）。</summary>
        public static double Cross(Double2 a, Double2 b)
        {
            return a.X * b.Y - a.Y * b.X;
        }

        public static Double2 operator +(Double2 a, Double2 b)
        {
            return new Double2(a.X + b.X, a.Y + b.Y);
        }

        public static Double2 operator -(Double2 a, Double2 b)
        {
            return new Double2(a.X - b.X, a.Y - b.Y);
        }

        public static Double2 operator *(Double2 a, double s)
        {
            return new Double2(a.X * s, a.Y * s);
        }

        public static Double2 operator *(double s, Double2 a)
        {
            return new Double2(a.X * s, a.Y * s);
        }

        public static Double2 operator /(Double2 a, double s)
        {
            return new Double2(a.X / s, a.Y / s);
        }

        /// <inheritdoc />
        public bool Equals(Double2 other)
        {
            return X.Equals(other.X) && Y.Equals(other.Y);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is Double2 other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                return (X.GetHashCode() * 397) ^ Y.GetHashCode();
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(CultureInfo.InvariantCulture, "({0:F4}, {1:F4})", X, Y);
        }
    }

    /// <summary>
    /// 纯 C# 双精度三维向量（替代 Unity.Mathematics.double3，用于 ECEF 坐标与 Unity 局部空间双精度表示）。
    /// </summary>
    public readonly struct Double3 : IEquatable<Double3>
    {
        /// <summary>零向量。</summary>
        public static readonly Double3 Zero = new Double3(0.0, 0.0, 0.0);

        /// <summary>X 分量。</summary>
        public double X { get; }

        /// <summary>Y 分量。</summary>
        public double Y { get; }

        /// <summary>Z 分量。</summary>
        public double Z { get; }

        /// <summary>构造三维双精度向量。</summary>
        public Double3(double x, double y, double z)
        {
            X = x;
            Y = y;
            Z = z;
        }

        /// <summary>向量模长。</summary>
        public double Length
        {
            get { return Math.Sqrt(X * X + Y * Y + Z * Z); }
        }

        public static Double3 operator +(Double3 a, Double3 b)
        {
            return new Double3(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
        }

        public static Double3 operator -(Double3 a, Double3 b)
        {
            return new Double3(a.X - b.X, a.Y - b.Y, a.Z - b.Z);
        }

        public static Double3 operator *(Double3 a, double s)
        {
            return new Double3(a.X * s, a.Y * s, a.Z * s);
        }

        /// <inheritdoc />
        public bool Equals(Double3 other)
        {
            return X.Equals(other.X) && Y.Equals(other.Y) && Z.Equals(other.Z);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is Double3 other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = X.GetHashCode();
                hash = (hash * 397) ^ Y.GetHashCode();
                hash = (hash * 397) ^ Z.GetHashCode();
                return hash;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(CultureInfo.InvariantCulture, "({0:F4}, {1:F4}, {2:F4})", X, Y, Z);
        }
    }

    /// <summary>
    /// WGS84 大地坐标（经度 LonDeg、纬度 LatDeg 单位为十进制度；椭球高 HeightM 单位为米）。
    /// </summary>
    public readonly struct GeoCoord : IEquatable<GeoCoord>
    {
        /// <summary>经度（十进制度，东经为正，[-180, 180]）。</summary>
        public double LonDeg { get; }

        /// <summary>纬度（十进制度，北纬为正，[-90, 90]）。</summary>
        public double LatDeg { get; }

        /// <summary>相对 WGS84 椭球面的大地高（米）。</summary>
        public double HeightM { get; }

        /// <summary>构造大地坐标。</summary>
        public GeoCoord(double lonDeg, double latDeg, double heightM = 0.0)
        {
            LonDeg = lonDeg;
            LatDeg = latDeg;
            HeightM = heightM;
        }

        /// <inheritdoc />
        public bool Equals(GeoCoord other)
        {
            return LonDeg.Equals(other.LonDeg) && LatDeg.Equals(other.LatDeg) && HeightM.Equals(other.HeightM);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is GeoCoord other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = LonDeg.GetHashCode();
                hash = (hash * 397) ^ LatDeg.GetHashCode();
                hash = (hash * 397) ^ HeightM.GetHashCode();
                return hash;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            return string.Format(CultureInfo.InvariantCulture, "({0:F6}°, {1:F6}°, {2:F2}m)", LonDeg, LatDeg, HeightM);
        }
    }
}
