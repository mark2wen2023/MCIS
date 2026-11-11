using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.W18.HF.Tests.RestHourTests;

namespace Mcis.W18.HF.Tests
{
    /// <summary>W18.1：D06（21:25 复裁：总量规则严格任意窗口；拆分规则按完整休息段、对齐窗口）与 D07（只读副本）。全部为合成数据（虚构）。</summary>
    public class W18_1Tests
    {
        private static readonly RestHourRules RestOnly = new RestHourRules { ApplyWorkHourLimits = false };

        internal static RestHourReport Run(double recordHours, params (double, double)[] rest)
        {
            var s = WorkRestSchedule.FromRest(H(0), H(recordHours), rest.Select(p => (H(p.Item1), H(p.Item2))));
            Assert.True(s.IsSuccess, s.ErrorCode);
            var r = new RestHourChecker(RestOnly).Check(s.Value);
            Assert.True(r.IsSuccess, r.ErrorCode);
            return r.Value;
        }

        // ---------- D06（21:25 复裁：方案 C 规范化）----------
        // 总量规则（Rest24h / Rest7d）：严格任意窗口，截断部分按窗口内长度。
        // 拆分规则（LongestRest / RestSplit）：按完整休息段判定——只在休息段起止点对齐的 24h 窗口上评估，与窗口相交的休息段按全长计。

        private static List<(double, double)> DailyH(int days, params (double s, double e)[] pattern)
        {
            var list = new List<(double, double)>();
            for (int d = 0; d < days; d++)
            {
                foreach (var p in pattern)
                {
                    list.Add((d * 24 + p.s, d * 24 + p.e));
                }
            }

            return list;
        }

        private static bool IsSplit(RestHourViolation v) { return v.Rule == RestRule.LongestRest || v.Rule == RestRule.RestSplit; }

        [Fact]
        public void C_Daily6Plus4_IsCompliant()
        {
            var rest = DailyH(4, (1, 7), (13, 17));
            var rep = Run(96, rest.ToArray());
            Assert.True(rep.IsCompliant, string.Join("; ", rep.Violations.Concat(rep.InsufficientData).Select(v => v.Detail)));
            AssertMatchesBruteForce(rep, 96, rest);
        }

        [Fact]
        public void C_DailyContiguous10h_IsCompliant()
        {
            var rest = DailyH(3, (8, 18));
            var rep = Run(72, rest.ToArray());
            Assert.True(rep.IsCompliant, string.Join("; ", rep.Violations.Concat(rep.InsufficientData).Select(v => v.Detail)));
            AssertMatchesBruteForce(rep, 72, rest);
        }

