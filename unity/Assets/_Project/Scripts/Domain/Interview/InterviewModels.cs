using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.Interview
{
    /// <summary>受询问人（演示数据均为虚构角色）。</summary>
    public sealed class Interviewee
    {
        public string IntervieweeId { get; }
        public string Name { get; }
        /// <summary>职务，如“船长”“二副（OOW）”“VTS 值班员”。</summary>
        public string Role { get; }
        /// <summary>所属船舶或单位，如“Mary 轮”“星屿 VTS”。</summary>
        public string Affiliation { get; }

        public Interviewee(string intervieweeId, string name, string role, string affiliation)
        {
            IntervieweeId = intervieweeId ?? string.Empty;
            Name = name ?? string.Empty;
            Role = role ?? string.Empty;
            Affiliation = affiliation ?? string.Empty;
        }
    }

    /// <summary>笔录中的一轮问答（原文逐字保存）。</summary>
    public sealed class QaTurn
    {
        /// <summary>轮次，从 1 开始连续编号（即“第几问”）。</summary>
        public int Round { get; }
        public string Question { get; }
        public string Answer { get; }
        /// <summary>该轮问答时间（可空）。</summary>
        public DateTimeOffset? Utc { get; }

        public QaTurn(int round, string question, string answer, DateTimeOffset? utc)
        {
            Round = round;
            Question = question ?? string.Empty;
            Answer = answer ?? string.Empty;
            Utc = utc;
        }

        public string TextOf(QaField field)
        {
            return field == QaField.Question ? Question : Answer;
        }
    }

    public enum QaField : byte
    {
        Question = 0,
        Answer = 1,
    }

    /// <summary>陈述项类别（ARCHITECTURE §15 ③：时间 / 位置 / 操作 / 观察）。</summary>
    public enum StatementKind : byte
    {
        Time = 0,
        Position = 1,
        Operation = 2,
        Observation = 3,
    }

    /// <summary>原文片段定位：第几问、问或答、字符起点与长度（UTF-16 下标）。</summary>
    public readonly struct SourceSpan : IEquatable<SourceSpan>
    {
        public int Round { get; }
        public QaField Field { get; }
        public int Start { get; }
        public int Length { get; }

        public SourceSpan(int round, QaField field, int start, int length)
        {
            Round = round;
            Field = field;
            Start = start;
            Length = length;
        }

        public bool Equals(SourceSpan other)
        {
            return Round == other.Round && Field == other.Field && Start == other.Start && Length == other.Length;
        }

        public override bool Equals(object obj)
        {
            return obj is SourceSpan o && Equals(o);
        }

        public override int GetHashCode()
        {
            unchecked
            {
                return (((Round * 397) ^ (int)Field) * 397 ^ Start) * 397 ^ Length;
            }
        }

        public override string ToString()
        {
            return "第" + Round + "问" + (Field == QaField.Answer ? "答" : "问") + "[" + Start + "+" + Length + "]";
        }
    }

    /// <summary>陈述可比对值的类型。</summary>
    public enum ClaimValueType : byte
    {
        /// <summary>某事件发生的时刻（如“14:23 开始左舵”的 14:23）。</summary>
        EventTime = 0,
        /// <summary>带单位的数值（如左舵 20°、距离 3 nm）。</summary>
        Scalar = 1,
        /// <summary>地理位置。</summary>
        Position = 2,
        /// <summary>某操作/现象是否发生（如“鸣放一长声”）。</summary>
        Occurrence = 3,
    }

    /// <summary>陈述的结构化取值。用静态工厂构造。</summary>
    public sealed class StatementClaim
    {
        public ClaimValueType ValueType { get; }
        public DateTimeOffset? Time { get; }
        public double? Scalar { get; }
        public string Unit { get; }
        public GeoCoord? Position { get; }
        public bool? Occurred { get; }

        private StatementClaim(ClaimValueType type, DateTimeOffset? time, double? scalar, string unit, GeoCoord? position, bool? occurred)
        {
            ValueType = type;
            Time = time;
            Scalar = scalar;
            Unit = unit ?? string.Empty;
            Position = position;
            Occurred = occurred;
        }

        public static StatementClaim EventTime(DateTimeOffset utc) { return new StatementClaim(ClaimValueType.EventTime, utc, null, null, null, null); }
        public static StatementClaim ScalarValue(double value, string unit) { return new StatementClaim(ClaimValueType.Scalar, null, value, unit, null, null); }
        public static StatementClaim At(GeoCoord position) { return new StatementClaim(ClaimValueType.Position, null, null, null, position, null); }
        public static StatementClaim Occurrence(bool occurred) { return new StatementClaim(ClaimValueType.Occurrence, null, null, null, null, occurred); }
    }

    /// <summary>陈述复核状态（contracts interview.statement.reviewStatus）。</summary>
    public enum StatementReviewStatus : byte
    {
        /// <summary>草稿（抽取后待调查员复核）。</summary>
        Draft = 0,
        Confirmed = 1,
        Rejected = 2,
        /// <summary>调查员修改过的草稿，仍待确认。</summary>
        Modified = 3,
    }

    /// <summary>陈述抽取来源（contracts interview.statement.extractedBy）。</summary>
    public enum StatementOrigin : byte
    {
        Agent = 0,
        Investigator = 1,
    }

    /// <summary>
    /// 陈述项：从笔录抽取的一条时间/位置/操作/观察陈述，必须带原文出处。
    /// Subject 是数据源可查询的主题键（如 "Mary.rudder_angle"），由数据源实现约定。
    /// </summary>
    public sealed class Statement
    {
        public string StatementId { get; }
        public string RecordId { get; }
        public StatementKind Kind { get; }
        public string Subject { get; }
        /// <summary>陈述摘要，如“14:23 开始左舵 20°”。</summary>
        public string Summary { get; }
        public StatementClaim Claim { get; }
        /// <summary>陈述所指时刻（Scalar/Position/Occurrence 用于在数据中定位；EventTime 可空）。</summary>
        public DateTimeOffset? ReferenceUtc { get; }
        public SourceSpan Span { get; }
        /// <summary>由 Span 从原文截取的片段。</summary>
        public string Quote { get; }
        public StatementReviewStatus ReviewStatus { get; }
        public StatementOrigin ExtractedBy { get; }
        /// <summary>修订号：新登记为 1，每次修改 +1。</summary>
        public int Revision { get; }
        public string ReviewedBy { get; }
        public DateTimeOffset? ReviewedUtc { get; }

        internal Statement(string statementId, string recordId, StatementKind kind, string subject, string summary, StatementClaim claim, DateTimeOffset? referenceUtc, SourceSpan span, string quote,
            StatementReviewStatus reviewStatus = StatementReviewStatus.Draft, StatementOrigin extractedBy = StatementOrigin.Agent, int revision = 1, string reviewedBy = null, DateTimeOffset? reviewedUtc = null)
        {
            ReviewStatus = reviewStatus;
            ExtractedBy = extractedBy;
            Revision = revision;
            ReviewedBy = reviewedBy ?? string.Empty;
            ReviewedUtc = reviewedUtc;
            StatementId = statementId;
            RecordId = recordId;
            Kind = kind;
            Subject = subject;
            Summary = summary ?? string.Empty;
            Claim = claim;
            ReferenceUtc = referenceUtc;
            Span = span;
            Quote = quote;
        }
    }

    /// <summary>询问笔录：问答原文按轮次追加，陈述项须能定位到原文。</summary>
    public sealed class InterviewRecord
    {
        public const string ErrInvalidArgument = "interview_invalid_argument";
        public const string ErrSpanOutOfRange = "interview_span_out_of_range";
        public const string ErrDuplicateStatement = "interview_duplicate_statement";
        public const string ErrStatementNotFound = "interview_statement_not_found";
        public const string ErrNotEditable = "interview_statement_not_editable";

        /// <summary>W3-D08：陈述取值含 NaN/±∞（数值或经纬度）。</summary>
        public const string ErrInvalidNumber = "inv_invalid_number";

        /// <summary>取值中的数值（标量、经纬度）都必须是有限数。</summary>
        public static bool HasFiniteNumbers(StatementClaim claim)
        {
            if (claim == null)
            {
                return true;
            }

            if (claim.Scalar.HasValue && !IsFinite(claim.Scalar.Value))
            {
                return false;
            }

            return !claim.Position.HasValue || (IsFinite(claim.Position.Value.LatDeg) && IsFinite(claim.Position.Value.LonDeg));
        }

        private static bool IsFinite(double v)
        {
            return !double.IsNaN(v) && !double.IsInfinity(v);
        }

        public const string ActionStatementModify = "interview.statement.modify";
        public const string ActionStatementReview = "interview.statement.review";

        /// <summary>contracts interview.recordId：IR- 加至少 2 位数字。</summary>
        public static readonly Regex RecordIdPattern = new Regex(@"\AIR-[0-9]{2,}\z", RegexOptions.CultureInvariant); // W3-D09

        private readonly List<QaTurn> _turns = new List<QaTurn>();
        private readonly List<Statement> _statements = new List<Statement>();
        private readonly List<string> _interviewers;

        /// <summary>笔录编号，如 IR-03。</summary>
        public string RecordId { get; }
        public Interviewee Interviewee { get; }
        public DateTimeOffset StartUtc { get; }
        public string Location { get; }
        public string Recorder { get; }
        public IReadOnlyList<string> Interviewers { get { return _interviewers; } }
        /// <summary>笔录原件（录音/PDF）哈希，可关联保管链证据；可空。</summary>
        public string SourceSha256 { get; }
        /// <summary>所属案件号；空串表示未填（填写时校验格式）。</summary>
        public string CaseId { get; }
        /// <summary>受询问人是否已签字确认笔录（只能由未签改为已签）。</summary>
        public bool Signed { get; private set; }

        public IReadOnlyList<QaTurn> Turns { get { return _turns; } }
        public IReadOnlyList<Statement> Statements { get { return _statements; } }

        public InterviewRecord(
            string recordId,
            Interviewee interviewee,
            DateTimeOffset startUtc,
            IEnumerable<string> interviewers = null,
            string recorder = null,
            string location = null,
            string sourceSha256 = null,
            string caseId = null,
            bool signed = false)
        {
            if (recordId == null || !RecordIdPattern.IsMatch(recordId))
            {
                throw new ArgumentException("recordId 须为 IR- 加至少 2 位数字：" + (recordId ?? "(null)"), nameof(recordId));
            }

            if (!string.IsNullOrEmpty(caseId) && !EvidenceItem.IsValidCaseId(caseId))
            {
                throw new ArgumentException("caseId 格式不符：" + caseId, nameof(caseId));
            }

            CaseId = caseId ?? string.Empty;
            Signed = signed;

            RecordId = recordId;
            Interviewee = interviewee ?? throw new ArgumentNullException(nameof(interviewee));
            StartUtc = startUtc;
            _interviewers = interviewers == null ? new List<string>() : new List<string>(interviewers);
            Recorder = recorder ?? string.Empty;
            Location = location ?? string.Empty;
            SourceSha256 = sourceSha256 ?? string.Empty;
        }

        /// <summary>登记受询问人已签字（不可撤销）。</summary>
        public void MarkSigned()
        {
            Signed = true;
        }

        public Statement GetStatement(string statementId)
        {
            int i = IndexOfStatement(statementId);
            return i < 0 ? null : _statements[i];
        }

        private int IndexOfStatement(string statementId)
        {
            for (int i = 0; i < _statements.Count; i++)
            {
                if (string.Equals(_statements[i].StatementId, statementId, StringComparison.Ordinal))
                {
                    return i;
                }
            }

            return -1;
        }

        /// <summary>
        /// 修改陈述草稿（原型“修改”按钮）：仅 Draft / Modified 可改；新版本状态为 Modified、修订号 +1，仍需确认。
        /// 原文出处必须仍然有效。写审计。
        /// </summary>
        public Result<Statement> ModifyStatement(
            string statementId,
            string summary,
            StatementClaim claim,
            SourceSpan span,
            DateTimeOffset? referenceUtc,
            string investigator,
            DateTimeOffset utc,
            IInvestigationAuditSink audit)
        {
            if (audit == null)
            {
                throw new ArgumentNullException(nameof(audit));
            }

            int idx = IndexOfStatement(statementId);
            if (idx < 0)
            {
                return Result<Statement>.Fail(ErrStatementNotFound, "陈述不存在：" + (statementId ?? "(null)"));
            }

            if (string.IsNullOrWhiteSpace(investigator) || claim == null)
            {
                return Result<Statement>.Fail(ErrInvalidArgument, "调查员与取值不能为空");
            }

            if (!HasFiniteNumbers(claim))
            {
                return Result<Statement>.Fail(ErrInvalidNumber, "陈述取值不能为 NaN/±∞：" + statementId);
            }

            Statement old = _statements[idx];
            if (old.ReviewStatus != StatementReviewStatus.Draft && old.ReviewStatus != StatementReviewStatus.Modified)
            {
                return Result<Statement>.Fail(ErrNotEditable, "仅草稿/已修改的陈述可修改，当前：" + old.ReviewStatus);
            }

            Result<string> quote = ResolveSpan(span);
            if (!quote.IsSuccess)
            {
                return Result<Statement>.Fail(quote.ErrorCode, quote.ErrorMessage);
            }

            var updated = new Statement(old.StatementId, RecordId, old.Kind, old.Subject, summary, claim, referenceUtc, span, quote.Value,
                StatementReviewStatus.Modified, old.ExtractedBy, old.Revision + 1, investigator, utc);
            audit.Append(new InvestigationAuditEntry(utc, investigator, ActionStatementModify, InvestigationAuditCategories.Interview,
                "修改陈述 " + old.StatementId + "（" + RecordId + "）",
                "r" + old.Revision + "；" + old.Summary + "；出处=" + old.Span,
                "r" + updated.Revision + "；" + updated.Summary + "；出处=" + updated.Span));
            _statements[idx] = updated;
            return Result<Statement>.Ok(updated);
        }

        /// <summary>调查员复核陈述：确认或驳回（驳回须写理由）。仅 Draft / Modified 可复核。写审计。</summary>
        public Result<Statement> ReviewStatement(
            string statementId,
            StatementReviewStatus decision,
            string investigator,
            DateTimeOffset utc,
            IInvestigationAuditSink audit,
            string note = null)
        {
            if (audit == null)
            {
                throw new ArgumentNullException(nameof(audit));
            }

            if (decision != StatementReviewStatus.Confirmed && decision != StatementReviewStatus.Rejected)
            {
                return Result<Statement>.Fail(ErrInvalidArgument, "复核结论只能是 Confirmed 或 Rejected");
            }

            if (string.IsNullOrWhiteSpace(investigator))
            {
                return Result<Statement>.Fail(ErrInvalidArgument, "调查员不能为空");
            }

            if (decision == StatementReviewStatus.Rejected && string.IsNullOrWhiteSpace(note))
            {
                return Result<Statement>.Fail(ErrInvalidArgument, "驳回必须写明理由");
            }

            int idx = IndexOfStatement(statementId);
            if (idx < 0)
            {
                return Result<Statement>.Fail(ErrStatementNotFound, "陈述不存在：" + (statementId ?? "(null)"));
            }

            Statement old = _statements[idx];
            if (old.ReviewStatus != StatementReviewStatus.Draft && old.ReviewStatus != StatementReviewStatus.Modified)
            {
                return Result<Statement>.Fail(ErrNotEditable, "该陈述已复核：" + old.ReviewStatus);
            }

            var updated = new Statement(old.StatementId, RecordId, old.Kind, old.Subject, old.Summary, old.Claim, old.ReferenceUtc, old.Span, old.Quote,
                decision, old.ExtractedBy, old.Revision, investigator, utc);
            audit.Append(new InvestigationAuditEntry(utc, investigator, ActionStatementReview, InvestigationAuditCategories.Interview,
                "复核陈述 " + old.StatementId + "（" + RecordId + "）", old.ReviewStatus + "；r" + old.Revision,
                decision + (string.IsNullOrEmpty(note) ? string.Empty : "；" + note)));
            _statements[idx] = updated;
            return Result<Statement>.Ok(updated);
        }

        /// <summary>笔录时长（首末轮时间差，分钟）；轮次无时间时为 null。</summary>
        public double? DurationMinutes
        {
            get
            {
                DateTimeOffset? last = null;
                for (int i = _turns.Count - 1; i >= 0 && !last.HasValue; i--)
                {
                    last = _turns[i].Utc;
                }

                return last.HasValue ? (last.Value - StartUtc).TotalMinutes : (double?)null;
            }
        }

        /// <summary>追加一轮问答，轮次自动编号。问答时间若早于上一轮则拒绝。</summary>
        public Result<QaTurn> AddTurn(string question, string answer, DateTimeOffset? utc = null)
        {
            if (string.IsNullOrEmpty(question) && string.IsNullOrEmpty(answer))
            {
                return Result<QaTurn>.Fail(ErrInvalidArgument, "问与答不能同时为空");
            }

            if (utc.HasValue)
            {
                if (utc.Value < StartUtc)
                {
                    return Result<QaTurn>.Fail(ErrInvalidArgument, "问答时间早于笔录开始时间");
                }

                for (int i = _turns.Count - 1; i >= 0; i--)
                {
                    if (_turns[i].Utc.HasValue)
                    {
                        if (utc.Value < _turns[i].Utc.Value)
                        {
                            return Result<QaTurn>.Fail(ErrInvalidArgument, "问答时间早于上一轮");
                        }

                        break;
                    }
                }
            }

            var turn = new QaTurn(_turns.Count + 1, question, answer, utc);
            _turns.Add(turn);
            return Result<QaTurn>.Ok(turn);
        }

        public QaTurn GetTurn(int round)
        {
            return round >= 1 && round <= _turns.Count ? _turns[round - 1] : null;
        }

        /// <summary>按片段定位取原文；越界返回失败。</summary>
        public Result<string> ResolveSpan(SourceSpan span)
        {
            QaTurn turn = GetTurn(span.Round);
            if (turn == null)
            {
                return Result<string>.Fail(ErrSpanOutOfRange, "轮次不存在：" + span.Round);
            }

            string text = turn.TextOf(span.Field);
            if (span.Length <= 0 || span.Start < 0 || span.Start > text.Length - span.Length)
            {
                return Result<string>.Fail(ErrSpanOutOfRange, "片段越界：" + span);
            }

            return Result<string>.Ok(text.Substring(span.Start, span.Length));
        }

        /// <summary>按原文片段首次出现的位置构造定位（便于录入）；找不到返回失败。</summary>
        public Result<SourceSpan> Locate(int round, QaField field, string fragment)
        {
            QaTurn turn = GetTurn(round);
            if (turn == null || string.IsNullOrEmpty(fragment))
            {
                return Result<SourceSpan>.Fail(ErrSpanOutOfRange, "轮次不存在或片段为空");
            }

            int idx = turn.TextOf(field).IndexOf(fragment, StringComparison.Ordinal);
            if (idx < 0)
            {
                return Result<SourceSpan>.Fail(ErrSpanOutOfRange, "原文中找不到片段");
            }

            return Result<SourceSpan>.Ok(new SourceSpan(round, field, idx, fragment.Length));
        }

        /// <summary>登记陈述项。没有有效原文出处的陈述直接拒绝（§15.7：无出处输出丢弃）。</summary>
        public Result<Statement> AddStatement(
            string statementId,
            StatementKind kind,
            string subject,
            string summary,
            StatementClaim claim,
            SourceSpan span,
            DateTimeOffset? referenceUtc = null,
            StatementOrigin extractedBy = StatementOrigin.Agent)
        {
            if (string.IsNullOrWhiteSpace(statementId) || string.IsNullOrWhiteSpace(subject) || claim == null)
            {
                return Result<Statement>.Fail(ErrInvalidArgument, "陈述编号、主题、取值不能为空");
            }

            if (!HasFiniteNumbers(claim))
            {
                return Result<Statement>.Fail(ErrInvalidNumber, "陈述取值不能为 NaN/±∞：" + statementId);
            }

            for (int i = 0; i < _statements.Count; i++)
            {
                if (string.Equals(_statements[i].StatementId, statementId, StringComparison.Ordinal))
                {
                    return Result<Statement>.Fail(ErrDuplicateStatement, "陈述编号重复：" + statementId);
                }
            }

            Result<string> quote = ResolveSpan(span);
            if (!quote.IsSuccess)
            {
                return Result<Statement>.Fail(quote.ErrorCode, quote.ErrorMessage);
            }

            // 无论智能体还是调查员录入，一律先为草稿，经复核后才确认（§15.5）。
            var st = new Statement(statementId, RecordId, kind, subject, summary, claim, referenceUtc, span, quote.Value,
                StatementReviewStatus.Draft, extractedBy);
            _statements.Add(st);
            return Result<Statement>.Ok(st);
        }
    }
}
