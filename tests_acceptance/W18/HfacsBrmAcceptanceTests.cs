using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Mcis.Domain.HumanFactors;
using Xunit;
using static Mcis.Acceptance.W18.Fx;

namespace Mcis.Acceptance.W18
{
    /// <summary>HFACS-MA 分类与结论、BRM 核查单、错误码与依赖约束验收。示例数据·虚构。</summary>
    public sealed class HfacsBrmAcceptanceTests
    {
        private static readonly string[] Ev = { "EV-001" };
        private static readonly string[] Node = { "C2" };

        // ---------- HFACS-MA 分类树 ----------

        [Fact]
        public void Taxonomy_Has32UniqueCodes_5Roots()
        {
            var all = HfacsMaTaxonomy.All;
            Assert.Equal(32, all.Count);
            Assert.Equal(32, all.Select(c => c.Code).Distinct(StringComparer.Ordinal).Count());
            var roots = all.Where(c => c.ParentCode == null).ToList();
            Assert.Equal(5, roots.Count);
            Assert.Equal(Enum.GetValues(typeof(HfacsLayer)).Cast<HfacsLayer>().OrderBy(x => x), roots.Select(r => r.Layer).OrderBy(x => x));
            Assert.All(all, c => Assert.False(string.IsNullOrWhiteSpace(c.Name)));
        }

        /// <summary>层级一致性：父节点存在、子层=父层、码以"父码-"为前缀、无环、ChildrenOf 与 ParentCode 一致、各层前缀固定（UA/PC/US/OI/EF）。</summary>
        [Fact]
        public void Taxonomy_HierarchyConsistent()
        {
            var prefix = new Dictionary<HfacsLayer, string>
            {
                [HfacsLayer.UnsafeActs] = "UA", [HfacsLayer.Preconditions] = "PC", [HfacsLayer.UnsafeSupervision] = "US",
                [HfacsLayer.OrganizationalInfluences] = "OI", [HfacsLayer.ExternalFactors] = "EF"
            };
            foreach (var c in HfacsMaTaxonomy.All)
            {
                Assert.StartsWith(prefix[c.Layer], c.Code);
                Assert.Equal(c.Layer, HfacsMaTaxonomy.LayerOf(c.Code));
                Assert.Same(c, HfacsMaTaxonomy.Get(c.Code));
                if (c.ParentCode != null)
                {
                    var p = HfacsMaTaxonomy.Get(c.ParentCode);
                    Assert.NotNull(p);
                    Assert.Equal(p.Layer, c.Layer);
                    Assert.StartsWith(p.Code + "-", c.Code);
                    Assert.Contains(c, HfacsMaTaxonomy.ChildrenOf(p.Code));
                }
                int depth = 0; var cur = c;
                while (cur.ParentCode != null) { cur = HfacsMaTaxonomy.Get(cur.ParentCode); Assert.True(++depth < 5); }
            }
            Assert.Equal(32, HfacsMaTaxonomy.All.Count(c => c.ParentCode == null) + HfacsMaTaxonomy.All.Sum(c => HfacsMaTaxonomy.ChildrenOf(c.Code).Count));
            Assert.Null(HfacsMaTaxonomy.Get("XX"));
            Assert.Null(HfacsMaTaxonomy.Get(null));
            Assert.Null(HfacsMaTaxonomy.LayerOf("XX"));
            Assert.Empty(HfacsMaTaxonomy.ChildrenOf("UA-ERR-DEC"));
        }

        /// <summary>HFACS-MA（Chauvin 2013）各层关键类目齐全：L1 决策/技能/感知差错、习惯/偶然违规；L2 物理/技术环境、心理/生理/能力局限、BRM/准备；L3 四类；L4 三类。</summary>
        [Theory]
        [InlineData("UA-ERR-DEC")][InlineData("UA-ERR-SKL")][InlineData("UA-ERR-PER")][InlineData("UA-VIO-ROU")][InlineData("UA-VIO-EXC")]
        [InlineData("PC-ENV-PHY")][InlineData("PC-ENV-TEC")][InlineData("PC-OPR-MEN")][InlineData("PC-OPR-PHY")][InlineData("PC-OPR-LIM")]
        [InlineData("PC-PER-BRM")][InlineData("PC-PER-RDY")]
        [InlineData("US-INADEQ")][InlineData("US-PLAN")][InlineData("US-FAIL-CORR")][InlineData("US-VIO")]
        [InlineData("OI-RES")][InlineData("OI-CLIM")][InlineData("OI-PROC")]
        public void Taxonomy_HfacsMaCategoriesPresent(string code) => Assert.NotNull(HfacsMaTaxonomy.Get(code));

        // ---------- HFACS 结论 ----------

