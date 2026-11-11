using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Systemic;
using Xunit;
using static Mcis.Acceptance.W15.Fx;

namespace Mcis.Acceptance.W15
{
    /// <summary>AcciMap 验收。依据：Rasmussen (1997) / Svedung &amp; Rasmussen (2002) 社会-技术系统层级；规格 6 层（政府与法规、监管、公司、船舶管理、船员行为、设备与环境），因果不成环；
    /// 已接受假设：只允许上层→下层/同层，例外设备与环境→船员行为（AllowEnvironmentToCrew 默认开）。</summary>
    public class AcciMapAcceptanceTests
    {
        private static readonly AcciMapLevel[] Levels = (AcciMapLevel[])Enum.GetValues(typeof(AcciMapLevel));

        [Fact]
        public void SixLevels_TopDownOrder_ChineseLabels()
        {
            Assert.Equal(6, Levels.Length);
            Assert.Equal(new[] { "政府与法规", "监管", "公司", "船舶管理", "船员行为", "设备与环境" }, Levels.OrderBy(l => (int)l).Select(AcciMapModel.LevelLabel));
        }

        /// <summary>36 组合 × 开关两种：方向矩阵完全符合已接受假设。</summary>
        [Fact]
        public void DirectionMatrix_MatchesAcceptedAssumption()
        {
            foreach (bool allow in new[] { true, false })
            foreach (var a in Levels)
            foreach (var b in Levels)
            {
                bool expected = (int)b >= (int)a || (allow && a == AcciMapLevel.EquipmentEnvironment && b == AcciMapLevel.CrewActs);
                Assert.True(expected == AcciMapModel.IsDirectionAllowed(a, b, allow), a + "→" + b + " allow=" + allow);
            }
        }

        [Fact]
        public void Connect_DownSameSkip_Allowed_UpRejected()
        {
            var m = MiniAcciMap();
            Ok(m.Connect("N0", "N5"));  // 跨层直达
            Ok(m.Connect("N2", "N3"));
            Ok(m.AddNode("N3b", "同层", AcciMapLevel.ShipManagement, M, Ev1));
            Ok(m.Connect("N3", "N3b"));
            Code(SystemicErrors.LevelDirection, m.Connect("N4", "N3"));
            Code(SystemicErrors.LevelDirection, m.Connect("N5", "N0"));
            Code(SystemicErrors.LevelDirection, m.Connect("N5", "N3")); // 环境→船舶管理不在例外内
            Code(SystemicErrors.LevelDirection, m.Connect("N1", "N0"));
        }

        [Fact]
        public void EnvironmentToCrew_DefaultOn_ConfigurableOff()
        {
            var on = MiniAcciMap();
            Assert.True(on.AllowEnvironmentToCrew);
            Ok(on.Connect("N5", "N4"));
            var off = MiniAcciMap(false);
            Code(SystemicErrors.LevelDirection, off.Connect("N5", "N4"));
        }

        [Fact]
        public void Cycles_Rejected_IncludingViaEnvironmentException()
        {
            var m = MiniAcciMap();
            Code(SystemicErrors.Cycle, m.Connect("N4", "N4"));
            Ok(m.AddNode("A", "a", AcciMapLevel.Company, M, Ev1));
            Ok(m.AddNode("B", "b", AcciMapLevel.Company, M, Ev1));
            Ok(m.AddNode("C", "c", AcciMapLevel.Company, M, Ev1));
            Ok(m.Connect("A", "B"));
            Ok(m.Connect("B", "C"));
            Code(SystemicErrors.Cycle, m.Connect("C", "A"));
            Ok(m.Connect("N4", "N5"));
            Code(SystemicErrors.Cycle, m.Connect("N5", "N4")); // 例外方向合法但成环
            Assert.Equal(3, m.Edges.Count);
        }

        [Fact]
        public void Errors_UnknownDuplicateInvalidLevelAndCreate()
        {
            var m = MiniAcciMap();
            Code(SystemicErrors.UnknownNode, m.Connect("N0", "X"));
            Ok(m.Connect("N0", "N1"));
            Code(SystemicErrors.DuplicateEdge, m.Connect("N0", "N1"));
            Code(SystemicErrors.InvalidArgument, m.AddNode("Z", "z", (AcciMapLevel)6, M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddNode("Z", "z", (AcciMapLevel)(-1), M, Ev1));
            Code(SystemicErrors.DuplicateId, m.AddNode("N0", "dup", AcciMapLevel.Company, M, Ev1));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddNode("Z", "z", AcciMapLevel.Company, S));
            Code(SystemicErrors.InvalidId, AcciMapModel.Create("bad id", "t"));
            Code(SystemicErrors.InvalidArgument, AcciMapModel.Create("AM-1", " "));
        }

