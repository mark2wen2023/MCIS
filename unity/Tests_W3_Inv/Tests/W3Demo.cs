using System;
using System.Collections.Generic;
using Mcis.Domain.Common;
using Mcis.Domain.Interview;

namespace Mcis.W3.Tests
{
    /// <summary>
    /// 示例数据（虚构）：星屿港，2026-05-18 14:15–14:27（UTC+8），Mary 轮撞 Lily 轮左舷。
    /// 人物、单位、数值均为虚构，不来自任何真实报告。
    /// </summary>
    internal static class W3Demo
    {
        public static readonly TimeSpan Cst = TimeSpan.FromHours(8);

        public static DateTimeOffset At(int h, int m, int s = 0)
        {
            return new DateTimeOffset(2026, 5, 18, h, m, s, Cst);
        }

        public static DateTimeOffset Day(int month, int day, int h = 9, int m = 0)
        {
            return new DateTimeOffset(2026, month, day, h, m, 0, Cst);
        }

        public static InterviewRecord Ir03()
        {
            var who = new Interviewee("P-03", "Mary 轮二副（虚构）", "二副（OOW）", "Mary 轮");
            var ir = new InterviewRecord("IR-03", who, Day(5, 19, 9, 30), new[] { "调查员 A（虚构）" }, "记录人 B（虚构）", "星屿海事局询问室");
            ir.AddTurn("你什么时候第一次在雷达上看到 Lily 轮？", "大概 14:17 左右，在 3 号浮标北面，距离差不多 3 海里，当时看它是出港的。", Day(5, 19, 9, 32));
            ir.AddTurn("两船距离接近时你采取了什么行动？", "我觉得它会从我右边过，就在 14:23 才开始左舵，左舵 20 度，同时鸣了一长声。", Day(5, 19, 9, 40));
            ir.AddTurn("你和 Lily 轮或 VTS 有没有 VHF 联系？", "VTS 在 14:20 叫过我们，我回答了保持航向。", Day(5, 19, 9, 45));
            return ir;
        }
    }

    /// <summary>虚构 VDR/AIS 查询源：按主题键返回固定观测值。</summary>
    internal sealed class FakeDataSource : IStatementDataSource
    {
        private readonly Dictionary<string, DataObservation> _map = new Dictionary<string, DataObservation>(StringComparer.Ordinal);
        public List<StatementQuery> Queries { get; } = new List<StatementQuery>();

        public FakeDataSource Set(string subject, DataObservation obs)
        {
            _map[subject] = obs;
            return this;
        }

        public DataObservation Query(StatementQuery query)
        {
            Queries.Add(query);
            return _map.TryGetValue(query.Subject, out DataObservation o) ? o : DataObservation.NotFound("虚构数据源");
        }

        public static FakeDataSource LilyMary()
        {
            return new FakeDataSource()
                .Set("Mary.radar_first_sighting_range", DataObservation.ScalarValue(5.1, "nm", "AIS 14:17（虚构）", W3Demo.At(14, 17)))
                .Set("Mary.port_helm_start", DataObservation.EventAt(W3Demo.At(14, 22, 15), "VDR 舵角（虚构）"))
                .Set("Mary.rudder_angle", DataObservation.ScalarValue(20, "deg", "VDR 舵角（虚构）", W3Demo.At(14, 23)))
                .Set("Mary.long_blast", DataObservation.Occurrence(false, "VDR 驾驶台音频（虚构）", W3Demo.At(14, 23)))
                .Set("VTS.call_mary", DataObservation.EventAt(W3Demo.At(14, 20, 12), "VHF16（虚构）"))
                .Set("Mary.position_1417", DataObservation.At(new GeoCoord(113.7000, 21.8000), "AIS（虚构）", W3Demo.At(14, 17)));
        }
    }
}
