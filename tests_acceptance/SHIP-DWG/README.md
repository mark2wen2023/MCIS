# 离线 DWG 转换质量验收

本入口调用已存在的 ship_reconstruction.dwg_adapter.convert_and_parse。独立用 GNU LibreDWG 的 dwgread 从原始 DWG 导出对象和数值，用 dwg2dxf 生成 DXF，再由 ezdxf 读取转换件。两种原生程序共享 LibreDWG 的 DWG 解码器。复核证据覆盖解码得到的数据，专有 CAD 的绘制效果仍需同版出图件判定。

## 运行

测试机须有 Python 3.11+、ezdxf、GNU LibreDWG 及可执行的 dwgread 和 dwg2dxf。此次实测分别使用 ezdxf 1.4.5 与 GNU LibreDWG 0.14。macOS 联网准备可用 Homebrew 安装 libredwg，内网部署预置同平台二进制与动态库。运行工具没有联网依赖。

将私有原图放在同一目录。清单中的 drawings 数组按图列出 id、file、sha256、modelspace_entities；在型线图条目另列 offset_values、station_labels、column_labels、grid_lines 等经定位的实体句柄。基准材料持有人保管原件、私有清单与逐句柄报告。

```sh
python tests_acceptance/SHIP-DWG/check.py 私有清单.json 原始DWG目录 新的私有输出目录
```

输出逐图 DXF、转换和直读日志、原件与派生件哈希以及 quality.json。退出 4 表示发现异常或输入不完整；对本次真实基准，默认命令预期返回 4。若明确限定模型空间，可加 --modelspace-only，异常仍保存在结果里。whole_document_approved 保持 false。转换前后只按原图和真实转换件比对；历史模型或电子表仅作外部参照。

## 检查范围

- 模型空间按句柄双向核对实体类型与图层，坐标等数值使用绝对容差 1e-6 个图纸单位。主控调用的已有解析器与直接调用 dwg2dxf 所得 DXF 哈希也须相等。
- TEXT、MTEXT 对比原文、位置和字高，TEXT 另核转角。DIMENSION 对比覆盖文字、缓存数值、类型、定义点与适用的角度。缓存数值与从定义点重新测量是两个概念。
- 直线、圆、圆弧、椭圆、射线类 XLINE、点、多段线、样条、引线、块引用、SOLID 与填充按 compare.py 中的显式字段比对。样条区分拟合点和控制点；填充比较所支持的边界数据。线型、字体显示、材料、打印样式、外部参照及所有非图形对象的保真度尚未验收。
- 型值表按指定图元定位，复核数字、站号、表头及网格线。此项检查辨别转换丢字、移动或改值，工程单位、型值采用口径和图纸版次仍由专业人员确定。
- 模型空间以外逐原实体核对句柄存在性，并复核找到的 TEXT/MTEXT。CAD 的 Unicode 转义单列计数；其余块内图形仅核对句柄的存在，不据此推定几何属性一致。详细报告留在本地。

本分支只跟踪通用验收代码和汇总统计。私有清单、真实图纸、派生 DXF、直读 JSON、原始日志、文字、坐标及句柄明细均无须入库。
