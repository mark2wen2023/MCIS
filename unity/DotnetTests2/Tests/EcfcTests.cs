using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Ecfc;
using Mcis.Domain.Models;
using Mcis.Fixtures;
using Mcis.Simulation.Ecfc;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class EcfcTests
    {
        [Fact]
        public void Validator_Table4_FlagsEventToCondition_AndMissingPresumptive_AndRequiresSingleIncident()
        {
            var e1 = Event("E1", "Lily 轮出港", 0, 0, false);
            var e2 = Event("E2", "两船发生碰撞", 10, 0, true);
            var c1 = new EcfcNode("C1", EcfcNodeKind.Condition, "能见度低", new SimTime(0), null, 1, false, false, null, null, null, Array.Empty<string>());
            // 故意：事件指向条件（禁止）；条件无证据且未标推定
            var edges = new[]
            {
                new EcfcEdge("x", "E1", "E2", EcfcEdgeKind.Sequence, true),
                new EcfcEdge("bad", "E1", "C1", EcfcEdgeKind.Sequence, false)
            };
            var issues = EcfcValidator.Validate(new[] { e1, e2, c1 }, edges);
            Assert.Contains(issues, i => i.RuleCode == "ECFC-E03" && i.IsError);
            Assert.Contains(issues, i => i.RuleCode == "ECFC-E08" && i.RelatedNodeId == "C1");

            var issues2 = EcfcValidator.Validate(new[] { Event("E1b", "Lily 轮出港", 0, 0, true), Event("E3", "Mary 轮进港", 0, 0, true) }, new[] { new EcfcEdge("a", "E1b", "E3", EcfcEdgeKind.Sequence, true) });
            Assert.Contains(issues2, i => i.RuleCode == "ECFC-E06"); // two primary incidents
        }

        [Fact]
        public void ConnectNodes_DerivesSolidForEvents_DashedForConditions()
        {
            var svc = new EcfcService();
            svc.UpsertNode(Event("E1", "Lily 轮出港", 0, 0, false));
            svc.UpsertNode(Event("E2", "两船发生碰撞", 10, 0, true));
            var c = new EcfcNode("C1", EcfcNodeKind.Condition, "涨潮流急", new SimTime(0), null, 1, false, false, null, null, Q("流速", "1.8 kn"), new[] { "ev" });
            svc.UpsertNode(c);

            var evEdge = svc.ConnectNodes("E1", "E2");
            Assert.True(evEdge.IsSuccess, evEdge.ErrorMessage);
            Assert.Equal(EcfcEdgeKind.Sequence, evEdge.Value.Kind);
            Assert.True(evEdge.Value.IsPrimarySequenceBold);

            var condEdge = svc.ConnectNodes("C1", "E2");
            Assert.True(condEdge.IsSuccess);
            Assert.Equal(EcfcEdgeKind.Influence, condEdge.Value.Kind);
            Assert.False(condEdge.Value.IsPrimarySequenceBold);

            var forbidden = svc.ConnectNodes("E1", "C1");
            Assert.False(forbidden.IsSuccess);
        }

        [Fact]
        public void Layout_PlacesPrimaryLaneHorizontally_AndVisibleCardsFollowSimTime()
        {
            var svc = new EcfcService(8.0);
            LilyMaryDemo.PopulateEcfc(svc);
            var layout = svc.ComputeAutoLayout();
            Assert.True(layout["E1"].Y == layout["E7"].Y);
            Assert.True(layout["E7"].X > layout["E1"].X);
            Assert.True(layout.ContainsKey("C1"));

            var atStart = svc.GetVisibleCardsAt(new SimTime(0));
            Assert.Contains(atStart, n => n.NodeId == "E1");
            Assert.DoesNotContain(atStart, n => n.NodeId == "E7");

            var atCollision = svc.GetVisibleCardsAt(LilyMaryDemo.CollisionTime);
            Assert.Contains(atCollision, n => n.NodeId == "E7" && n.IsPrimaryIncident);

            var after = svc.GetVisibleCardsAt(new SimTime(LilyMaryDemo.CollisionTime.Seconds + 8.1));
            Assert.DoesNotContain(after, n => n.NodeId == "E7");

            var issues = svc.ValidateGraph();
            Assert.DoesNotContain(issues, i => i.IsError);
        }

        [Fact]
        public void EventTextHeuristic_AcceptsNounPlusVerb()
        {
            Assert.True(EcfcValidator.LooksLikeNounPlusActiveVerb("Mary 轮撞击 Lily 轮右舷货舱"));
            Assert.False(EcfcValidator.LooksLikeNounPlusActiveVerb("雾"));
        }

        private static EcfcNode Event(string id, string text, double t, int lane, bool primary)
        {
            return new EcfcNode(id, EcfcNodeKind.Event, text, new SimTime(t), null, lane, primary, false, null, null, Q("量", "1"), new[] { "ev" });
        }

        private static IReadOnlyDictionary<string, string> Q(string k, string v)
        {
            return new Dictionary<string, string> { { k, v } };
        }
    }
}
