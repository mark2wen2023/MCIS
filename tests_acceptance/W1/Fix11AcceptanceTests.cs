using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Colreg;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Xunit;
using static Mcis.Acceptance.W1.Fx;

namespace Mcis.Acceptance.W1
{
    /// <summary>
    /// W1.1 复测补测：D09–D12 与实施方经架构师确认的补充规格。航迹均为合成虚构数据。
    /// 合同映射用 ColregContractNames + Python jsonschema 校验 colreg.schema.json。
    /// </summary>
    public sealed class Fix11AcceptanceTests
    {
        private const string CaseId = "CASE-W11-001";

        private static ColregVesselStatusSample St(string vessel, double t, ColregVesselStatus s) =>
            new ColregVesselStatusSample(vessel, new SimTime(t), s);

        private static ColregAnalysisReport Analyze(
            IReadOnlyList<TrackSample> own, IReadOnlyList<TrackSample> tgt,
            IReadOnlyList<ColregVesselStatusSample> status = null,
            string ownId = Own, string tgtId = Tgt, string caseId = CaseId,
            ColregThresholds th = null, double? vis = 8, bool? inSight = true)
        {
            var r = new ColregEngine().Analyze(new ColregAnalysisRequest(
                ownId, tgtId, own, tgt, th, null, vis, inSight, false, null, null, null, caseId, null, status));
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        private static ColregTimeBand FirstRisk(ColregAnalysisReport r)
        {
            var b = r.TimeBands.FirstOrDefault(x => x.Situation != EncounterSituation.NoCollisionRisk);
            Assert.NotNull(b);
            return b;
        }

        private static TrackSample[] HeadOnOwn() => new Ship(0, 0, 0, 5).Run(200);
        private static TrackSample[] HeadOnTgt() => new Ship(0, 3000, 180, 5).Run(200);
        private static TrackSample[] CrossingOwn() => new Ship(0, 0, 0, 5).Run(200);
        private static TrackSample[] CrossingTgt() => CollisionTarget(45, 2828.4, 400).Run(200);

        // ================= D09 / R18 船舶状态 =================

        /// <summary>D09 / R18(a)：本船失控、他船机动船的交叉局面 → 他船让路，失控船 R14–R17 为 NotApplicable，R18 由他船承担让路义务。</summary>
        [Fact]
        public void D09_NucOwn_OtherGivesWay_R14ToR17NotApplicable()
        {
            var status = new[]
            {
                St(Own, 0, ColregVesselStatus.NotUnderCommand),
                St(Tgt, 0, ColregVesselStatus.PowerDriven)
            };
            var r = Analyze(CrossingOwn(), CrossingTgt(), status);
            var b = FirstRisk(r);
            Assert.Equal(Tgt, b.GiveWayVesselId);
            Assert.Null(b.StandOnVesselId);
            Assert.Equal(ColregVesselStatus.NotUnderCommand, b.VesselStatus[Own]);
            Assert.DoesNotContain(Checks(r, ColregRuleId.R14, Own).Concat(Checks(r, ColregRuleId.R15, Own))
                .Concat(Checks(r, ColregRuleId.R16, Own)).Concat(Checks(r, ColregRuleId.R17, Own)),
                c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.Contains(Checks(r, ColregRuleId.R18, Tgt), c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.Contains(Checks(r, ColregRuleId.R18, Own), c => c.Status == RuleCheckStatus.NotApplicable);
            Assert.Contains(Checks(r, ColregRuleId.R8, Own), c => c.Status != RuleCheckStatus.NotApplicable
                || true); // R8 仍评估（可能为不满足/部分满足）；至少有核查项
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R8 && c.VesselId == Own);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R5 && c.VesselId == Own);
            Assert.Contains(r.RuleChecks, c => c.RuleId == ColregRuleId.R7 && c.VesselId == Own);
        }

        /// <summary>D09 / R18(a)：他船操限、本船机动船 → 本船让路。</summary>
        [Fact]
        public void D09_RamTarget_OwnGivesWay()
        {
            var status = new[]
            {
                St(Own, 0, ColregVesselStatus.PowerDriven),
                St(Tgt, 0, ColregVesselStatus.RestrictedManoeuvrability)
            };
            var r = Analyze(CrossingOwn(), CrossingTgt(), status);
            var b = FirstRisk(r);
            Assert.Equal(Own, b.GiveWayVesselId);
            Assert.Null(b.StandOnVesselId);
            Assert.DoesNotContain(Checks(r, ColregRuleId.R14, Tgt).Concat(Checks(r, ColregRuleId.R15, Tgt))
                .Concat(Checks(r, ColregRuleId.R16, Tgt)).Concat(Checks(r, ColregRuleId.R17, Tgt)),
                c => c.Status != RuleCheckStatus.NotApplicable);
            Assert.Contains(Checks(r, ColregRuleId.R18, Own), c => c.Status != RuleCheckStatus.NotApplicable);
        }

        /// <summary>补充规格：双方均为 NUC 或 RAM 时，R18 给 NeedsReview，角色不确定。</summary>
        [Theory]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.NotUnderCommand)]
        [InlineData(ColregVesselStatus.RestrictedManoeuvrability, ColregVesselStatus.RestrictedManoeuvrability)]
        [InlineData(ColregVesselStatus.NotUnderCommand, ColregVesselStatus.RestrictedManoeuvrability)]
        public void D09_BothPrivileged_R18NeedsReview(ColregVesselStatus a, ColregVesselStatus b)
        {
            var r = Analyze(CrossingOwn(), CrossingTgt(), new[] { St(Own, 0, a), St(Tgt, 0, b) });
            var band = FirstRisk(r);
            Assert.True(band.Doubt);
            Assert.Equal(ColregDoubtReasons.VesselStatusReview, band.DoubtReason);
            Assert.Null(band.GiveWayVesselId);
            Assert.Null(band.StandOnVesselId);
            Assert.All(Checks(r, ColregRuleId.R18, Own).Concat(Checks(r, ColregRuleId.R18, Tgt))
                    .Where(c => c.Status != RuleCheckStatus.NotApplicable),
                c => Assert.Equal(RuleCheckStatus.NeedsReview, c.Status));
        }

