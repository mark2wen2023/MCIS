using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using Mcis.Domain.Interview;

namespace Mcis.Domain.InterviewCompare
{
    /// <summary>与数据矛盾标记：仅来自登记簿中本笔录的“矛盾”结论；已驳回 → None。</summary>
    public enum ContradictionMark : byte
    {
        None = 0,
        Pending = 1,
        Confirmed = 2,
    }

    /// <summary>高亮片段（UTF-16 下标，与 SourceSpan 一致）。</summary>
    public sealed class HighlightSegment
    {
        public int Start { get; }
        public int Length { get; }
        public string Text { get; }
        public IReadOnlyList<StatementKind> Kinds { get; }
        public IReadOnlyList<string> StatementIds { get; }
        public ContradictionMark Contradiction { get; }
        public bool IsPlain { get { return StatementIds.Count == 0; } }

        internal HighlightSegment(int start, string text, List<StatementKind> kinds, List<string> ids, ContradictionMark mark)
        {
            Start = start;
            Length = text.Length;
            Text = text;
            Kinds = new ReadOnlyCollection<StatementKind>(kinds);
            StatementIds = new ReadOnlyCollection<string>(ids);
            Contradiction = mark;
        }
    }

    /// <summary>把一轮问/答切成覆盖全文的片段，供原型“时间/位置/操作陈述 · 与数据矛盾”高亮使用。已驳回的陈述不高亮。</summary>
    public static class TranscriptHighlighter
    {
        public static IReadOnlyList<HighlightSegment> Segments(InterviewRecord record, int round, QaField field, CrossCheckRegister register = null)
        {
            var result = new List<HighlightSegment>();
            QaTurn turn = record?.GetTurn(round);
            if (turn == null)
            {
                return new ReadOnlyCollection<HighlightSegment>(result);
            }

            string text = turn.TextOf(field);
            var stmts = new List<Statement>();
            var cuts = new SortedSet<int> { 0, text.Length };
            foreach (Statement s in record.Statements)
            {
                if (s.ReviewStatus == StatementReviewStatus.Rejected || s.Span.Round != round || s.Span.Field != field)
                {
                    continue;
                }

                stmts.Add(s);
                cuts.Add(s.Span.Start);
                cuts.Add(s.Span.Start + s.Span.Length);
            }

            int prev = -1;
            foreach (int c in cuts)
            {
                if (prev >= 0 && c > prev)
                {
                    var kinds = new List<StatementKind>();
                    var ids = new List<string>();
                    var mark = ContradictionMark.None;
                    foreach (Statement s in stmts)
                    {
                        if (s.Span.Start <= prev && s.Span.Start + s.Span.Length >= c)
                        {
                            ids.Add(s.StatementId);
                            if (!kinds.Contains(s.Kind))
                            {
                                kinds.Add(s.Kind);
                            }

                            ContradictionMark m = MarkOf(record, register, s.StatementId);
                            mark = m > mark ? m : mark;
                        }
                    }

                    result.Add(new HighlightSegment(prev, text.Substring(prev, c - prev), kinds, ids, mark));
                }

                prev = c;
            }

            return new ReadOnlyCollection<HighlightSegment>(result);
        }

        internal static ContradictionMark MarkOf(InterviewRecord record, CrossCheckRegister register, string statementId)
        {
            CrossCheckEntry e = register?.Get(statementId);
            // W5.1：过期结论（陈述已改版）不再标矛盾。
            if (e == null || e.Result.RecordId != record.RecordId || e.Result.Outcome != CrossCheckOutcome.Contradictory || e.IsStale(record))
            {
                return ContradictionMark.None;
            }

            return e.State == CrossCheckState.Confirmed ? ContradictionMark.Confirmed
                : e.State == CrossCheckState.PendingConfirmation ? ContradictionMark.Pending
                : ContradictionMark.None;
        }
    }
}
