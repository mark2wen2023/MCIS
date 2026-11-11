using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Recommendations;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    /// <summary>节点引用（证据/ECFC/HFACS/建议）验收。规格：SystemicRefContext 只读，传哪项校验哪项；Strong 结论须有证据。</summary>
    public class RefsAcceptanceTests
    {
        private static AcciMapModel WithRefs(EvidenceStrength s, SystemicRefs r)
        {
            var m = Ok(AcciMapModel.Create("AM-R", "引用测试"));
            Ok(m.AddNode("A", "a", AcciMapLevel.Company, s, r));
            Ok(m.AddNode("B", "b", AcciMapLevel.CrewActs, M, Ev1));
            Ok(m.Connect("A", "B"));
            return m;
        }

        private static readonly SystemicRefs AllUnknown = Refs(new[] { "EV-999" }, new[] { "E99" }, new[] { "HF-F99" }, new[] { "SR-2099-99" });

        [Fact]
        public void Refs_NormalizedTrimDedupKeepOrder()
        {
            var r = new SystemicRefs(new[] { " EV-2 ", "EV-1", "EV-2", null, "  ", "EV-1" }, new[] { "E1", "E1" });
            Assert.Equal(new[] { "EV-2", "EV-1" }, r.EvidenceIds);
            Assert.Equal(new[] { "E1" }, r.EcfcNodeIds);
            Assert.Empty(r.HfacsFindingIds);
            Assert.False(r.IsEmpty);
            Assert.True(new SystemicRefs().IsEmpty);
        }

        [Fact]
        public void NoContext_NoReferenceChecks()
        {
            Assert.True(WithRefs(M, AllUnknown).Validate().IsValid);
            Assert.True(WithRefs(M, AllUnknown).Validate(new SystemicRefContext()).IsValid); // 全空上下文 = 不查
        }

        [Fact]
        public void EachKindCheckedOnlyWhenProvided()
        {
            // 21:25 / D05：每种 kind 只在提供来源时做存在性校验（报 Error）；
            // 未提供来源时不报 Error，但必须有 Info 级 sys_ref_not_checked，且 NotCheckedRefCount > 0。旧名 ref_not_checked 不再出现。
            var m = WithRefs(M, AllUnknown);
            AssertKindOnlyWhenProvided(m, new SystemicRefContext(ledger: Ledger(new[] { "EV-001" })), SystemicErrors.UnknownEvidence);
            AssertKindOnlyWhenProvided(m, new SystemicRefContext(knownEcfcNodeIds: new[] { "E1" }), SystemicErrors.UnknownEcfc);
            AssertKindOnlyWhenProvided(m, new SystemicRefContext(hfacs: Hfacs(new[] { "HF-F01" })), SystemicErrors.UnknownHfacs);
            AssertKindOnlyWhenProvided(m, new SystemicRefContext(recommendations: Board(new[] { "SR-2026-01" })), SystemicErrors.UnknownRecommendation);

            var none = m.Validate(new SystemicRefContext());
            Assert.True(none.IsValid);
            Assert.Empty(none.Errors);
            Assert.Contains(none.Issues, i => i.Severity == SystemicIssueSeverity.Info && i.Code == SystemicErrors.RefNotChecked);
            Assert.True(none.NotCheckedRefCount > 0);
            AssertNoLegacyName(none);

            var all = m.Validate(new SystemicRefContext(Ledger(new[] { "EV-001" }), Hfacs(new[] { "HF-F01" }), Board(new[] { "SR-2026-01" }), new[] { "E1" }));
            Assert.Equal(4, all.Errors.Count);
            Assert.All(all.Errors, i => Assert.Equal("A", i.ElementId));
            Assert.Equal(0, all.NotCheckedRefCount);
            Assert.DoesNotContain(all.Issues, i => i.Code == SystemicErrors.RefNotChecked);
            AssertNoLegacyName(all);

            foreach (var f in typeof(SystemicErrors).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (f.FieldType != typeof(string)) continue;
                string v = (string)f.GetValue(null);
                Assert.NotEqual("ref_not_checked", v);
                Assert.StartsWith("sys_", v);
            }
        }

        private static void AssertKindOnlyWhenProvided(AcciMapModel m, SystemicRefContext ctx, string expectedError)
        {
            var v = m.Validate(ctx);
            Assert.Equal(new[] { expectedError }, v.Errors.Select(i => i.Code));
            Assert.Contains(v.Issues, i => i.Severity == SystemicIssueSeverity.Info && i.Code == SystemicErrors.RefNotChecked);
            Assert.Equal("sys_ref_not_checked", SystemicErrors.RefNotChecked);
            Assert.True(v.NotCheckedRefCount > 0);
            AssertNoLegacyName(v);
        }

        private static void AssertNoLegacyName(SystemicValidation v)
        {
            Assert.DoesNotContain(v.Issues, i => i.Code == "ref_not_checked");
            Assert.DoesNotContain(v.Issues, i => i.Message != null && i.Message.IndexOf("ref_not_checked", StringComparison.Ordinal) >= 0 && i.Message.IndexOf("sys_ref_not_checked", StringComparison.Ordinal) < 0);
        }

        [Fact]
        public void KnownRefs_Pass_InAllThreeModels()
        {
            var ctx = DemoContext();
            var doc = SystemicDemoData.Build();
            var v = doc.Validate(ctx);
            Assert.Equal(new[] { SystemicErrors.MissingFeedback }, v.Issues.Select(i => i.Code)); // 只剩有意缺省的反馈
        }

        /// <summary>Strong 节点引用了未登记证据：结构上有证据 ID，但在 ledger 下报 sys_unknown_evidence。</summary>
        [Fact]
        public void StrongWithUnregisteredEvidence_FlaggedUnderLedger()
        {
            var m = WithRefs(S, Ev("EV-404"));
            Assert.True(m.Validate().IsValid);
            var v = m.Validate(new SystemicRefContext(ledger: Ledger(new[] { "EV-001" })));
            Assert.Equal(SystemicErrors.UnknownEvidence, Assert.Single(v.Issues).Code);
        }

        /// <summary>只读：校验前后 ledger 事件、HFACS 发现、建议看板不变（查证据不得产生 Access 留痕）。</summary>
        [Fact]
        public void Context_IsReadOnly()
        {
            var ledger = Ledger(new[] { "EV-001", "EV-002" });
            var hf = Hfacs(new[] { "HF-F01" });
            var board = Board(new[] { "SR-2026-01" });
            int ev = ledger.Events.Count, lines = ledger.JsonLines.Count, f = hf.Findings.Count, b = board.All.Count;
            var hist = board.Get("SR-2026-01").History.Count;
            var ctx = new SystemicRefContext(ledger, hf, board, new[] { "E1" });
            var m = WithRefs(S, Refs(new[] { "EV-001", "EV-404" }, new[] { "E1" }, new[] { "HF-F01" }, new[] { "SR-2026-01" }));
            m.Validate(ctx);
            m.Validate(ctx);
            Assert.Equal(ev, ledger.Events.Count);
            Assert.Equal(lines, ledger.JsonLines.Count);
            Assert.Equal(0, ledger.AccessCount("EV-001"));
            Assert.Equal(f, hf.Findings.Count);
            Assert.Equal(b, board.All.Count);
            Assert.Equal(hist, board.Get("SR-2026-01").History.Count);
        }

        [Fact]
        public void RefsChecked_OnEveryElementType()
        {
            var ctx = new SystemicRefContext(ledger: Ledger(new[] { "EV-001" }));
            var bad = Ev("EV-404");
            var bt = MiniBowTie();
            Ok(bt.AddEscalationFactor("EF", "ef", "PB1", M, bad));
            Assert.Contains(bt.Validate(ctx).Issues, i => i.Code == SystemicErrors.UnknownEvidence && i.ElementId == "EF");
            var st = MiniStamp();
            Ok(st.AddUnsafeControlAction("U", "u", "CA", UcaType.NotProvided, "c", M, bad));
            Ok(st.AddFeedback("FB2", "f2", "PROC", "CTL", M, bad));
            var ids = st.Validate(ctx).Of(SystemicErrors.UnknownEvidence).Select(i => i.ElementId).ToArray();
            Assert.Contains("U", ids);
            Assert.Contains("FB2", ids);
        }
    }

    /// <summary>JSON 往返验收（schema mcis.systemic/1），Result 与 sys_* 错误码、确定性、无 UnityEngine。</summary>
    public class JsonAcceptanceTests
    {
        [Fact]
        public void Demo_RoundTrip_ByteIdentical_SchemaAndFlagsPreserved()
        {
            var doc = SystemicDemoData.Build();
            string j1 = doc.ToJson();
            Assert.StartsWith("{\"schema\":\"mcis.systemic/1\"", j1);
            var back = Ok(SystemicDocument.FromJson(j1));
            Assert.Equal(j1, back.ToJson());
            Assert.True(back.IsFictionalDemo);
            Assert.Equal(SystemicDemoData.CaseId, back.CaseId);
            Assert.Equal(doc.BowTie.Elements.Count, back.BowTie.Elements.Count);
            Assert.Equal(doc.AcciMap.Edges.Count, back.AcciMap.Edges.Count);
            Assert.Equal(doc.Stamp.UnsafeControlActions.Count, back.Stamp.UnsafeControlActions.Count);
            Assert.Equal(Issues(doc.Validate(DemoContext())), Issues(back.Validate(DemoContext())));
        }

        [Fact]
        public void RoundTrip_PreservesStateBarrierIdLevelsUcaTypeAndRefs()
        {
            var back = Ok(SystemicDocument.FromJson(SystemicDemoData.Build().ToJson()));
            Assert.Equal(BarrierState.Missing, back.BowTie.Get("PB-LOOK").State);
            Assert.Equal("PB-BRM", back.BowTie.Get("EF-MASTER").BarrierId);
            Assert.Equal(AcciMapLevel.Government, back.AcciMap.Get("G1").Level);
            Assert.Equal(UcaType.StoppedTooSoonOrAppliedTooLong, ((UnsafeControlAction)back.Stamp.Get("UCA-4")).Type);
            var r = back.BowTie.Get("PB-FOG").Refs;
            Assert.Equal(new[] { "EV-001", "EV-008" }, r.EvidenceIds);
            Assert.Equal(new[] { "SR-2026-02" }, r.RecommendationIds);
            Assert.Equal(EvidenceStrength.ToBeVerified, back.BowTie.Get("PB-PLAN").Strength);
        }

        [Fact]
        public void RoundTrip_AllowEnvFalse_And_MissingFeedbackModelNotRejected()
        {
            var am = MiniAcciMap(false);
            for (int i = 0; i < 5; i++) Ok(am.Connect("N" + i, "N" + (i + 1)));
            var st = Ok(StampModel.Create("ST-B", "h"));
            Ok(st.AddController("C", "c", M, Ev1));
            Ok(st.AddControlledProcess("P", "p", M, Ev1));
            Ok(st.AddControlAction("A", "a", "C", "P", M, Ev1));
            var doc = new SystemicDocument("CASE-X1", false, null, am, st);
            var back = Ok(SystemicDocument.FromJson(doc.ToJson()));
            Assert.False(back.AcciMap.AllowEnvironmentToCrew);
            Assert.Null(back.BowTie);
            Assert.True(back.Validate().Has(SystemicErrors.MissingFeedback));
            Assert.Equal(doc.ToJson(), back.ToJson());
        }

        [Fact]
        public void SpecialCharacters_RoundTrip()
        {
            string label = "引号\" 反斜杠\\ 斜杠/ 换行\n 回车\r 制表\t 退格\b 换页\f 控制\u0001\u001f emoji🚢 中文 ‘’“” \u2028";
            var am = Ok(AcciMapModel.Create("AM-S", label));
            Ok(am.AddNode("A", label, AcciMapLevel.Company, M, Refs(new[] { "EV:\"1\"" })));
            Ok(am.AddNode("B", "b", AcciMapLevel.CrewActs, M, Ev1));
            Ok(am.Connect("A", "B"));
            var doc = new SystemicDocument("CASE-S", false, null, am, null);
            var back = Ok(SystemicDocument.FromJson(doc.ToJson()));
            Assert.Equal(label, back.AcciMap.Title);
            Assert.Equal(label, back.AcciMap.Get("A").Label);
            Assert.Equal("EV:\"1\"", back.AcciMap.Get("A").Refs.EvidenceIds[0]);
            Assert.Equal(doc.ToJson(), back.ToJson());
        }

        [Fact]
        public void Pretty_Whitespace_AndUnknownExtraFields_Tolerated()
        {
            string j = SystemicDemoData.Build().ToJson();
            string pretty = j.Replace(",", ",\n  ").Replace("{", "{\r\n\t").Replace(":", " : ");
            // 字符串内容里没有逗号/冒号/花括号才能这样粗暴格式化；演示数据里含中文冒号与逗号不受影响
            var back = SystemicDocument.FromJson(pretty);
            Assert.True(back.IsSuccess, back.ErrorMessage);
        }

        [Fact]
        public void EmptyDocument_RoundTrip_EmptyModel()
        {
            var d = new SystemicDocument("CASE-E", false);
            var back = Ok(SystemicDocument.FromJson(d.ToJson()));
            Assert.Null(back.BowTie);
            Assert.Null(back.AcciMap);
            Assert.Null(back.Stamp);
            Assert.Equal(SystemicErrors.EmptyModel, Assert.Single(back.Validate().Issues).Code);
        }

        [Theory]
        [InlineData("")]
        [InlineData("   ")]
        [InlineData("{")]
        [InlineData("[]")]
        [InlineData("\"mcis.systemic/1\"")]
        [InlineData("{\"schema\":\"mcis.systemic/1\"} x")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false}")]
        [InlineData("{'schema':'mcis.systemic/1'}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":\"false\"}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":5}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":{\"id\":\"A\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[{\"id\":\"N\",\"label\":\"n\",\"strength\":\"Moderate\",\"level\":\"Crew\"}],\"edges\":[]}}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":{\"id\":\"A\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[{\"id\":\"N\",\"label\":\"n\",\"strength\":\"1\",\"level\":\"Company\"}],\"edges\":[]}}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":{\"id\":\"A\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[{\"id\":\"N\",\"label\":\"n\",\"strength\":\"moderate\",\"level\":\"Company\"}],\"edges\":[]}}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":{\"id\":\"A\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[],\"edges\":[[\"A\"]]}}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false,\"acciMap\":{\"id\":\"A\",\"title\":\"t\",\"allowEnvironmentToCrew\":true,\"nodes\":[{\"id\":\"N\",\"label\":\"n\",\"strength\":\"Moderate\",\"level\":\"Company\",\"refs\":{\"evidence\":\"EV-1\"}}],\"edges\":[]}}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":\"x\\q\",\"isFictionalDemo\":false}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":\"\\u12\",\"isFictionalDemo\":false}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":\"tab\there\",\"isFictionalDemo\":false}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":-,\"isFictionalDemo\":false}")]
        [InlineData("{\"schema\":\"mcis.systemic/1\",\"caseId\":nul,\"isFictionalDemo\":false}")]
        [InlineData("\uFEFF{\"schema\":\"mcis.systemic/1\",\"caseId\":null,\"isFictionalDemo\":false}")]
        public void Malformed_IsJsonInvalid(string json)
        {
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(json));
        }

        [Fact]
        public void Null_DeepNesting_HugeNesting_NoThrow()
        {
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(null));
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(new string('[', 65) + new string(']', 65)));
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(new string('[', 200000)));
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson("{\"a\":" + string.Concat(Enumerable.Repeat("{\"a\":", 100000))));
        }

        [Fact]
        public void WrongOrMissingSchema()
        {
            string j = SystemicDemoData.Build().ToJson();
            Code(SystemicErrors.JsonUnsupportedSchema, SystemicDocument.FromJson(j.Replace("mcis.systemic/1", "mcis.systemic/2")));
            Code(SystemicErrors.JsonUnsupportedSchema, SystemicDocument.FromJson(j.Replace("mcis.systemic/1", "MCIS.SYSTEMIC/1")));
            var missing = SystemicDocument.FromJson("{\"caseId\":null,\"isFictionalDemo\":false}");
            Assert.False(missing.IsSuccess);
            Assert.StartsWith("sys_json_", missing.ErrorCode);
        }

        /// <summary>篡改 JSON：反序列化走 Add/Connect 重放，结构规则原样执行并返回对应 sys_* 码。</summary>
        [Fact]
        public void Tampered_StructuralRulesEnforcedOnLoad()
        {
            string j = SystemicDemoData.Build().ToJson();
            // AcciMap 上行边
            Code(SystemicErrors.LevelDirection, SystemicDocument.FromJson(j.Replace("[\"G1\",\"R1\"]", "[\"R1\",\"G1\"]")));
            // AcciMap 成环（EE5 → G1 是上行，先被方向拒；换同层环 CA2 → CA1）
            Code(SystemicErrors.Cycle, SystemicDocument.FromJson(j.Replace("[\"CA1\",\"CA2\"]", "[\"CA1\",\"CA2\"],[\"CA2\",\"CA1\"]")));
            // Bow-tie 非法边：威胁直达后果
            Code(SystemicErrors.InvalidEdge, SystemicDocument.FromJson(j.Replace("[\"T-VIS\",\"PB-FOG\"]", "[\"T-VIS\",\"CQ-SINK\"]")));
            // 重复边
            Code(SystemicErrors.DuplicateEdge, SystemicDocument.FromJson(j.Replace("[\"G1\",\"R1\"]", "[\"G1\",\"R1\"],[\"G1\",\"R1\"]")));
            // 关闭例外后环境→船员边被拒
            Code(SystemicErrors.LevelDirection, SystemicDocument.FromJson(j.Replace("\"allowEnvironmentToCrew\":true", "\"allowEnvironmentToCrew\":false")));
            // Strong 去掉证据
            Code(SystemicErrors.StrongWithoutEvidence, SystemicDocument.FromJson(j.Replace("\"refs\":{\"evidence\":[\"EV-007\"],\"ecfc\":[\"C4\"]", "\"refs\":{\"evidence\":[],\"ecfc\":[\"C4\"]")));
            // 顶事件出现在 elements 中
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(j.Replace("\"kind\":\"Threat\"", "\"kind\":\"TopEvent\"")));
            // 未知 UCA 类型
            Code(SystemicErrors.JsonInvalid, SystemicDocument.FromJson(j.Replace("\"type\":\"NotProvided\"", "\"type\":\"TooLate\"")));
            // 控制动作由受控过程发出
            Code(SystemicErrors.InvalidEdge, SystemicDocument.FromJson(j.Replace("\"controller\":\"OOW\",\"target\":\"SHIP-M\"", "\"controller\":\"SHIP-M\",\"target\":\"OOW\"")));
            // 重复 ID
            Code(SystemicErrors.DuplicateId, SystemicDocument.FromJson(j.Replace("{\"id\":\"R2\"", "{\"id\":\"R1\"")));
        }

        [Fact]
        public void Determinism_BuildTwice_SameJson_SameIssues()
        {
            Assert.Equal(SystemicDemoData.Build().ToJson(), SystemicDemoData.Build().ToJson());
            var a = SystemicDemoData.Build().Validate(DemoContext());
            var b = SystemicDemoData.Build().Validate(DemoContext());
            Assert.Equal(Issues(a), Issues(b));
            var m1 = MiniBowTie(); Ok(m1.AddThreat("X", "x", M, Ev1)); Ok(m1.AddConsequence("Y", "y", M, Ev1));
            var m2 = MiniBowTie(); Ok(m2.AddThreat("X", "x", M, Ev1)); Ok(m2.AddConsequence("Y", "y", M, Ev1));
            Assert.Equal(Issues(m1.Validate()), Issues(m2.Validate()));
        }

        [Fact]
        public void Determinism_CultureIndependent()
        {
            var prev = System.Globalization.CultureInfo.CurrentCulture;
            string baseline = SystemicDemoData.Build().ToJson();
            try
            {
                foreach (var c in new[] { "tr-TR", "de-DE", "ar-SA", "zh-CN" })
                {
                    System.Globalization.CultureInfo.CurrentCulture = new System.Globalization.CultureInfo(c);
                    Assert.Equal(baseline, SystemicDemoData.Build().ToJson());
                    Assert.True(SystemicDocument.FromJson(baseline).IsSuccess);
                }
            }
            finally
            {
                System.Globalization.CultureInfo.CurrentCulture = prev;
            }
        }

        [Fact]
        public void ErrorCodes_AllSysPrefixed_AndUnique()
        {
            var codes = typeof(SystemicErrors).GetFields(BindingFlags.Public | BindingFlags.Static).Select(f => (string)f.GetValue(null)).ToArray();
            Assert.NotEmpty(codes);
            Assert.All(codes, c => Assert.StartsWith("sys_", c));
            Assert.Equal(codes.Length, codes.Distinct().Count());
            // 源码中出现的所有 "xxx_yyy" 风格错误码字面量都应为 sys_
            foreach (var f in Directory.GetFiles(SystemicDir(), "*.cs"))
            {
                foreach (System.Text.RegularExpressions.Match m in System.Text.RegularExpressions.Regex.Matches(File.ReadAllText(f), "\"([a-z]+_[a-z_]+)\""))
                {
                    Assert.StartsWith("sys_", m.Groups[1].Value);
                }
            }
        }

        [Fact]
        public void NoUnityEngine_NoDataAssembly_SevenFilesPresent()
        {
            var files = Directory.GetFiles(SystemicDir(), "*.cs").Select(Path.GetFileName).OrderBy(x => x).ToArray();
            foreach (var n in new[] { "SystemicCommon.cs", "BowTie.cs", "AcciMap.cs", "StampCast.cs", "SystemicJson.cs", "SystemicDocument.cs", "SystemicDemoData.cs" })
            {
                Assert.Contains(n, files);
            }

            foreach (var f in Directory.GetFiles(SystemicDir(), "*.cs"))
            {
                string s = File.ReadAllText(f);
                Assert.DoesNotContain("UnityEngine", s);
                Assert.DoesNotContain("using Mcis.Data", s);
            }

            Assert.DoesNotContain(typeof(SystemicDocument).Assembly.GetReferencedAssemblies(), a => a.Name.StartsWith("UnityEngine"));
        }

        /// <summary>公共 API 对 null/垃圾输入返回 Result 失败而不抛异常。</summary>
        [Fact]
        public void PublicApi_NullInputs_NoThrow()
        {
            var bt = MiniBowTie();
            Code(SystemicErrors.InvalidId, BowTieModel.Create(null, null, null, null));
            Code(SystemicErrors.InvalidArgument, BowTieModel.Create("BT", null, "TOP", "t"));
            Code(SystemicErrors.InvalidArgument, bt.AddConsequence("C9", null, M, Ev1));
            Assert.Null(bt.Get(null));
            var am = MiniAcciMap();
            Code(SystemicErrors.UnknownNode, am.Connect(null, "N1"));
            Assert.Null(am.Get(null));
            var st = MiniStamp();
            Code(SystemicErrors.UnknownNode, st.AddControlAction("X", "x", null, null, M, Ev1));
            Code(SystemicErrors.UnknownNode, st.AddFeedback("X", "x", null, "CTL", M, Ev1));
            Code(SystemicErrors.UnknownNode, st.AddUnsafeControlAction("X", "x", null, UcaType.NotProvided, null, M, Ev1));
            Assert.Null(st.Get(null));
            Assert.True(new SystemicRefs(null, null, null, null).IsEmpty);
            Assert.True(new SystemicRefContext(null, null, null, new string[] { null }) != null);
        }

        // ------------------------------------------------------------------ 已知缺陷

        /// <summary>W15-D01：模型公开的集合是内部可变实例（List / string[]），调用方强转后可绕过 Add/Connect 的全部结构规则，
        /// 随后 ToJson 写出的文件无法再被 FromJson 读回（或 Strong 证据规则被绕过）。期望：公开只读视图/副本，篡改不影响模型。</summary>
        [Fact]
        public void W15_D01_ExposedCollections_CannotBypassStructuralRules()
        {
            var bt = MiniBowTie();
            var am = MiniAcciMap();
            for (int i = 0; i < 5; i++) Ok(am.Connect("N" + i, "N" + (i + 1)));
            var strong = Ok(am.AddNode("SX", "Strong 结论", AcciMapLevel.Company, S, Ev("EV-001")));
            Ok(am.Connect("SX", "N4"));

            var tampered = new List<string>();
            if (bt.Edges is IList<SystemicEdge> edges && !edges.IsReadOnly)
            {
                try { edges.Add(new SystemicEdge("C1", "T1")); tampered.Add("BowTie.Edges.Add(后果→威胁)"); } catch (NotSupportedException) { }
            }

            if (bt.Elements is IList<BowTieElement> els && !els.IsReadOnly)
            {
                try { els.RemoveAt(0); tampered.Add("BowTie.Elements.RemoveAt(顶事件)"); } catch (NotSupportedException) { }
            }

            if (am.Edges is IList<SystemicEdge> aed && !aed.IsReadOnly)
            {
                try { aed.Add(new SystemicEdge("N5", "N0")); tampered.Add("AcciMap.Edges.Add(上行边)"); } catch (NotSupportedException) { }
            }

            if (strong.Refs.EvidenceIds is IList<string> ev)
            {
                try { ev[0] = " "; tampered.Add("Refs.EvidenceIds[0]=\" \"(Strong 去证据)"); } catch (NotSupportedException) { }
            }

            var load = SystemicDocument.FromJson(new SystemicDocument("CASE-T", false, bt, am, null).ToJson());
            Assert.True(tampered.Count == 0 && load.IsSuccess,
                "可被篡改：" + string.Join("；", tampered) + "；写出的 JSON 读回结果：" + (load.IsSuccess ? "成功" : load.ErrorCode));
        }
    }
}
