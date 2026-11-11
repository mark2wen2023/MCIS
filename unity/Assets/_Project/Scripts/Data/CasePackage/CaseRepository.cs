using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Mcis.Core;
using Mcis.Core.Commands;
using Mcis.Data.Audit;
using Mcis.Domain.Models;

namespace Mcis.Data.CasePackage
{
    public sealed class CaseSummaryCard
    {
        public string CaseId { get; }
        public string Title { get; }
        public string AccidentType { get; }
        public string IncidentTimeDisplay { get; }
        public string FilePath { get; }
        public string ThumbnailPath { get; }
        public bool IsDemo { get; }

        public CaseSummaryCard(
            string caseId,
            string title,
            string accidentType,
            string incidentTimeDisplay,
            string filePath,
            string thumbnailPath,
            bool isDemo)
        {
            CaseId = caseId;
            Title = title;
            AccidentType = accidentType;
            IncidentTimeDisplay = incidentTimeDisplay;
            FilePath = filePath;
            ThumbnailPath = thumbnailPath;
            IsDemo = isDemo;
        }
    }

    /// <summary>负责 .mcase 案件包的读写、解压工作区管理、SHA-256 证据校验与自动保存。</summary>
    public interface ICaseRepository
    {
        CaseMetadata CurrentCaseMetadata { get; }
        string ActiveWorkspaceDirectory { get; }
        bool HasUnsavedChanges { get; }

        Task<Result<CaseMetadata>> CreateNewAsync(CaseMetadata initialMeta, string targetMcasePath, CancellationToken ct = default);
        Task<Result<CaseMetadata>> OpenAsync(string mcasePath, CancellationToken ct = default);
        Task<Result<bool>> SaveAsync(CancellationToken ct = default);
        Task<Result<bool>> SaveAsAsync(string newMcasePath, CancellationToken ct = default);
        Task<Result<bool>> WriteAutoSaveAsync(CancellationToken ct = default);
        Task<IntegrityCheckReport> VerifyIntegrityAsync(string mcasePath, CancellationToken ct = default);
        Task<IReadOnlyList<CaseSummaryCard>> GetRecentCasesAsync(CancellationToken ct = default);
        void CloseCurrentCase();
    }

    /// <summary>.mcase 案件库默认实现（纯文件系统，不依赖 UnityEngine）。</summary>
    public sealed class CaseRepository : ICaseRepository
    {
        private readonly string _recentListPath;
        private readonly List<string> _recent = new List<string>();
        private string _packagePath;
        private string _workspace;
        private CaseMetadata _meta;
        private AuditLog _audit;
        private CommandHistory _history;
        private bool _dirty;
        private string _operatorName;

        public CaseMetadata CurrentCaseMetadata { get { return _meta; } }
        public string ActiveWorkspaceDirectory { get { return _workspace; } }
        public bool HasUnsavedChanges { get { return _dirty; } }
        public AuditLog Audit { get { return _audit; } }
        public CommandHistory History { get { return _history; } }

        public CaseRepository(string recentListPath = null, string operatorName = "调查员")
        {
            _recentListPath = recentListPath ?? Path.Combine(Path.GetTempPath(), "mcis-recent-cases.txt");
            _operatorName = string.IsNullOrEmpty(operatorName) ? "调查员" : operatorName;
            LoadRecent();
        }

        public Task<Result<CaseMetadata>> CreateNewAsync(CaseMetadata initialMeta, string targetMcasePath, CancellationToken ct = default)
        {
            return Task.Run(() => CreateNew(initialMeta, targetMcasePath), ct);
        }

        public Result<CaseMetadata> CreateNew(CaseMetadata initialMeta, string targetMcasePath)
        {
            if (initialMeta == null)
            {
                return Result<CaseMetadata>.Fail("CASE-E01", "案件元数据不能为空");
            }

            if (string.IsNullOrWhiteSpace(targetMcasePath))
            {
                return Result<CaseMetadata>.Fail("CASE-E02", "目标 .mcase 路径不能为空");
            }

            CloseCurrentCase();

            string workspace = CreateWorkspaceDir(initialMeta.CaseId);
            CasePackageLayout.EnsureWorkspaceDirectories(workspace);
            File.WriteAllText(CasePackageLayout.Combine(workspace, CasePackageLayout.CaseFileName), CaseJson.ToJson(initialMeta));
            string auditPath = CasePackageLayout.Combine(workspace, CasePackageLayout.AuditDirectory + "/" + CasePackageLayout.AuditFileName);
            File.WriteAllText(auditPath, string.Empty);
            PackageManifest manifest = PackageManifest.BuildFromWorkspace(workspace, initialMeta.CaseId);
            File.WriteAllText(CasePackageLayout.Combine(workspace, CasePackageLayout.ManifestFileName), manifest.ToJson());
            ZipArchiveUtil.PackDirectory(workspace, targetMcasePath);

            Attach(workspace, targetMcasePath, initialMeta);
            RememberRecent(targetMcasePath);
            _dirty = false;
            return Result<CaseMetadata>.Ok(initialMeta);
        }

