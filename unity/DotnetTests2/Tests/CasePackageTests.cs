using System;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using Mcis.Core.Commands;
using Mcis.Data.Audit;
using Mcis.Data.CasePackage;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Fixtures;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class CasePackageTests
    {
        private static CaseMetadata DemoMeta()
        {
            return LilyMaryDemo.CreateMetadata();
        }

        [Fact]
        public async Task CreateOpenSave_RoundTrip_PreservesFictionalFlagAndIntegrity()
        {
            string dir = Path.Combine(Path.GetTempPath(), "mcis-n1-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            string mcase = Path.Combine(dir, "Demo_LilyMary.mcase");
            string recent = Path.Combine(dir, "recent.txt");
            try
            {
                var repo = new CaseRepository(recent, "测试员");
                var created = await repo.CreateNewAsync(DemoMeta(), mcase);
                Assert.True(created.IsSuccess, created.ErrorMessage);
                Assert.True(created.Value.IsFictionalDemo);
                Assert.True(File.Exists(mcase));

                repo.AddWorkspaceFile("raw/ais/lily_shore_station.nmea", Encoding.UTF8.GetBytes("!AIVDM,DEMO,FICTIONAL"));
                repo.AddWorkspaceFile("evidence/E01_statement.txt", Encoding.UTF8.GetBytes("虚构陈述"));
                var saved = await repo.SaveAsync();
                Assert.True(saved.IsSuccess, saved.ErrorMessage);
                repo.CloseCurrentCase();

                var opened = await repo.OpenAsync(mcase);
                Assert.True(opened.IsSuccess, opened.ErrorMessage);
                Assert.Equal(LilyMaryDemo.CaseId, opened.Value.CaseId);
                Assert.True(opened.Value.IsFictionalDemo);
                string workspace = repo.ActiveWorkspaceDirectory;
                Assert.True(Directory.Exists(Path.Combine(workspace, "raw", "ais")));
                Assert.True(Directory.Exists(Path.Combine(workspace, "derived")));
                Assert.True(Directory.Exists(Path.Combine(workspace, "evidence")));
                Assert.True(Directory.Exists(Path.Combine(workspace, "audit")));
                Assert.True(File.Exists(Path.Combine(workspace, "raw", "ais", "lily_shore_station.nmea")));

                var report = await repo.VerifyIntegrityAsync(mcase);
                Assert.True(report.IsValid);
                Assert.Empty(report.TamperedFiles);
                Assert.Empty(report.MissingFiles);
            }
            finally
            {
                try { Directory.Delete(dir, true); } catch (IOException) { }
            }
        }

        [Fact]
        public async Task VerifyIntegrity_DetectsTamperedRawFile()
        {
            string dir = Path.Combine(Path.GetTempPath(), "mcis-n1t-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            string mcase = Path.Combine(dir, "t.mcase");
            try
            {
                var repo = new CaseRepository(Path.Combine(dir, "r.txt"));
                Assert.True((await repo.CreateNewAsync(DemoMeta(), mcase)).IsSuccess);
                repo.AddWorkspaceFile("raw/ais/a.nmea", Encoding.UTF8.GetBytes("ORIGINAL"));
                Assert.True((await repo.SaveAsync()).IsSuccess);
                repo.CloseCurrentCase();

                string unpack = Path.Combine(dir, "unpack");
                ZipArchiveUtil.ExtractToDirectory(mcase, unpack);
                File.WriteAllText(Path.Combine(unpack, "raw", "ais", "a.nmea"), "TAMPERED");
                string tampered = Path.Combine(dir, "tampered.mcase");
                ZipArchiveUtil.PackDirectory(unpack, tampered);

                var report = await IntegrityChecker.VerifyPackageAsync(tampered);
                Assert.False(report.IsValid);
                Assert.Contains(report.TamperedFiles, p => p.Replace('\\', '/').EndsWith("raw/ais/a.nmea"));
            }
            finally
            {
                try { Directory.Delete(dir, true); } catch (IOException) { }
            }
        }

        [Fact]
        public void AuditLog_AppendOnly_AndCommandHistoryUndoRedo()
        {
            string path = Path.Combine(Path.GetTempPath(), "audit-" + Guid.NewGuid().ToString("N") + ".jsonl");
            try
            {
                var log = new AuditLog(path);
                int value = 0;
                var history = new CommandHistory((cmd, action) => log.AppendCommand(cmd, action, "测试员"));
                var inc = new DelegateCommand("增加计数", "Threshold", "0", "1", () => value++, () => value--);
                history.Execute(inc);
                history.Execute(new DelegateCommand("再加一", "Threshold", "1", "2", () => value++, () => value--));
                Assert.Equal(2, value);
                Assert.True(history.Undo());
                Assert.Equal(1, value);
                Assert.True(history.Redo());
                Assert.Equal(2, value);

                var records = log.ReadAll();
                Assert.Equal(4, records.Count); // execute, execute, undo, redo
                Assert.Equal("Execute", records[0].Action);
                Assert.Equal("测试员", records[0].OperatorName);
                string raw = File.ReadAllText(path);
                Assert.Contains("增加计数", raw);
                int before = File.ReadAllBytes(path).Length;
                log.Append(new AuditRecord(DateTimeOffset.UtcNow, "测试员", "Note", "Audit", "备注", "", ""));
                Assert.True(File.ReadAllBytes(path).Length > before);
            }
            finally
            {
                if (File.Exists(path)) File.Delete(path);
            }
        }

        [Fact]
        public void Sha256_KnownEmptyHash()
        {
            // SHA-256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
            Assert.Equal("e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", Sha256Util.ComputeBytesHex(Array.Empty<byte>()));
        }
    }
}
