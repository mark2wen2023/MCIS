using System;
using System.Collections.Generic;
using Mcis.Core;

namespace Mcis.Domain.Evidence
{
    /// <summary>
    /// 证据保管链（② 最小版）：只追加。没有删除/修改 API；变更以 Change 事件追加，登记快照永不改写。
    /// 每行带 prev（上一行哈希），<see cref="Load"/> 会校验整条链，发现改写、删行、乱序即失败。
    /// </summary>
    public sealed class CustodyLedger
    {
        /// <summary>.mcase 包内文件位置（ARCHITECTURE §15.4）。</summary>
        public const string RelativePath = "audit/custody.jsonl";

        public const string ErrInvalidArgument = "custody_invalid_argument";
        public const string ErrInvalidId = "custody_invalid_id";
        public const string ErrInvalidCaseId = "custody_invalid_case_id";
        public const string ErrNoReviewChange = "custody_review_unchanged";
        public const string ErrDuplicateId = "custody_duplicate_id";
        public const string ErrUnknownEvidence = "custody_unknown_evidence";
        public const string ErrInvalidSha256 = "custody_invalid_sha256";
        public const string ErrNoChange = "custody_no_change";
        public const string ErrTimeRegression = "custody_time_regression";
        public const string ErrChainBroken = "custody_chain_broken";
        public const string ErrParse = "custody_parse_error";

        private readonly List<CustodyEvent> _events = new List<CustodyEvent>();
        private readonly List<string> _lines = new List<string>();
        private readonly List<EvidenceItem> _items = new List<EvidenceItem>();
        private readonly Dictionary<string, EvidenceItem> _byId = new Dictionary<string, EvidenceItem>(StringComparer.Ordinal);
        private readonly Dictionary<string, string> _currentSha = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly Dictionary<string, bool?> _lastVerify = new Dictionary<string, bool?>(StringComparer.Ordinal);
        private readonly HashSet<string> _needsReview = new HashSet<string>(StringComparer.Ordinal);
        private readonly ICustodyLineSink _sink;

        public CustodyLedger(ICustodyLineSink sink = null)
        {
            _sink = sink;
        }

        public IReadOnlyList<CustodyEvent> Events { get { return _events; } }
        public IReadOnlyList<string> JsonLines { get { return _lines; } }
        public IReadOnlyList<EvidenceItem> Items { get { return _items; } }

        public EvidenceItem Get(string evidenceId)
        {
            return evidenceId != null && _byId.TryGetValue(evidenceId, out EvidenceItem it) ? it : null;
        }

        /// <summary>最近一次登记/变更后的哈希；未知证据返回 null。</summary>
        public string CurrentSha256(string evidenceId)
        {
            return evidenceId != null && _currentSha.TryGetValue(evidenceId, out string s) ? s : null;
        }

        /// <summary>
        /// 推导证据状态：标注需复核优先；否则按最近一次校验（一致/不一致）；无校验或变更后未再校验为 Unverified。
        /// 未知证据返回 null。
        /// </summary>
        public EvidenceStatus? StatusOf(string evidenceId)
        {
            if (evidenceId == null || !_byId.ContainsKey(evidenceId))
            {
                return null;
            }

            if (_needsReview.Contains(evidenceId))
            {
                return EvidenceStatus.NeedsReview;
            }

            bool? v = _lastVerify.TryGetValue(evidenceId, out bool? x) ? x : null;
            return !v.HasValue ? EvidenceStatus.Unverified : (v.Value ? EvidenceStatus.Verified : EvidenceStatus.Mismatch);
        }

        public bool IsMarkedNeedsReview(string evidenceId)
        {
            return evidenceId != null && _needsReview.Contains(evidenceId);
        }

        /// <summary>调查员标注“需复核”（追加 Review 事件，必须写明原因）。已处于需复核时返回失败。</summary>
        public Result<CustodyEvent> MarkNeedsReview(string evidenceId, string investigator, DateTimeOffset utc, string reason)
        {
            return Review(evidenceId, investigator, utc, reason, true);
        }

        /// <summary>调查员解除“需复核”（追加 Review 事件，必须写明原因）。</summary>
        public Result<CustodyEvent> ResolveNeedsReview(string evidenceId, string investigator, DateTimeOffset utc, string reason)
        {
            return Review(evidenceId, investigator, utc, reason, false);
        }

        private Result<CustodyEvent> Review(string evidenceId, string investigator, DateTimeOffset utc, string reason, bool flag)
        {
            Result<CustodyEvent> pre = CheckKnown(evidenceId, investigator, utc);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            if (string.IsNullOrWhiteSpace(reason))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "复核标注必须写明原因");
            }

            if (_needsReview.Contains(evidenceId) == flag)
            {
                return Result<CustodyEvent>.Fail(ErrNoReviewChange, flag ? "已标注需复核" : "未处于需复核状态");
            }