        [Fact]
        public void Validate_EmptyAndIsolated()
        {
            var e = Ok(AcciMapModel.Create("AM-E", "空"));
            Assert.True(e.Validate().Has(SystemicErrors.EmptyModel));
            var m = MiniAcciMap();
            Assert.Equal(6, m.Validate().Of(SystemicErrors.IsolatedNode).Count);
            for (int i = 0; i < 5; i++) Ok(m.Connect("N" + i, "N" + (i + 1)));
            Assert.True(m.Validate().IsValid, Issues(m.Validate()));
            Assert.Equal(1, m.ByLevel(AcciMapLevel.CrewActs).Count);
        }

        [Fact]
        public void Demo_AcciMap_Valid_AllSixLevelsUsed()
        {
            var m = SystemicDemoData.BuildAcciMap();
            var v = m.Validate(DemoContext());
            Assert.True(v.IsValid, Issues(v));
            Assert.All(Levels, l => Assert.NotEmpty(m.ByLevel(l)));
        }
    }

    /// <summary>STAMP/CAST 验收。依据：Leveson《Engineering a Safer World》(2011) 与 CAST Handbook (2019)：控制器、受控过程、控制动作、反馈；
    /// UCA 四类（未提供、提供导致危险、时机/顺序错、过早停止/持续过久）。已接受假设：缺反馈只报 sys_missing_feedback 不拒绝。</summary>
    public class StampAcceptanceTests
    {
        [Fact]
        public void UcaTypes_ExactlyFour_STPACategories()
        {
            var names = Enum.GetNames(typeof(UcaType));
            Assert.Equal(4, names.Length);
            Assert.Contains("NotProvided", names);
            Assert.Contains("ProvidedCausesHazard", names);
            Assert.Contains("WrongTimingOrOrder", names);
            Assert.Contains("StoppedTooSoonOrAppliedTooLong", names);
        }

        [Fact]
        public void Minimal_ClosedLoop_Valid_AllUcaTypesAccepted()
        {
            var m = MiniStamp();
            foreach (UcaType t in Enum.GetValues(typeof(UcaType)))
            {
                Ok(m.AddUnsafeControlAction("U" + (int)t, "UCA " + t, "CA", t, "情境", M, Ev1));
            }

            Assert.True(m.Validate().IsValid, Issues(m.Validate()));
            Assert.All(Enum.GetValues(typeof(UcaType)).Cast<UcaType>(), t => Assert.Single(m.UcasOfType(t)));
        }

