namespace Mcis.Domain.InterviewCompare
{
    /// <summary>W5（询问笔录比对页）错误码。前缀 icmp_。W3 Interview 自身的错误码（interview_* / crosscheck_*）原样透传。</summary>
    public static class InterviewCompareErrors
    {
        /// <summary>参数为空或非法。</summary>
        public const string InvalidArgument = "icmp_invalid_argument";

        /// <summary>转写文本为空，或找不到任何“问/答/Q/A”标记。</summary>
        public const string EmptyTranscript = "icmp_empty_transcript";

        /// <summary>“答”之前没有未回答的“问”（错误）。</summary>
        public const string OrphanAnswer = "icmp_orphan_answer";

        /// <summary>“问”之后没有“答”（警告，轮次保留，答为空）。</summary>
        public const string MissingAnswer = "icmp_missing_answer";

        /// <summary>时间戳格式或取值非法（分、秒须 &lt; 60）。</summary>
        public const string InvalidTimestamp = "icmp_invalid_timestamp";

        /// <summary>时间倒序：时间戳早于上一条，或写入后早于笔录开始/已有轮次。</summary>
        public const string TimeOrder = "icmp_time_order";

        /// <summary>解析结果含错误，拒绝写入笔录。</summary>
        public const string TranscriptInvalid = "icmp_transcript_invalid";

        /// <summary>笔录中没有该陈述。</summary>
        public const string StatementNotFound = "icmp_statement_not_found";

        /// <summary>该行没有任何待复核项（陈述已复核/已驳回，且比对结论不是待确认）。</summary>
        public const string NotReviewable = "icmp_not_reviewable";

        /// <summary>驳回时比对结论已不是待确认（例如已确认）。</summary>
        public const string EntryNotPending = "icmp_entry_not_pending";

        /// <summary>登记簿中同一 statementId 的比对结论属于另一份笔录。</summary>
        public const string RecordMismatch = "icmp_record_mismatch";

        /// <summary>W5.1：比对结论已过期（陈述改版后未重新比对），须先“重新比对”再确认。</summary>
        public const string EntryStale = "icmp_entry_stale";

        /// <summary>W5.1：该行不允许重新比对（结论未过期且待确认——直接确认/驳回；或已确认——不可撤销）。</summary>
        public const string RecheckNotAllowed = "icmp_recheck_not_allowed";
    }
}
