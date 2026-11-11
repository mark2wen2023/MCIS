using System;
using System.Collections.Generic;
using System.IO;
using Mcis.Core;
using Mcis.Domain.Ais;
using Mcis.Domain.Common;
using Mcis.Domain.Cpa;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Cpa;
using Xunit;

namespace Mcis.Pure.Tests
{
    /// <summary>
    /// M8a 示例数据测试：Lily/Mary 示例（虚构）经 CSV 与 NMEA 两条路径
    /// 解析→清洗→插值→CpaService 预计算，结果应一致且呈现碰撞情节。
    /// </summary>
    public sealed class DemoDataTests
    {
        private const string LilyMmsi = "999000001";
        private const string MaryMmsi = "999000002";
        private static readonly DateTimeOffset Epoch = new DateTimeOffset(2026, 5, 18, 10, 0, 0, TimeSpan.Zero);

        private sealed class PathResult
        {
            public IShipTrack Lily;
            public IShipTrack Mary;
            public CpaTimeSeries Series;
            public int Rejected;
        }

        private static string DemoDir()
        {
            string dir = AppContext.BaseDirectory;
            while (dir != null)
            {
                string candidate = Path.Combine(dir, "Assets", "StreamingAssets", "Mcis", "Demo");
                if (Directory.Exists(candidate)) return candidate;
                dir = Path.GetDirectoryName(dir);
            }
            throw new DirectoryNotFoundException("Demo data directory not found from " + AppContext.BaseDirectory);
        }

        private static PathResult Run(AisImportBatchResult batch)
        {
            Assert.True(batch.RecordsByMmsi.ContainsKey(LilyMmsi), "Lily missing");
            Assert.True(batch.RecordsByMmsi.ContainsKey(MaryMmsi), "Mary missing");

            LocalEnuGeoConverter geo = new LocalEnuGeoConverter(new GeoCoord(113.70, 21.78, 0.0), 0.0);
            TrackCleaningConfig cfg = TrackCleaningConfig.CreateDefault();
            TrackInterpolator interp = new TrackInterpolator();
            IShipTrack lily = interp.BuildFromAisRecords(
                "lily", batch.RecordsByMmsi[LilyMmsi], AntennaOffset.Zero, Epoch, geo, cfg);
            IShipTrack mary = interp.BuildFromAisRecords(
                "mary", batch.RecordsByMmsi[MaryMmsi], AntennaOffset.Zero, Epoch, geo, cfg);

            CpaService svc = new CpaService(lily, mary, 1.0, RiskThresholds.Default);
            return new PathResult
            {
                Lily = lily,
                Mary = mary,
                Series = svc.PrecomputeSeries("lily", "mary", 1.0),
                Rejected = lily.RejectedSamples.Count + mary.RejectedSamples.Count
            };
        }

        private static PathResult RunCsv()
        {
            CsvMappingProfile map = new CsvMappingProfile(
                "Demo", "mmsi", "timestamp_utc", null, 0, "lon", "lat", "sog_kn", "cog_deg",
                "hdg_deg", "vessel_name");
            string text = File.ReadAllText(Path.Combine(DemoDir(), "lily_mary_demo.csv"));
            Result<AisImportBatchResult> res = new AisDecoder().DecodeCsvText(text, map);
            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            return Run(res.Value);
        }

        private static PathResult RunNmea()
        {
            string text = File.ReadAllText(Path.Combine(DemoDir(), "lily_mary_demo.nmea"));
            Result<AisImportBatchResult> res = new AisDecoder().DecodeNmeaText(text);
            Assert.True(res.IsSuccess);
            Assert.Empty(res.Value.ChecksumOrSyntaxErrors);
            Assert.Equal("LILY", res.Value.DiscoveredStaticParticulars[LilyMmsi].Name);
            Assert.Equal("MARY", res.Value.DiscoveredStaticParticulars[MaryMmsi].Name);
            return Run(res.Value);
        }

        private static void AssertCollisionScenario(PathResult r)
        {
            Assert.Equal(0, r.Rejected);
            double minSec = r.Series.MinDistanceTime.Seconds;
            Assert.InRange(minSec, 8 * 60.0, 10 * 60.0);
            Assert.True(r.Series.MinDistanceNm < 0.1, "min distance " + r.Series.MinDistanceNm);

            bool dangerBefore = false;
            foreach (CpaResult s in r.Series.Samples)
            {
                if (s.Time.Seconds < minSec && s.RiskLevel == RiskLevel.Danger) dangerBefore = true;
            }
            Assert.True(dangerBefore, "no Danger before collision");
        }

        [Fact]
        public void CsvPath_ProducesCollisionScenario()
        {
            AssertCollisionScenario(RunCsv());
        }

        [Fact]
        public void NmeaPath_ProducesCollisionScenario()
        {
            AssertCollisionScenario(RunNmea());
        }

        [Fact]
        public void CsvAndNmeaPaths_AgreeWithin20Meters()
        {
            PathResult csv = RunCsv();
            PathResult nmea = RunNmea();
            for (double t = 0.0; t <= 900.0; t += 10.0)
            {
                AssertClose(csv.Lily, nmea.Lily, t);
                AssertClose(csv.Mary, nmea.Mary, t);
            }
        }

        private static void AssertClose(IShipTrack a, IShipTrack b, double t)
        {
            EnuPosition pa = a.SampleAt(new SimTime(t)).EnuCenter;
            EnuPosition pb = b.SampleAt(new SimTime(t)).EnuCenter;
            double d = Math.Sqrt(Math.Pow(pa.EastM - pb.EastM, 2) + Math.Pow(pa.NorthM - pb.NorthM, 2));
            Assert.True(d < 20.0, a.VesselId + " t=" + t + " diff=" + d + " m");
        }
    }
}