            return Append(CustodyEventKind.Review, utc, investigator, evidenceId, _currentSha[evidenceId], null, reason, null, null, flag);
        }

        public IReadOnlyList<CustodyEvent> HistoryOf(string evidenceId)
        {
            var list = new List<CustodyEvent>();
            for (int i = 0; i < _events.Count; i++)
            {
                if (string.Equals(_events[i].EvidenceId, evidenceId, StringComparison.Ordinal))
                {
                    list.Add(_events[i]);
                }
            }

            return list;
        }

        public int AccessCount(string evidenceId)
        {
            int n = 0;
            for (int i = 0; i < _events.Count; i++)
            {
                if (_events[i].Kind == CustodyEventKind.Access && string.Equals(_events[i].EvidenceId, evidenceId, StringComparison.Ordinal))
                {
                    n++;
                }
            }

            return n;
        }

        public Result<CustodyEvent> Register(EvidenceItem item, string operatorName, DateTimeOffset utc)
        {
            if (item == null || string.IsNullOrWhiteSpace(item.EvidenceId))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "证据编号不能为空");
            }

            if (!EvidenceItem.IsValidId(item.EvidenceId))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidId, "证据编号须为 EV- 加至少 3 位数字：" + item.EvidenceId);
            }

            if (item.CaseId.Length > 0 && !EvidenceItem.IsValidCaseId(item.CaseId))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidCaseId, "案件号格式不符：" + item.CaseId);
            }

            if (string.IsNullOrWhiteSpace(item.Source) || string.IsNullOrWhiteSpace(item.ExtractedBy))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "来源与提取人不能为空");
            }

            if (!Sha256Hex.IsValid(item.Sha256))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidSha256, "SHA-256 必须为 64 位十六进制");
            }

            if (_byId.ContainsKey(item.EvidenceId))
            {
                return Result<CustodyEvent>.Fail(ErrDuplicateId, "证据编号已登记：" + item.EvidenceId);
            }

            Result<CustodyEvent> pre = CheckCommon(operatorName, utc);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            return Append(CustodyEventKind.Register, utc, operatorName, item.EvidenceId, item.Sha256, null, string.Empty, null, item);
        }

        public Result<CustodyEvent> RecordAccess(string evidenceId, string operatorName, DateTimeOffset utc, string purpose)
        {
            Result<CustodyEvent> pre = CheckKnown(evidenceId, operatorName, utc);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            if (string.IsNullOrWhiteSpace(purpose))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "访问目的不能为空");
            }

            return Append(CustodyEventKind.Access, utc, operatorName, evidenceId, _currentSha[evidenceId], null, purpose, null, null);
        }

        /// <summary>记录派生/变更（如转写、脱敏副本）。原登记快照保留，当前哈希更新为 newSha256。</summary>
        public Result<CustodyEvent> RecordChange(string evidenceId, string operatorName, DateTimeOffset utc, string newSha256, string reason)
        {
            Result<CustodyEvent> pre = CheckKnown(evidenceId, operatorName, utc);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            if (string.IsNullOrWhiteSpace(reason))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "变更原因不能为空");
            }

            if (!Sha256Hex.IsValid(newSha256))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidSha256, "SHA-256 必须为 64 位十六进制");
            }

            string norm = Sha256Hex.Normalize(newSha256);
            string old = _currentSha[evidenceId];
            if (string.Equals(norm, old, StringComparison.Ordinal))
            {
                return Result<CustodyEvent>.Fail(ErrNoChange, "新哈希与当前哈希相同");
            }

            return Append(CustodyEventKind.Change, utc, operatorName, evidenceId, norm, old, reason, null, null);
        }

        /// <summary>重新计算文件哈希后登记校验结果（一致或不一致都追加一行）。</summary>
        public Result<CustodyEvent> Verify(string evidenceId, string operatorName, DateTimeOffset utc, string observedSha256)
        {
            Result<CustodyEvent> pre = CheckKnown(evidenceId, operatorName, utc);
            if (!pre.IsSuccess)
            {
                return pre;
            }

            if (!Sha256Hex.IsValid(observedSha256))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidSha256, "SHA-256 必须为 64 位十六进制");
            }

            string norm = Sha256Hex.Normalize(observedSha256);
            string expected = _currentSha[evidenceId];
            bool matched = string.Equals(norm, expected, StringComparison.Ordinal);
            return Append(CustodyEventKind.Verify, utc, operatorName, evidenceId, norm, expected, matched ? "一致" : "不一致", matched, null);
        }

        /// <summary>从 custody.jsonl 的行重建并校验整条链（空行忽略）。</summary>
        public static Result<CustodyLedger> Load(IEnumerable<string> lines, ICustodyLineSink sink = null)
        {
            if (lines == null)
            {
                return Result<CustodyLedger>.Fail(ErrInvalidArgument, "lines 为空");
            }

            var ledger = new CustodyLedger(sink);
            int lineNo = 0;
            foreach (string raw in lines)
            {
                lineNo++;
                string line = raw == null ? string.Empty : raw.Trim();
                if (line.Length == 0)
                {
                    continue;
                }

                if (!CustodyEvent.TryParse(line, out CustodyEvent ev, out string err))
                {
                    return Result<CustodyLedger>.Fail(ErrParse, "第 " + lineNo + " 行：" + err);
                }

                string expectedPrev = ledger._lines.Count == 0 ? Sha256Hex.Zero : Sha256Hex.OfUtf8(ledger._lines[ledger._lines.Count - 1]);
                if (!string.Equals(ev.PrevLineHash, expectedPrev, StringComparison.Ordinal) || ev.Seq != ledger._events.Count + 1)
                {
                    return Result<CustodyLedger>.Fail(ErrChainBroken, "第 " + lineNo + " 行：链断裂（改写、删行或乱序）");
                }

                // 重新序列化必须与原文逐字一致，否则说明字段被改写或格式不符。
                if (!string.Equals(ev.ToJsonLine(), line, StringComparison.Ordinal))
                {
                    return Result<CustodyLedger>.Fail(ErrChainBroken, "第 " + lineNo + " 行：内容与规范格式不一致");
                }

                Result<bool> applied = ledger.ApplyLoaded(ev, line);
                if (!applied.IsSuccess)
                {
                    return Result<CustodyLedger>.Fail(applied.ErrorCode, "第 " + lineNo + " 行：" + applied.ErrorMessage);
                }
            }

            return Result<CustodyLedger>.Ok(ledger);
        }

        private Result<bool> ApplyLoaded(CustodyEvent ev, string line)
        {
            if (_events.Count > 0 && ev.Utc < _events[_events.Count - 1].Utc)
            {
                return Result<bool>.Fail(ErrTimeRegression, "时间倒退");
            }

            if (ev.Kind == CustodyEventKind.Register)
            {
                if (_byId.ContainsKey(ev.EvidenceId))
                {
                    return Result<bool>.Fail(ErrDuplicateId, "重复登记 " + ev.EvidenceId);
                }

                if (!EvidenceItem.IsValidId(ev.EvidenceId))
                {
                    return Result<bool>.Fail(ErrInvalidId, "证据编号格式不符 " + ev.EvidenceId);
                }

                _byId[ev.EvidenceId] = ev.RegisteredItem;
                _items.Add(ev.RegisteredItem);
                _currentSha[ev.EvidenceId] = ev.Sha256;
            }
            else
            {
                if (!_byId.ContainsKey(ev.EvidenceId))
                {
                    return Result<bool>.Fail(ErrUnknownEvidence, "未登记的证据 " + ev.EvidenceId);
                }

                if (ev.Kind == CustodyEventKind.Change)
                {
                    _currentSha[ev.EvidenceId] = ev.Sha256;
                    _lastVerify[ev.EvidenceId] = null;
                }
                else if (ev.Kind == CustodyEventKind.Verify)
                {
                    _lastVerify[ev.EvidenceId] = ev.VerifyMatched;
                }
                else if (ev.Kind == CustodyEventKind.Review)
                {
                    if (ev.NeedsReview == true)
                    {
                        _needsReview.Add(ev.EvidenceId);
                    }
                    else
                    {
                        _needsReview.Remove(ev.EvidenceId);
                    }
                }
            }

            _events.Add(ev);
            _lines.Add(line);
            return Result<bool>.Ok(true);
        }

        private Result<CustodyEvent> CheckCommon(string operatorName, DateTimeOffset utc)
        {
            if (string.IsNullOrWhiteSpace(operatorName))
            {
                return Result<CustodyEvent>.Fail(ErrInvalidArgument, "操作人不能为空");
            }

            if (_events.Count > 0 && AuditJson.TruncateToSecond(utc) < _events[_events.Count - 1].Utc)
            {
                return Result<CustodyEvent>.Fail(ErrTimeRegression, "时间早于上一条保管链记录");
            }

            return Result<CustodyEvent>.Ok(null);
        }

        private Result<CustodyEvent> CheckKnown(string evidenceId, string operatorName, DateTimeOffset utc)
        {
            if (evidenceId == null || !_byId.ContainsKey(evidenceId))
            {
                return Result<CustodyEvent>.Fail(ErrUnknownEvidence, "未登记的证据：" + (evidenceId ?? "(null)"));
            }

            return CheckCommon(operatorName, utc);
        }

        private Result<CustodyEvent> Append(
            CustodyEventKind kind,
            DateTimeOffset utc,
            string operatorName,
            string evidenceId,
            string sha256,
            string previousSha256,
            string detail,
            bool? matched,
            EvidenceItem item,
            bool? needsReview = null)
        {
            string prev = _lines.Count == 0 ? Sha256Hex.Zero : Sha256Hex.OfUtf8(_lines[_lines.Count - 1]);
            var ev = new CustodyEvent(_events.Count + 1, utc, operatorName, kind, evidenceId, sha256, previousSha256, detail, matched, prev, item, needsReview);
            string line = ev.ToJsonLine();

            // 先写外部汇，成功后才进内存，避免内存与文件不一致。
            if (_sink != null)
            {
                _sink.AppendLine(line);
            }

            ApplyLoaded(ev, line);
            return Result<CustodyEvent>.Ok(ev);
        }
    }
}
