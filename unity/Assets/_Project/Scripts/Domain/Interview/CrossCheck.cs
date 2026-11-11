using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Domain.Common;

namespace Mcis.Domain.Interview
{
    /// <summary>向数据源发出的查询：主题键 + 值类型 + 参考时刻。</summary>
    public sealed class StatementQuery
    {
        public string Subject { get; }
        public ClaimValueType ValueType { get; }
        public DateTimeOffset? ReferenceUtc { get; }

        public StatementQuery(string subject, ClaimValueType valueType, DateTimeOffset? referenceUtc)
        {
            Subject = subject ?? string.Empty;
            ValueType = valueType;
            ReferenceUtc = referenceUtc;
        }
    }

    /// <summary>数据源返回的客观观测值（VDR/AIS/ECDIS 等）。</summary>
    public sealed class DataObservation
    {
        public bool Found { get; }
        public string SourceLabel { get; }
        public DateTimeOffset? Time { get; }
        public double? Scalar { get; }
        public string Unit { get; }
        public GeoCoord? Position { get; }
        public bool? Occurred { get; }

        private DataObservation(bool found, string label, DateTimeOffset? time, double? scalar, string unit, GeoCoord? pos, bool? occurred)
        {
            Found = found;
            SourceLabel = label ?? string.Empty;
            Time = time;
            Scalar = scalar;
            Unit = unit ?? string.Empty;
            Position = pos;
            Occurred = occurred;
        }

        public static DataObservation NotFound(string sourceLabel = null) { return new DataObservation(false, sourceLabel, null, null, null, null, null); }
        public static DataObservation EventAt(DateTimeOffset utc, string sourceLabel) { return new DataObservation(true, sourceLabel, utc, null, null, null, null); }
        public static DataObservation ScalarValue(double value, string unit, string sourceLabel, DateTimeOffset? utc = null) { return new DataObservation(true, sourceLabel, utc, value, unit, null, null); }
        public static DataObservation At(GeoCoord position, string sourceLabel, DateTimeOffset? utc = null) { return new DataObservation(true, sourceLabel, utc, null, null, position, null); }
        public static DataObservation Occurrence(bool occurred, string sourceLabel, DateTimeOffset? utc = null) { return new DataObservation(true, sourceLabel, utc, null, null, null, occurred); }
    }

    /// <summary>可查询的数据源接口（由 VDR/AIS 时间轴等实现）。无数据时返回 NotFound，不应抛异常。</summary>
    public interface IStatementDataSource
    {
        DataObservation Query(StatementQuery query);
    }

    public enum CrossCheckOutcome : byte
    {
        /// <summary>一致。</summary>
        Consistent = 0,
        /// <summary>矛盾。</summary>
        Contradictory = 1,
        /// <summary>无法核实。</summary>
        Unverifiable = 2,
    }

    /// <summary>比对容差（可配置；数值写入结果的 Rule 字段便于复核）。</summary>
    public sealed class CrossCheckTolerance
    {
        private readonly Dictionary<string, double> _scalarBySubject = new Dictionary<string, double>(StringComparer.Ordinal);

        /// <summary>事件时刻容差（秒），默认 30 s。</summary>
        public double TimeSeconds { get; set; } = 30.0;
        /// <summary>位置容差（米），默认 185.2 m（0.1 nm）。</summary>
        public double PositionMeters { get; set; } = 185.2;
        /// <summary>未单独配置主题时的数值绝对容差，默认 0（必须相等）。容差单位 = 陈述单位。</summary>
        public double DefaultScalarAbs { get; set; } = 0.0;

        public CrossCheckTolerance SetScalar(string subject, double absTolerance)
        {
            if (absTolerance < 0 || double.IsNaN(absTolerance) || double.IsInfinity(absTolerance))
            {
                throw new ArgumentOutOfRangeException(nameof(absTolerance));
            }

            _scalarBySubject[subject ?? string.Empty] = absTolerance;
            return this;
        }

        public double ScalarFor(string subject)
        {
            return subject != null && _scalarBySubject.TryGetValue(subject, out double t) ? t : DefaultScalarAbs;
        }
    }

    /// <summary>单条陈述的比对结果（不可变）。Delta = 陈述值 − 数据值（位置为距离，Occurrence 无差值）。</summary>
    public sealed class CrossCheckResult
    {
        public string StatementId { get; }
        public string RecordId { get; }
        public CrossCheckOutcome Outcome { get; }
        public double? Delta { get; }
        /// <summary>差值单位：s / m / 陈述单位。</summary>
        public string DeltaUnit { get; }
        public string ClaimedText { get; }
        public string ObservedText { get; }
        public string SourceLabel { get; }
        /// <summary>判定规则与容差文字说明。</summary>
        public string Rule { get; }