        [Fact]
        public void ControlActionErrors()
        {
            var m = MiniStamp();
            Ok(m.AddController("UP", "公司", M, Ev1));
            Code(SystemicErrors.InvalidEdge, m.AddControlAction("X1", "过程发控制", "PROC", "CTL", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddControlAction("X1", "x", "CTL", "NOPE", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddControlAction("X1", "x", "CA", "PROC", M, Ev1)); // 动作 ID 不是组件
            Code(SystemicErrors.Cycle, m.AddControlAction("X1", "自控", "CTL", "CTL", M, Ev1));
            Ok(m.AddControlAction("CA-UP", "SMS", "UP", "CTL", M, Ev1));
            Code(SystemicErrors.Cycle, m.AddControlAction("X1", "层级成环", "CTL", "UP", M, Ev1));
            Code(SystemicErrors.DuplicateId, m.AddControlAction("CTL", "与组件同 ID", "UP", "PROC", M, Ev1));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddControlAction("X2", "x", "UP", "PROC", S));
        }

        /// <summary>反馈不参与成环判断（控制向下、反馈向上是正常闭环）。</summary>
        [Fact]
        public void FeedbackErrors_AndUpwardFeedbackNotACycle()
        {
            var m = MiniStamp();
            Code(SystemicErrors.InvalidEdge, m.AddFeedback("F1", "送达过程", "CTL", "PROC", M, Ev1));
            Code(SystemicErrors.Cycle, m.AddFeedback("F1", "自身", "CTL", "CTL", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddFeedback("F1", "x", "NOPE", "CTL", M, Ev1));
            Code(SystemicErrors.DuplicateId, m.AddFeedback("FB", "重复", "PROC", "CTL", M, Ev1));
            Assert.True(m.Validate().IsValid);
        }

        [Fact]
        public void UcaErrors()
        {
            var m = MiniStamp();
            Code(SystemicErrors.InvalidArgument, m.AddUnsafeControlAction("U1", "x", "CA", (UcaType)4, "c", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddUnsafeControlAction("U1", "x", "NOPE", UcaType.NotProvided, "c", M, Ev1));
            Code(SystemicErrors.UnknownNode, m.AddUnsafeControlAction("U1", "x", "FB", UcaType.NotProvided, "c", M, Ev1)); // 反馈不是控制动作
            Code(SystemicErrors.UnknownNode, m.AddUnsafeControlAction("U1", "x", "CTL", UcaType.NotProvided, "c", M, Ev1));
            Code(SystemicErrors.StrongWithoutEvidence, m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, "c", S));
            // A8：情境必填。带证据以免先被 A6 挡住。
            Code(SystemicErrors.InvalidArgument, m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, null, M, Ev1));
            Code(SystemicErrors.InvalidArgument, m.AddUnsafeControlAction("U1", "x", "CA", UcaType.NotProvided, "  ", M, Ev1));
        }

        /// <summary>缺反馈：模型照常建立（不拒绝），Validate 报 sys_missing_feedback 并指向控制动作。</summary>
        [Fact]
        public void MissingFeedback_ReportedNotRejected()
        {
            var m = Ok(StampModel.Create("ST-B", "h"));
            Ok(m.AddController("CTL", "c", M, Ev1));
            Ok(m.AddControlledProcess("PROC", "p", M, Ev1));
            Ok(m.AddControlAction("CA", "a", "CTL", "PROC", M, Ev1));
            var v = m.Validate();
            Assert.Equal(new[] { "CA" }, v.Of(SystemicErrors.MissingFeedback).Select(i => i.ElementId));
            // 反馈送到别的控制器不能闭合该回路
            Ok(m.AddController("CTL2", "另一控制器", M, Ev1));
            Ok(m.AddFeedback("FB-OTHER", "反馈到别的控制器", "PROC", "CTL2", M, Ev1));
            Assert.True(m.Validate().Has(SystemicErrors.MissingFeedback));
            Ok(m.AddFeedback("FB", "闭合", "PROC", "CTL", M, Ev1));
            Assert.False(m.Validate().Has(SystemicErrors.MissingFeedback));
        }

        [Fact]
        public void EmptyModel_AndIsolatedProcess()
        {
            var m = Ok(StampModel.Create("ST-E", "h"));
            Assert.True(m.Validate().Has(SystemicErrors.EmptyModel));
            Ok(m.AddController("CTL", "c", M, Ev1));
            Ok(m.AddControlledProcess("P1", "p1", M, Ev1));
            Ok(m.AddControlledProcess("P2", "p2", M, Ev1));
            Ok(m.AddControlAction("CA", "a", "CTL", "P1", M, Ev1));
            Ok(m.AddFeedback("FB", "f", "P1", "CTL", M, Ev1));
            var v = m.Validate();
            Assert.Equal(new[] { "P2" }, v.Of(SystemicErrors.IsolatedNode).Select(i => i.ElementId));
            Code(SystemicErrors.InvalidId, StampModel.Create("", "h"));
            Code(SystemicErrors.InvalidArgument, StampModel.Create("ST-1", null));
        }

        /// <summary>演示控制结构：唯一问题是有意缺省的 OOW→船长反馈（CAST 发现），4 类 UCA 齐全。</summary>
        [Fact]
        public void Demo_Stamp_OnlyIntentionalMissingFeedback()
        {
            var m = SystemicDemoData.BuildStamp();
            var v = m.Validate(DemoContext());
            Assert.Single(v.Issues);
            Assert.Equal(SystemicErrors.MissingFeedback, v.Issues[0].Code);
            Assert.Equal("CA-ORD", v.Issues[0].ElementId);
            Assert.All(Enum.GetValues(typeof(UcaType)).Cast<UcaType>(), t => Assert.NotEmpty(m.UcasOfType(t)));
        }
    }
}
