using System;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Evidence;

namespace Mcis.Domain.Recommendations
{
    /// <summary>征求意见对象（实质利益国 / 利益方）。</summary>
    public sealed class ConsultationParty
    {
        public string PartyId { get; }
        public string Name { get; }

        public ConsultationParty(string partyId, string name)
        {
            PartyId = partyId ?? string.Empty;
            Name = name ?? string.Empty;
        }
    }

    public enum ReplyStatus : byte
    {
        /// <summary>未回复，未过期限。</summary>
        Pending = 0,
        /// <summary>期限内已回复。</summary>
        Replied = 1,
        /// <summary>过期限后回复。</summary>
        RepliedLate = 2,
        /// <summary>过期限仍未回复。</summary>
        Overdue = 3,
        /// <summary>该方放弃 / 免于回复（contracts responses.status = Waived）。</summary>
        Waived = 4,
    }

    public enum AdoptionDecision : byte
    {
        Pending = 0,
        Adopted = 1,
        PartiallyAdopted = 2,
        NotAdopted = 3,
    }

    /// <summary>一条意见及其采纳记录。</summary>
    public sealed class ConsultationComment
    {
        public string CommentId { get; }
        public int Round { get; }
        public string PartyId { get; }
        public string Text { get; }
        public AdoptionDecision Decision { get; internal set; }
        /// <summary>对采纳情况的书面反馈（MSC.255 第 25 章）。</summary>
        public string Feedback { get; internal set; }
        public string DecidedBy { get; internal set; }
        public DateTimeOffset? DecidedUtc { get; internal set; }

        internal ConsultationComment(string commentId, int round, string partyId, string text)
        {
            CommentId = commentId;
            Round = round;
            PartyId = partyId;
            Text = text ?? string.Empty;
            Decision = AdoptionDecision.Pending;
            Feedback = string.Empty;
            DecidedBy = string.Empty;
        }
    }

    /// <summary>某方在某轮的回复。</summary>
    public sealed class ConsultationReply
    {
        public string PartyId { get; }
        public DateTimeOffset Utc { get; }
        public string Text { get; }
        public IReadOnlyList<ConsultationComment> Comments { get; }

        internal ConsultationReply(string partyId, DateTimeOffset utc, string text, IReadOnlyList<ConsultationComment> comments)
        {
            PartyId = partyId;
            Utc = utc;
            Text = text ?? string.Empty;
            Comments = comments;
        }
    }

    /// <summary>某轮某方的采纳统计。</summary>
    public readonly struct AdoptionTally
    {
        public int Adopted { get; }
        public int PartiallyAdopted { get; }
        public int NotAdopted { get; }
        public int Pending { get; }
        public int Total { get { return Adopted + PartiallyAdopted + NotAdopted + Pending; } }

        public AdoptionTally(int adopted, int partially, int notAdopted, int pending)
        {
            Adopted = adopted;
            PartiallyAdopted = partially;
            NotAdopted = notAdopted;
            Pending = pending;
        }
    }

    /// <summary>一轮征求意见：草案版本、各方、期限（默认发出后 30 天或双方商定）、回复与采纳。</summary>
    public sealed class ConsultationRound
    {
        internal readonly Dictionary<string, ConsultationReply> RepliesByParty = new Dictionary<string, ConsultationReply>(StringComparer.Ordinal);
        internal readonly List<ConsultationComment> CommentList = new List<ConsultationComment>();
        internal readonly Dictionary<string, string> WaivedByParty = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly List<ConsultationParty> _parties;

        public int RoundNo { get; }
        public string DraftVersion { get; }
        public DateTimeOffset OpenedUtc { get; }
        public DateTimeOffset DeadlineUtc { get; }
        public bool IsAgreedDeadline { get; }
        /// <summary>本轮草案文件 SHA-256（小写十六进制，可关联保管链）；空串表示未填。</summary>
        public string DraftSha256 { get; }
        public bool IsClosed { get; internal set; }
        public DateTimeOffset? ClosedUtc { get; internal set; }
        public IReadOnlyList<ConsultationParty> Parties { get { return _parties; } }
        public IReadOnlyList<ConsultationComment> Comments { get { return CommentList; } }