        /// <summary>
        /// W5.1（DEFECTS/W5.md 21:32 D01）：比对时陈述的版本（= <see cref="Statement.Revision"/>，≥1，缺省 1）。
        /// 陈述经 ModifyStatement 改版后与之不等，见 <see cref="CrossCheckEntry.IsStale"/>。合同键 statementVersion。
        /// </summary>
        public int StatementVersion { get; }

        public CrossCheckResult(string statementId, string recordId, CrossCheckOutcome outcome, double? delta, string deltaUnit, string claimedText, string observedText, string sourceLabel, string rule, int statementVersion = 1)
        {
            if (statementVersion < 1)
            {
                throw new ArgumentOutOfRangeException(nameof(statementVersion), "陈述版本从 1 起");
            }

            StatementVersion = statementVersion;
            StatementId = statementId ?? string.Empty;
            RecordId = recordId ?? string.Empty;
            Outcome = outcome;
            Delta = delta;
            DeltaUnit = deltaUnit ?? string.Empty;
            ClaimedText = claimedText ?? string.Empty;
            ObservedText = observedText ?? string.Empty;
            SourceLabel = sourceLabel ?? string.Empty;
            Rule = rule ?? string.Empty;
        }
    }

    /// <summary>陈述↔数据确定性比对器（不调用 LLM）。</summary>
    public sealed class StatementCrossChecker
    {
        private const double EarthRadiusM = 6371008.8;

        public CrossCheckTolerance Tolerance { get; }

        public StatementCrossChecker(CrossCheckTolerance tolerance = null)
        {
            Tolerance = tolerance ?? new CrossCheckTolerance();
        }

        public IReadOnlyList<CrossCheckResult> CheckAll(InterviewRecord record, IStatementDataSource source)
        {
            if (record == null)
            {
                throw new ArgumentNullException(nameof(record));
            }

            var list = new List<CrossCheckResult>(record.Statements.Count);
            for (int i = 0; i < record.Statements.Count; i++)
            {
                list.Add(Check(record.Statements[i], source));
            }

            return list;
        }

        private static bool IsFinite(double v)
        {
            return !double.IsNaN(v) && !double.IsInfinity(v);
        }

        public CrossCheckResult Check(Statement statement, IStatementDataSource source)
        {
            if (statement == null)
            {
                throw new ArgumentNullException(nameof(statement));
            }

            if (source == null)
            {
                throw new ArgumentNullException(nameof(source));
            }

            StatementClaim c = statement.Claim;
            DataObservation obs = source.Query(new StatementQuery(statement.Subject, c.ValueType, statement.ReferenceUtc))
                                  ?? DataObservation.NotFound();
            string claimed = Describe(c);
            if (!obs.Found)
            {
                return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, "无数据", obs.SourceLabel, "数据源无对应记录");
            }

            switch (c.ValueType)
            {
                case ClaimValueType.EventTime:
                {
                    if (!c.Time.HasValue || !obs.Time.HasValue)
                    {
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "缺少可比较的时刻");
                    }

                    double d = (c.Time.Value - obs.Time.Value).TotalSeconds;
                    string rule = "|Δt| ≤ " + Fmt(Tolerance.TimeSeconds) + " s";
                    return Make(statement, Math.Abs(d) <= Tolerance.TimeSeconds ? CrossCheckOutcome.Consistent : CrossCheckOutcome.Contradictory, d, "s", claimed, DescribeObs(obs), obs.SourceLabel, rule);
                }

                case ClaimValueType.Scalar:
                {
                    if (!c.Scalar.HasValue || !obs.Scalar.HasValue)
                    {
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "缺少可比较的数值");
                    }

                    if (!IsFinite(c.Scalar.Value) || !IsFinite(obs.Scalar.Value))
                    {
                        // W3-D08：NaN/±∞ 不得判一致或矛盾。
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "无效数值（NaN/±∞），无法比较");
                    }

                    double observed = obs.Scalar.Value;
                    string observedText = DescribeObs(obs);
                    string conversion = string.Empty;
                    bool sameUnit = string.Equals(c.Unit.Trim(), obs.Unit.Trim(), StringComparison.OrdinalIgnoreCase);
                    if (!sameUnit)
                    {
                        if (!UnitConversion.TryConvert(obs.Scalar.Value, obs.Unit, c.Unit, out observed))
                        {
                            string why = !UnitConversion.IsKnown(c.Unit) || !UnitConversion.IsKnown(obs.Unit) ? "未知单位" : "量纲不同";
                            return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, observedText, obs.SourceLabel, why + "（" + c.Unit + " vs " + obs.Unit + "），无法换算");
                        }