        public Task<Result<CaseMetadata>> OpenAsync(string mcasePath, CancellationToken ct = default)
        {
            return Task.Run(() => Open(mcasePath), ct);
        }

        public Result<CaseMetadata> Open(string mcasePath)
        {
            if (string.IsNullOrWhiteSpace(mcasePath) || !File.Exists(mcasePath))
            {
                return Result<CaseMetadata>.Fail("CASE-E03", "找不到案件包：" + mcasePath);
            }

            IntegrityCheckReport report = IntegrityChecker.VerifyPackage(mcasePath);
            if (!report.IsValid)
            {
                string detail = "缺失：" + string.Join(",", report.MissingFiles) + "；篡改：" + string.Join(",", report.TamperedFiles);
                return Result<CaseMetadata>.Fail("CASE-E04", "案件包完整性校验失败。" + detail);
            }

            CloseCurrentCase();
            string workspace = CreateWorkspaceDir(Path.GetFileNameWithoutExtension(mcasePath));
            ZipArchiveUtil.ExtractToDirectory(mcasePath, workspace);
            CasePackageLayout.EnsureWorkspaceDirectories(workspace, false);
            string casePath = CasePackageLayout.Combine(workspace, CasePackageLayout.CaseFileName);
            if (!File.Exists(casePath))
            {
                return Result<CaseMetadata>.Fail("CASE-E05", "案件包缺少 case.json");
            }

            CaseMetadata meta = CaseJson.FromJson(File.ReadAllText(casePath));
            Attach(workspace, mcasePath, meta);
            RememberRecent(mcasePath);
            _dirty = false;
            return Result<CaseMetadata>.Ok(meta);
        }

        public Task<Result<bool>> SaveAsync(CancellationToken ct = default)
        {
            return Task.Run(() => Save(), ct);
        }

        public Result<bool> Save()
        {
            if (string.IsNullOrEmpty(_workspace) || string.IsNullOrEmpty(_packagePath) || _meta == null)
            {
                return Result<bool>.Fail("CASE-E06", "当前没有打开的案件");
            }

            RefreshManifestAndPack(_packagePath);
            _dirty = false;
            return Result<bool>.Ok(true);
        }

        public Task<Result<bool>> SaveAsAsync(string newMcasePath, CancellationToken ct = default)
        {
            return Task.Run(() => SaveAs(newMcasePath), ct);
        }

        public Result<bool> SaveAs(string newMcasePath)
        {
            if (string.IsNullOrEmpty(_workspace) || _meta == null)
            {
                return Result<bool>.Fail("CASE-E06", "当前没有打开的案件");
            }

            RefreshManifestAndPack(newMcasePath);
            _packagePath = newMcasePath;
            RememberRecent(newMcasePath);
            _dirty = false;
            return Result<bool>.Ok(true);
        }

        public Task<Result<bool>> WriteAutoSaveAsync(CancellationToken ct = default)
        {
            return Task.Run(() =>
            {
                if (string.IsNullOrEmpty(_packagePath))
                {
                    return Result<bool>.Fail("CASE-E06", "当前没有打开的案件");
                }

                string auto = Path.Combine(
                    Path.GetDirectoryName(_packagePath) ?? string.Empty,
                    Path.GetFileNameWithoutExtension(_packagePath) + ".autosave.mcase");
                RefreshManifestAndPack(auto);
                return Result<bool>.Ok(true);
            }, ct);
        }

        public Task<IntegrityCheckReport> VerifyIntegrityAsync(string mcasePath, CancellationToken ct = default)
        {
            return IntegrityChecker.VerifyPackageAsync(mcasePath, ct);
        }

        public Task<IReadOnlyList<CaseSummaryCard>> GetRecentCasesAsync(CancellationToken ct = default)
        {
            return Task.FromResult(GetRecentCases());
        }