        internal ConsultationRound(int roundNo, string draftVersion, DateTimeOffset openedUtc, DateTimeOffset deadlineUtc, bool agreed, List<ConsultationParty> parties, string draftSha256)
        {
            DraftSha256 = draftSha256 ?? string.Empty;
            RoundNo = roundNo;
            DraftVersion = draftVersion ?? string.Empty;
            OpenedUtc = openedUtc;
            DeadlineUtc = deadlineUtc;
            IsAgreedDeadline = agreed;
            _parties = parties;
        }

        public bool HasParty(string partyId)
        {
            for (int i = 0; i < _parties.Count; i++)
            {
                if (string.Equals(_parties[i].PartyId, partyId, StringComparison.Ordinal))
                {
                    return true;
                }
            }

            return false;
        }

        public ConsultationReply ReplyOf(string partyId)
        {
            return partyId != null && RepliesByParty.TryGetValue(partyId, out ConsultationReply r) ? r : null;
        }

        public bool IsWaived(string partyId)
        {
            return partyId != null && WaivedByParty.ContainsKey(partyId);
        }

        public ReplyStatus StatusOf(string partyId, DateTimeOffset asOfUtc)
        {
            if (IsWaived(partyId))
            {
                return ReplyStatus.Waived;
            }

            ConsultationReply r = ReplyOf(partyId);
            if (r != null)
            {
                return r.Utc > DeadlineUtc ? ReplyStatus.RepliedLate : ReplyStatus.Replied;
            }

            return asOfUtc > DeadlineUtc ? ReplyStatus.Overdue : ReplyStatus.Pending;
        }

        /// <summary>剩余天数（向上取整，不足一天按一天；过期为 0）。</summary>
        public int DaysRemaining(DateTimeOffset asOfUtc)
        {
            double d = (DeadlineUtc - asOfUtc).TotalDays;
            return d <= 0 ? 0 : (int)Math.Ceiling(d);
        }

        /// <summary>各方均已回复或已放弃。</summary>
        public bool AllReplied
        {
            get
            {
                for (int i = 0; i < _parties.Count; i++)
                {
                    if (!RepliesByParty.ContainsKey(_parties[i].PartyId) && !WaivedByParty.ContainsKey(_parties[i].PartyId))
                    {
                        return false;
                    }
                }

                return true;
            }
        }

        public AdoptionTally TallyFor(string partyId)
        {
            int a = 0, p = 0, n = 0, pend = 0;
            for (int i = 0; i < CommentList.Count; i++)
            {
                ConsultationComment c = CommentList[i];
                if (partyId != null && !string.Equals(c.PartyId, partyId, StringComparison.Ordinal))
                {
                    continue;
                }

                switch (c.Decision)
                {
                    case AdoptionDecision.Adopted: a++; break;
                    case AdoptionDecision.PartiallyAdopted: p++; break;
                    case AdoptionDecision.NotAdopted: n++; break;
                    default: pend++; break;
                }
            }

            return new AdoptionTally(a, p, n, pend);
        }
    }

    /// <summary>
    /// 报告草案征求意见（⑩，P6a 先提供领域模型）：按轮次进行，同一时刻只有一轮开放；
    /// 回复、采纳决定、开/关轮均写审计。
    /// </summary>
    public sealed class Consultation
    {
        public const int DefaultDeadlineDays = 30;

        public const string ErrInvalidArgument = "consultation_invalid_argument";
        public const string ErrRoundOpen = "consultation_round_open";
        public const string ErrRoundNotFound = "consultation_round_not_found";
        public const string ErrRoundClosed = "consultation_round_closed";
        public const string ErrUnknownParty = "consultation_unknown_party";
        public const string ErrDuplicateReply = "consultation_duplicate_reply";
        public const string ErrCommentNotFound = "consultation_comment_not_found";
        public const string ErrAlreadyDecided = "consultation_already_decided";
        public const string ErrCannotClose = "consultation_cannot_close";
        public const string ErrInvalidSha256 = "consultation_invalid_sha256";
        public const string ErrInvalidCaseId = "consultation_invalid_case_id";

