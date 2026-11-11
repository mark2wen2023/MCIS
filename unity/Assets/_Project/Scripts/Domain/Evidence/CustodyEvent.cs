using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Mcis.Domain.Evidence
{
    public enum CustodyEventKind : byte
    {
        Register = 0,
        Access = 1,
        Change = 2,
        Verify = 3,
        /// <summary>调查员复核标注（需复核 / 解除）。</summary>
        Review = 4,
    }

    /// <summary>
    /// 保管链事件，对应 audit/custody.jsonl 的一行。
    /// 行格式 = audit.jsonl 的 7 个标准键（utc/operator/action/category/command/before/after）
    /// + 扩展键（seq/evidence_id/sha256/detail/result/prev 及登记元数据），
    /// 因此 Data 层 AuditRecord.FromJsonLine 可原样读取（忽略扩展键）。
    /// prev 为上一行 UTF-8 文本的 SHA-256（首行为 64 个 0），用于检测改写/删行。
    /// </summary>
    public sealed class CustodyEvent
    {
        public const string ActionRegister = "custody.register";
        public const string ActionAccess = "custody.access";
        public const string ActionChange = "custody.change";
        public const string ActionVerify = "custody.verify";
        public const string ActionReview = "custody.review";

        public long Seq { get; }
        public DateTimeOffset Utc { get; }
        public string OperatorName { get; }
        public CustodyEventKind Kind { get; }
        public string EvidenceId { get; }
        /// <summary>Register：登记哈希；Access：当前哈希；Change：新哈希；Verify：实测哈希。</summary>
        public string Sha256 { get; }
        /// <summary>Change：变更前哈希；Verify：期望哈希；其他为空。</summary>
        public string PreviousSha256 { get; }
        /// <summary>访问目的 / 变更原因 / 备注。</summary>
        public string Detail { get; }
        /// <summary>仅 Verify：实测与当前哈希是否一致。</summary>
        public bool? VerifyMatched { get; }
        /// <summary>仅 Review：true = 标注需复核，false = 解除需复核。</summary>
        public bool? NeedsReview { get; }
        public string PrevLineHash { get; }
        /// <summary>仅 Register 有值。</summary>
        public EvidenceItem RegisteredItem { get; }

        internal CustodyEvent(
            long seq,
            DateTimeOffset utc,
            string operatorName,
            CustodyEventKind kind,
            string evidenceId,
            string sha256,
            string previousSha256,
            string detail,
            bool? verifyMatched,
            string prevLineHash,
            EvidenceItem registeredItem,
            bool? needsReview = null)
        {
            Seq = seq;
            Utc = AuditJson.TruncateToSecond(utc);
            OperatorName = operatorName ?? string.Empty;
            Kind = kind;
            EvidenceId = evidenceId ?? string.Empty;
            Sha256 = sha256 ?? string.Empty;
            PreviousSha256 = previousSha256 ?? string.Empty;
            Detail = detail ?? string.Empty;
            VerifyMatched = verifyMatched;
            PrevLineHash = prevLineHash ?? Sha256Hex.Zero;
            RegisteredItem = registeredItem;
            NeedsReview = needsReview;
        }

        public string Action
        {
            get
            {
                switch (Kind)
                {
                    case CustodyEventKind.Register: return ActionRegister;
                    case CustodyEventKind.Access: return ActionAccess;
                    case CustodyEventKind.Change: return ActionChange;
                    case CustodyEventKind.Review: return ActionReview;
                    default: return ActionVerify;
                }
            }
        }

        public string CommandName
        {
            get
            {
                switch (Kind)
                {
                    case CustodyEventKind.Register: return "登记证据 " + EvidenceId;
                    case CustodyEventKind.Access: return "访问证据 " + EvidenceId;
                    case CustodyEventKind.Change: return "证据派生/变更 " + EvidenceId;
                    case CustodyEventKind.Review: return (NeedsReview == true ? "标注需复核 " : "解除需复核 ") + EvidenceId;
                    default: return "校验证据哈希 " + EvidenceId;
                }
            }
        }

        public string BeforeSummary
        {
            get { return Kind == CustodyEventKind.Change || Kind == CustodyEventKind.Verify ? PreviousSha256 : string.Empty; }
        }

        public string AfterSummary
        {
            get
            {
                if (Kind == CustodyEventKind.Access)
                {
                    return Detail;
                }

                if (Kind == CustodyEventKind.Review)
                {
                    return NeedsReview == true ? "NeedsReview" : "Cleared";
                }

                return Sha256;
            }
        }

        public string ToJsonLine()
        {
            var sb = new StringBuilder();
            AuditJson.AppendStandardFields(sb, Utc, OperatorName, Action, InvestigationAuditCategories.Custody, CommandName, BeforeSummary, AfterSummary);
            sb.Append(",\"seq\":").Append(Seq.ToString(CultureInfo.InvariantCulture));
            sb.Append(",\"evidence_id\":").Append(AuditJson.Quote(EvidenceId));
            sb.Append(",\"sha256\":").Append(AuditJson.Quote(Sha256));
            sb.Append(",\"detail\":").Append(AuditJson.Quote(Detail));
            if (VerifyMatched.HasValue)
            {
                sb.Append(",\"result\":").Append(AuditJson.Quote(VerifyMatched.Value ? "match" : "mismatch"));
            }

            if (NeedsReview.HasValue)
            {
                sb.Append(",\"result\":").Append(AuditJson.Quote(NeedsReview.Value ? "needs_review" : "cleared"));
            }

            if (RegisteredItem != null)
            {
                sb.Append(",\"title\":").Append(AuditJson.Quote(RegisteredItem.Title));
                sb.Append(",\"source\":").Append(AuditJson.Quote(RegisteredItem.Source));
                sb.Append(",\"extracted_by\":").Append(AuditJson.Quote(RegisteredItem.ExtractedBy));
                sb.Append(",\"extracted_utc\":").Append(AuditJson.Quote(AuditJson.FormatIso(RegisteredItem.ExtractedUtc)));
                sb.Append(",\"path\":").Append(AuditJson.Quote(RegisteredItem.RelativePath));
                // 仅在非默认时写出，保证旧格式行重新序列化后逐字不变。
                if (RegisteredItem.CaseId.Length > 0)
                {
                    sb.Append(",\"case_id\":").Append(AuditJson.Quote(RegisteredItem.CaseId));
                }

                if (RegisteredItem.IsRestricted)
                {
                    sb.Append(",\"confidentiality\":").Append(AuditJson.Quote("Restricted"));
                }
            }

            sb.Append(",\"prev\":").Append(AuditJson.Quote(PrevLineHash));
            sb.Append('}');
            return sb.ToString();
        }

        internal static bool TryParse(string line, out CustodyEvent ev, out string error)
        {
            ev = null;
            error = null;
            if (!AuditJson.TryParseFlatObject(line, out Dictionary<string, string> f))
            {
                error = "not a flat JSON object";
                return false;
            }

            string Get(string k) { return f.TryGetValue(k, out string v) && v != null ? v : string.Empty; }

            if (Get("category") != InvestigationAuditCategories.Custody)
            {
                error = "category is not Custody";
                return false;
            }

            CustodyEventKind kind;
            switch (Get("action"))
            {
                case ActionRegister: kind = CustodyEventKind.Register; break;
                case ActionAccess: kind = CustodyEventKind.Access; break;
                case ActionChange: kind = CustodyEventKind.Change; break;
                case ActionVerify: kind = CustodyEventKind.Verify; break;
                case ActionReview: kind = CustodyEventKind.Review; break;
                default:
                    error = "unknown action";
                    return false;
            }

            if (!long.TryParse(Get("seq"), NumberStyles.Integer, CultureInfo.InvariantCulture, out long seq))
            {
                error = "bad seq";
                return false;
            }

            DateTimeOffset utc;
            try
            {
                utc = AuditJson.ParseIso(Get("utc"));
            }
            catch (FormatException)
            {
                error = "bad utc";
                return false;
            }

            string evidenceId = Get("evidence_id");
            EvidenceItem item = null;
            if (kind == CustodyEventKind.Register)
            {
                DateTimeOffset extracted;
                try
                {
                    extracted = AuditJson.ParseIso(Get("extracted_utc"));
                }
                catch (FormatException)
                {
                    error = "bad extracted_utc";
                    return false;
                }

                EvidenceConfidentiality conf = Get("confidentiality") == "Restricted" ? EvidenceConfidentiality.Restricted : EvidenceConfidentiality.Normal;
                item = new EvidenceItem(evidenceId, Get("title"), Get("source"), Get("extracted_by"), extracted, Get("sha256"), Get("path"), Get("case_id"), conf);
            }

            bool? matched = null;
            if (kind == CustodyEventKind.Verify)
            {
                matched = Get("result") == "match";
            }

            bool? review = null;
            if (kind == CustodyEventKind.Review)
            {
                review = Get("result") == "needs_review";
            }

            string previous = kind == CustodyEventKind.Change || kind == CustodyEventKind.Verify ? Get("before") : string.Empty;
            ev = new CustodyEvent(seq, utc, Get("operator"), kind, evidenceId, Get("sha256"), previous, Get("detail"), matched, Get("prev"), item, review);
            return true;
        }
    }

    /// <summary>保管链行写入口。Data 层实现时追加写入 .mcase/audit/custody.jsonl。</summary>
    public interface ICustodyLineSink
    {
        void AppendLine(string jsonLine);
    }
}
