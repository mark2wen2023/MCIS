using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>
    /// W18.1 复测补测（21:25 复裁）：Assumptions 口径、记录首/尾−24h 窗口是否误判截断段、
    /// 以及 b1_bruteforce.py 完整段模式对 ≥200 组随机排班（含 6h/14h 边界与 ±1 分钟）的对照。合成数据（虚构）。
    /// </summary>
    public sealed class RetestW181AcceptanceTests
    {
        [Fact]
        public void Assumptions_Match21_25Ruling()
        {
            var rep = Check(Rest(24, P(1, 7), P(13, 17)), RestOnly());
            Assert.Contains(rep.Assumptions, a => a.Contains("拆分规则按完整休息段判定，不是严格的任意窗口"));
            Assert.Contains(rep.Assumptions, a => a.Contains("任意 24h") && a.Contains("任意 7d") && a.Contains("严格的任意窗口"));
            Assert.Contains(rep.Assumptions, a => a.Contains("间隔") && a.Contains("14h") && a.Contains("完整休息段"));
            Assert.Contains(rep.Assumptions, a => a.Contains("记录首尾") || (a.Contains("未标注") && a.Contains("数据不足")));
            Assert.Equal(RestHourAssumptions.CreateDefaultList(), rep.Assumptions.ToList());
            Assert.Contains(RestHourAssumptions.SplitRuleByFullSegment, rep.Assumptions);
            Assert.Throws<NotSupportedException>(() => ((IList<string>)rep.Assumptions).Clear());
        }

        [Fact]
        public void RecordEdgeWindows_DoNotFalselyViolate_TruncatedRests()
        {
            // 记录恰 24h：记录首与记录尾−24h 是同一窗口。
            // 首段 [0, 5h59m)、尾段 [18h01m, 24) 被记录截断，中间完整 6h。
            // 乐观视图把首尾段视为足够长，不得报 LongestRest 违规；悲观按观测长度才报，只进 InsufficientData。
            // 中间段也不足 6h，悲观最长 5h59m；用分钟对齐避免 AddHours(n/60) 的浮点误差。
            var r24 = Check(FromMinutes(24 * 60, (0, 5 * 60 + 59), (10 * 60, 15 * 60), (18 * 60 + 1, 24 * 60)), RestOnly());
            Assert.DoesNotContain(r24.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.Contains(r24.InsufficientData, v => v.Rule == RestRule.LongestRest);
            Assert.All(r24.InsufficientData.Where(v => v.Rule == RestRule.LongestRest), v =>
            {
                Assert.Equal(T0, v.WindowStart);
                Assert.Equal(T0.AddHours(24), v.WindowEnd);
            });

            // 48h 记录：短首段 [0, 5h59m) + 完整 6h [20,26)。
            // 记录首窗口乐观不因 5h59m 报违规；记录尾−24h（t=24）与 [20,26) 相交按全长 6h，不得因首段截断误报。
            var r48 = Check(FromMinutes(48 * 60, (0, 5 * 60 + 59), (20 * 60, 26 * 60)), RestOnly());
            Assert.DoesNotContain(r48.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.DoesNotContain(r48.InsufficientData, v => v.Rule == RestRule.LongestRest);

            // 贴记录尾的 5h59m，另有不贴边的 5h 段：乐观足够长，悲观最长 < 6h → 只进数据不足。
            var rEnd = Check(FromMinutes(24 * 60, (60, 6 * 60), (18 * 60 + 1, 24 * 60)), RestOnly());
            Assert.DoesNotContain(rEnd.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.Contains(rEnd.InsufficientData, v => v.Rule == RestRule.LongestRest);
        }

        /// <summary>
        /// 记录尾被截断的短休息使记录尾−24h 窗口仅在悲观视图下报 LongestRest，
        /// 但该窗口与更早的确定违规对齐窗口相邻，整组被记为违规，边界窗口没有 InsufficientData 痕迹。
        /// </summary>
        [Fact]
        public void W18_D08_EdgeWindow_AbsorbedIntoAdjacentViolationGroup()
        {
            // W18.2独立验收已验证：记录尾−24h 窗口结论取决于被截断的 5h59m 段，应进 InsufficientData，不应被相邻确定违规组吞掉。
            var rep = Check(FromMinutes(48 * 60, (4 * 60, 10 * 60), (42 * 60 + 1, 48 * 60)), RestOnly());
            var t24 = T0.AddHours(24);
            Assert.Contains(rep.InsufficientData, v => v.Rule == RestRule.LongestRest && v.ViolatingFrom <= t24 && t24 <= v.ViolatingTo);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest && v.ViolatingFrom <= t24 && t24 <= v.ViolatingTo);
        }

        [Fact]
        public void Boundaries_6h_And_14h_PlusMinusOneMinute()
        {
            Assert.True(Check(Rest(48, P(1, 7), P(13, 17), P(25, 31), P(37, 41)), RestOnly()).IsCompliant);
            Assert.True(Check(Rest(48, P(8, 18), P(32, 42)), RestOnly()).IsCompliant);

            var shortLongest = Check(FromMinutes(48 * 60,
                (60, 7 * 60 - 1), (13 * 60, 17 * 60 + 1),
                (25 * 60, 31 * 60 - 1), (37 * 60, 41 * 60 + 1)), RestOnly());
            Assert.NotEmpty(Of(shortLongest, RestRule.LongestRest));
            Assert.All(Of(shortLongest, RestRule.LongestRest), v => Assert.Equal(TimeSpan.FromMinutes(359), v.Actual));
            Assert.DoesNotContain(Of(shortLongest, RestRule.RestSplit), _ => true);

            // 24h 记录只有记录首窗口，6h01m 最长段应合规（48h 会在后半无休息的对齐窗口上另报 LongestRest）。
            var plus = Check(FromMinutes(24 * 60, (60, 7 * 60 + 1), (13 * 60, 17 * 60 - 1)), RestOnly());
            Assert.DoesNotContain(Of(plus, RestRule.LongestRest), _ => true);

            // 间隔恰好 14h 合规；14h+1min 违规；14h−1min 合规。
            var exact = Check(FromMinutes(48 * 60, (60, 7 * 60), (21 * 60, 27 * 60)), RestOnly());
            Assert.DoesNotContain(Of(exact, RestRule.RestInterval), _ => true);
            var over = Check(FromMinutes(48 * 60, (60, 7 * 60), (21 * 60 + 1, 27 * 60)), RestOnly());
            var iv = Assert.Single(Of(over, RestRule.RestInterval));
            Assert.Equal(TimeSpan.FromHours(14) + TimeSpan.FromMinutes(1), iv.Actual);
            var under = Check(FromMinutes(48 * 60, (60, 7 * 60), (21 * 60 - 1, 27 * 60)), RestOnly());
            Assert.DoesNotContain(Of(under, RestRule.RestInterval), _ => true);
        }

        [Fact]
        public void TwoHundredRandomSchedules_MatchPythonFullSegmentAndClippedTotal()
        {
            var cases = BuildCases();
            Assert.True(cases.Count >= 200, "cases=" + cases.Count);

            var payload = new
            {
                mode = "fullsegment",
                cases = cases.Select(c => new
                {
                    id = c.Id,
                    recordStart = T0.ToString("o"),
                    recordEnd = At(c.RecordHours).ToString("o"),
                    rest = c.Rest.Select(p => new[] { At(p.Item1).ToString("o"), At(p.Item2).ToString("o") }).ToArray(),
                    windowHours = 24,
                    minRestHours = 10,
                    minLongestHours = 6,
                    maxPeriods = 2,
                    maxIntervalHours = 14,
                    stepSeconds = 60
                }).ToArray()
            };

            using JsonDocument fullDoc = RunBruteForce(payload, "--mode", "fullsegment");
            Assert.Equal(cases.Count, fullDoc.RootElement.GetProperty("caseCount").GetInt32());

            var clippedPayload = new
            {
                mode = "clipped",
                cases = payload.cases
            };
            using JsonDocument clippedDoc = RunBruteForce(clippedPayload, "--mode", "clipped");

            int compared = 0;
            for (int i = 0; i < cases.Count; i++)
            {
                CaseSpec c = cases[i];
                var s = FromHoursRounded(c.RecordHours, c.Rest.ToArray());
                var rep = Check(s, RestOnly());
                var full = fullDoc.RootElement.GetProperty("cases")[i];
                CompareSplit(c, rep, full);
                CompareIntervals(c, rep, full);
                CompareTotal(c, rep, clippedDoc.RootElement.GetProperty("cases")[i]);
                compared++;
            }

            Assert.Equal(cases.Count, compared);
        }

        private static void CompareSplit(CaseSpec c, RestHourReport rep, JsonElement full)
        {
            var opt = full.GetProperty("optimistic");
            var pes = full.GetProperty("pessimistic");
            CompareRuleWindows(c, rep, RestRule.LongestRest, opt, pes, "LongestRest", "longestHours");
            CompareRuleWindows(c, rep, RestRule.RestSplit, opt, pes, "RestSplit", "topNHours");
        }

        private static void CompareRuleWindows(CaseSpec c, RestHourReport rep, RestRule rule, JsonElement opt, JsonElement pes, string flag, string valueName)
        {
            var viol = rep.Violations.Where(v => v.Rule == rule).ToList();
            var insuff = rep.InsufficientData.Where(v => v.Rule == rule).ToList();
            foreach (JsonElement w in pes.GetProperty("windows").EnumerateArray())
            {
                DateTimeOffset t = DateTimeOffset.Parse(w.GetProperty("start").GetString(), CultureInfo.InvariantCulture);
                int tm = Minutes(t - T0);
                bool pessFlag = HasFlag(w, flag);
                bool optFlag = OptimisticWindow(opt, w.GetProperty("start").GetString(), flag);
                double value = w.GetProperty(valueName).GetDouble();
                string ctx = c.Id + " " + flag + " t=" + tm + "min value=" + value;

                if (optFlag)
                {
                    var hit = viol.Where(v => Minutes(v.ViolatingFrom - T0) <= tm && tm <= Minutes(v.ViolatingTo - T0)).ToList();
                    Assert.True(hit.Count > 0, "C# 漏报违规 " + ctx + " " + Describe(rep));
                    Assert.True(hit.Any(v => Minutes(v.Actual) <= Minutes(TimeSpan.FromHours(value))), "C# Actual 偏大 " + ctx + " actual=" + string.Join(",", hit.Select(v => v.Actual)));
                }
                else if (pessFlag)
                {
                    var hitI = insuff.Where(v => Minutes(v.ViolatingFrom - T0) <= tm && tm <= Minutes(v.ViolatingTo - T0)).ToList();
                    var hitV = viol.Where(v => Minutes(v.ViolatingFrom - T0) <= tm && tm <= Minutes(v.ViolatingTo - T0)).ToList();
                    // W18.2: every pessimistic-only window must remain visible;
                    // overlap with a neighbouring definite group is not an exemption.
                    Assert.True(hitI.Count > 0, "C# 漏报数据不足 " + ctx + " " + Describe(rep));
                    Assert.Empty(hitV);
                }
                else
                {
                    Assert.DoesNotContain(viol, v => Minutes(v.ViolatingFrom - T0) <= tm && tm <= Minutes(v.ViolatingTo - T0));
                    Assert.DoesNotContain(insuff, v => Minutes(v.ViolatingFrom - T0) <= tm && tm <= Minutes(v.ViolatingTo - T0));
                }
            }

            foreach (var v in viol.Concat(insuff))
            {
                Assert.True(v.WindowStart.AddHours(24) == v.WindowEnd, v.Detail);
                Assert.True(v.ViolatingFrom <= v.WindowStart && v.WindowStart <= v.ViolatingTo, v.Detail);
            }
        }

        private static bool OptimisticWindow(JsonElement opt, string start, string flag)
        {
            foreach (JsonElement w in opt.GetProperty("windows").EnumerateArray())
            {
                if (w.GetProperty("start").GetString() == start)
                {
                    return HasFlag(w, flag);
                }
            }

            return false;
        }

        private static bool HasFlag(JsonElement window, string flag)
        {
            return window.GetProperty("violations").EnumerateArray().Any(x => x.GetString() == flag);
        }

        private static void CompareIntervals(CaseSpec c, RestHourReport rep, JsonElement full)
        {
            // FromRest 无未标注，乐观/悲观间隔相同，取悲观即可。
            var py = full.GetProperty("pessimistic").GetProperty("intervals")
                .EnumerateArray()
                .Select(x => (
                    From: DateTimeOffset.Parse(x.GetProperty("from").GetString(), CultureInfo.InvariantCulture),
                    To: DateTimeOffset.Parse(x.GetProperty("to").GetString(), CultureInfo.InvariantCulture),
                    Gap: TimeSpan.FromHours(x.GetProperty("gapHours").GetDouble())
                ))
                .OrderBy(x => x.From)
                .ToList();
            var cs = Of(rep, RestRule.RestInterval).OrderBy(v => v.WindowStart).ToList();
            Assert.True(py.Count == cs.Count, c.Id + " RestInterval 条数 python=" + py.Count + " csharp=" + cs.Count + " " + Describe(rep));
            for (int i = 0; i < py.Count; i++)
            {
                Assert.Equal(Minutes(py[i].From - T0), Minutes(cs[i].WindowStart - T0));
                Assert.Equal(Minutes(py[i].To - T0), Minutes(cs[i].WindowEnd - T0));
                Assert.Equal(Minutes(py[i].Gap), Minutes(cs[i].Actual));
            }
        }

        private static void CompareTotal(CaseSpec c, RestHourReport rep, JsonElement clipped)
        {
            var vs = Of(rep, RestRule.Rest24h).ToList();
            // 无未标注时总量规则不应进入 InsufficientData。
            Assert.Empty(OfInsufficient(rep, RestRule.Rest24h));
            foreach (JsonElement w in Rest24hWindows(clipped))
            {
                DateTimeOffset t = DateTimeOffset.Parse(w.GetProperty("start").GetString(), CultureInfo.InvariantCulture);
                bool brute = HasFlag(w, "Rest24h") || w.GetProperty("totalRestHours").GetDouble() < 10.0 - 1e-9;
                // clipped 输出只列出违规窗口；rest24hStartsHours 更完整。这里用 starts 列表。
            }

            if (clipped.TryGetProperty("rest24hStartsHours", out JsonElement starts))
            {
                var set = new HashSet<int>();
                foreach (JsonElement e in starts.EnumerateArray())
                {
                    int minutes = (int)Math.Round(e.GetDouble() * 60);
                    set.Add(minutes);
                    DateTimeOffset w = T0.AddMinutes(minutes);
                    bool hit = vs.Any(v => v.ViolatingFrom <= w && w <= v.ViolatingTo);
                    Assert.True(hit, c.Id + " Rest24h 漏报 w=" + e.GetDouble() + "h " + Describe(rep));
                }

                // 误报：违规开区间内的整分钟必须出现在暴力列表中。端点可能是插值限值点，用开区间。
                for (DateTimeOffset w = T0; w <= At(c.RecordHours - 24); w = w.AddMinutes(1))
                {
                    bool inside = vs.Any(v => v.ViolatingFrom < w && w < v.ViolatingTo);
                    if (!inside)
                    {
                        continue;
                    }

                    int minutes = (int)Math.Round((w - T0).TotalMinutes);
                    Assert.True(set.Contains(minutes), c.Id + " Rest24h 误报 w=" + (minutes / 60.0) + "h " + Describe(rep));
                }
            }
        }

        private static IEnumerable<JsonElement> Rest24hWindows(JsonElement clipped)
        {
            if (clipped.TryGetProperty("first", out JsonElement first)
                && first.TryGetProperty("Rest24h", out JsonElement sample)
                && sample.ValueKind == JsonValueKind.Object)
            {
                yield return sample;
            }
        }

        private static IEnumerable<RestHourViolation> OfInsufficient(RestHourReport r, RestRule rule) => r.InsufficientData.Where(v => v.Rule == rule);

        private static int Minutes(TimeSpan t) => (int)Math.Round(t.TotalMinutes);

        private static List<CaseSpec> BuildCases()
        {
            var list = new List<CaseSpec>();
            void Add(string id, double record, params (double, double)[] rest)
            {
                list.Add(new CaseSpec { Id = id, RecordHours = record, Rest = rest.ToList() });
            }

            // 固定边界与跨记录首尾
            Add("daily-6plus4", 96, Daily(4, (1, 7), (13, 17)));
            Add("daily-10h", 72, Daily(3, (8, 18)));
            Add("longest-5h59m", 72, Daily(3, (1, 7 - 1.0 / 60), (13, 17 + 1.0 / 60)));
            Add("longest-6h", 72, Daily(3, (1, 7), (13, 17)));
            Add("longest-6h01m", 48, (1, 7 + 1.0 / 60), (13, 17 - 1.0 / 60));
            Add("gap-14h", 48, (1, 7), (21, 27));
            Add("gap-14h-plus1", 48, (1, 7), (21 + 1.0 / 60, 27));
            Add("gap-14h-minus1", 48, (1, 7), (21 - 1.0 / 60, 27));
            Add("b1-96h", 96, (12, 18), (24, 30), (36, 41), (46, 51), (52, 60), (70, 80), (88, 96));
            Add("edge-24h-short-ends", 24, (0, 5 + 59.0 / 60), (10, 16), (18 + 1.0 / 60, 24));
            Add("edge-48h-start-plus-6h", 48, (0, 5 + 59.0 / 60), (20, 26));
            Add("edge-48h-end-short", 48, (4, 10), (42 + 1.0 / 60, 48));
            Add("edge-both-48h", 48, (0, 6), (20, 26), (42, 48));
            Add("record-exactly-24-continuous10", 24, (8, 18));
            Add("three-short-split", 72, Daily(3, (6, 12), (15, 17), (20, 22)));
            Add("total-strict-demo", 48, (2, 10), (28, 36));

            var rng = new Random(20261111);
            int n = 0;
            while (list.Count < 220)
            {
                n++;
                double record = 24 + rng.Next(0, 8) * 24; // 24h–192h
                if (n % 17 == 0)
                {
                    record = 24; // 加重记录首=记录尾−24h 的情况
                }

                bool touchStart = n % 5 == 0;
                bool touchEnd = n % 7 == 0;
                var rest = RandomRest(rng, record, touchStart, touchEnd, n % 11 == 0, n % 13 == 0);
                if (rest.Count == 0)
                {
                    continue;
                }

                Add("rng-" + n, record, rest.ToArray());
            }

            return list;
        }

        private static (double, double)[] Daily(int days, params (double s, double e)[] pattern)
        {
            var list = new List<(double, double)>();
            for (int d = 0; d < days; d++)
            {
                foreach (var p in pattern)
                {
                    list.Add((d * 24 + p.s, d * 24 + p.e));
                }
            }

            return list.ToArray();
        }

        private static List<(double, double)> RandomRest(Random rng, double record, bool touchStart, bool touchEnd, bool force6h, bool force14h)
        {
            var rest = new List<(double, double)>();
            double t = touchStart ? 0 : 1 + rng.Next(0, 8) * 0.25;
            int guard = 0;
            while (t < record - 0.5 && guard++ < 40)
            {
                double len;
                if (force6h && rest.Count == 0)
                {
                    int which = rng.Next(0, 3);
                    len = which == 0 ? 6 : which == 1 ? 6 - 1.0 / 60 : 6 + 1.0 / 60;
                }
                else
                {
                    len = 0.5 + rng.Next(0, 34) * 0.25;
                }

                if (t + len > record)
                {
                    if (touchEnd && t < record)
                    {
                        if (record - t >= 0.25)
                        {
                            rest.Add((t, record));
                        }
                    }

                    break;
                }

                rest.Add((t, t + len));
                double gap;
                if (force14h && rest.Count == 1)
                {
                    int which = rng.Next(0, 3);
                    gap = which == 0 ? 14 : which == 1 ? 14 + 1.0 / 60 : 14 - 1.0 / 60;
                }
                else
                {
                    gap = 0.5 + rng.Next(0, 40) * 0.25;
                }

                t += len + gap;
            }

            if (touchEnd && rest.Count > 0 && Math.Abs(rest[rest.Count - 1].Item2 - record) > 1e-9 && rest[rest.Count - 1].Item2 < record - 0.25)
            {
                double start = Math.Max(rest[rest.Count - 1].Item2 + 0.5, record - (2 + rng.Next(0, 8) * 0.25));
                if (start < record - 0.25)
                {
                    rest.Add((start, record));
                }
            }

            return rest;
        }

        private static DateTimeOffset At(double hours) => T0.AddMinutes(Math.Round(hours * 60.0, MidpointRounding.AwayFromZero));

        private static WorkRestSchedule FromMinutes(int recordMinutes, params (int, int)[] rest)
        {
            var r = WorkRestSchedule.FromRest(T0, T0.AddMinutes(recordMinutes), rest.Select(p => (T0.AddMinutes(p.Item1), T0.AddMinutes(p.Item2))));
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        private static WorkRestSchedule FromHoursRounded(double recordHours, params (double, double)[] rest)
        {
            var r = WorkRestSchedule.FromRest(T0, At(recordHours), rest.Select(p => (At(p.Item1), At(p.Item2))));
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        private sealed class CaseSpec
        {
            public string Id;
            public double RecordHours;
            public List<(double, double)> Rest;
        }
    }
}
