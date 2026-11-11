using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Mcis.Domain.Models;

namespace Mcis.Data.CasePackage
{
    /// <summary>清单中单个文件条目。</summary>
    public sealed class ManifestFileEntry
    {
        public string RelativePath { get; }
        public string Role { get; }
        public long SizeBytes { get; }
        public string Sha256 { get; }

        public ManifestFileEntry(string relativePath, string role, long sizeBytes, string sha256)
        {
            RelativePath = (relativePath ?? string.Empty).Replace('\\', '/');
            Role = role ?? "Derived";
            SizeBytes = sizeBytes;
            Sha256 = sha256 ?? string.Empty;
        }
    }

    /// <summary>.mcase 包清单（manifest.json）。</summary>
    public sealed class PackageManifest
    {
        public string PackageFormat { get; set; }
        public string PackageVersion { get; set; }
        public string CaseId { get; set; }
        public DateTimeOffset CreatedAtUtc { get; set; }
        public DateTimeOffset LastModifiedAtUtc { get; set; }
        public string GeneratorVersion { get; set; }
        public IList<ManifestFileEntry> Files { get; }

        public PackageManifest()
        {
            PackageFormat = CasePackageLayout.PackageFormat;
            PackageVersion = CasePackageLayout.PackageVersion;
            GeneratorVersion = CasePackageLayout.GeneratorVersion;
            Files = new List<ManifestFileEntry>();
            CreatedAtUtc = DateTimeOffset.UtcNow;
            LastModifiedAtUtc = CreatedAtUtc;
        }

        public ManifestFileEntry Find(string relativePath)
        {
            string n = (relativePath ?? string.Empty).Replace('\\', '/');
            for (int i = 0; i < Files.Count; i++)
            {
                if (string.Equals(Files[i].RelativePath, n, StringComparison.OrdinalIgnoreCase))
                {
                    return Files[i];
                }
            }

            return null;
        }

        public string ToJson()
        {
            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"packageFormat\": ").Append(SimpleJson.Quote(PackageFormat)).Append(",\n");
            sb.Append("  \"packageVersion\": ").Append(SimpleJson.Quote(PackageVersion)).Append(",\n");
            sb.Append("  \"caseId\": ").Append(SimpleJson.Quote(CaseId)).Append(",\n");
            sb.Append("  \"createdAtUtc\": ").Append(SimpleJson.Quote(SimpleJson.FormatIso(CreatedAtUtc))).Append(",\n");
            sb.Append("  \"lastModifiedAtUtc\": ").Append(SimpleJson.Quote(SimpleJson.FormatIso(LastModifiedAtUtc))).Append(",\n");
            sb.Append("  \"generatorVersion\": ").Append(SimpleJson.Quote(GeneratorVersion)).Append(",\n");
            sb.Append("  \"files\": [\n");
            for (int i = 0; i < Files.Count; i++)
            {
                ManifestFileEntry e = Files[i];
                sb.Append("    {\n");
                sb.Append("      \"relativePath\": ").Append(SimpleJson.Quote(e.RelativePath)).Append(",\n");
                sb.Append("      \"role\": ").Append(SimpleJson.Quote(e.Role)).Append(",\n");
                sb.Append("      \"sizeBytes\": ").Append(e.SizeBytes.ToString(CultureInfo.InvariantCulture)).Append(",\n");
                sb.Append("      \"sha256\": ").Append(SimpleJson.Quote(e.Sha256)).Append("\n");
                sb.Append("    }");
                if (i < Files.Count - 1)
                {
                    sb.Append(',');
                }

                sb.Append('\n');
            }

            sb.Append("  ]\n}\n");
            return sb.ToString();
        }

        public static PackageManifest FromJson(string json)
        {
            SimpleJson.JsonValue root = SimpleJson.Parse(json);
            var m = new PackageManifest();
            m.PackageFormat = root.GetString("packageFormat", CasePackageLayout.PackageFormat);
            m.PackageVersion = root.GetString("packageVersion", CasePackageLayout.PackageVersion);
            m.CaseId = root.GetString("caseId");
            string created = root.GetString("createdAtUtc", null);
            if (!string.IsNullOrEmpty(created))
            {
                m.CreatedAtUtc = SimpleJson.ParseIso(created);
            }

            string modified = root.GetString("lastModifiedAtUtc", null);
            if (!string.IsNullOrEmpty(modified))
            {
                m.LastModifiedAtUtc = SimpleJson.ParseIso(modified);
            }

            m.GeneratorVersion = root.GetString("generatorVersion", CasePackageLayout.GeneratorVersion);
            m.Files.Clear();
            SimpleJson.JsonValue files = root["files"];
            if (files != null && files.Items != null)
            {
                for (int i = 0; i < files.Items.Count; i++)
                {
                    SimpleJson.JsonValue f = files.Items[i];
                    m.Files.Add(new ManifestFileEntry(
                        f.GetString("relativePath"),
                        f.GetString("role", "Derived"),
                        (long)f.GetDouble("sizeBytes"),
                        f.GetString("sha256")));
                }
            }

            return m;
        }

        public static string InferRole(string relativePath)
        {
            string n = (relativePath ?? string.Empty).Replace('\\', '/');
            if (string.Equals(n, CasePackageLayout.CaseFileName, StringComparison.OrdinalIgnoreCase))
            {
                return "CaseDefinition";
            }

            if (CasePackageLayout.IsRawPath(n) || n.StartsWith("evidence/", StringComparison.OrdinalIgnoreCase))
            {
                return "RawEvidence";
            }

            if (n.StartsWith("audit/", StringComparison.OrdinalIgnoreCase))
            {
                return "Audit";
            }

            if (n.StartsWith("exports/", StringComparison.OrdinalIgnoreCase))
            {
                return "Export";
            }

            if (n.StartsWith("thumbnails/", StringComparison.OrdinalIgnoreCase))
            {
                return "Thumbnail";
            }

            return "Derived";
        }