        private readonly IInvestigationAuditSink _audit;
        private readonly List<ConsultationRound> _rounds = new List<ConsultationRound>();

        public string ReportId { get; }
        /// <summary>所属案件号；空串表示未填（填写时校验格式）。</summary>
        public string CaseId { get; }
        public IReadOnlyList<ConsultationRound> Rounds { get { return _rounds; } }

        public Consultation(string reportId, IInvestigationAuditSink audit, string caseId = null)
        {
            if (!string.IsNullOrEmpty(caseId) && !EvidenceItem.IsValidCaseId(caseId))
            {
                throw new ArgumentException("caseId 格式不符：" + caseId, nameof(caseId));
            }

            ReportId = reportId ?? string.Empty;
            CaseId = caseId ?? string.Empty;
            _audit = audit ?? throw new ArgumentNullException(nameof(audit));
        }

        public ConsultationRound CurrentRound
        {
            get { return _rounds.Count == 0 ? null : _rounds[_rounds.Count - 1]; }
        }

        public ConsultationRound GetRound(int roundNo)
        {
            return roundNo >= 1 && roundNo <= _rounds.Count ? _rounds[roundNo - 1] : null;
        }

        /// <summary>
        /// 开一轮。期限默认 openedUtc + 30 天；传入 agreedDeadlineUtc 表示双方商定的期限（须晚于发出时间）。
        /// 上一轮未关闭时拒绝。
        /// </summary>
        public Result<ConsultationRound> OpenRound(
            string draftVersion,
            IEnumerable<ConsultationParty> parties,
            DateTimeOffset openedUtc,
            string operatorName,
            DateTimeOffset? agreedDeadlineUtc = null,
            string draftSha256 = null)
        {
            if (!string.IsNullOrEmpty(draftSha256) && !Sha256Hex.IsValid(draftSha256))
            {
                return Result<ConsultationRound>.Fail(ErrInvalidSha256, "草案哈希须为 64 位十六进制");
            }

            if (string.IsNullOrWhiteSpace(draftVersion) || string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "草案版本与操作人不能为空");
            }

            ConsultationRound cur = CurrentRound;
            if (cur != null && !cur.IsClosed)
            {
                return Result<ConsultationRound>.Fail(ErrRoundOpen, "第 " + cur.RoundNo + " 轮尚未关闭");
            }

