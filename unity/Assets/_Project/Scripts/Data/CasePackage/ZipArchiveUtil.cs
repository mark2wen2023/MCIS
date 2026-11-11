using System;
using System.IO;
using System.IO.Compression;
using System.Text;

namespace Mcis.Data.CasePackage
{
    /// <summary>使用 ZipArchive（Deflate）读写 .mcase 包，不依赖 ZipFile 静态 API，以便在 netstandard2.1 下编译。</summary>
    public static class ZipArchiveUtil
    {
        public static void PackDirectory(string sourceDirectory, string zipPath)
        {
            string dir = Path.GetDirectoryName(zipPath);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            if (File.Exists(zipPath))
            {
                File.Delete(zipPath);
            }

            using (FileStream fs = File.Create(zipPath))
            using (var zip = new ZipArchive(fs, ZipArchiveMode.Create, true, Encoding.UTF8))
            {
                foreach (string file in Directory.GetFiles(sourceDirectory, "*", SearchOption.AllDirectories))
                {
                    string rel = CasePackageLayout.ToRelativePath(sourceDirectory, file);
                    ZipArchiveEntry entry = zip.CreateEntry(rel, CompressionLevel.Optimal);
                    using (Stream entryStream = entry.Open())
                    using (FileStream input = File.OpenRead(file))
                    {
                        input.CopyTo(entryStream);
                    }
                }
            }
        }

        public static void ExtractToDirectory(string zipPath, string targetDirectory)
        {
            if (Directory.Exists(targetDirectory))
            {
                Directory.Delete(targetDirectory, true);
            }

            Directory.CreateDirectory(targetDirectory);

            using (FileStream fs = File.OpenRead(zipPath))
            using (var zip = new ZipArchive(fs, ZipArchiveMode.Read, false, Encoding.UTF8))
            {
                foreach (ZipArchiveEntry entry in zip.Entries)
                {
                    if (string.IsNullOrEmpty(entry.FullName) || entry.FullName.EndsWith("/"))
                    {
                        continue;
                    }

                    string dest = CasePackageLayout.Combine(targetDirectory, entry.FullName);
                    string destDir = Path.GetDirectoryName(dest);
                    if (!string.IsNullOrEmpty(destDir))
                    {
                        Directory.CreateDirectory(destDir);
                    }

                    // 防止路径穿越
                    string fullDest = Path.GetFullPath(dest);
                    string fullRoot = Path.GetFullPath(targetDirectory);
                    if (!fullDest.StartsWith(fullRoot, StringComparison.Ordinal) &&
                        !fullDest.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase))
                    {
                        throw new InvalidOperationException("案件包包含非法路径：" + entry.FullName);
                    }

                    using (Stream src = entry.Open())
                    using (FileStream dst = File.Create(dest))
                    {
                        src.CopyTo(dst);
                    }
                }
            }
        }
    }
}