        [Theory]
        [InlineData(EvidenceStrength.Strong)]
        [InlineData(EvidenceStrength.Moderate)]
        public void Finding_StrongModerate_RequireEvidenceAndEcfc(EvidenceStrength s)
        {
            var a = new HfacsAnalysis("虚构二副甲");
            Assert.Equal("hf_missing_evidence", a.AddFinding("F1", "UA-ERR-DEC", "d", s, null, Node).ErrorCode);
            Assert.Equal("hf_missing_evidence", a.AddFinding("F1", "UA-ERR-DEC", "d", s, new[] { " ", "" }, Node).ErrorCode);
            Assert.Equal("hf_missing_ecfc_link", a.AddFinding("F1", "UA-ERR-DEC", "d", s, Ev, null).ErrorCode);
            Assert.Equal("hf_missing_ecfc_link", a.AddFinding("F1", "UA-ERR-DEC", "d", s, Ev, new[] { "  " }).ErrorCode);
            Assert.Empty(a.Findings); // 失败不落库
            var ok = a.AddFinding("F1", "UA-ERR-DEC", "d", s, Ev, Node);
            Assert.True(ok.IsSuccess);
            Assert.Equal(HfacsLayer.UnsafeActs, ok.Value.Layer);
            Assert.Equal(Ev, ok.Value.EvidenceIds);
            Assert.Equal(Node, ok.Value.EcfcNodeIds);
        }

        [Fact]
        public void Finding_ToBeVerified_MayHaveNoEvidence()
        {
            var a = new HfacsAnalysis("虚构二副甲");
            Assert.True(a.AddFinding("F1", "EF-DES", "航道浮标间距偏大", EvidenceStrength.ToBeVerified, null, null).IsSuccess);
            Assert.Equal(HfacsLayer.ExternalFactors, a.Findings[0].Layer);
        }

