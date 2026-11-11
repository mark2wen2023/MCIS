using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// 重组完成后的完整 AIS 载荷报文。
    /// </summary>
    public readonly struct AssembledAisPayload
    {
        /// <summary>首句行号。</summary>
        public int FirstLineNumber { get; }
        /// <summary>拼接后的原始语句文本。</summary>
        public string CombinedRawSentences { get; }
        /// <summary>拼接后的 6-bit 装甲载荷。</summary>
        public string Payload { get; }
        /// <summary>末句填充位数。</summary>
        public int FillBits { get; }
        /// <summary>提取的时间戳。</summary>
        public DateTimeOffset? ExtractedTimestampUtc { get; }
        /// <summary>时间质量等级。</summary>
        public TimeQuality TimeQuality { get; }

        /// <summary>构造重组完成的 AIS 载荷。</summary>
        public AssembledAisPayload(
            int firstLineNumber,
            string combinedRawSentences,
            string payload,
            int fillBits,
            DateTimeOffset? extractedTimestampUtc,
            TimeQuality timeQuality)
        {
            FirstLineNumber = firstLineNumber;
            CombinedRawSentences = combinedRawSentences;
            Payload = payload;
            FillBits = fillBits;
            ExtractedTimestampUtc = extractedTimestampUtc;
            TimeQuality = timeQuality;
        }
    }

    /// <summary>
    /// NMEA 多片段报文重组器（按信道 + 顺序消息 ID + 片段总数缓存，支持乱序重组、超时淘汰与容量上限控制）。
    /// </summary>
    public sealed class NmeaMultiSentenceAssembler
    {
        private sealed class Bucket
        {
            public readonly string Key;
            public readonly int FragmentCount;
            public readonly ParsedNmeaSentence[] Fragments;
            public readonly bool[] Received;
            public int ReceivedCount;
            public DateTimeOffset FirstTimestampUtc;
            public bool HasTimestamp;
            public int FirstLineNumber;

            public Bucket(string key, int fragmentCount, int firstLineNumber, DateTimeOffset? ts)
            {
                Key = key;
                FragmentCount = fragmentCount;
                Fragments = new ParsedNmeaSentence[fragmentCount];
                Received = new bool[fragmentCount];
                ReceivedCount = 0;
                FirstLineNumber = firstLineNumber;
                HasTimestamp = ts.HasValue;
                FirstTimestampUtc = ts.GetValueOrDefault();
            }
        }

        private readonly Dictionary<string, Bucket> _buckets = new Dictionary<string, Bucket>(StringComparer.Ordinal);
        private readonly List<string> _insertionOrder = new List<string>();
        private readonly double _timeoutSeconds;
        private readonly int _maxCachedBuckets;

        /// <summary>构造多片段重组器。</summary>
        public NmeaMultiSentenceAssembler(double timeoutSeconds = 5.0, int maxCachedBuckets = 64)
        {
            _timeoutSeconds = timeoutSeconds;
            _maxCachedBuckets = Math.Max(4, maxCachedBuckets);
        }

        /// <summary>压入单句已解析的 NMEA 语句；若单句即完整或多句已凑齐则返回 true。</summary>
        public bool Push(
            ParsedNmeaSentence sentence,
            List<RejectedSample> errorCollector,
            out AssembledAisPayload assembled)
        {
            assembled = default(AssembledAisPayload);

            if (sentence.FragmentCount == 1)
            {
                assembled = new AssembledAisPayload(
                    sentence.LineNumber,
                    sentence.RawLine,
                    sentence.Payload,
                    sentence.FillBits,
                    sentence.ExtractedTimestampUtc,
                    sentence.TimeQuality);
                return true;
            }

            if (sentence.ExtractedTimestampUtc.HasValue)
            {
                EvictTimedOutBuckets(sentence.ExtractedTimestampUtc.Value, errorCollector);
            }

            string key = string.Format(
                CultureInfo.InvariantCulture,
                "{0}|{1}|{2}",
                sentence.Channel.ToUpperInvariant(),
                sentence.SequentialMessageId,
                sentence.FragmentCount);

            int slot = sentence.FragmentNumber - 1;
            Bucket bucket;
            if (_buckets.TryGetValue(key, out bucket))
            {
                if (bucket.Received[slot])
                {
                    FlushBucketAsRejected(bucket, "Duplicate or collided fragment before completion.", errorCollector);
                    RemoveBucket(key);
                    bucket = null;
                }
            }

            if (bucket == null)
            {
                while (_buckets.Count >= _maxCachedBuckets && _insertionOrder.Count > 0)
                {
                    string oldestKey = _insertionOrder[0];
                    Bucket oldest;
                    if (_buckets.TryGetValue(oldestKey, out oldest))
                    {
                        FlushBucketAsRejected(oldest, "Multi-sentence cache capacity exceeded.", errorCollector);
                    }
                    RemoveBucket(oldestKey);
                }

                bucket = new Bucket(key, sentence.FragmentCount, sentence.LineNumber, sentence.ExtractedTimestampUtc);
                _buckets[key] = bucket;
                _insertionOrder.Add(key);
            }

            bucket.Fragments[slot] = sentence;
            bucket.Received[slot] = true;
            bucket.ReceivedCount++;

            if (bucket.ReceivedCount < bucket.FragmentCount)
            {
                return false;
            }

            RemoveBucket(key);
            StringBuilder payloadSb = new StringBuilder();
            StringBuilder rawSb = new StringBuilder();
            DateTimeOffset? firstTs = null;
            TimeQuality bestQuality = TimeQuality.Estimated;
            int firstLine = bucket.Fragments[0].LineNumber;

            for (int i = 0; i < bucket.FragmentCount; i++)
            {
                ParsedNmeaSentence frag = bucket.Fragments[i];
                payloadSb.Append(frag.Payload);
                if (i > 0)
                {
                    rawSb.Append('\n');
                }
                rawSb.Append(frag.RawLine);
                if (!firstTs.HasValue && frag.ExtractedTimestampUtc.HasValue)
                {
                    firstTs = frag.ExtractedTimestampUtc;
                    bestQuality = frag.TimeQuality;
                }
            }

            int lastFillBits = bucket.Fragments[bucket.FragmentCount - 1].FillBits;
            assembled = new AssembledAisPayload(
                firstLine,
                rawSb.ToString(),
                payloadSb.ToString(),
                lastFillBits,
                firstTs,
                bestQuality);
            return true;
        }

        /// <summary>流结束时将所有未凑齐的残缺多句片段记入拒绝列表并清空缓存。</summary>
        public void FlushRemaining(List<RejectedSample> errorCollector)
        {
            for (int i = 0; i < _insertionOrder.Count; i++)
            {
                Bucket bucket;
                if (_buckets.TryGetValue(_insertionOrder[i], out bucket))
                {
                    FlushBucketAsRejected(bucket, "Incomplete multi-sentence AIS message at end of stream.", errorCollector);
                }
            }
            _buckets.Clear();
            _insertionOrder.Clear();
        }

        private void EvictTimedOutBuckets(DateTimeOffset currentTs, List<RejectedSample> errorCollector)
        {
            for (int i = _insertionOrder.Count - 1; i >= 0; i--)
            {
                string key = _insertionOrder[i];
                Bucket bucket;
                if (_buckets.TryGetValue(key, out bucket) && bucket.HasTimestamp)
                {
                    double elapsed = Math.Abs((currentTs - bucket.FirstTimestampUtc).TotalSeconds);
                    if (elapsed > _timeoutSeconds)
                    {
                        FlushBucketAsRejected(bucket, "Multi-sentence AIS message timed out (>5s).", errorCollector);
                        RemoveBucket(key);
                    }
                }
            }
        }

        private void RemoveBucket(string key)
        {
            _buckets.Remove(key);
            _insertionOrder.Remove(key);
        }

        private static void FlushBucketAsRejected(Bucket bucket, string reasonDetail, List<RejectedSample> errorCollector)
        {
            if (errorCollector == null)
            {
                return;
            }
            for (int i = 0; i < bucket.FragmentCount; i++)
            {
                if (bucket.Received[i])
                {
                    ParsedNmeaSentence s = bucket.Fragments[i];
                    errorCollector.Add(new RejectedSample(
                        s.LineNumber,
                        SimTime.Zero,
                        new GeoCoord(181.0, 91.0, 0.0),
                        102.3f,
                        360.0f,
                        RejectReason.OutOfOrder,
                        reasonDetail));
                }
            }
        }
    }
}
