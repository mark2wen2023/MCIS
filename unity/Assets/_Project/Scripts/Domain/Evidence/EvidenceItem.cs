using System;
using System.Text.RegularExpressions;

namespace Mcis.Domain.Evidence
{
    /// <summary>保密标记（contracts evidence-item.confidentiality；Restricted = MSC.255(84) 第 23 章保密资料）。</summary>
    public enum EvidenceConfidentiality : byte
    {
        Normal = 0,
        Restricted = 1,
    }

    /// <summary>证据状态（由保管链事件推导，不可直接写）。</summary>
    public enum EvidenceStatus : byte
    {
        /// <summary>尚无校验记录（或变更后未重新校验）。</summary>
        Unverified = 0,
        /// <summary>最近一次校验一致。</summary>
        Verified = 1,
        /// <summary>最近一次校验不一致。</summary>
        Mismatch = 2,
        /// <summary>调查员标注需复核（优先于校验结果显示）。</summary>
        NeedsReview = 3,
    }

    /// <summary>
    /// 证据条目（登记时的不可变快照）：编号、案件号、来源、提取人、提取时间、SHA-256、保密标记。
    /// 之后的访问、变更、校验、复核标注只以保管链事件追加，不修改本对象。
    /// </summary>
    public sealed class EvidenceItem
    {
        /// <summary>contracts common.evidenceRef：EV- 加至少 3 位数字。</summary>
        public static readonly Regex IdPattern = new Regex(@"\AEV-[0-9]{3,}\z", RegexOptions.CultureInvariant); // W3-D09：\z 拒绝末尾换行；只认 ASCII [0-9]

        /// <summary>contracts common.caseId：至少 3 位，字母数字与 . _ -。</summary>
        public static readonly Regex CaseIdPattern = new Regex(@"\A[A-Za-z0-9._-]{3,}\z", RegexOptions.CultureInvariant);

        public string EvidenceId { get; }
        /// <summary>所属案件号（如 CASE-2026-LM01）；空串表示未填（登记时如填写则校验格式）。</summary>
        public string CaseId { get; }
        public string Title { get; }
        public string Source { get; }
        public string ExtractedBy { get; }
        public DateTimeOffset ExtractedUtc { get; }
        public string Sha256 { get; }
        /// <summary>案件包内相对路径，如 raw/vdr/mary.zip；可空。</summary>
        public string RelativePath { get; }
        public EvidenceConfidentiality Confidentiality { get; }
        public bool IsRestricted { get { return Confidentiality == EvidenceConfidentiality.Restricted; } }

        public EvidenceItem(
            string evidenceId,
            string title,
            string source,
            string extractedBy,
            DateTimeOffset extractedUtc,
            string sha256,
            string relativePath = null,
            string caseId = null,
            EvidenceConfidentiality confidentiality = EvidenceConfidentiality.Normal)
        {
            EvidenceId = evidenceId ?? string.Empty;
            Title = title ?? string.Empty;
            Source = source ?? string.Empty;
            ExtractedBy = extractedBy ?? string.Empty;
            ExtractedUtc = AuditJson.TruncateToSecond(extractedUtc);
            Sha256 = Sha256Hex.Normalize(sha256) ?? string.Empty;
            RelativePath = (relativePath ?? string.Empty).Replace('\\', '/');
            CaseId = caseId ?? string.Empty;
            Confidentiality = confidentiality;
        }

        public static bool IsValidId(string evidenceId)
        {
            return evidenceId != null && IdPattern.IsMatch(evidenceId);
        }

        public static bool IsValidCaseId(string caseId)
        {
            return caseId != null && CaseIdPattern.IsMatch(caseId);
        }
    }
}