        [Fact]
        public void Finding_Validation_Codes()
        {
            var a = new HfacsAnalysis("虚构二副甲");
            Assert.Equal("hf_unknown_category", a.AddFinding("F1", "UA-XXX", "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.Equal("hf_unknown_category", a.AddFinding("F1", null, "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.Equal("hf_invalid_argument", a.AddFinding(" ", "UA", "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node).IsSuccess);
            Assert.Equal("hf_duplicate_finding", a.AddFinding("F1", "PC-OPR-PHY", "d", EvidenceStrength.Strong, Ev, Node).ErrorCode);
            Assert.Single(a.Findings);
        }

        [Fact]
        public void Finding_Ledger_RegisteredEvidenceRequired()
        {
            var ledger = LedgerWith("EV-001", "EV-003");
            var a = new HfacsAnalysis("虚构二副甲");
            Assert.Equal("hf_unknown_evidence", a.AddFinding("F1", "PC-ENV-PHY", "d", EvidenceStrength.Strong, new[] { "EV-001", "EV-999" }, Node, ledger).ErrorCode);
            Assert.Equal("hf_unknown_evidence", a.AddFinding("F1", "PC-ENV-PHY", "d", EvidenceStrength.ToBeVerified, new[] { "EV-999" }, null, ledger).ErrorCode);
            Assert.True(a.AddFinding("F1", "PC-ENV-PHY", "d", EvidenceStrength.Strong, new[] { "EV-001", "EV-003", "EV-001" }, Node, ledger).IsSuccess);
            Assert.Equal(new[] { "EV-001", "EV-003" }, a.Findings[0].EvidenceIds); // 去重保序
        }

        [Fact]
        public void Analysis_ByLayer_CountByLayer()
        {
            // D05：未确认的草稿不计入 ByLayer / CountByLayer；IncludingDrafts 版本另计。
            var a = new HfacsAnalysis("虚构二副甲");
            Assert.True(a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, Ev, Node).IsSuccess);
            Assert.True(a.AddFinding("F2", "UA-VIO-EXC", "d", EvidenceStrength.Moderate, Ev, Node).IsSuccess);
            Assert.True(a.AddFinding("F3", "OI-PROC", "d", EvidenceStrength.ToBeVerified, null, null).IsSuccess);

            var c = a.CountByLayer();
            Assert.Equal(5, c.Count);
            Assert.Equal(0, c[HfacsLayer.UnsafeActs]);
            Assert.Equal(0, c[HfacsLayer.OrganizationalInfluences]);
            Assert.Equal(0, c[HfacsLayer.ExternalFactors]);
            Assert.Empty(a.ByLayer(HfacsLayer.UnsafeActs));

            var d = a.CountByLayerIncludingDrafts();
            Assert.Equal(2, d[HfacsLayer.UnsafeActs]);
            Assert.Equal(1, d[HfacsLayer.OrganizationalInfluences]);
            Assert.Equal(0, d[HfacsLayer.ExternalFactors]);
            Assert.Equal(new[] { "F1", "F2" }, a.ByLayerIncludingDrafts(HfacsLayer.UnsafeActs).Select(f => f.Id));

            Assert.True(a.Confirm("F1", "调查员甲", T0).IsSuccess);
            Assert.True(a.Confirm("F2", "调查员甲", T0).IsSuccess);
            c = a.CountByLayer();
            Assert.Equal(2, c[HfacsLayer.UnsafeActs]);
            Assert.Equal(0, c[HfacsLayer.OrganizationalInfluences]); // F3 仍为草稿
            Assert.Equal(new[] { "F1", "F2" }, a.ByLayer(HfacsLayer.UnsafeActs).Select(f => f.Id));
            Assert.Equal(1, a.CountByLayerIncludingDrafts()[HfacsLayer.OrganizationalInfluences]);
        }

        /// <summary>未定义的证据强度枚举值（如 99）应被拒绝（hf_invalid_argument），不得作为结论落库（BRM SetResult 已对枚举做同样校验）。</summary>
        [Fact]
        public void W18_D04_Finding_UndefinedStrength_Rejected()
        {
            var a = new HfacsAnalysis("虚构二副甲");
            var r = a.AddFinding("F1", "UA-ERR-DEC", "d", (EvidenceStrength)99, Ev, Node);
            Assert.False(r.IsSuccess);
            Assert.Equal("hf_invalid_argument", r.ErrorCode);
        }

        /// <summary>
        /// ARCHITECTURE §15.5：⑤ HFACS 分类由人员/作业智能体给出建议，"均为草稿，经人工确认后才生效"；§15.3 DoD"所有智能体输出都要经人工确认并写入审计"；
        /// 原型 13"4 条待确认 · 已确认 9 条"。HfacsFinding 需有来源/复核状态（草稿→确认/驳回）与确认操作，并写审计。
        /// </summary>
        [Fact]
        public void W18_D05_Finding_HasDraftConfirmWorkflow()
        {
            Assert.True(typeof(HfacsFinding).GetProperties().Any(p => p.Name.Contains("Review") || p.Name.Contains("Status") || p.Name.Contains("Confirmed")), "HfacsFinding 无复核状态");
            Assert.True(typeof(HfacsAnalysis).GetMethods().Any(m => m.Name.StartsWith("Confirm")), "HfacsAnalysis 无确认操作");
        }

        // ---------- BRM ----------

        [Fact]
        public void Brm_Default6Items_MatchPrototype()
        {
            var c = BrmChecklist.CreateDefault("虚构 Mary 轮当值班组");
            Assert.Equal(new[] { "HF-CAP-01", "HF-LOOK-01", "HF-ARPA-01", "HF-HELM-01", "HF-VTS-01", "HF-RADAR-02" }, c.Items.Select(i => i.Id));
            Assert.Contains("船长", c.Items[0].Text);
            Assert.Contains("瞭望", c.Items[1].Text);
            Assert.Contains("ARPA", c.Items[2].Text);
            Assert.Contains("复", c.Items[3].Text);
            Assert.Contains("VTS", c.Items[4].Text);
            Assert.Contains("雷达双机", c.Items[5].Text);
            Assert.All(c.Items, i => Assert.Equal(BrmResult.NotAssessed, i.Result));
            var s = c.Summary();
            Assert.Equal(5, s.Count);
            Assert.Equal(6, s[BrmResult.NotAssessed]);
            Assert.Equal(0, s[BrmResult.Fail]);
        }

        /// <summary>原型 13 的评估：3 不符合、1 部分（"?"）、2 符合 → Summary 计数正确；重新评估覆盖旧结果。</summary>
        [Fact]
        public void Brm_SetResult_SummaryAndReassess()
        {
            var ledger = LedgerWith("EV-010", "EV-011");
            var c = BrmChecklist.CreateDefault("虚构 Mary 轮当值班组");
            Assert.True(c.SetResult("HF-CAP-01", BrmResult.Fail, new[] { "EV-010" }, "调查员甲", null, ledger).IsSuccess);
            Assert.True(c.SetResult("HF-LOOK-01", BrmResult.Fail, new[] { "EV-011" }, "调查员甲").IsSuccess);
            Assert.True(c.SetResult("HF-HELM-01", BrmResult.Fail, new[] { "EV-010" }, "调查员甲").IsSuccess);
            Assert.True(c.SetResult("HF-ARPA-01", BrmResult.Partial, new[] { "EV-011" }, "调查员甲").IsSuccess);
            Assert.True(c.SetResult("HF-VTS-01", BrmResult.Pass, null, "调查员甲").IsSuccess);
            Assert.True(c.SetResult("HF-RADAR-02", BrmResult.Pass, null, "调查员甲").IsSuccess);
            var s = c.Summary();
            Assert.Equal(3, s[BrmResult.Fail]); Assert.Equal(1, s[BrmResult.Partial]); Assert.Equal(2, s[BrmResult.Pass]); Assert.Equal(0, s[BrmResult.NotAssessed]);
            Assert.True(c.SetResult("HF-ARPA-01", BrmResult.NotApplicable, null, "调查员乙", "虚构：未装 ARPA").IsSuccess);
            s = c.Summary();
            Assert.Equal(0, s[BrmResult.Partial]); Assert.Equal(1, s[BrmResult.NotApplicable]);
            Assert.Equal("调查员乙", c.Items[2].Assessor);
            Assert.Equal(6, c.Items.Count);
        }

        [Fact]
        public void Brm_Validation_Codes()
        {
            var c = BrmChecklist.CreateDefault("虚构");
            Assert.Equal("hf_missing_evidence", c.SetResult("HF-CAP-01", BrmResult.Fail, null, "甲").ErrorCode);
            Assert.Equal("hf_missing_evidence", c.SetResult("HF-CAP-01", BrmResult.Partial, new[] { " " }, "甲").ErrorCode);
            Assert.Equal("hf_unknown_item", c.SetResult("HF-NOPE", BrmResult.Pass, null, "甲").ErrorCode);
            Assert.Equal("hf_unknown_item", c.SetResult(null, BrmResult.Pass, null, "甲").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.SetResult("HF-CAP-01", BrmResult.Pass, null, " ").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.SetResult("HF-CAP-01", (BrmResult)42, null, "甲").ErrorCode);
            Assert.Equal("hf_unknown_evidence", c.SetResult("HF-CAP-01", BrmResult.Pass, new[] { "EV-404" }, "甲", null, LedgerWith("EV-001")).ErrorCode);
            Assert.Equal("hf_duplicate_item", c.AddItem("HF-CAP-01", "x", "y").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.AddItem("", "x", "y").ErrorCode);
            Assert.Equal("hf_invalid_argument", c.AddItem("HF-X", " ", "y").ErrorCode);
            Assert.All(c.Items, i => Assert.Equal(BrmResult.NotAssessed, i.Result)); // 失败不改状态
            Assert.True(c.AddItem("HF-X-01", "自定义虚构项", "其他").IsSuccess);
            Assert.Equal(7, c.Summary()[BrmResult.NotAssessed]);
        }

        // ---------- 约束 ----------

        /// <summary>所有错误码常量为 hf_* 前缀（Result 约定）。</summary>
        [Fact]
        public void ErrorCodes_AllHfPrefixed()
        {
            var types = typeof(HfacsAnalysis).Assembly.GetTypes().Where(t => t.Namespace == "Mcis.Domain.HumanFactors");
            var codes = types.SelectMany(t => t.GetFields(BindingFlags.Public | BindingFlags.Static).Where(f => f.IsLiteral && f.FieldType == typeof(string) && f.Name.StartsWith("Err")))
                .Select(f => (string)f.GetRawConstantValue()).ToList();
            Assert.True(codes.Count >= 15, "codes=" + codes.Count);
            Assert.All(codes, c => Assert.StartsWith("hf_", c));
        }

        /// <summary>纯逻辑：HumanFactors 源码不引用 UnityEngine（可在 dotnet 与 Unity 双端编译）。</summary>
        [Fact]
        public void NoUnityEngineReference()
        {
            var dir = Path.Combine(RepoRoot(), "unity", "Assets", "_Project", "Scripts", "Domain", "HumanFactors");
            var files = Directory.GetFiles(dir, "*.cs");
            Assert.Equal(4, files.Length);
            Assert.All(files, f => Assert.DoesNotContain("UnityEngine", File.ReadAllText(f)));
            Assert.DoesNotContain(typeof(HfacsAnalysis).Assembly.GetReferencedAssemblies(), a => a.Name.StartsWith("UnityEngine"));
        }

        /// <summary>确定性：同序列操作 → 相同结论与计数。</summary>
        [Fact]
        public void Determinism_HfacsAndBrm()
        {
            string Run()
            {
                var a = new HfacsAnalysis("虚构");
                a.AddFinding("F1", "UA-ERR-DEC", "d", EvidenceStrength.Strong, new[] { "EV-002", "EV-001" }, Node);
                a.AddFinding("F2", "PC-OPR-PHY", "疲劳", EvidenceStrength.Moderate, Ev, new[] { "C3", "C2" });
                var c = BrmChecklist.CreateDefault("虚构");
                c.SetResult("HF-LOOK-01", BrmResult.Fail, Ev, "甲");
                return string.Join(";", a.Findings.Select(f => f.Id + f.CategoryCode + f.Layer + string.Join(",", f.EvidenceIds) + string.Join(",", f.EcfcNodeIds)))
                    + "|" + string.Join(";", c.Summary().OrderBy(k => k.Key).Select(k => k.Key + "=" + k.Value));
            }
            Assert.Equal(Run(), Run());
        }
    }
}
