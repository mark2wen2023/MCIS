using System;
using System.Globalization;

namespace Mcis.Simulation.WhatIf
{
    /// <summary>输入参数的来源分类。</summary>
    public enum ValueSource
    {
        /// <summary>报告直接给出的数值（附页码/行号）。</summary>
        ReportDirect = 0,
        /// <summary>由报告数据推算的数值（附推算方法）。</summary>
        ReportDerived = 1,
        /// <summary>报告缺失、按同类船或工程经验估计的数值（附估计依据）。</summary>
        Estimated = 2,
        /// <summary>虚构示例数据，仅用于方法演示。</summary>
        Fictional = 3
    }

    /// <summary>
    /// 带来源标注的数值输入。Name 为中文参数名，Value/Unit 为数值与单位，
    /// Reference 记录报告页码/行号或文件字段，Note 记录推算/估计方法与取舍。
    /// </summary>
    public sealed class SourcedValue
    {
        /// <summary>参数名称（中文）。</summary>
        public string Name { get; }

        /// <summary>参数数值。</summary>
        public double Value { get; }

        /// <summary>单位（可为空）。</summary>
        public string Unit { get; }

        /// <summary>来源分类。</summary>
        public ValueSource Source { get; }

        /// <summary>来源引用（页码/行号/字段/文件）。</summary>
        public string Reference { get; }

        /// <summary>补充说明（推算方法、估计依据、取舍规则）。</summary>
        public string Note { get; }

        /// <summary>构造带来源标注的数值。</summary>
        public SourcedValue(
            string name,
            double value,
            string unit,
            ValueSource source,
            string reference,
            string note = null)
        {
            if (string.IsNullOrWhiteSpace(name))
            {
                throw new ArgumentException("参数名称不能为空。", nameof(name));
            }
            if (double.IsNaN(value) || double.IsInfinity(value))
            {
                throw new ArgumentOutOfRangeException(nameof(value), "参数数值必须为有限数。");
            }
            if (string.IsNullOrWhiteSpace(reference))
            {
                throw new ArgumentException("来源引用不能为空。", nameof(reference));
            }
            Name = name;
            Value = value;
            Unit = unit ?? string.Empty;
            Source = source;
            Reference = reference;
            Note = note ?? string.Empty;
        }

        /// <summary>来源分类的中文名称。</summary>
        public string SourceText
        {
            get
            {
                switch (Source)
                {
                    case ValueSource.ReportDirect:
                        return "报告直接";
                    case ValueSource.ReportDerived:
                        return "推算";
                    case ValueSource.Estimated:
                        return "估计";
                    default:
                        return "虚构示例";
                }
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            string unit = string.IsNullOrEmpty(Unit) ? string.Empty : " " + Unit;
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0}={1:0.###}{2}（{3}；{4}）",
                Name, Value, unit, SourceText, Reference);
        }
    }
}
