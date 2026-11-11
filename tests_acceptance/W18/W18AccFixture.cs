using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;
using Xunit;

namespace Mcis.Acceptance.W18
{
    /// <summary>W18 验收夹具。所有排班/睡眠/证据均为虚构示例数据（虚构二副"甲"）。船时 UTC+8。</summary>
    internal static class Fx
    {
        public static readonly TimeSpan Ship = TimeSpan.FromHours(8);
        /// <summary>2026-05-11（周一）00:00 船时。</summary>
        public static readonly DateTimeOffset T0 = new DateTimeOffset(2026, 5, 11, 0, 0, 0, Ship);
        public const string Sha = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

        public static DateTimeOffset H(double hours) => T0.AddHours(hours);
        public static DateTimeOffset HM(int h, int m) => T0.AddHours(h).AddMinutes(m);
        public static (DateTimeOffset, DateTimeOffset) P(double a, double b) => (H(a), H(b));
        public static (DateTimeOffset, DateTimeOffset) P(DateTimeOffset a, DateTimeOffset b) => (a, b);

        public static WorkRestSchedule Rest(double recordHours, params (DateTimeOffset, DateTimeOffset)[] rest)
        {
            var r = WorkRestSchedule.FromRest(T0, H(recordHours), rest);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static WorkRestSchedule Work(double recordHours, params (DateTimeOffset, DateTimeOffset)[] work)
        {
            var r = WorkRestSchedule.FromWork(T0, H(recordHours), work);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static RestHourReport Check(WorkRestSchedule s, RestHourRules rules = null)
        {
            var r = new RestHourChecker(rules).Check(s);
            Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            return r.Value;
        }

        public static RestHourRules RestOnly() => new RestHourRules { ApplyWorkHourLimits = false };

        public static IEnumerable<RestHourViolation> Of(RestHourReport r, RestRule rule) => r.Violations.Where(v => v.Rule == rule);

        public static string Describe(RestHourReport r)
        {
            var sb = new StringBuilder();
            sb.AppendFormat(CultureInfo.InvariantCulture, "rest={0} work={1} unknown={2}\n", r.TotalRest, r.TotalWork, r.TotalUnknown);
            foreach (var v in r.Violations)
                sb.AppendFormat(CultureInfo.InvariantCulture, "{0} win={1:o}~{2:o} actual={3} limit={4} from={5:o} to={6:o} {7} | {8}\n",
                    v.Rule, v.WindowStart.UtcDateTime, v.WindowEnd.UtcDateTime, v.Actual, v.Limit, v.ViolatingFrom.UtcDateTime, v.ViolatingTo.UtcDateTime, v.Clause, v.Detail);
            return sb.ToString();
        }

        public static CustodyLedger LedgerWith(params string[] ids)
        {
            var ledger = new CustodyLedger();
            foreach (var id in ids)
            {
                var r = ledger.Register(new EvidenceItem(id, "虚构证据 " + id, "VDR", "调查员甲", T0, Sha), "调查员甲", T0);
                Assert.True(r.IsSuccess, r.ErrorCode + " " + r.ErrorMessage);
            }
            return ledger;
        }

        public static string RepoRoot()
        {
            var d = new DirectoryInfo(AppContext.BaseDirectory);
            while (d != null && !Directory.Exists(Path.Combine(d.FullName, "unity", "Assets"))) d = d.Parent;
            Assert.NotNull(d);
            return d.FullName;
        }

        public static string PythonExe()
        {
            const string venv = "/workspace/.venv-reports/bin/python";
            return File.Exists(venv) ? venv : "python3";
        }

        public static string BruteForceScript() => Path.Combine(RepoRoot(), "tests_acceptance", "W18", "b1_bruteforce.py");

        public static JsonDocument RunBruteForce(object payload, params string[] extraArgs)
        {
            string tmp = Path.Combine(Path.GetTempPath(), "w18-b1-" + Guid.NewGuid().ToString("N") + ".json");
            File.WriteAllText(tmp, JsonSerializer.Serialize(payload));
            try
            {
                var psi = new ProcessStartInfo(PythonExe())
                {
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    UseShellExecute = false
                };
                psi.ArgumentList.Add(BruteForceScript());
                psi.ArgumentList.Add("--file");
                psi.ArgumentList.Add(tmp);
                foreach (string a in extraArgs)
                {
                    psi.ArgumentList.Add(a);
                }

                using var proc = Process.Start(psi);
                Assert.NotNull(proc);
                string stdout = proc.StandardOutput.ReadToEnd();
                string stderr = proc.StandardError.ReadToEnd();
                bool exited = proc.WaitForExit(180000);
                Assert.True(exited && proc.ExitCode == 0,
                    "python exit " + (exited ? proc.ExitCode.ToString() : "timeout") + " stderr=" + stderr + " stdout=" + stdout);
                return JsonDocument.Parse(stdout);
            }
            finally
            {
                try { File.Delete(tmp); } catch { /* ignore */ }
            }
        }
    }
}