            if (cur != null && openedUtc < cur.ClosedUtc.Value)
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "新一轮发出时间早于上一轮关闭时间");
            }

            var list = new List<ConsultationParty>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            if (parties != null)
            {
                foreach (ConsultationParty p in parties)
                {
                    if (p == null || string.IsNullOrWhiteSpace(p.PartyId))
                    {
                        return Result<ConsultationRound>.Fail(ErrInvalidArgument, "征求意见方编号不能为空");
                    }

                    if (!seen.Add(p.PartyId))
                    {
                        return Result<ConsultationRound>.Fail(ErrInvalidArgument, "征求意见方重复：" + p.PartyId);
                    }

                    list.Add(p);
                }
            }

            if (list.Count == 0)
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "至少一方");
            }

            DateTimeOffset deadline = agreedDeadlineUtc ?? openedUtc.AddDays(DefaultDeadlineDays);
            if (deadline <= openedUtc)
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "期限必须晚于发出时间");
            }

            var round = new ConsultationRound(_rounds.Count + 1, draftVersion, openedUtc, deadline, agreedDeadlineUtc.HasValue, list, Sha256Hex.Normalize(draftSha256));
            var names = new List<string>();
            for (int i = 0; i < list.Count; i++)
            {
                names.Add(list[i].PartyId);
            }

            _audit.Append(new InvestigationAuditEntry(openedUtc, operatorName, "consultation.open", InvestigationAuditCategories.Consultation,
                "发出征求意见 " + ReportId + " 第 " + round.RoundNo + " 轮", string.Empty,
"草案=" + draftVersion + (string.IsNullOrEmpty(round.DraftSha256) ? string.Empty : "（" + round.DraftSha256 + "）") + "；各方=" + string.Join(",", names) + "；期限=" + AuditJson.FormatIso(deadline) + (round.IsAgreedDeadline ? "（商定）" : "（默认 30 天）")));
            _rounds.Add(round);
            return Result<ConsultationRound>.Ok(round);
        }

        /// <summary>登记某方回复及其逐条意见。逾期回复接受但标记为 RepliedLate；每方每轮只登记一次。</summary>
        public Result<ConsultationReply> RecordReply(int roundNo, string partyId, DateTimeOffset utc, string text, IEnumerable<string> comments, string operatorName)
        {
            ConsultationRound r = GetRound(roundNo);
            if (r == null)
            {
                return Result<ConsultationReply>.Fail(ErrRoundNotFound, "轮次不存在：" + roundNo);
            }

            if (r.IsClosed)
            {
                return Result<ConsultationReply>.Fail(ErrRoundClosed, "第 " + roundNo + " 轮已关闭");
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<ConsultationReply>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (!r.HasParty(partyId))
            {
                return Result<ConsultationReply>.Fail(ErrUnknownParty, "该方不在本轮名单：" + (partyId ?? "(null)"));
            }

            if (r.RepliesByParty.ContainsKey(partyId) || r.WaivedByParty.ContainsKey(partyId))
            {
                return Result<ConsultationReply>.Fail(ErrDuplicateReply, "该方本轮已回复或已放弃：" + partyId);
            }

            if (utc < r.OpenedUtc)
            {
                return Result<ConsultationReply>.Fail(ErrInvalidArgument, "回复时间早于发出时间");
            }

            var cs = new List<ConsultationComment>();
            if (comments != null)
            {
                foreach (string c in comments)
                {
                    if (!string.IsNullOrWhiteSpace(c))
                    {
                        cs.Add(new ConsultationComment("C" + roundNo + "-" + (r.CommentList.Count + cs.Count + 1).ToString(CultureInfo.InvariantCulture), roundNo, partyId, c));
                    }
                }
            }

            var reply = new ConsultationReply(partyId, utc, text, cs);
            bool late = utc > r.DeadlineUtc;
            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "consultation.reply", InvestigationAuditCategories.Consultation,
                "登记回复 " + ReportId + " 第 " + roundNo + " 轮 " + partyId, ReplyStatus.Pending.ToString(),
                (late ? ReplyStatus.RepliedLate : ReplyStatus.Replied) + "；意见 " + cs.Count + " 条"));
            r.RepliesByParty[partyId] = reply;
            r.CommentList.AddRange(cs);
            return Result<ConsultationReply>.Ok(reply);
        }

        /// <summary>登记某方放弃/免于回复（须写明理由）。与回复互斥；写审计。</summary>
        public Result<ConsultationRound> WaiveReply(int roundNo, string partyId, string operatorName, DateTimeOffset utc, string reason)
        {
            ConsultationRound r = GetRound(roundNo);
            if (r == null)
            {
                return Result<ConsultationRound>.Fail(ErrRoundNotFound, "轮次不存在：" + roundNo);
            }

            if (r.IsClosed)
            {
                return Result<ConsultationRound>.Fail(ErrRoundClosed, "第 " + roundNo + " 轮已关闭");
            }

            if (string.IsNullOrWhiteSpace(operatorName) || string.IsNullOrWhiteSpace(reason))
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "操作人与放弃理由不能为空");
            }

            if (!r.HasParty(partyId))
            {
                return Result<ConsultationRound>.Fail(ErrUnknownParty, "该方不在本轮名单：" + (partyId ?? "(null)"));
            }

            if (r.RepliesByParty.ContainsKey(partyId) || r.WaivedByParty.ContainsKey(partyId))
            {
                return Result<ConsultationRound>.Fail(ErrDuplicateReply, "该方本轮已回复或已放弃：" + partyId);
            }

            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "consultation.waive", InvestigationAuditCategories.Consultation,
                "登记放弃回复 " + ReportId + " 第 " + roundNo + " 轮 " + partyId, ReplyStatus.Pending.ToString(), ReplyStatus.Waived + "；" + reason));
            r.WaivedByParty[partyId] = reason;
            return Result<ConsultationRound>.Ok(r);
        }

        /// <summary>
        /// 记录对一条意见的采纳决定。部分采纳/不采纳必须附书面反馈；决定一经作出不可改（需改请新开一轮）。
        /// </summary>
        public Result<ConsultationComment> DecideComment(string commentId, AdoptionDecision decision, string feedback, string operatorName, DateTimeOffset utc)
        {
            if (decision == AdoptionDecision.Pending)
            {
                return Result<ConsultationComment>.Fail(ErrInvalidArgument, "决定不能为 Pending");
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<ConsultationComment>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (decision != AdoptionDecision.Adopted && string.IsNullOrWhiteSpace(feedback))
            {
                return Result<ConsultationComment>.Fail(ErrInvalidArgument, "部分采纳/不采纳必须附书面反馈");
            }

            ConsultationComment c = FindComment(commentId);
            if (c == null)
            {
                return Result<ConsultationComment>.Fail(ErrCommentNotFound, "意见不存在：" + (commentId ?? "(null)"));
            }

            if (c.Decision != AdoptionDecision.Pending)
            {
                return Result<ConsultationComment>.Fail(ErrAlreadyDecided, "该意见已有决定：" + c.Decision);
            }

            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "consultation.decide", InvestigationAuditCategories.Consultation,
                "意见采纳决定 " + ReportId + " " + c.CommentId, AdoptionDecision.Pending.ToString(),
                decision + (string.IsNullOrEmpty(feedback) ? string.Empty : "；" + feedback)));
            c.Decision = decision;
            c.Feedback = feedback ?? string.Empty;
            c.DecidedBy = operatorName;
            c.DecidedUtc = utc;
            return Result<ConsultationComment>.Ok(c);
        }

        /// <summary>关闭当前轮：各方均已回复/放弃，或已到期限（utc ≥ 期限，到达瞬间即可关闭），才允许关闭。</summary>
        public Result<ConsultationRound> CloseRound(int roundNo, string operatorName, DateTimeOffset utc)
        {
            ConsultationRound r = GetRound(roundNo);
            if (r == null)
            {
                return Result<ConsultationRound>.Fail(ErrRoundNotFound, "轮次不存在：" + roundNo);
            }

            if (r.IsClosed)
            {
                return Result<ConsultationRound>.Fail(ErrRoundClosed, "已关闭");
            }

            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<ConsultationRound>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (!r.AllReplied && utc < r.DeadlineUtc)
            {
                return Result<ConsultationRound>.Fail(ErrCannotClose, "期限未到且仍有方未回复");
            }

            _audit.Append(new InvestigationAuditEntry(utc, operatorName, "consultation.close", InvestigationAuditCategories.Consultation,
                "关闭征求意见 " + ReportId + " 第 " + roundNo + " 轮", "open", "closed；回复 " + r.RepliesByParty.Count + "/" + r.Parties.Count + "；放弃 " + r.WaivedByParty.Count));
            r.IsClosed = true;
            r.ClosedUtc = utc;
            return Result<ConsultationRound>.Ok(r);
        }

        private ConsultationComment FindComment(string commentId)
        {
            for (int i = 0; i < _rounds.Count; i++)
            {
                List<ConsultationComment> list = _rounds[i].CommentList;
                for (int k = 0; k < list.Count; k++)
                {
                    if (string.Equals(list[k].CommentId, commentId, StringComparison.Ordinal))
                    {
                        return list[k];
                    }
                }
            }

            return null;
        }
    }
}