                        conversion = "；数据 " + Fmt(obs.Scalar.Value) + " " + obs.Unit + " 换算为 " + Fmt(observed) + " " + c.Unit;
                        observedText = observedText + "（≈ " + Fmt(observed) + " " + c.Unit + "）";
                    }

                    // 容差单位与陈述单位相同。
                    double tol = Tolerance.ScalarFor(statement.Subject);
                    double d = c.Scalar.Value - observed;
                    string rule = "|Δ| ≤ " + Fmt(tol) + " " + c.Unit + conversion;
                    return Make(statement, Math.Abs(d) <= tol + 1e-9 ? CrossCheckOutcome.Consistent : CrossCheckOutcome.Contradictory, d, c.Unit, claimed, observedText, obs.SourceLabel, rule);
                }

                case ClaimValueType.Position:
                {
                    if (!c.Position.HasValue || !obs.Position.HasValue)
                    {
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "缺少可比较的位置");
                    }

                    if (!IsFinite(c.Position.Value.LatDeg) || !IsFinite(c.Position.Value.LonDeg) || !IsFinite(obs.Position.Value.LatDeg) || !IsFinite(obs.Position.Value.LonDeg))
                    {
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "无效数值（NaN/±∞），无法比较");
                    }

                    double d = HaversineMeters(c.Position.Value, obs.Position.Value);
                    string rule = "距离 ≤ " + Fmt(Tolerance.PositionMeters) + " m";
                    return Make(statement, d <= Tolerance.PositionMeters ? CrossCheckOutcome.Consistent : CrossCheckOutcome.Contradictory, d, "m", claimed, DescribeObs(obs), obs.SourceLabel, rule);
                }

                default:
                {
                    if (!c.Occurred.HasValue || !obs.Occurred.HasValue)
                    {
                        return Make(statement, CrossCheckOutcome.Unverifiable, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "缺少可比较的发生状态");
                    }

                    bool same = c.Occurred.Value == obs.Occurred.Value;
                    return Make(statement, same ? CrossCheckOutcome.Consistent : CrossCheckOutcome.Contradictory, null, string.Empty, claimed, DescribeObs(obs), obs.SourceLabel, "发生与否须一致");
                }
            }
        }

        /// <summary>球面大圆距离（米）。</summary>
        public static double HaversineMeters(GeoCoord a, GeoCoord b)
        {
            double rad = Math.PI / 180.0;
            double dLat = (b.LatDeg - a.LatDeg) * rad;
            double dLon = (b.LonDeg - a.LonDeg) * rad;
            double h = Math.Sin(dLat / 2) * Math.Sin(dLat / 2) +
                       Math.Cos(a.LatDeg * rad) * Math.Cos(b.LatDeg * rad) * Math.Sin(dLon / 2) * Math.Sin(dLon / 2);
            return 2 * EarthRadiusM * Math.Asin(Math.Min(1.0, Math.Sqrt(h)));
        }

        private static CrossCheckResult Make(Statement s, CrossCheckOutcome o, double? delta, string unit, string claimed, string observed, string label, string rule)
        {
            return new CrossCheckResult(s.StatementId, s.RecordId, o, delta, unit, claimed, observed, label, rule, s.Revision);
        }

        private static string Fmt(double v)
        {
            return v.ToString("0.###", CultureInfo.InvariantCulture);
        }

        private static string Describe(StatementClaim c)
        {
            switch (c.ValueType)
            {
                case ClaimValueType.EventTime: return c.Time.HasValue ? c.Time.Value.ToUniversalTime().ToString("HH:mm:ss'Z'", CultureInfo.InvariantCulture) : "?";
                case ClaimValueType.Scalar: return c.Scalar.HasValue ? Fmt(c.Scalar.Value) + " " + c.Unit : "?";
                case ClaimValueType.Position: return c.Position.HasValue ? c.Position.Value.ToString() : "?";
                default: return c.Occurred.HasValue ? (c.Occurred.Value ? "发生" : "未发生") : "?";
            }
        }

        private static string DescribeObs(DataObservation o)
        {
            if (o.Scalar.HasValue)
            {
                return Fmt(o.Scalar.Value) + " " + o.Unit;
            }

            if (o.Position.HasValue)
            {
                return o.Position.Value.ToString();
            }

            if (o.Occurred.HasValue)
            {
                return o.Occurred.Value ? "发生" : "未发生";
            }

            return o.Time.HasValue ? o.Time.Value.ToUniversalTime().ToString("HH:mm:ss'Z'", CultureInfo.InvariantCulture) : "?";
        }
    }
}