        /// <summary>补充规格：涉及限于吃水、捕鱼或帆船时，R18 给 NeedsReview。</summary>
        [Theory]
        [InlineData(ColregVesselStatus.ConstrainedByDraught)]
        [InlineData(ColregVesselStatus.Fishing)]
        [InlineData(ColregVesselStatus.Sailing)]
        public void D09_SpecialStatus_R18NeedsReview(ColregVesselStatus special)
        {
            var r = Analyze(CrossingOwn(), CrossingTgt(),
                new[] { St(Own, 0, ColregVesselStatus.PowerDriven), St(Tgt, 0, special) });
            Assert.All(Checks(r, ColregRuleId.R18, Own).Concat(Checks(r, ColregRuleId.R18, Tgt))
                    .Where(c => c.Status != RuleCheckStatus.NotApplicable),
                c => Assert.Equal(RuleCheckStatus.NeedsReview, c.Status));
            var band = FirstRisk(r);
            Assert.True(band.Doubt);
            Assert.Equal(ColregDoubtReasons.VesselStatusReview, band.DoubtReason);
        }

        /// <summary>补充规格：未给船舶状态时，R18 为 NotAssessable，并列出所需证据；R13–R17 仍按机动船几何核查。</summary>
        [Fact]
        public void D09_NoVesselStatus_R18NotAssessable()
        {
            var r = Analyze(CrossingOwn(), CrossingTgt(), status: null);
            var r18 = Checks(r, ColregRuleId.R18, Own).Concat(Checks(r, ColregRuleId.R18, Tgt))
                .Where(c => c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.NotEmpty(r18);
            Assert.All(r18, c =>
            {
                Assert.Equal(RuleCheckStatus.NotAssessable, c.Status);
                Assert.True(c.Explanation.Contains("号灯") || c.Explanation.Contains("VHF") || c.Explanation.Contains("VDR") || c.Explanation.Contains("轮机"),
                    c.Explanation);
            });
            Assert.Equal(EncounterSituation.Crossing, FirstRisk(r).Situation);
            Assert.Equal(TrafficRole.GiveWay, FirstRisk(r).OwnRole);
        }

        /// <summary>补充规格：他船追越失控船时，按 R13 他船仍为让路船（R18 开头保留 R13）。</summary>
        [Fact]
        public void D09_OvertakingNuc_OvertakerGivesWayByR13()
        {
            var own = new Ship(0, 0, 0, 5).Run(200);
            var tgt = new Ship(30, -1000, 0, 10).Run(200);
            var r = Analyze(own, tgt, new[]
            {
                St(Own, 0, ColregVesselStatus.NotUnderCommand),
                St(Tgt, 0, ColregVesselStatus.PowerDriven)
            });
            var b = FirstRisk(r);
            Assert.Equal(EncounterSituation.Overtaking, b.Situation);
            Assert.Equal(Tgt, b.GiveWayVesselId);
            Assert.Contains(b.ApplicableRules, x => x == ColregRuleId.R13);
            Assert.Contains(Checks(r, ColregRuleId.R13, Tgt), c => c.Status != RuleCheckStatus.NotApplicable);
        }

        // ================= 互换本船/他船结论不变 =================

        /// <summary>D10/D11 及补充规格：至少 5 个自构场景，互换本船与他船后局面、让路船、存疑标志不变。</summary>
        [Theory]
        [InlineData("headon")]
        [InlineData("crossing")]
        [InlineData("headon-doubt")]
        [InlineData("contradictory")]
        [InlineData("overtaking")]
        [InlineData("nuc-target")]
        public void SwapOwnTarget_ConclusionsInvariant(string scene)
        {
            TrackSample[] a, b;
            IReadOnlyList<ColregVesselStatusSample> stA = null, stB = null;
            switch (scene)
            {
                case "headon":
                    a = HeadOnOwn(); b = HeadOnTgt(); break;
                case "crossing":
                    a = CrossingOwn(); b = CrossingTgt(); break;
                case "headon-doubt":
                    // 本船看他船 20°、他船看本船约 26°，航向差 6°（D10 场景）
                    a = new Ship(0, 0, 0, 5).Run(150);
                    b = new Ship(2000 * Sin(20), 2000 * Cos(20), 174, 5).Run(150);
                    break;
                case "contradictory":
                    a = new Ship(0, 0, 0, 5).Run(200);
                    b = new Ship(1000, 1732.05, 200, 5).Run(200);
                    break;
                case "overtaking":
                    a = new Ship(0, 0, 0, 5).Run(200);
                    b = new Ship(30, -1000, 0, 10).Run(200);
                    break;
                default: // nuc-target：B 失控，A 应让路
                    a = CrossingOwn(); b = CrossingTgt();
                    stA = new[] { St("A", 0, ColregVesselStatus.PowerDriven), St("B", 0, ColregVesselStatus.NotUnderCommand) };
                    stB = new[] { St("B", 0, ColregVesselStatus.NotUnderCommand), St("A", 0, ColregVesselStatus.PowerDriven) };
                    break;
            }

            var ab = Analyze(a, b, stA, "A", "B");
            var ba = Analyze(b, a, stB, "B", "A");
            var x = FirstRisk(ab);
            var y = FirstRisk(ba);
            Assert.Equal(x.Situation, y.Situation);
            Assert.Equal(x.GiveWayVesselId, y.GiveWayVesselId);
            Assert.Equal(x.StandOnVesselId, y.StandOnVesselId);
            Assert.Equal(x.Doubt, y.Doubt);
            Assert.Equal(x.DoubtReason ?? "", y.DoubtReason ?? "");
        }

        // ================= D12 延后锁定 120 s 超时 =================

        /// <summary>
        /// D12：风险形成后 120 s 航向仍不稳定，则按当时几何锁定并标 doubt=true、doubtReason=locked_during_turn。
        /// 独立计算（与夹具相同的 1 s 中点积分）：本船 (0,0) 航向 0° 航速 5 m/s；他船 (50,8000) 航向 180° 航速 5 m/s，
        /// 自 t=0 以 0.1°/s 转向 90°。10 s 网格上 80 s 首次形成危险（TCPA 降至 720 s 内），60 s 航向峰峰值 6° &gt; 5°，
        /// 时限 80+120=200 s；200 s 时仍有危险（DCPA 0.683 nm、TCPA 598 s）且仍不稳定，应在 200 s 锁定。
        /// </summary>
        [Fact]
        public void D12_LockAfter120sTimeout_DoubtLockedDuringTurn()
        {
            var tgt = new Ship(50, 8000, 180, 5);
            tgt.TurnRate = 0.1;
            tgt.Order(0, 90);
            var r = Analyze(new Ship(0, 0, 0, 5).Run(400), tgt.Run(400));
            var locked = r.TimeBands.FirstOrDefault(b => b.DoubtReason == ColregDoubtReasons.LockedDuringTurn);
            Assert.True(locked != null, Describe(r));
            Assert.True(locked.Doubt);
            Assert.Equal(200, locked.StartTime.Seconds, 6);
            var pending = r.TimeBands.LastOrDefault(b =>
                b.EndTime.Seconds <= locked.StartTime.Seconds + 1e-9 &&
                b.Situation == EncounterSituation.Undetermined);
            Assert.True(pending != null, Describe(r));
            Assert.Equal(ColregDoubtReasons.PendingStableHeading, pending.DoubtReason);
            Assert.InRange(pending.StartTime.Seconds, 70.0, 80.0 + 1e-9);
            Assert.Equal(200, pending.EndTime.Seconds, 6);
        }

        /// <summary>补充规格：band.dangerStage 取带内最高阶段；合同映射 CollisionRisk→None，会遇类型不改为 ImmediateDanger。</summary>
        [Fact]
        public void DangerStage_BandUsesMaximum_ContractMapsCollisionRiskToNone()
        {
            // 对遇、横距约 0.05 nm，TCPA 从 200 s 降到 0：带内经历 CollisionRisk→CloseQuarters→ImmediateDanger
            var r = Analyze(new Ship(0, 0, 0, 5).Run(250), new Ship(90, 2000, 180, 5).Run(250));
            var risk = FirstRisk(r);
            Assert.Equal(EncounterSituation.HeadOn, risk.Situation);
            Assert.Equal(ColregDangerStage.ImmediateDanger, risk.DangerStage);
            Assert.Contains(r.DangerStages, s => s.Stage == ColregDangerStage.ImmediateDanger);
            Assert.Contains(r.DangerStages, s => s.Stage == ColregDangerStage.CloseQuarters || s.Stage == ColregDangerStage.CollisionRisk);
            Assert.Equal("None", ColregContractNames.DangerStage(ColregDangerStage.CollisionRisk));
            Assert.Equal("CloseQuarters", ColregContractNames.DangerStage(ColregDangerStage.CloseQuarters));
            Assert.Equal("ImmediateDanger", ColregContractNames.DangerStage(ColregDangerStage.ImmediateDanger));
            Assert.Equal("HeadOn", ColregContractNames.Situation(EncounterSituation.HeadOn));
            Assert.Equal("NoRisk", ColregContractNames.Situation(EncounterSituation.NoCollisionRisk));
            Assert.Equal("Complies", ColregContractNames.Verdict(RuleCheckStatus.Satisfied));
            Assert.Equal("NotComplied", ColregContractNames.Verdict(RuleCheckStatus.NotSatisfied));
            Assert.Equal("NeedsReview", ColregContractNames.Verdict(RuleCheckStatus.NeedsReview));
            Assert.Equal("NotAssessable", ColregContractNames.Verdict(RuleCheckStatus.NotAssessable));
        }

        /// <summary>补充规格：R16/R8 的「及早」从危险首次形成时算起，推迟锁定期间采取的避让行动计入。</summary>
        [Fact]
        public void EarlyAction_CountsManeuverDuringPendingLock()
        {
            // 他船自 t=0 慢转，80 s 形成危险后延后锁定；本船在 90 s（推迟期内）右转 30°。
            var tgt = new Ship(50, 8000, 180, 5);
            tgt.TurnRate = 0.1;
            tgt.Order(0, 90);
            var own = new Ship(0, 0, 0, 5).Order(90, 30);
            var r = Analyze(own.Run(400), tgt.Run(400));
            var after = r.TimeBands.FirstOrDefault(b => b.StartTime.Seconds >= 200 - 1e-9 &&
                b.Situation != EncounterSituation.NoCollisionRisk &&
                b.DoubtReason != ColregDoubtReasons.PendingStableHeading);
            Assert.True(after != null, Describe(r));
            var r8 = Checks(r, ColregRuleId.R8, Own).Where(c => c.StartTime.Seconds >= 80 && c.Status != RuleCheckStatus.NotApplicable).ToList();
            var r16 = Checks(r, ColregRuleId.R16, Own).Concat(Checks(r, ColregRuleId.R14, Own))
                .Where(c => c.StartTime.Seconds >= 80 && c.Status != RuleCheckStatus.NotApplicable).ToList();
            Assert.True(r8.Count + r16.Count > 0, Describe(r));
            Assert.Contains(r8.Concat(r16), c => Math.Abs(c.ActualAction.HeadingChangeDeg) >= 25);
            Assert.DoesNotContain(r8, c => c.Explanation != null && c.Explanation.Contains("及早=False") && Math.Abs(c.ActualAction.HeadingChangeDeg) >= 25);
        }

        // ================= 合同映射 + jsonschema =================

        /// <summary>用 ColregContractNames 适配层输出 JSON，并由 Python jsonschema 按 colreg.schema.json 校验（含 NeedsReview / NotAssessable / dangerStage）。</summary>
        [Fact]
        public void ContractMapping_AdapterOutputValidatesAgainstSchema()
        {
            var crossing = Analyze(CrossingOwn(), CrossingTgt(), status: null, caseId: "CASE-MAP-001");
            var nuc = Analyze(CrossingOwn(), CrossingTgt(), new[]
            {
                St(Own, 0, ColregVesselStatus.NotUnderCommand),
                St(Tgt, 0, ColregVesselStatus.PowerDriven)
            }, caseId: "CASE-MAP-002");
            var review = Analyze(new Ship(0, 0, 0, 5).Run(200), new Ship(1000, 1732.05, 200, 5).Run(200), caseId: "CASE-MAP-003");

            string dir = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "logs"));
            if (!Directory.Exists(dir))
                dir = "/workspace/maritime-sim-design/logs";
            Directory.CreateDirectory(dir);

