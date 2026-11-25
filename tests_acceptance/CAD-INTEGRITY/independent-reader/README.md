# 离线 DWG 直读对照

本探针使用 ACadSharp 3.8.35 从 DWG 直接读取块成员、旧式二维多段线、顶点顺序、位置、宽度、标志、凸度和单行文字。预先准备 .NET 10 和 NuGet 包，构建后可在禁止网络的进程中运行。输出包含私有几何与原文，请始终写入仓库以外的本地目录。

```sh
dotnet restore IndependentReader.csproj
dotnet build --no-restore -c Release IndependentReader.csproj
dotnet bin/Release/net10.0/IndependentReader.dll --fixture /local/private/test.dwg
dotnet bin/Release/net10.0/IndependentReader.dll /local/private/test.dwg /local/private/objects.json
```

合成入口用独立写入器直接生成 R2000 DWG，其中有两个顶点及一个非零凸度。核查 DXF 时应按原始组码计每个顶点的出现次数；读取器归一化后的对象集合会隐藏重复。未知非图形对象的告警保留在 warnings。导出只覆盖程序列出的对象和字段。

### 对照实验

在 ODA File Converter 中关闭 Audit，输入目录仅放本次样本，输出使用新的私有目录。成功条件应同时验证进程退出、非空可读 DXF、逐文件错误文件与目标几何字段。有些读取失败仍返回进程码 0。保留原始结果；对 MIF 字符串的解释仅写入独立比对副本。对于拟合样条，额外的控制点和节点须单独记录。

工具来源见 [ACadSharp](https://github.com/DomCR/ACadSharp) 和 [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter)。

合成所有权实验脚本位于上级目录的 compare_vertex_ownership.py。传入新的临时目录、可执行的基线写出器和防重复实验写出器，二者均为离线研究用驱动。脚本对同一串生成的 DXF 字节只改 VERTEX 的 330 值，并检查两个输出中的原始顶点出现次数、字段值和相邻线段。整个中间 DWG 的句柄冲突另外记录。实验驱动与写出器补丁保存在本地 CAD-03 研究交付中。
