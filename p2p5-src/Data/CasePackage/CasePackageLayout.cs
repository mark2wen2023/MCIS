using System.IO;

namespace Mcis.Data.CasePackage
{
    /// <summary>.mcase 包内目录与关键文件名约定（对应 ARCHITECTURE 11.1 节）。</summary>
    public static class CasePackageLayout
    {
        public const string PackageFormat = "MCIS-MCASE";
        public const string PackageVersion = "1.0.0";
        public const string GeneratorVersion = "MCIS-Unity6-0.9.0";
        public const string PackageExtension = ".mcase";

        public const string ManifestFileName = "manifest.json";
        public const string CaseFileName = "case.json";
        public const string AuditDirectory = "audit";
        public const string AuditFileName = "audit.jsonl";
        public const string RawDirectory = "raw";
        public const string RawAisDirectory = "raw/ais";
        public const string RawChartsDirectory = "raw/charts";
        public const string DerivedDirectory = "derived";
        public const string DerivedTracksDirectory = "derived/tracks";
        public const string DerivedCpaDirectory = "derived/cpa";
        public const string DerivedDamageDirectory = "derived/damage_bake";
        public const string EvidenceDirectory = "evidence";
        public const string ExportsDirectory = "exports";
        public const string ThumbnailsDirectory = "thumbnails";

        public static readonly string[] RequiredDirectories = new string[]
        {
            RawDirectory,
            RawAisDirectory,
            RawChartsDirectory,
            DerivedDirectory,
            DerivedTracksDirectory,
            DerivedCpaDirectory,
            DerivedDamageDirectory,
            EvidenceDirectory,
            AuditDirectory,
            ExportsDirectory,
            ThumbnailsDirectory
        };

        public static string Combine(string workspaceRoot, string relativePath)
        {
            relativePath = (relativePath ?? string.Empty).Replace('\\', '/').TrimStart('/');
            string[] parts = relativePath.Split('/');
            string path = workspaceRoot;
            for (int i = 0; i < parts.Length; i++)
            {
                if (parts[i].Length == 0)
                {
                    continue;
                }

                path = Path.Combine(path, parts[i]);
            }

            return path;
        }

        public static string ToRelativePath(string workspaceRoot, string fullPath)
        {
            string root = Path.GetFullPath(workspaceRoot);
            string full = Path.GetFullPath(fullPath);
            if (!full.StartsWith(root, System.StringComparison.OrdinalIgnoreCase) &&
                !full.StartsWith(root, System.StringComparison.Ordinal))
            {
                return full.Replace('\\', '/');
            }

            string rel = full.Substring(root.Length).TrimStart(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            return rel.Replace('\\', '/');
        }

        public static bool IsRawPath(string relativePath)
        {
            if (string.IsNullOrEmpty(relativePath))
            {
                return false;
            }

            string n = relativePath.Replace('\\', '/');
            return n.StartsWith("raw/", System.StringComparison.Ordinal) || n == "raw";
        }

        public static void EnsureWorkspaceDirectories(string workspaceRoot, bool writeKeepFiles = true)
        {
            Directory.CreateDirectory(workspaceRoot);
            for (int i = 0; i < RequiredDirectories.Length; i++)
            {
                string dir = Combine(workspaceRoot, RequiredDirectories[i]);
                Directory.CreateDirectory(dir);
                if (writeKeepFiles)
                {
                    string keep = Path.Combine(dir, ".keep");
                    if (!File.Exists(keep))
                    {
                        File.WriteAllText(keep, string.Empty);
                    }
                }
            }
        }
    }
}
