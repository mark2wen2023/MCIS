using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Text;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>
    /// 同一情景在某一输入估计（如天线位置）下的结果，用于对比表的敏感性区间与“临界”判定（裁定 7c）。
    /// </summary>
    public sealed class SensitivityOutcome
    {
        /// <summary>敏感性设定标签（如“VEGA 0.35L”）。</summary>
        public string Label { get; }

        /// <summary>是否碰撞。</summary>
        public bool Collision { get; }

        /// <summary>结论枚举。</summary>
        public ScenarioVerdict Verdict { get; }

        /// <summary>最小净距（米）；碰撞为 0。</summary>
        public double MinClearanceM { get; }

        /// <summary>构造敏感性结果。</summary>
        public SensitivityOutcome(string label, bool collision, ScenarioVerdict verdict, double minClearanceM)
        {
            Label = label ?? string.Empty;
            Collision = collision;
            Verdict = verdict;
            MinClearanceM = collision ? 0.0 : minClearanceM;
        }

        /// <summary>由情景结果构造。</summary>
        public static SensitivityOutcome From(string label, ScenarioResult result)
        {
            if (result == null)
            {
                throw new ArgumentNullException(nameof(result));
            }
            return new SensitivityOutcome(label, result.Collision, result.Verdict, result.MinClearanceM);
        }

        /// <summary>摘要文字，如“0.35L 无碰撞 185.5 m”。</summary>
        public string ToSummary()
        {
            string verdict = ScenarioResult.VerdictToText(Verdict);
            return Collision
                ? Label + " " + verdict
                : Label + " " + verdict + " " + MinClearanceM.ToString("F1", CultureInfo.InvariantCulture) + " m";
        }
    }

    /// <summary>情景对比表的一行。</summary>
    public sealed class ComparisonRow
    {
        /// <summary>“临界”标签。</summary>
        public const string CriticalText = "临界";

        /// <summary>是否标“临界”（裁定 7c：离安全线不到临界裕度，或敏感性区间跨越安全线）。</summary>
        public bool IsCritical { get; private set; }

        /// <summary>“临界”原因（中文）；非临界为空串。</summary>
        public string CriticalReason { get; private set; }

        /// <summary>判定使用的安全线（米）。</summary>
        public double SafeDistanceM { get; private set; }

        /// <summary>敏感性结果（按输入顺序）；无敏感性数据为空列表。</summary>
        public IReadOnlyList<SensitivityOutcome> Sensitivity { get; private set; }

        /// <summary>敏感性区间文字（含名义值的净距范围与各设定结论）；无数据为“—”。</summary>
        public string SensitivityRangeText { get; private set; }

        /// <summary>表中显示的结论：临界时为“险情（临界）”等，否则同 VerdictText。</summary>
        public string DisplayVerdictText
        {
            get { return IsCritical ? VerdictText + "（" + CriticalText + "）" : VerdictText; }
        }
        /// <summary>情景标识。</summary>
        public string ScenarioId { get; }

        /// <summary>情景名称。</summary>
        public string Name { get; }

        /// <summary>改动摘要。</summary>
        public string ChangeSummary { get; }

        /// <summary>最小船中心距离（海里）。</summary>
        public double MinDistanceNm { get; }

        /// <summary>OBB 最小净距（米）。</summary>
        public double MinClearanceM { get; }

        /// <summary>最小预测 DCPA（海里）。</summary>
        public double MinDcpaNm { get; }

        /// <summary>偏离后最小预测 DCPA（海里）；原始情景为 null。</summary>
        public double? MinDcpaAfterDeviationNm { get; }

        /// <summary>是否碰撞。</summary>
        public bool Collision { get; }

        /// <summary>碰撞当地时刻文字；未碰撞为“—”。</summary>
        public string TcLocalText { get; }

        /// <summary>碰撞角（度）；未碰撞为 null。</summary>
        public double? CollisionAngleDeg { get; }

        /// <summary>碰撞角文字（如“70°”）；未碰撞为“—”。</summary>
        public string CollisionAngleText { get; }

        /// <summary>接触部位文字（如“右舷 距船首 120 m”）；未碰撞为“—”。</summary>
        public string ContactPartText { get; }

        /// <summary>结论文字。</summary>
        public string VerdictText { get; }

        /// <summary>相对 S0 的最小距离增量（海里）。</summary>
        public double DeltaMinDistanceNm { get; }

        /// <summary>构造对比表行。</summary>
        public ComparisonRow(
            string scenarioId,
            string name,
            string changeSummary,
            double minDistanceNm,
            double minClearanceM,
            double minDcpaNm,
            bool collision,
            string tcLocalText,
            string verdictText,
            double deltaMinDistanceNm,
            double? collisionAngleDeg = null,
            string contactPartText = null,
            double? minDcpaAfterDeviationNm = null)
        {
            MinDcpaAfterDeviationNm = minDcpaAfterDeviationNm;
            ScenarioId = scenarioId ?? string.Empty;
            Name = name ?? string.Empty;
            ChangeSummary = changeSummary ?? string.Empty;
            MinDistanceNm = minDistanceNm;
            MinClearanceM = minClearanceM;
            MinDcpaNm = minDcpaNm;
            Collision = collision;
            TcLocalText = string.IsNullOrEmpty(tcLocalText) ? "—" : tcLocalText;
            VerdictText = verdictText ?? string.Empty;
            DeltaMinDistanceNm = deltaMinDistanceNm;
            CollisionAngleDeg = collisionAngleDeg;
            CollisionAngleText = collisionAngleDeg.HasValue
                ? collisionAngleDeg.Value.ToString("F0", CultureInfo.InvariantCulture) + "°"
                : "—";
            ContactPartText = string.IsNullOrEmpty(contactPartText) ? "—" : contactPartText;
            IsCritical = false;
            CriticalReason = string.Empty;
            SafeDistanceM = double.NaN;
            Sensitivity = new ReadOnlyCollection<SensitivityOutcome>(new List<SensitivityOutcome>());
            SensitivityRangeText = "—";
        }

        /// <summary>写入临界判定与敏感性区间（由 ScenarioComparison.Build 调用）。</summary>
        internal void SetCriticality(
            double safeDistanceM,
            bool isCritical,
            string reason,
            IReadOnlyList<SensitivityOutcome> sensitivity,
            string rangeText)
        {
            SafeDistanceM = safeDistanceM;
            IsCritical = isCritical;
            CriticalReason = reason ?? string.Empty;
            Sensitivity = new ReadOnlyCollection<SensitivityOutcome>(
                sensitivity != null ? new List<SensitivityOutcome>(sensitivity) : new List<SensitivityOutcome>());
            SensitivityRangeText = string.IsNullOrEmpty(rangeText) ? "—" : rangeText;
        }
    }

    /// <summary>情景对比表，含 Markdown 导出。</summary>
    public sealed class ComparisonTable
    {
        private readonly ReadOnlyCollection<ComparisonRow> _rows;
        private readonly ReadOnlyCollection<string> _assumptions;
        private readonly ReadOnlyCollection<SourcedValue> _inputs;

        /// <summary>对比行（按输入顺序）。</summary>
        public IReadOnlyList<ComparisonRow> Rows
        {
            get { return _rows; }
        }

        /// <summary>各情景输入参数及来源（按情景顺序去重合并）。</summary>
        public IReadOnlyList<SourcedValue> Inputs
        {
            get { return _inputs; }
        }

        /// <summary>中文模型假设列表。</summary>
        public IReadOnlyList<string> Assumptions
        {
            get { return _assumptions; }
        }

        /// <summary>固定免责声明。</summary>
        public string Disclaimer { get; }

        /// <summary>“临界”裕度（米）：最小净距离安全线不到该值即标临界。</summary>
        public double CriticalMarginM { get; }

        /// <summary>构造情景对比表。</summary>
        public ComparisonTable(
            IReadOnlyList<ComparisonRow> rows,
            IReadOnlyList<string> assumptions,
            string disclaimer,
            IReadOnlyList<SourcedValue> inputs = null,
            double criticalMarginM = ScenarioComparison.DefaultCriticalMarginM)
        {
            CriticalMarginM = criticalMarginM;
            _rows = new ReadOnlyCollection<ComparisonRow>(
                rows != null ? new List<ComparisonRow>(rows) : new List<ComparisonRow>());
            _assumptions = new ReadOnlyCollection<string>(
                assumptions != null ? new List<string>(assumptions) : WhatIfAssumptions.CreateDefaultList());
            Disclaimer = string.IsNullOrEmpty(disclaimer) ? WhatIfAssumptions.DisclaimerText : disclaimer;
            _inputs = new ReadOnlyCollection<SourcedValue>(
                inputs != null ? new List<SourcedValue>(inputs) : new List<SourcedValue>());
        }

        /// <summary>导出 Markdown 对比表，末尾附模型假设与免责声明。</summary>
        public string ToMarkdown()
        {
            StringBuilder builder = new StringBuilder();
            builder.AppendLine("| 情景 | 改动 | 最小距离(nm) | 最小净距(m) | 最小DCPA(nm) | 碰撞时刻 | 结论 | 碰撞角 | 接触部位 | 偏离后最小DCPA(nm) | 敏感性区间 |");
            builder.AppendLine("|---|---|---|---|---|---|---|---|---|---|---|");

            for (int i = 0; i < _rows.Count; i++)
            {
                ComparisonRow row = _rows[i];
                builder.Append("| ");
                builder.Append(Escape(row.ScenarioId));
                builder.Append(" | ");
                builder.Append(Escape(row.ChangeSummary));
                builder.Append(" | ");
                builder.Append(row.MinDistanceNm.ToString("F3", CultureInfo.InvariantCulture));
                builder.Append(" | ");
                builder.Append(row.MinClearanceM.ToString("F1", CultureInfo.InvariantCulture));
                builder.Append(" | ");
                builder.Append(row.MinDcpaNm.ToString("F3", CultureInfo.InvariantCulture));
                builder.Append(" | ");
                builder.Append(Escape(row.TcLocalText));
                builder.Append(" | ");
                builder.Append(Escape(row.DisplayVerdictText));
                builder.Append(" | ");
                builder.Append(Escape(row.CollisionAngleText));
                builder.Append(" | ");
                builder.Append(Escape(row.ContactPartText));
                builder.Append(" | ");
                builder.Append(row.MinDcpaAfterDeviationNm.HasValue
                    ? row.MinDcpaAfterDeviationNm.Value.ToString("F3", CultureInfo.InvariantCulture)
                    : "—");
                builder.Append(" | ");
                builder.Append(Escape(row.SensitivityRangeText));
                builder.AppendLine(" |");
            }

            builder.AppendLine();
            double safeForNote = double.NaN;
            bool anyCritical = false;
            for (int i = 0; i < _rows.Count; i++)
            {
                if (double.IsNaN(safeForNote) && !double.IsNaN(_rows[i].SafeDistanceM))
                {
                    safeForNote = _rows[i].SafeDistanceM;
                }
                anyCritical = anyCritical || _rows[i].IsCritical;
            }
            builder.AppendLine(string.Format(
                CultureInfo.InvariantCulture,
                "注：最小净距(m) 为全程全局最小 OBB 真实净距（粗扫 + 局部极小细化）。「临界」= 最小净距离安全线 {0:F1} m 不到 {1:F1} m，或敏感性区间跨越安全线；临界结论对输入估计敏感，应按敏感性区间解读。",
                double.IsNaN(safeForNote) ? ScenarioComparison.FallbackSafeDistanceM : safeForNote,
                CriticalMarginM));
            if (anyCritical)
            {
                for (int i = 0; i < _rows.Count; i++)
                {
                    if (_rows[i].IsCritical)
                    {
                        builder.AppendLine("- " + _rows[i].ScenarioId + " 临界：" + _rows[i].CriticalReason);
                    }
                }
            }
            builder.AppendLine("注：最小DCPA(nm) 为全时段最小值，干预前各情景相同，不宜用于比较干预效果；请看「偏离后最小DCPA(nm)」（原始情景无偏离，记“—”）。");

            builder.AppendLine();
            builder.AppendLine("**模型假设：**");
            for (int i = 0; i < _assumptions.Count; i++)
            {
                builder.Append("- ");
                builder.AppendLine(_assumptions[i]);
            }
            builder.AppendLine();
            builder.Append("**免责声明：** ");
            builder.AppendLine(Disclaimer);
            return builder.ToString();
        }

        private static string Escape(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                return string.Empty;
            }
            return text.Replace("|", "\\|").Replace("\r", " ").Replace("\n", " ");
        }
    }

    /// <summary>由情景评价结果构建对比表。</summary>
    public static class ScenarioComparison
    {
        /// <summary>默认“临界”裕度（米，裁定 7c：离安全线不到 5 m）。</summary>
        public const double DefaultCriticalMarginM = 5.0;

        /// <summary>结果未携带安全线时的回退值（米，0.1 nm）。</summary>
        public const double FallbackSafeDistanceM = 185.2;

        /// <summary>构建对比表；缺少 S0 时抛出 ArgumentException。无敏感性数据，只按裕度判临界。</summary>
        public static ComparisonTable Build(IReadOnlyList<ScenarioResult> results)
        {
            return Build(results, null, DefaultCriticalMarginM);
        }

        /// <summary>
        /// 构建对比表并做“临界”判定（裁定 7c）：未碰撞且 |最小净距 − 安全线| &lt; criticalMarginM，
        /// 或名义值与敏感性结果的净距区间跨越安全线（最小 &lt; 安全线 ≤ 最大；碰撞按 0 m 计）时标“临界”，并给出敏感性区间。
        /// 安全线取各结果的 SafeDistanceM（来自 setup.SafeDistanceNm，可配置）。
        /// </summary>
        /// <param name="results">情景结果，必须含 S0。</param>
        /// <param name="sensitivity">按情景标识给出的敏感性结果；可为 null。</param>
        /// <param name="criticalMarginM">临界裕度（米），须为非负有限数。</param>
        public static ComparisonTable Build(
            IReadOnlyList<ScenarioResult> results,
            IReadOnlyDictionary<string, IReadOnlyList<SensitivityOutcome>> sensitivity,
            double criticalMarginM = DefaultCriticalMarginM)
        {
            if (double.IsNaN(criticalMarginM) || double.IsInfinity(criticalMarginM) || criticalMarginM < 0.0)
            {
                throw new ArgumentOutOfRangeException(nameof(criticalMarginM), "临界裕度必须为非负有限数。");
            }
            if (results == null)
            {
                throw new ArgumentNullException(nameof(results));
            }

            ScenarioResult baseline = null;
            for (int i = 0; i < results.Count; i++)
            {
                if (results[i] != null && string.Equals(results[i].ScenarioId, "S0", StringComparison.Ordinal))
                {
                    baseline = results[i];
                    break;
                }
            }
            if (baseline == null)
            {
                throw new ArgumentException("情景对比必须包含 S0 原始情景。", nameof(results));
            }

            List<ComparisonRow> rows = new List<ComparisonRow>(results.Count);
            for (int i = 0; i < results.Count; i++)
            {
                ScenarioResult result = results[i];
                if (result == null)
                {
                    throw new ArgumentException("情景结果列表中存在空项。", nameof(results));
                }
                string contactPart = "—";
                if (result.Geometry != null)
                {
                    contactPart = ContactPartText(result.Geometry);
                }
                ComparisonRow row = new ComparisonRow(
                    result.ScenarioId,
                    result.Name,
                    result.ChangeSummary,
                    result.MinDistanceNm,
                    result.MinClearanceM,
                    result.MinDcpaNm,
                    result.Collision,
                    result.TcLocalText,
                    result.VerdictText,
                    result.MinDistanceNm - baseline.MinDistanceNm,
                    result.Geometry != null ? (double?)result.Geometry.CollisionAngleDeg : null,
                    contactPart,
                    result.MinDcpaAfterDeviationNm);
                IReadOnlyList<SensitivityOutcome> outcomes = null;
                if (sensitivity != null)
                {
                    sensitivity.TryGetValue(result.ScenarioId, out outcomes);
                }
                ApplyCriticality(row, result, outcomes, criticalMarginM);
                rows.Add(row);
            }

            IReadOnlyList<SourcedValue> inputs = CollectInputs(results);
            List<string> assumptions = WhatIfAssumptions.CreateDefaultList();
            HashSet<string> seenAssumptions = new HashSet<string>(assumptions, StringComparer.Ordinal);
            for (int i = 0; i < results.Count; i++)
            {
                for (int j = 0; j < results[i].Assumptions.Count; j++)
                {
                    string a = results[i].Assumptions[j];
                    if (!string.IsNullOrWhiteSpace(a) && !a.StartsWith("本情景输入为虚构", StringComparison.Ordinal) &&
                        seenAssumptions.Add(a))
                    {
                        assumptions.Add(a);
                    }
                }
            }
            for (int i = 0; i < inputs.Count; i++)
            {
                if (inputs[i] != null && inputs[i].Source == ValueSource.Fictional)
                {
                    assumptions.Add("本对比表中的输入为虚构示例数据，仅用于方法演示，不代表任何真实事故。");
                    break;
                }
            }
            return new ComparisonTable(
                rows,
                new ReadOnlyCollection<string>(assumptions),
                WhatIfAssumptions.DisclaimerText,
                inputs,
                criticalMarginM);
        }

        /// <summary>对比表“接触部位”文字：单一撞击船为“右舷 距船首 96 m”；船首对船首为“船首对船首（船首距接触点 A 8.8 m / B 6.8 m）”。</summary>
        public static string ContactPartText(CollisionGeometry geometry)
        {
            if (geometry == null)
            {
                return "—";
            }
            if (geometry.IsBowToBow)
            {
                return string.Format(
                    CultureInfo.InvariantCulture,
                    "{0}（船首距接触点 {1} {2:F1} m / {3} {4:F1} m）",
                    CollisionGeometry.BowToBowText,
                    geometry.OwnVesselId,
                    geometry.OwnBowToContactM,
                    geometry.TargetVesselId,
                    geometry.TargetBowToContactM);
            }
            return geometry.StruckSide + " 距船首 " +
                geometry.ContactFromStruckBowM.ToString("F0", CultureInfo.InvariantCulture) + " m";
        }

        private static void ApplyCriticality(
            ComparisonRow row,
            ScenarioResult result,
            IReadOnlyList<SensitivityOutcome> outcomes,
            double marginM)
        {
            double safe = !double.IsNaN(result.SafeDistanceM) && !double.IsInfinity(result.SafeDistanceM)
                ? result.SafeDistanceM
                : FallbackSafeDistanceM;
            double nominal = result.Collision ? 0.0 : result.MinClearanceM;
            List<string> reasons = new List<string>();

            if (!result.Collision && Math.Abs(nominal - safe) < marginM)
            {
                reasons.Add(string.Format(
                    CultureInfo.InvariantCulture,
                    "最小净距 {0:F1} m 距安全线 {1:F1} m 仅 {2:F1} m（< {3:F1} m）",
                    nominal, safe, Math.Abs(nominal - safe), marginM));
            }

            string rangeText = "—";
            if (outcomes != null && outcomes.Count > 0)
            {
                double lo = nominal;
                double hi = nominal;
                List<string> parts = new List<string>(outcomes.Count);
                for (int i = 0; i < outcomes.Count; i++)
                {
                    SensitivityOutcome o = outcomes[i];
                    if (o == null)
                    {
                        continue;
                    }
                    double v = o.Collision ? 0.0 : o.MinClearanceM;
                    if (v < lo) lo = v;
                    if (v > hi) hi = v;
                    parts.Add(o.ToSummary());
                }
                rangeText = string.Format(
                    CultureInfo.InvariantCulture,
                    "净距 {0:F1}–{1:F1} m：{2}",
                    lo, hi, string.Join("；", parts));
                if (lo < safe && hi >= safe)
                {
                    reasons.Add(string.Format(
                        CultureInfo.InvariantCulture,
                        "敏感性区间 {0:F1}–{1:F1} m 跨越安全线 {2:F1} m（{3}）",
                        lo, hi, safe, string.Join("；", parts)));
                }
            }

            row.SetCriticality(safe, reasons.Count > 0, string.Join("；", reasons), outcomes, rangeText);
        }

        private static IReadOnlyList<SourcedValue> CollectInputs(IReadOnlyList<ScenarioResult> results)
        {
            List<SourcedValue> inputs = new List<SourcedValue>();
            HashSet<string> seen = new HashSet<string>(StringComparer.Ordinal);
            for (int i = 0; i < results.Count; i++)
            {
                ScenarioResult result = results[i];
                if (result == null)
                {
                    continue;
                }
                for (int j = 0; j < result.Inputs.Count; j++)
                {
                    SourcedValue value = result.Inputs[j];
                    if (value == null)
                    {
                        continue;
                    }
                    string key = value.Name + "|" + value.Source + "|" + value.Reference + "|" +
                                 value.Value.ToString("R", CultureInfo.InvariantCulture);
                    if (seen.Add(key))
                    {
                        inputs.Add(value);
                    }
                }
            }
            return new ReadOnlyCollection<SourcedValue>(inputs);
        }
    }
}