        public IReadOnlyList<CaseSummaryCard> GetRecentCases()
        {
            var cards = new List<CaseSummaryCard>();
            for (int i = 0; i < _recent.Count; i++)
            {
                string path = _recent[i];
                if (!File.Exists(path))
                {
                    continue;
                }

                try
                {
                    string temp = Path.Combine(Path.GetTempPath(), "mcis-peek-" + Guid.NewGuid().ToString("N"));
                    ZipArchiveUtil.ExtractToDirectory(path, temp);
                    string casePath = CasePackageLayout.Combine(temp, CasePackageLayout.CaseFileName);
                    if (File.Exists(casePath))
                    {
                        CaseMetadata meta = CaseJson.FromJson(File.ReadAllText(casePath));
                        string thumb = CasePackageLayout.Combine(temp, "thumbnails/cover_16x9.png");
                        cards.Add(new CaseSummaryCard(
                            meta.CaseId,
                            meta.Title,
                            meta.AccidentType,
                            meta.IncidentTimeUtc.ToOffset(TimeSpan.FromMinutes(meta.DisplayTimeZoneOffsetMinutes))
                                .ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture),
                            path,
                            File.Exists(thumb) ? thumb : null,
                            meta.IsFictionalDemo));
                    }

                    Directory.Delete(temp, true);
                }
                catch (Exception)
                {
                }
            }

            return cards;
        }

        /// <summary>向工作区写入原始或证据文件（写入 raw/ 或 evidence/ 后标记为未保存）。</summary>
        public void AddWorkspaceFile(string relativePath, byte[] content)
        {
            EnsureOpen();
            string n = relativePath.Replace('\\', '/');
            string dest = CasePackageLayout.Combine(_workspace, n);
            string dir = Path.GetDirectoryName(dest);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            File.WriteAllBytes(dest, content ?? Array.Empty<byte>());
            _dirty = true;
        }

        public void MarkDirty()
        {
            _dirty = true;
        }

        public void ExecuteCommand(IReversibleCommand command)
        {
            EnsureOpen();
            if (_history == null)
            {
                throw new InvalidOperationException("命令历史未初始化");
            }

            _history.Execute(command);
            _dirty = true;
        }

        public void CloseCurrentCase()
        {
            if (!string.IsNullOrEmpty(_workspace) && Directory.Exists(_workspace))
            {
                try
                {
                    Directory.Delete(_workspace, true);
                }
                catch (IOException)
                {
                }
            }

            _workspace = null;
            _packagePath = null;
            _meta = null;
            _audit = null;
            _history = null;
            _dirty = false;
        }

        private void Attach(string workspace, string packagePath, CaseMetadata meta)
        {
            _workspace = workspace;
            _packagePath = packagePath;
            _meta = meta;
            _audit = AuditLog.OpenInWorkspace(workspace);
            string op = _operatorName;
            _history = new CommandHistory((cmd, action) =>
            {
                _audit.AppendCommand(cmd, action, op);
            });
        }

        private void RefreshManifestAndPack(string targetPath)
        {
            File.WriteAllText(CasePackageLayout.Combine(_workspace, CasePackageLayout.CaseFileName), CaseJson.ToJson(_meta));
            string manifestPath = CasePackageLayout.Combine(_workspace, CasePackageLayout.ManifestFileName);
            PackageManifest previous = null;
            if (File.Exists(manifestPath))
            {
                previous = PackageManifest.FromJson(File.ReadAllText(manifestPath));
            }

            PackageManifest manifest = PackageManifest.BuildFromWorkspace(_workspace, _meta.CaseId, previous);
            File.WriteAllText(manifestPath, manifest.ToJson());
            ZipArchiveUtil.PackDirectory(_workspace, targetPath);
        }

        private void EnsureOpen()
        {
            if (string.IsNullOrEmpty(_workspace) || _meta == null)
            {
                throw new InvalidOperationException("当前没有打开的案件");
            }
        }

        private static string CreateWorkspaceDir(string hint)
        {
            string safe = string.IsNullOrWhiteSpace(hint) ? "case" : hint;
            foreach (char c in Path.GetInvalidFileNameChars())
            {
                safe = safe.Replace(c, '_');
            }

            return Path.Combine(Path.GetTempPath(), "mcis-workspace-" + safe + "-" + Guid.NewGuid().ToString("N"));
        }

        private void LoadRecent()
        {
            _recent.Clear();
            if (_recentListPath != null && File.Exists(_recentListPath))
            {
                foreach (string line in File.ReadAllLines(_recentListPath))
                {
                    if (!string.IsNullOrWhiteSpace(line))
                    {
                        _recent.Add(line.Trim());
                    }
                }
            }
        }

        private void RememberRecent(string path)
        {
            string full = Path.GetFullPath(path);
            _recent.RemoveAll(p => string.Equals(p, full, StringComparison.OrdinalIgnoreCase));
            _recent.Insert(0, full);
            while (_recent.Count > 20)
            {
                _recent.RemoveAt(_recent.Count - 1);
            }

            string dir = Path.GetDirectoryName(_recentListPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            File.WriteAllLines(_recentListPath, _recent);
        }
    }
}
