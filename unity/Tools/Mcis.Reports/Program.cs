using System;
using System.IO;
using Mcis.Reports;

internal static class Program
{
    private static int Main(string[] args)
    {
        string font = NotoSansScFontResolver.FindDefaultFontPath();
        if (string.IsNullOrEmpty(font) || !File.Exists(font))
        {
            Console.Error.WriteLine("找不到 Noto Sans SC 字体（OFL）。请将字体放到 /workspace/maritime-sim-design/fonts/NotoSansSC-Regular.otf");
            return 2;
        }

        string output = args.Length > 0
            ? args[0]
            : "/workspace/maritime-sim-design/samples/Demo_LilyMary_调查报告.pdf";

        try
        {
            InvestigationReportBuilder.ReportBuildResult result = InvestigationReportBuilder.BuildLilyMarySample(output, font);
            Console.WriteLine("PDF=" + result.PdfPath);
            Console.WriteLine("PAGES=" + result.PageCount);
            Console.WriteLine("PDF_SHA256=" + result.PdfSha256);
            Console.WriteLine("PACKAGE_SHA256=" + result.PackageSha256);
            Console.WriteLine("FONT=" + font);
            return 0;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex);
            return 1;
        }
    }
}