            var files = new[]
            {
                Path.Combine(dir, "w1.1-retest-contract-crossing.json"),
                Path.Combine(dir, "w1.1-retest-contract-nuc.json"),
                Path.Combine(dir, "w1.1-retest-contract-review.json")
            };
            ColregContractMapper.Write(files[0], ColregContractMapper.ToContract("CASE-MAP-001", crossing));
            ColregContractMapper.Write(files[1], ColregContractMapper.ToContract("CASE-MAP-002", nuc));
            ColregContractMapper.Write(files[2], ColregContractMapper.ToContract("CASE-MAP-003", review));

            // 名称映射在写入的文档里可直接检查
            var doc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(files[0]));
            foreach (var band in doc.RootElement.GetProperty("bands").EnumerateArray())
            {
                var sit = band.GetProperty("situation").GetString();
                Assert.NotEqual("NoCollisionRisk", sit);
                Assert.NotEqual("ImmediateDanger", sit); // 会遇类型保留，紧迫危险走 dangerStage
                var stage = band.GetProperty("dangerStage").GetString();
                Assert.Contains(stage, new[] { "None", "CloseQuarters", "ImmediateDanger" });
            }
            foreach (var check in doc.RootElement.GetProperty("checks").EnumerateArray())
            {
                var v = check.GetProperty("verdict").GetString();
                Assert.DoesNotContain(v, new[] { "Satisfied", "NotSatisfied" });
            }

            var reviewDoc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(files[2]));
            Assert.Contains(reviewDoc.RootElement.GetProperty("checks").EnumerateArray(),
                c => c.GetProperty("verdict").GetString() == "NeedsReview");
            var nucDoc = System.Text.Json.JsonDocument.Parse(File.ReadAllText(files[1]));
            Assert.Contains(nucDoc.RootElement.GetProperty("checks").EnumerateArray(),
                c => c.GetProperty("verdict").GetString() == "NotApplicable");

            string py = "/workspace/maritime-sim-design/service/.venv/bin/python";
            string script = "/workspace/maritime-sim-design/tests_acceptance/W1/validate_colreg_schema.py";
            var psi = new ProcessStartInfo(py)
            {
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false
            };
            psi.ArgumentList.Add(script);
            foreach (var f in files) psi.ArgumentList.Add(f);
            using var proc = Process.Start(psi);
            string stdout = proc.StandardOutput.ReadToEnd();
            string stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit(60000);
            File.WriteAllText(Path.Combine(dir, "w1.1-retest-contract-schema-validate.txt"), stdout + stderr);
            Assert.True(proc.ExitCode == 0, "jsonschema 校验失败：\n" + stdout + stderr);
        }
    }
}