        /// <summary>扫描工作区并生成（或刷新）清单。原始证据文件若已有哈希则保持不变以便检测篡改。</summary>
        public static PackageManifest BuildFromWorkspace(string workspaceRoot, string caseId, PackageManifest previous = null)
        {
            var manifest = new PackageManifest();
            manifest.CaseId = caseId;
            if (previous != null)
            {
                manifest.CreatedAtUtc = previous.CreatedAtUtc;
                manifest.PackageVersion = previous.PackageVersion;
                manifest.GeneratorVersion = previous.GeneratorVersion;
            }

            manifest.LastModifiedAtUtc = DateTimeOffset.UtcNow;

            if (!Directory.Exists(workspaceRoot))
            {
                return manifest;
            }

            foreach (string file in Directory.GetFiles(workspaceRoot, "*", SearchOption.AllDirectories))
            {
                string rel = CasePackageLayout.ToRelativePath(workspaceRoot, file);
                if (string.Equals(rel, CasePackageLayout.ManifestFileName, StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                var info = new FileInfo(file);
                string role = InferRole(rel);
                string hash = Sha256Util.ComputeFileHex(file);
                manifest.Files.Add(new ManifestFileEntry(rel, role, info.Length, hash));
            }

            return manifest;
        }
    }

    /// <summary>case.json 的读写（案件元数据核心字段）。</summary>
    public static class CaseJson
    {
        public static string ToJson(CaseMetadata meta)
        {
            var sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append("  \"caseId\": ").Append(SimpleJson.Quote(meta.CaseId)).Append(",\n");
            sb.Append("  \"schemaVersion\": ").Append(SimpleJson.Quote(meta.SchemaVersion)).Append(",\n");
            sb.Append("  \"title\": ").Append(SimpleJson.Quote(meta.Title)).Append(",\n");
            sb.Append("  \"accidentCode\": ").Append(SimpleJson.Quote(meta.AccidentCode)).Append(",\n");
            sb.Append("  \"accidentType\": ").Append(SimpleJson.Quote(meta.AccidentType)).Append(",\n");
            sb.Append("  \"accidentGrade\": ").Append(SimpleJson.Quote(meta.AccidentGrade)).Append(",\n");
            sb.Append("  \"incidentTimeUtc\": ").Append(SimpleJson.Quote(SimpleJson.FormatIso(meta.IncidentTimeUtc))).Append(",\n");
            sb.Append("  \"caseEpochUtc\": ").Append(SimpleJson.Quote(SimpleJson.FormatIso(meta.CaseEpochUtc))).Append(",\n");
            sb.Append("  \"displayTimeZoneOffsetMinutes\": ").Append(SimpleJson.Number(meta.DisplayTimeZoneOffsetMinutes)).Append(",\n");
            sb.Append("  \"incidentLocation\": {\n");
            sb.Append("    \"lonDeg\": ").Append(SimpleJson.Number(meta.IncidentLocation.LonDeg)).Append(",\n");
            sb.Append("    \"latDeg\": ").Append(SimpleJson.Number(meta.IncidentLocation.LatDeg)).Append(",\n");
            sb.Append("    \"heightM\": ").Append(SimpleJson.Number(meta.IncidentLocation.HeightM)).Append("\n");
            sb.Append("  },\n");
            sb.Append("  \"seaLevelOffsetM\": ").Append(SimpleJson.Number(meta.SeaLevelOffsetM)).Append(",\n");
            sb.Append("  \"leadInvestigator\": ").Append(SimpleJson.Quote(meta.LeadInvestigator)).Append(",\n");
            sb.Append("  \"agencyName\": ").Append(SimpleJson.Quote(meta.AgencyName)).Append(",\n");
            sb.Append("  \"isFictionalDemo\": ").Append(SimpleJson.Bool(meta.IsFictionalDemo)).Append(",\n");
            sb.Append("  \"summaryNotes\": ").Append(SimpleJson.Quote(meta.SummaryNotes)).Append("\n");
            sb.Append("}\n");
            return sb.ToString();
        }

        public static CaseMetadata FromJson(string json)
        {
            SimpleJson.JsonValue root = SimpleJson.Parse(json);
            SimpleJson.JsonValue loc = root["incidentLocation"];
            var geo = new Mcis.Domain.Common.GeoCoord(
                loc != null ? loc.GetDouble("lonDeg") : 0.0,
                loc != null ? loc.GetDouble("latDeg") : 0.0,
                loc != null ? loc.GetDouble("heightM") : 0.0);
            return new CaseMetadata(
                root.GetString("caseId"),
                root.GetString("schemaVersion", CaseMetadata.CurrentSchemaVersion),
                root.GetString("title"),
                root.GetString("accidentCode"),
                root.GetString("accidentType"),
                root.GetString("accidentGrade"),
                SimpleJson.ParseIso(root.GetString("incidentTimeUtc", SimpleJson.FormatIso(DateTimeOffset.UtcNow))),
                SimpleJson.ParseIso(root.GetString("caseEpochUtc", SimpleJson.FormatIso(DateTimeOffset.UtcNow))),
                root.GetInt("displayTimeZoneOffsetMinutes", 480),
                geo,
                root.GetDouble("seaLevelOffsetM"),
                root.GetString("leadInvestigator"),
                root.GetString("agencyName"),
                root.GetBool("isFictionalDemo"),
                root.GetString("summaryNotes"));
        }
    }
}
