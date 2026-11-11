using System;
using System.IO;
using PdfSharp.Fonts;

namespace Mcis.Reports
{
    /// <summary>将 Noto Sans SC（OFL）注册为 PDFsharp 字体，用于中文调查报告。</summary>
    public sealed class NotoSansScFontResolver : IFontResolver
    {
        public const string FamilyName = "Noto Sans SC";
        private readonly byte[] _regular;
        private readonly byte[] _bold;

        public NotoSansScFontResolver(string regularPath, string boldPath = null)
        {
            if (!File.Exists(regularPath))
            {
                throw new FileNotFoundException("找不到 Noto Sans SC 字体文件（OFL）", regularPath);
            }

            _regular = File.ReadAllBytes(regularPath);
            _bold = !string.IsNullOrEmpty(boldPath) && File.Exists(boldPath)
                ? File.ReadAllBytes(boldPath)
                : _regular;
        }

        public FontResolverInfo ResolveTypeface(string familyName, bool isBold, bool isItalic)
        {
            if (string.IsNullOrEmpty(familyName) ||
                familyName.IndexOf("Noto", StringComparison.OrdinalIgnoreCase) >= 0 ||
                familyName.IndexOf("Source Han", StringComparison.OrdinalIgnoreCase) >= 0 ||
                string.Equals(familyName, "sans-serif", StringComparison.OrdinalIgnoreCase))
            {
                return new FontResolverInfo(isBold ? "NotoSansSC-Bold" : "NotoSansSC-Regular");
            }

            return new FontResolverInfo("NotoSansSC-Regular");
        }

        public byte[] GetFont(string faceName)
        {
            if (string.Equals(faceName, "NotoSansSC-Bold", StringComparison.OrdinalIgnoreCase))
            {
                return _bold;
            }

            return _regular;
        }

        public static string FindDefaultFontPath()
        {
            string[] candidates =
            {
                "/workspace/maritime-sim-design/fonts/NotoSansSC-Regular.ttf",
                Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "fonts", "NotoSansSC-Regular.ttf")),
                "/workspace/maritime-sim-design/fonts/NotoSansSC-Regular.otf",
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Fonts), "NotoSansSC-Regular.ttf")
            };
            for (int i = 0; i < candidates.Length; i++)
            {
                if (File.Exists(candidates[i]))
                {
                    return candidates[i];
                }
            }

            return null;
        }
    }
}