        [Fact]
        public void C_Longest5h59m_IsLongestRestViolation_ActualIsFullSegment()
        {
            var rest = DailyH(3, (1, 7 - 1.0 / 60), (13, 17 + 1.0 / 60));
            var rep = Run(72, rest.ToArray());
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.Rest24h);
            var lr = rep.Violations.Where(v => v.Rule == RestRule.LongestRest).ToList();
            Assert.NotEmpty(lr);
            Assert.All(lr, v => Assert.Equal(TimeSpan.FromMinutes(359), v.Actual));
            Assert.Equal(H(0), lr.Min(v => v.ViolatingFrom));
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.RestSplit);
            AssertMatchesBruteForce(rep, 72, rest);
        }

        [Fact]
        public void C_OldD06Counterexample_FullSixHourSegment_NoLongestRest()
        {
            // 原 D06 反例：[24,30) 恰 6h。按完整段判定，被窗口截短也按 6h 计 → 不报 LongestRest。
            var rest = new[] { (12.0, 18.0), (24.0, 30.0), (36.0, 41.0), (46.0, 51.0), (52.0, 60.0), (70.0, 80.0), (88.0, 96.0) };
            var rep = Run(96, rest);
            Assert.DoesNotContain(rep.Violations, IsSplit);
            AssertMatchesBruteForce(rep, 96, rest);
        }

        [Fact]
        public void C_TotalRuleStaysStrict_SplitRuleUsesFullSegments()
        {
            // [2,10) 与 [28,36)：窗口 [7,31) 内只有 3h+3h → Rest24h（严格任意窗口）违规；
            // 两段完整长度都是 8h → 拆分规则不报。
            var rest = new[] { (2.0, 10.0), (28.0, 36.0) };
            var rep = Run(48, rest);
            var r24 = Assert.Single(rep.Violations, v => v.Rule == RestRule.Rest24h);
            Assert.True(r24.ViolatingFrom <= H(7) && H(7) <= r24.ViolatingTo);
            Assert.Equal(TimeSpan.FromHours(6), r24.Actual);
            Assert.DoesNotContain(rep.Violations, IsSplit);
            AssertMatchesBruteForce(rep, 48, rest);
        }

        [Fact]
        public void C_Daily5Plus5_LongestRestOnly()
        {
            var rest = DailyH(3, (1, 6), (13, 18));
            var rep = Run(72, rest.ToArray());
            Assert.All(rep.Violations.Where(v => v.Rule == RestRule.LongestRest), v => Assert.Equal(TimeSpan.FromHours(5), v.Actual));
            Assert.Contains(rep.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.RestSplit);
            AssertMatchesBruteForce(rep, 72, rest);
        }

        [Fact]
        public void C_Daily6Plus2Plus2_RestSplitOnly_TopTwo8h()
        {
            var rest = DailyH(3, (6, 12), (15, 17), (20, 22));
            var rep = Run(72, rest.ToArray());
            Assert.DoesNotContain(rep.Violations, v => v.Rule == RestRule.LongestRest);
            var rs = rep.Violations.Where(v => v.Rule == RestRule.RestSplit).ToList();
            Assert.NotEmpty(rs);
            var g = Assert.Single(rs); // 全部对齐窗口相邻违规 → 一组
            Assert.Equal(TimeSpan.FromHours(8), g.Actual);
            Assert.Equal(H(0), g.ViolatingFrom);
            Assert.Equal(H(48), g.ViolatingTo);
            Assert.Equal(H(0), g.WindowStart); // 同值取最早
            AssertMatchesBruteForce(rep, 72, rest);
        }

        [Fact]
        public void C_NonAdjacentViolatingWindows_AreSeparateGroups()
        {
            // 第一天 4+3+3（RestSplit 7h），之后每天 6+4（合规）：只有前几个对齐窗口违规，归为一组。
            var rest = new List<(double, double)> { (6, 10), (14, 17), (20, 23) };
            rest.AddRange(DailyH(3, (1, 7), (13, 17)).Select(p => (p.Item1 + 24, p.Item2 + 24)));
            var rep = Run(96, rest.ToArray());
            // 对齐窗口：t=0 → 4+3+3（7h，违规）；t=6 → 再吃进次日完整 6h 段（合规）；t=10 → 3+3+6（9h，违规）。不相邻 → 两组。
            var rs = rep.Violations.Where(v => v.Rule == RestRule.RestSplit).OrderBy(v => v.ViolatingFrom).ToList();
            Assert.Equal(2, rs.Count);
            Assert.Equal((H(0), H(0), TimeSpan.FromHours(7)), (rs[0].ViolatingFrom, rs[0].ViolatingTo, rs[0].Actual));
            Assert.Equal((H(10), H(10), TimeSpan.FromHours(9)), (rs[1].ViolatingFrom, rs[1].ViolatingTo, rs[1].Actual));
            Assert.Equal(H(0), rs[0].WindowStart);
            Assert.Equal(H(24), rs[0].WindowEnd);
            AssertMatchesBruteForce(rep, 96, rest);
        }

        [Fact]
        public void C_RandomSchedules_MatchReference()
        {
            var rng = new Random(20261111);
            for (int n = 0; n < 80; n++)
            {
                double record = 48 + rng.Next(0, 3) * 24;
                var rest = new List<(double, double)>();
                double t = 1 + rng.Next(0, 4) * 0.25; // 首段不贴记录起点（避开乐观视图首尾特例）
                while (true)
                {
                    double len = 0.5 + rng.Next(0, 34) * 0.25; // 0.5h–8.75h，15 分钟粒度
                    if (t + len > record - 1)
                    {
                        break;
                    }

                    rest.Add((t, t + len));
                    t += len + 0.5 + rng.Next(0, 40) * 0.25;
                }

                if (rest.Count == 0)
                {
                    continue;
                }

                AssertMatchesBruteForce(Run(record, rest.ToArray()), record, rest);
            }
        }

        [Fact]
        public void C_RestOnlyEarly_LastWindowStillEvaluated()
        {
            // 72h 记录只有首日 1–7、13–17 休息：对齐窗口 7、13、17 及末窗口 48（无休息）都报 LongestRest，归为一组到 48。
            var rest = new[] { (1.0, 7.0), (13.0, 17.0) };
            var rep = Run(72, rest);
            var lr = Assert.Single(rep.Violations, v => v.Rule == RestRule.LongestRest);
            Assert.Equal(H(7), lr.ViolatingFrom);
            Assert.Equal(H(48), lr.ViolatingTo);
            Assert.Equal(TimeSpan.Zero, lr.Actual);
            AssertMatchesBruteForce(rep, 72, rest);
        }

        [Fact]
        public void C_RestTouchingRecordEnd_OptimisticUnknownLength_IsInsufficientNotViolation()
        {
            // 记录恰 24h：19–24 的休息可能延续到记录之后，乐观视图视为足够长 → LongestRest 只进数据不足。
            var rep = Run(24, (3, 5), (10, 14), (19, 24));
            Assert.DoesNotContain(rep.Violations, x => x.Rule == RestRule.LongestRest);
            Assert.Contains(rep.InsufficientData, x => x.Rule == RestRule.LongestRest);
        }

        [Fact]
        public void C_NoRestAtAll_TotalRuleOnly_NoSplitRule()
        {
            var s = WorkRestSchedule.FromWork(H(0), H(48), new[] { (H(0), H(48)) });
            Assert.True(s.IsSuccess, s.ErrorCode);
            Assert.Empty(s.Value.RestPeriods);
            var rep = new RestHourChecker(RestOnly).Check(s.Value).Value;
            Assert.Contains(rep.Violations, v => v.Rule == RestRule.Rest24h);
            Assert.DoesNotContain(rep.Violations.Concat(rep.InsufficientData), IsSplit);
        }

        [Fact]
        public void C_Assumptions_StateSplitRuleSemantics()
        {
            var rep = Run(24, (1, 7), (13, 17));
            Assert.Contains(rep.Assumptions, a => a.Contains("拆分规则按完整休息段判定，不是严格的任意窗口"));
            Assert.Contains(rep.Assumptions, a => a.Contains("任意 24h") && a.Contains("任意 7d"));
            Assert.Contains(RestHourAssumptions.SplitRuleByFullSegment, rep.Assumptions);
            Assert.Throws<NotSupportedException>(() => ((IList<string>)rep.Assumptions).Clear());
        }

        /// <summary>
        /// 对照：总量规则（Rest24h/Rest7d）用 1 分钟步进的严格任意窗口暴力法；
        /// 拆分规则用独立参考实现（按分钟栅格重建休息段，对齐窗口 = 各段起止点（裁剪到 [记录首, 记录尾−24h]）∪ {记录首, 记录尾−24h}，相交段按全长计）。
        /// 每个对齐窗口起点：参考判违规 ⇔ 落在某条 C# 违规的 [From, To] 内；每条违规的 Actual = 组内参考值的最小值。
        /// </summary>
        internal static void AssertMatchesBruteForce(RestHourReport rep, double record, IEnumerable<(double, double)> restH)
        {
            var restList = restH.ToList();
            var rest = restList.Select(p => (H(p.Item1), H(p.Item2))).ToList();
            AssertRollingMatches(rep, record, rest, 24, TimeSpan.FromHours(10), RestRule.Rest24h);
            AssertRollingMatches(rep, record, rest, 168, TimeSpan.FromHours(77), RestRule.Rest7d);
            AssertSplitMatchesReference(rep, record, restList);
        }

        private static void AssertSplitMatchesReference(RestHourReport rep, double record, List<(double, double)> restH)
        {
            int total = (int)Math.Round(record * 60);
            int day = 24 * 60;
            var lr = rep.Violations.Where(v => v.Rule == RestRule.LongestRest).ToList();
            var rs = rep.Violations.Where(v => v.Rule == RestRule.RestSplit).ToList();
            if (total < day)
            {
                Assert.Empty(lr);
                Assert.Empty(rs);
                return;
            }

            var resting = new bool[total];
            foreach (var (a, b) in restH)
            {
                for (int m = (int)Math.Round(a * 60); m < (int)Math.Round(b * 60); m++)
                {
                    resting[m] = true;
                }
            }

            var segs = new List<(int s, int e)>();
            for (int m = 0; m < total; m++)
            {
                if (resting[m] && (m == 0 || !resting[m - 1]))
                {
                    int e = m;
                    while (e < total && resting[e])
                    {
                        e++;
                    }

                    segs.Add((m, e));
                }
            }

            int last = total - day;
            var starts = new SortedSet<int> { 0, last };
            foreach (var (a, b) in segs)
            {
                starts.Add(Math.Min(a, last));
                starts.Add(Math.Min(b, last));
            }

            var lrVals = new Dictionary<RestHourViolation, int>();
            var rsVals = new Dictionary<RestHourViolation, int>();
            foreach (int w in starts)
            {
                var lens = segs.Where(x => x.e > w && x.s < w + day).Select(x => x.e - x.s).OrderByDescending(x => x).ToList();
                int longest = lens.Count > 0 ? lens[0] : 0;
                int top2 = lens.Take(2).Sum();
                int sum = lens.Sum();
                bool refLr = segs.Count > 0 && longest < 6 * 60;
                bool refRs = sum >= 10 * 60 && top2 < 10 * 60;
                DateTimeOffset t = H(0).AddMinutes(w);
                string ctx = "record=" + record + "h rest=" + string.Join(",", restH.Select(p => "[" + p.Item1 + "," + p.Item2 + ")")) + " w=" + (w / 60.0) + "h";
                var inLr = lr.Where(v => v.ViolatingFrom <= t && t <= v.ViolatingTo).ToList();
                var inRs = rs.Where(v => v.ViolatingFrom <= t && t <= v.ViolatingTo).ToList();
                Assert.True(refLr == (inLr.Count > 0), "LongestRest 不一致 ref=" + refLr + " " + ctx);
                Assert.True(refRs == (inRs.Count > 0), "RestSplit 不一致 ref=" + refRs + " " + ctx);
                foreach (var v in inLr)
                {
                    lrVals[v] = lrVals.TryGetValue(v, out int g) ? Math.Min(g, longest) : longest;
                }

                foreach (var v in inRs)
                {
                    rsVals[v] = rsVals.TryGetValue(v, out int g) ? Math.Min(g, top2) : top2;
                }
            }

            foreach (var kv in lrVals.Concat(rsVals))
            {
                Assert.Equal(TimeSpan.FromMinutes(kv.Value), kv.Key.Actual);
            }

            foreach (var v in lr.Concat(rs))
            {
                Assert.True(v.Actual < v.Limit, v.Detail);
                Assert.Equal(v.WindowStart.AddHours(24), v.WindowEnd);
                Assert.True(v.ViolatingFrom <= v.WindowStart && v.WindowStart <= v.ViolatingTo, v.Detail);
                Assert.True(lrVals.ContainsKey(v) || rsVals.ContainsKey(v), "违规组不含任何对齐窗口：" + v.Detail);
            }
        }

        /// <summary>滚动总量规则（Rest24h/Rest7d）暴力对照：漏报 / 范围内部误报 / 最差值。</summary>
        private static void AssertRollingMatches(RestHourReport rep, double record, List<(DateTimeOffset, DateTimeOffset)> rest, double windowH, TimeSpan limit, RestRule rule)
        {
            var vs = rep.Violations.Where(v => v.Rule == rule).ToList();
            if (record < windowH)
            {
                Assert.Empty(vs);
                return;
            }

            for (DateTimeOffset w = H(0); w <= H(record - windowH); w = w.AddMinutes(1))
            {
                TimeSpan total = TimeSpan.Zero;
                foreach (var (a, b) in rest)
                {
                    var lo = a > w ? a : w;
                    var hi = b < w.AddHours(windowH) ? b : w.AddHours(windowH);
                    if (hi > lo)
                    {
                        total += hi - lo;
                    }
                }

                bool brute = total < limit;
                Assert.True(!brute || vs.Any(v => v.ViolatingFrom <= w && w <= v.ViolatingTo), rule + " 漏报 w=" + (w - H(0)).TotalHours);
                Assert.True(brute || !vs.Any(v => v.ViolatingFrom < w && w < v.ViolatingTo), rule + " 误报 w=" + (w - H(0)).TotalHours);
                Assert.True(!brute || vs.Any(v => v.ViolatingFrom <= w && w <= v.ViolatingTo && v.Actual <= total), rule + " 最差值偏大 w=" + (w - H(0)).TotalHours);
            }
        }

        [Fact]
        public void D06_RandomLongSchedules_Rolling7dAnd24h_MatchBruteForce()
        {
            var rng = new Random(77);
            for (int n = 0; n < 6; n++)
            {
                double record = 170 + rng.Next(0, 4) * 7.25; // 非周期
                var rest = new List<(double, double)>();
                double t = 1.25;
                while (true)
                {
                    double len = 1 + rng.Next(0, 40) * 0.25;
                    if (t + len > record - 1)
                    {
                        break;
                    }

                    rest.Add((t, t + len));
                    t += len + 0.75 + rng.Next(0, 44) * 0.25;
                }

                AssertMatchesBruteForce(Run(record, rest.ToArray()), record, rest);
            }
        }

        [Fact]
        public void D06_Rest7d_SlopeChangeAtBoundaryMinus7d_RangeExact()
        {
            // 7d 窗口 [t, t+168)，t ∈ [0, 2]：左缘丢掉 [0,1)，右缘在 t > 0.5（= 168.5 − 7d）后吃进 [168.5,170)。
            // 中间休息 76.25h → 总量 77.25−t（t≤0.5）、76.75（0.5≤t≤1）、75.75+t（t≥1）；< 77h ⇔ 0.25 < t < 1.25。
            var rest = new List<(double, double)> { (0, 1) };
            for (int k = 0; k < 7; k++) { rest.Add((3 + 24 * k, 13 + 24 * k)); }
            rest.Add((160, 166.25));
            rest.Add((168.5, 170));
            var rep = Run(170, rest.ToArray());
            var v = Assert.Single(rep.Violations, x => x.Rule == RestRule.Rest7d);
            Assert.Equal(H(0.25), v.ViolatingFrom);
            Assert.Equal(H(1.25), v.ViolatingTo);
            Assert.Equal(TimeSpan.FromHours(76.75), v.Actual);
        }

        [Fact]
        public void D06_WorkRule_UsesWorkBoundaries_WhenUnknownPresent()
        {
            // 0–2 未标注，2–18 工作 16h，18–20 未标注，20–30 休息，30–48 未标注（虚构）。确认视图只计已标注工作：
            // 窗口工作量 = |[2,18) ∩ [t,t+24)|，t ≤ 2 时 16h，之后 18−t；> 14h ⇔ t < 4。
            var s = WorkRestSchedule.Create(H(0), H(48), new[]
            {
                new DutyInterval(H(2), H(18), DutyKind.Work),
                new DutyInterval(H(20), H(30), DutyKind.Rest),
            }).Value;
            var rep = new RestHourChecker(new RestHourRules()).Check(s).Value;
            var v = Assert.Single(rep.Violations, x => x.Rule == RestRule.Work24h);
            Assert.Equal(H(0), v.ViolatingFrom);
            Assert.Equal(H(4), v.ViolatingTo);
            Assert.Equal(TimeSpan.FromHours(16), v.Actual);
        }

        [Fact]
        public void D06_RecordEdgeRest_OptimisticUnknownLength_IsInsufficientNotViolation()
        {
            // 记录恰 24h，唯一窗口 [0,24)：0–5 的休息可能更早开始（被记录起点截断），乐观视图视为足够长 → LongestRest 只进数据不足。
            var rep = Run(24, (0, 5), (9, 13), (17, 19));
            Assert.DoesNotContain(rep.Violations, x => x.Rule == RestRule.LongestRest);
            Assert.Contains(rep.InsufficientData, x => x.Rule == RestRule.LongestRest);
        }

        // ---------- D07 ----------

        [Fact]
        public void D07_Findings_ReadOnlySnapshot()
        {
            var a = new HfacsAnalysis("虚构对象");
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            var view = a.Findings;
            var list = Assert.IsAssignableFrom<IList<HfacsFinding>>(view);
            Assert.True(list.IsReadOnly);
            Assert.Throws<NotSupportedException>(() => list.Clear());
            Assert.Throws<NotSupportedException>(() => list.Add(view[0]));
            Assert.Single(a.Findings);
            Assert.True(a.AddFinding("F2", "UA-ERR-SKL", "d", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            Assert.Single(view); // 副本：之后的新增不影响已取出的视图
            Assert.Equal(2, a.Findings.Count);
        }

        [Fact]
        public void D07_Items_ReadOnlySnapshot()
        {
            var c = BrmChecklist.CreateDefault("虚构值班组");
            var view = c.Items;
            var list = Assert.IsAssignableFrom<IList<BrmItem>>(view);
            Assert.True(list.IsReadOnly);
            Assert.Throws<NotSupportedException>(() => list.Clear());
            Assert.Throws<NotSupportedException>(() => list.RemoveAt(0));
            Assert.Equal(6, c.Items.Count);
            Assert.NotSame(c.Items, c.Items);
            Assert.True(c.AddItem("BRM-X1", "虚构核查项", "沟通").IsSuccess);
            Assert.Equal(6, view.Count); // 副本：之后的新增不影响已取出的视图
            Assert.Equal(7, c.Items.Count);
        }
    }
}
