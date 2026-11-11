using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Mcis.Domain.Recommendations;
using Mcis.Domain.Systemic;
using Xunit;

namespace Mcis.Acceptance.W15
{
    /// <summary>W15 验收公共夹具。所有演示数据均为虚构；真实案例只读 reports/haili5/（Mark 已同意）。</summary>
    internal static class Fx
    {
        public const EvidenceStrength S = EvidenceStrength.Strong;
        public const EvidenceStrength M = EvidenceStrength.Moderate;
        public const EvidenceStrength V = EvidenceStrength.ToBeVerified;
        public static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 5, 18, 14, 30, 0, TimeSpan.FromHours(8));
        private const string Sha = "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd";

        public static SystemicRefs Ev(params string[] ids) { return new SystemicRefs(ids); }

        /// <summary>A6： Moderate 节点的默认证据（夹具用，虚构）。</summary>
        public static readonly SystemicRefs Ev1 = Ev("EV-001");

        public static SystemicRefs Refs(string[] ev = null, string[] ecfc = null, string[] hf = null, string[] sr = null)
        {
            return new SystemicRefs(ev, ecfc, hf, sr);
        }

        public static T Ok<T>(Result<T> r)
        {
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static void Code<T>(string code, Result<T> r)
        {
            Assert.False(r.IsSuccess, "期望失败 " + code + "，实际成功");
            Assert.Equal(code, r.ErrorCode);
        }

        public static CustodyLedger Ledger(IEnumerable<string> ids)
        {
            var l = new CustodyLedger();
            foreach (var id in ids)
            {
                Ok(l.Register(new EvidenceItem(id, "虚构证据 " + id, "VDR", "调查员甲", T0, Sha), "调查员甲", T0));
            }

            return l;
        }

        public static HfacsAnalysis Hfacs(IEnumerable<string> ids)
        {
            var a = new HfacsAnalysis("虚构对象");
            foreach (var id in ids)
            {
                Ok(a.AddFinding(id, "UA", "虚构发现", EvidenceStrength.ToBeVerified, null, null));
            }

            return a;
        }

        public static SafetyRecommendationBoard Board(IEnumerable<string> ids)
        {
            var b = new SafetyRecommendationBoard(new InMemoryInvestigationAuditSink());
            foreach (var id in ids)
            {
                Ok(b.CreateDraft(id, "虚构建议 " + id, "虚构机构", new[] { "E4" }, T0.AddDays(90), "调查员甲", T0));
            }

            return b;
        }

        public static SystemicRefContext DemoContext()
        {
            return new SystemicRefContext(
                Ledger(SystemicDemoData.EvidenceIds),
                Hfacs(SystemicDemoData.HfacsFindingIds),
                Board(SystemicDemoData.RecommendationIds),
                SystemicDemoData.EcfcNodeIds);
        }

        /// <summary>最小合法 Bow-tie：T1 → PB1 → TOP → MB1 → C1。</summary>
        public static BowTieModel MiniBowTie()
        {
            var m = Ok(BowTieModel.Create("BT-A", "窄航道雾中会遇（虚构）", "TOP", "两船碰撞（虚构）"));
            Ok(m.AddThreat("T1", "能见度不良", M, Ev1));
            Ok(m.AddBarrier("PB1", "雷达观测", BowTieElementKind.PreventionBarrier, BarrierState.Failed, M, Ev1));
            Ok(m.AddBarrier("MB1", "水密分舱", BowTieElementKind.MitigationBarrier, BarrierState.Effective, M, Ev1));
            Ok(m.AddConsequence("C1", "进水", M, Ev1));
            Ok(m.Connect("T1", "PB1"));
            Ok(m.Connect("PB1", "TOP"));
            Ok(m.Connect("TOP", "MB1"));
            Ok(m.Connect("MB1", "C1"));
            return m;
        }

        /// <summary>最小合法 STAMP：CTL → PROC，闭合反馈。</summary>
        public static StampModel MiniStamp()
        {
            var m = Ok(StampModel.Create("ST-A", "两船碰撞（虚构）"));
            Ok(m.AddController("CTL", "值班驾驶员", M, Ev1));
            Ok(m.AddControlledProcess("PROC", "船舶运动", M, Ev1));
            Ok(m.AddControlAction("CA", "舵令", "CTL", "PROC", M, Ev1));
            Ok(m.AddFeedback("FB", "雷达", "PROC", "CTL", M, Ev1));
            return m;
        }

        public static AcciMapModel MiniAcciMap(bool allowEnv = true)
        {
            var m = Ok(AcciMapModel.Create("AM-A", "虚构 AcciMap", allowEnv));
            foreach (AcciMapLevel l in Enum.GetValues(typeof(AcciMapLevel)))
            {
                Ok(m.AddNode("N" + (int)l, "层节点 " + l, l, M, Ev1));
            }

            return m;
        }

        public static string RepoRoot()
        {
            var d = new DirectoryInfo(AppContext.BaseDirectory);
            while (d != null && !Directory.Exists(Path.Combine(d.FullName, "unity", "Assets", "_Project")))
            {
                d = d.Parent;
            }

            Assert.NotNull(d);
            return d.FullName;
        }

        public static string SystemicDir()
        {
            return Path.Combine(RepoRoot(), "unity", "Assets", "_Project", "Scripts", "Domain", "Systemic");
        }

        public static string Issues(SystemicValidation v)
        {
            return string.Join(" | ", v.Issues.Select(i => i.ToString()));
        }
    }
}
