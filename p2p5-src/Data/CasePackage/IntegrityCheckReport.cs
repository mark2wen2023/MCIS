using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;

namespace Mcis.Data.CasePackage
{
    /// <summary>案件包 SHA-256 完整性校验报告。</summary>
    public sealed class IntegrityCheckReport
    {
        public bool IsValid { get; }
        public IReadOnlyList<string> TamperedFiles { get; }
        public IReadOnlyList<string> MissingFiles { get; }
        public IReadOnlyList<string> ExtraFiles { get; }

        public IntegrityCheckReport(
            bool isValid,
            IReadOnlyList<string> tamperedFiles,
            IReadOnlyList<string> missingFiles,
            IReadOnlyList<string> extraFiles = null)
        {
            IsValid = isValid;
            TamperedFiles = tamperedFiles ?? Array.Empty<string>();
            MissingFiles = missingFiles ?? Array.Empty<string>();
            ExtraFiles = extraFiles ?? Array.Empty<string>();
        }
    }

    /// <summary>对工作区或 .mcase 包执行 SHA-256 清单校验。</summary>
    public static class IntegrityChecker
    {
        public static IntegrityCheckReport VerifyWorkspace(string workspaceRoot)
        {
            string manifestPath = CasePackageLayout.Combine(workspaceRoot, CasePackageLayout.ManifestFileName);
            if (!File.Exists(manifestPath))
            {
                return new IntegrityCheckReport(false, Array.Empty<string>(), new[] { CasePackageLayout.ManifestFileName });
            }

            PackageManifest manifest = PackageManifest.FromJson(File.ReadAllText(manifestPath));
            var tampered = new List<string>();
            var missing = new List<string>();
            var listed = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

            for (int i = 0; i < manifest.Files.Count; i++)
            {
                ManifestFileEntry entry = manifest.Files[i];
                listed.Add(entry.RelativePath);
                string full = CasePackageLayout.Combine(workspaceRoot, entry.RelativePath);
                if (!File.Exists(full))
                {
                    missing.Add(entry.RelativePath);
                    continue;
                }

                string actual = Sha256Util.ComputeFileHex(full);
                if (!string.Equals(actual, entry.Sha256, StringComparison.OrdinalIgnoreCase))
                {
                    tampered.Add(entry.RelativePath);
                }
            }

            var extra = new List<string>();
            if (Directory.Exists(workspaceRoot))
            {
                foreach (string file in Directory.GetFiles(workspaceRoot, "*", SearchOption.AllDirectories))
                {
                    string rel = CasePackageLayout.ToRelativePath(workspaceRoot, file);
                    if (string.Equals(rel, CasePackageLayout.ManifestFileName, StringComparison.OrdinalIgnoreCase))
                    {
                        continue;
                    }

                    if (!listed.Contains(rel))
                    {
                        extra.Add(rel);
                    }
                }
            }

            bool valid = tampered.Count == 0 && missing.Count == 0;
            return new IntegrityCheckReport(valid, tampered, missing, extra);
        }

        public static IntegrityCheckReport VerifyPackage(string mcasePath)
        {
            string temp = Path.Combine(Path.GetTempPath(), "mcis-integrity-" + Guid.NewGuid().ToString("N"));
            try
            {
                ZipArchiveUtil.ExtractToDirectory(mcasePath, temp);
                return VerifyWorkspace(temp);
            }
            finally
            {
                try
                {
                    if (Directory.Exists(temp))
                    {
                        Directory.Delete(temp, true);
                    }
                }
                catch (IOException)
                {
                }
            }
        }

        public static Task<IntegrityCheckReport> VerifyPackageAsync(string mcasePath, CancellationToken ct = default)
        {
            ct.ThrowIfCancellationRequested();
            return Task.Run(() =>
            {
                ct.ThrowIfCancellationRequested();
                return VerifyPackage(mcasePath);
            }, ct);
        }
    }
}
