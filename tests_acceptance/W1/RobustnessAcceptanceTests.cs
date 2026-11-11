using System;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;
using static Mcis.Acceptance.W1.Fx;

namespace Mcis.Acceptance.W1
{
    /// <summary>时间带切分、输入健壮性、阈值配置、免责声明、确定性与规格覆盖验收。示例数据·虚构。</summary>
    public sealed class RobustnessAcceptanceTests
    {
        private static Ship CrossTgt() => CollisionTarget(45, 2828.4, 400);

        // ---------- 时间带 ----------

        /// <summary>时间带连续覆盖共同观测区间：首带起点=共同起点，末带终点=共同终点，相邻带首尾相接，相邻带分类不同。</summary>
        [Fact]
        public void TimeBands_ContiguousAndCoverOverlap()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 60).Run(450), CrossTgt().Run(450));
            Assert.Equal(0, r.TimeBands.First().StartTime.Seconds, 9);
            Assert.Equal(450, r.TimeBands.Last().EndTime.Seconds, 9);
            for (int i = 1; i < r.TimeBands.Count; i++)
            {
                Assert.Equal(r.TimeBands[i - 1].EndTime.Seconds, r.TimeBands[i].StartTime.Seconds, 9);
                var a = r.TimeBands[i - 1]; var b = r.TimeBands[i];
                Assert.False(a.Situation == b.Situation && a.OwnRole == b.OwnRole && a.TargetRole == b.TargetRole, "相邻时间带分类相同未合并");
            }
        }

        /// <summary>
        /// 局面随时间变化：交叉（有危险）→ 让路船右转 60° 后切出无危险带。复测按裁定 A5（DCPA&lt;1 nm 且 0&lt;TCPA≤720 s）改写预期：
        /// 独立公式（tests 外 Python 相对运动解析，logs/w1-retest-case4-calc.txt）得转向完成后 DCPA≈0.6378 nm &lt; 1 nm，
        /// 危险持续到 TCPA 过零 ≈ 277.1 s；采样网格 10 s → 解除于 [277, 280]。原 60–80 s 预期以旧 0.5 nm 阈值为前提，另用可配置阈值保留。
        /// </summary>
        [Fact]
        public void TimeBands_SplitWhenRiskEnds()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Order(60, 60).Run(450), CrossTgt().Run(450));
            Assert.Equal(new[] { EncounterSituation.Crossing, EncounterSituation.NoCollisionRisk }, r.TimeBands.Select(b => b.Situation).ToArray());
            Assert.InRange(r.TimeBands[0].EndTime.Seconds, 277.0, 280.0 + 1e-9);
            var legacy = Ok(new Ship(0, 0, 0, 5).Order(60, 60).Run(450), CrossTgt().Run(450), new ColregThresholds(collisionRiskDcpaNm: 0.5));
            Assert.Equal(new[] { EncounterSituation.Crossing, EncounterSituation.NoCollisionRisk }, legacy.TimeBands.Select(b => b.Situation).ToArray());
            Assert.InRange(legacy.TimeBands[0].EndTime.Seconds, 60, 80);
        }

        /// <summary>环境能见度在 t=100 s 由 8 nm 降为 1 nm（未给互见标志）→ 对遇段与能见度不良段在 100 s 处精确切分（环境切换时刻保留）。</summary>
        [Fact]
        public void TimeBands_SplitExactlyAtVisibilityChange()
        {
            var env = new[] { Env(0, 8f), Env(103, 1f) };
            var r = Ok(new Ship(0, 0, 0, 5).Run(300), CollisionTarget(0, 4000, 400).Run(300), vis: null, inSight: null, env: env);
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands[0].Situation);
            Assert.Equal(EncounterSituation.RestrictedVisibility, r.TimeBands[1].Situation);
            Assert.Equal(103, r.TimeBands[0].EndTime.Seconds, 9);
            Assert.Equal(103, r.TimeBands[1].StartTime.Seconds, 9);
            Assert.Equal(EncounterSituation.RestrictedVisibility, BandAt(r, 103).Situation); // 边界归后一带
        }

        /// <summary>
        /// 局面多次变化。W1.1 裁定补充② / D12 延后锁定。独立运动学与相对运动计算见
        /// logs/w1.1-retest-transitions-calc.py（1 s 中点积分，与夹具相同；未调用被测引擎）：
        /// 追越锁定至驶过让清（间距 0.5 nm 于 385.103 s，10 s 网格 390 s）→ 无危险 →
        /// 他船 500–530 s 以 6°/s 左转 180°；10 s 网格上 520 s 首次再形成危险（DCPA 0.570 nm、TCPA 79 s；
        /// 1 s 真值最早于 511 s，但本用例采样间隔为 10 s）。520 s 时 60 s 航向峰峰值 120° &gt; 5°，延后锁定，
        /// 记 Undetermined / pending_stable_heading。转向于 530 s 结束，60 s 窗口在 589 s 仍为 6°、590 s 为 0°，
        /// 故 590 s 两船航向稳定；120 s 时限为 520+120=640 s，未触发。590 s 几何：航向互差对向 0°，相对方位 19.7°
        ///（15°–22.5° 存疑扇区）→ 锁定为对遇（R14(c) 可标 Doubt）。危险持续到 TCPA 过零 620 s（网格 620–630 s）→ 无危险。
        /// </summary>
        [Fact]
        public void TimeBands_MultipleTransitions()
        {
            var own = new Ship(0, 0, 0, 5);
            var tgt = new Ship(30, -1000, 0, 10).Order(500, 180);
            var r = Ok(own.Run(900), tgt.Run(900));
            var seq = r.TimeBands.Select(b => b.Situation).ToArray();
            Assert.True(seq.SequenceEqual(new[] {
                EncounterSituation.Overtaking, EncounterSituation.NoCollisionRisk,
                EncounterSituation.Undetermined, EncounterSituation.HeadOn,
                EncounterSituation.NoCollisionRisk }), Describe(r));
            var ov = r.TimeBands[0];
            Assert.Equal(TrafficRole.StandOn, ov.OwnRole);
            Assert.Equal(TrafficRole.GiveWay, ov.TargetRole);
            Assert.InRange(ov.EndTime.Seconds, 385.0, 390.0 + 1e-9);
            var pending = r.TimeBands[2];
            Assert.Equal(EncounterSituation.Undetermined, pending.Situation);
            Assert.Equal(ColregDoubtReasons.PendingStableHeading, pending.DoubtReason);
            Assert.True(pending.Doubt, Describe(r));
            Assert.InRange(pending.StartTime.Seconds, 510.0 + 1e-9, 520.0 + 1e-9);
            Assert.Equal(590, pending.EndTime.Seconds, 6);
            var ho = r.TimeBands[3];
            Assert.Equal(EncounterSituation.HeadOn, ho.Situation);
            Assert.Equal(590, ho.StartTime.Seconds, 6);
            Assert.Equal(TrafficRole.BothActionRequired, ho.OwnRole);
            Assert.Equal(TrafficRole.BothActionRequired, ho.TargetRole);
            Assert.NotEqual(ColregDoubtReasons.PendingStableHeading, ho.DoubtReason);
            Assert.NotEqual(ColregDoubtReasons.LockedDuringTurn, ho.DoubtReason);
            Assert.InRange(ho.EndTime.Seconds, 620.0, 630.0 + 1e-9);
        }

        // ---------- 空 / 短 / 不同步 / NaN ----------

        [Fact]
        public void Input_Null_Fails() => Assert.False(new ColregEngine().Analyze(null).IsSuccess);

        [Fact]
        public void Input_EmptyTrack_FailsWithCode()
        {
            var r = Run(Array.Empty<TrackSample>(), CrossTgt().Run(100));
            Assert.False(r.IsSuccess);
            Assert.Equal("COLREG_INVALID_INPUT", r.ErrorCode);
        }

        [Fact]
        public void Input_NullTrack_Fails() => Assert.False(Run(null, CrossTgt().Run(100)).IsSuccess);

        [Fact]
        public void Input_SameVesselId_Fails()
        {
            var t = CrossTgt().Run(100);
            Assert.False(new ColregEngine().Analyze(new ColregAnalysisRequest("A", "A", new Ship(0, 0, 0, 5).Run(100), t)).IsSuccess);
        }

        /// <summary>单点（同一时刻各一点）→ 成功；局面可判定，但行动类核查只能 Partial/不适用（无法核实操纵过程）。</summary>
        [Fact]
        public void Input_SingleSampleEach_SucceedsWithPartial()
        {
            var own = new[] { S(0, 0, 0, 0, 5) };
            var tgt = CrossTgt().Run(0);
            var r = Ok(own, tgt);
            Assert.Single(r.TimeBands);
            Assert.Equal(EncounterSituation.Crossing, r.TimeBands[0].Situation);
            Assert.DoesNotContain(r.RuleChecks, c => (c.RuleId == ColregRuleId.R16 || c.RuleId == ColregRuleId.R15) && c.Status == RuleCheckStatus.Satisfied);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R16 && c.Status == RuleCheckStatus.Partial);
        }

        [Fact]
        public void Input_NoOverlap_FailsWithCode()
        {
            var r = Run(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100, t0: 200));
            Assert.False(r.IsSuccess);
            Assert.Equal("COLREG_NO_OVERLAP", r.ErrorCode);
        }

        /// <summary>不同步采样（本船 0/10/20…，他船 5/15/25…，且步长不同）→ 仅在共同区间内分析，结论与同步采样一致。</summary>
        [Fact]
        public void Input_UnsynchronisedSampling_UsesOverlapAndMatchesSynced()
        {
            var own = new Ship(0, 0, 0, 5).Run(400, outEvery: 10);
            var tgtSync = CrossTgt().Run(400, outEvery: 10);
            var tgtAsync = CrossTgt().Run(390, outEvery: 7, t0: 0).Select(s => s).ToArray();
            // 他船整体从 5 s 开始（截掉前段）
            tgtAsync = tgtAsync.Where(s => s.Time.Seconds >= 5).ToArray();
            var a = Ok(own, tgtSync);
            var b = Ok(own, tgtAsync);
            Assert.Equal(tgtAsync[0].Time.Seconds, b.TimeBands.First().StartTime.Seconds, 9);
            Assert.Equal(Math.Min(own.Last().Time.Seconds, tgtAsync.Last().Time.Seconds), b.TimeBands.Last().EndTime.Seconds, 9);
            Assert.Equal(a.TimeBands.First().Situation, b.TimeBands.First().Situation);
            Assert.Equal(a.TimeBands.First().OwnRole, b.TimeBands.First().OwnRole);
        }

        [Fact]
        public void Input_NonIncreasingTime_Fails()
        {
            var own = new[] { S(0, 0, 0, 0, 5), S(0, 0, 50, 0, 5) };
            Assert.False(Run(own, CrossTgt().Run(100)).IsSuccess);
            var rev = new Ship(0, 0, 0, 5).Run(100).Reverse().ToArray();
            Assert.False(Run(rev, CrossTgt().Run(100)).IsSuccess);
        }

        [Theory]
        [InlineData("pos")]
        [InlineData("vel")]
        [InlineData("sog")]
        [InlineData("time")]
        [InlineData("hdgAndCog")]
        public void Input_NaNInSample_Fails(string field)
        {
            var own = new Ship(0, 0, 0, 5).Run(100).ToList();
            var s = own[3];
            TrackSample bad = field switch
            {
                "pos" => new TrackSample(s.Time, s.Geo, new EnuPosition(double.NaN, 0), s.VelocityEnuMps, s.SogMps, s.CogDeg, s.HdgDeg, 0, s.Provenance, s.TimeQuality, false),
                "vel" => new TrackSample(s.Time, s.Geo, s.EnuCenter, new Mcis.Domain.Common.Double2(double.NaN, 1), s.SogMps, s.CogDeg, s.HdgDeg, 0, s.Provenance, s.TimeQuality, false),
                "sog" => new TrackSample(s.Time, s.Geo, s.EnuCenter, s.VelocityEnuMps, float.NaN, s.CogDeg, s.HdgDeg, 0, s.Provenance, s.TimeQuality, false),
                "time" => new TrackSample(new SimTime(double.NaN), s.Geo, s.EnuCenter, s.VelocityEnuMps, s.SogMps, s.CogDeg, s.HdgDeg, 0, s.Provenance, s.TimeQuality, false),
                _ => new TrackSample(s.Time, s.Geo, s.EnuCenter, s.VelocityEnuMps, s.SogMps, float.NaN, float.NaN, 0, s.Provenance, s.TimeQuality, false),
            };
            own[3] = bad;
            var r = Run(own, CrossTgt().Run(100));
            Assert.False(r.IsSuccess);
        }

        /// <summary>HDG 缺失（NaN）而 COG 有效 → 以 COG 代替，分析成功且局面正确（不得静默失败或 NaN 传播）。</summary>
        [Fact]
        public void Input_NaNHeadingWithValidCog_FallsBackToCog()
        {
            var own = new Ship(0, 0, 0, 5).Run(300).Select(s => new TrackSample(s.Time, s.Geo, s.EnuCenter, s.VelocityEnuMps, s.SogMps, s.CogDeg, float.NaN, 0, s.Provenance, s.TimeQuality, false)).ToArray();
            var r = Ok(own, CollisionTarget(0, 4000, 400).Run(300));
            Assert.Equal(EncounterSituation.HeadOn, r.TimeBands.First().Situation);
            Assert.All(r.RuleChecks, c => Assert.False(double.IsNaN(c.Evidence.RelativeBearingDeg)));
        }

        [Fact]
        public void Input_NaNVisibility_Fails()
        {
            Assert.False(Run(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100), vis: double.NaN).IsSuccess);
            Assert.False(Run(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100), vis: null, env: new[] { Env(0, float.NaN) }).IsSuccess);
        }

        [Fact]
        public void Input_NaNThreshold_Fails()
        {
            Assert.False(Run(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100), new ColregThresholds(headOnHalfAngleDeg: double.NaN)).IsSuccess);
            Assert.False(Run(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100), new ColregThresholds(sampleIntervalSeconds: 0)).IsSuccess);
        }

        [Fact]
        public void Input_HugeGrid_FailsGracefully()
        {
            var own = new[] { S(0, 0, 0, 0, 5), S(1e7, 0, 5e7, 0, 5) };
            var tgt = new[] { S(0, 100, 0, 0, 5), S(1e7, 100, 5e7, 0, 5) };
            var r = Run(own, tgt, new ColregThresholds(sampleIntervalSeconds: 1));
            Assert.False(r.IsSuccess);
        }

        // ---------- 阈值配置生效 ----------

        [Fact]
        public void Thresholds_HeadOnHalfAngle_Configurable()
        {
            double h = 188;
            var tgt = new Ship(-5 * Sin(h) * 400, 2000 - 5 * Cos(h) * 400, h, 5);
            Assert.Equal(EncounterSituation.Crossing, Ok(new Ship(0, 0, 0, 5).Run(200), tgt.Run(200)).TimeBands[0].Situation);
            Assert.Equal(EncounterSituation.HeadOn, Ok(new Ship(0, 0, 0, 5).Run(200), tgt.Run(200), new ColregThresholds(headOnHalfAngleDeg: 10)).TimeBands[0].Situation);
        }

        [Fact]
        public void Thresholds_OvertakingSector_Configurable()
        {
            var tgt = CollisionTarget(115, 1000, 300);
            Assert.Equal(EncounterSituation.Overtaking, Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100)).TimeBands[0].Situation);
            Assert.Equal(EncounterSituation.Crossing, Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100), new ColregThresholds(overtakingAbaftBeamAngleDeg: 30)).TimeBands[0].Situation);
        }

        [Fact]
        public void Thresholds_RestrictedVisibility_Configurable()
        {
            var tgt = CollisionTarget(0, 4000, 400);
            Assert.Equal(EncounterSituation.HeadOn, Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100), vis: 2.5, inSight: null).TimeBands[0].Situation);
            // 复测按裁定 D04 改写：未给互见标志时缺省"距离 ≤ 能见度即互见"。他船 4000 m=2.16 nm ≤ 2.5 nm → 互见 → 对遇（R11/R14），
            // 虽然阈值 3 nm 使能见度判为不良。阈值可配置性改用距离 > 能见度的他船（6000 m=3.24 nm）验证。
            var near = Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100), new ColregThresholds(restrictedVisibilityNm: 3), vis: 2.5, inSight: null);
            Assert.Equal(EncounterSituation.HeadOn, near.TimeBands[0].Situation);
            Assert.True(near.TimeBands[0].InSight);
            var far = CollisionTarget(0, 6000, 600);
            Assert.Equal(EncounterSituation.HeadOn, Ok(new Ship(0, 0, 0, 5).Run(50), far.Run(50), vis: 2.5, inSight: null).TimeBands[0].Situation);
            var farRv = Ok(new Ship(0, 0, 0, 5).Run(50), far.Run(50), new ColregThresholds(restrictedVisibilityNm: 3), vis: 2.5, inSight: null);
            Assert.Equal(EncounterSituation.RestrictedVisibility, farRv.TimeBands[0].Situation);
            Assert.False(farRv.TimeBands[0].InSight);
        }

        [Fact]
        public void Thresholds_CollisionRiskDcpa_Configurable()
        {
            // 反向平行、横距 0.4 nm
            var tgt = new Ship(0.4 * 1852, 4000, 180, 5);
            Assert.NotEqual(EncounterSituation.NoCollisionRisk, Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100)).TimeBands[0].Situation);
            Assert.Equal(EncounterSituation.NoCollisionRisk, Ok(new Ship(0, 0, 0, 5).Run(100), tgt.Run(100), new ColregThresholds(collisionRiskDcpaNm: 0.3)).TimeBands[0].Situation);
        }

        [Fact]
        public void Thresholds_SnapshotEchoedInReport()
        {
            var th = new ColregThresholds(headOnHalfAngleDeg: 7, substantialTurnDeg: 20);
            var r = Ok(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100), th);
            Assert.Equal(7, r.Thresholds.HeadOnHalfAngleDeg);
            Assert.Equal(20, r.Thresholds.SubstantialTurnDeg);
            Assert.Equal(112.5, ColregThresholds.Default.OvertakingBoundaryDeg, 9);
            Assert.Equal(6.0, ColregThresholds.Default.HeadOnHalfAngleDeg);
            Assert.Equal(2.0, ColregThresholds.Default.RestrictedVisibilityNm);
        }

        // ---------- 免责声明 / 确定性 ----------

        /// <summary>ARCHITECTURE §15.5：界面和报告一律注明"仅作安全调查技术分析，不作责任认定。"</summary>
        [Fact]
        public void Disclaimer_Present()
        {
            var r = Ok(new Ship(0, 0, 0, 5).Run(100), CrossTgt().Run(100));
            Assert.Equal("仅作安全调查技术分析，不作责任认定。", r.Disclaimer);
            Assert.NotEmpty(r.Assumptions);
        }

        /// <summary>确定性规则引擎（§15.5）：同输入（含新建引擎实例）→ 逐字段相同输出。</summary>
        [Fact]
        public void Determinism_SameInputSameOutput()
        {
            var own = new Ship(0, 0, 0, 5).Order(250, 60).Run(450);
            var tgt = CrossTgt().Order(300, 200, 3).Run(450);
            var env = new[] { Env(0, 8f), Env(200, 1.5f) };
            string a = Fingerprint(Ok(own, tgt, env: env, vis: null, inSight: null));
            string b = Fingerprint(new ColregEngine().Analyze(new ColregAnalysisRequest(Own, Tgt, own.ToList(), tgt.ToList(), null, env, null, null)).Value);
            Assert.Equal(a, b);
        }

        /// <summary>请求构造即快照：调用方随后修改原数组不影响结果。</summary>
        [Fact]
        public void Determinism_RequestSnapshotsInput()
        {
            var own = new Ship(0, 0, 0, 5).Run(300);
            var tgt = CollisionTarget(0, 4000, 400).Run(300);
            var req = new ColregAnalysisRequest(Own, Tgt, own, tgt, null, null, 8, true);
            string before = Fingerprint(new ColregEngine().Analyze(req).Value);
            own[5] = S(own[5].Time.Seconds, 999, 999, 90, 5);
            Assert.Equal(before, Fingerprint(new ColregEngine().Analyze(req).Value));
        }

        // ---------- 规格覆盖 ----------

        /// <summary>
        /// ARCHITECTURE §15.1 ⑥ 依据条款为 COLREGs R5–R9、R14–R19、R34–R35；原型 11 规则表列出 R5、R6、R7、R8、R9、R14、R17/2(b)、R19、R34/35。
        /// 规则目录至少应包含 R5、R6、R7、R34/R35 条目（可为 Partial/Undetermined 核查）。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D07_RuleCatalogCoversSpecRules()
        {
            var names = Enum.GetNames(typeof(ColregRuleId));
            foreach (var need in new[] { "R5", "R6", "R7", "R34" })
                Assert.Contains(names, n => n.StartsWith(need));
        }

        /// <summary>
        /// contracts/schemas/colreg.schema.json：band 含 inSight、give/stand-on 船号，situation 含 ImmediateDanger；原型 11 有"紧迫危险 R17(b)/R2(b)"时间带。
        /// 报告时间带模型须能表达互见与紧迫危险。
        /// </summary>
        [Fact]
        [Trait("Category", "KnownDefect")]
        public void W1_D08_TimeBandModelMatchesContract()
        {
            Assert.Contains("ImmediateDanger", Enum.GetNames(typeof(EncounterSituation)));
            Assert.NotNull(typeof(ColregTimeBand).GetProperty("InSight"));
        }
    }
}
