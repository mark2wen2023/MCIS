using System;
using System.Collections.Generic;
using System.IO;
using Xunit;
using Xunit.Sdk;

namespace Mcis.Tests.W14
{
    /// <summary>
    /// 从测试工程目录定位 ../../reports/yangze22 的真实报告数据；文件缺失时给出明确失败提示，
    /// 不把报告数据复制进仓库。
    /// </summary>
    internal static class Yangze22TestData
    {
        public static string CaseDirectory
        {
            get
            {
                string projectDir = FindProjectDirectory();
                string path = Path.GetFullPath(Path.Combine(projectDir, "..", "..", "reports", "yangze22"));
                if (!Directory.Exists(path))
                {
                    throw new XunitException(
                        "未找到真实报告目录：" + path +
                        "。请确认仓库根目录下 reports/yangze22/ 存在（测试不复制报告数据）。");
                }
                return path;
            }
        }

        public static string CaseJsonPath
        {
            get { return Path.Combine(CaseDirectory, "case.json"); }
        }

        public static string TracksCsvPath
        {
            get { return Path.Combine(CaseDirectory, "tracks_from_report.csv"); }
        }

        public static string[] ReadTrackLines()
        {
            string path = TracksCsvPath;
            Assert.True(File.Exists(path), "缺少真实航迹文件：" + path + "（测试不复制报告数据）");
            return File.ReadAllLines(path);
        }

        public static string ReadCaseJson()
        {
            string path = CaseJsonPath;
            Assert.True(File.Exists(path), "缺少真实案例文件：" + path + "（测试不复制报告数据）");
            return File.ReadAllText(path);
        }

        private static string FindProjectDirectory()
        {
            string dir = AppContext.BaseDirectory;
            for (int i = 0; i < 12 && !string.IsNullOrEmpty(dir); i++)
            {
                if (File.Exists(Path.Combine(dir, "Tests_W14_WhatIf.csproj")))
                {
                    return dir;
                }
                DirectoryInfo parent = Directory.GetParent(dir);
                if (parent == null)
                {
                    break;
                }
                dir = parent.FullName;
            }
            throw new XunitException(
                "无法从测试输出目录定位 Tests_W14_WhatIf.csproj：" + AppContext.BaseDirectory);
        }
    }
}
