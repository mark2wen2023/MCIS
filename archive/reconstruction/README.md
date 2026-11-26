# 图纸表格识别与证据检查归档

本目录保存 MCIS 研究分支中通用模块的冻结快照。drawing_parser 读入 DXF 图元、句柄与单位，对 DWG 记录离线转换需求。oriented_table 在局部坐标系识别旋转及镜像表格。table_extraction 保留文字句柄并按纵向允差分行。data_assessment 核对图纸种类、已审核观测和量纲，列出缺项及冲突。

tests 目录在运行时用虚构标签、数值和坐标生成 DXF。运行环境为 Python 3.11 以上、ezdxf 和 pytest。在本目录执行下列命令即可复验。资料完备性判断中的放样授权始终为关闭状态。

```sh
python -m pytest tests
```
