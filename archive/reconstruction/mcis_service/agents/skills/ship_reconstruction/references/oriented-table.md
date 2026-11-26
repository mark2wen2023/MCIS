# 从任意平面方向的 CAD 格表读取逐格证据

在安装了项目与 ezdxf 的服务 Python 环境中，从 service 目录运行。输入为本地 DXF 和 JSON 配置，输出路径须尚未存在。运行过程中直接读取源文件，计算原始 DXF 指纹。

```sh
python -m mcis_service.agents.skills.ship_reconstruction.oriented_table drawing.dxf profile.json --output table-candidate.json
```

下列合成例子要求三条站行和三条数据列。列表首尾是已知题头，数量给出待核的表格形状。中间的 null 让程序直接转录实际行、列标题。若已知完整标题，可逐项列出，让程序同时检验其顺序。标题匹配区分大小写，忽略首尾空白。

```json
{
  "row_labels": ["R0", null, "R2"],
  "column_labels": ["Level A", null, "Level C"],
  "layout": "Model",
  "plane_z": 0.0,
  "tolerance": 0.001
}
```

程序在指定布局与 WCS 的 XY 平面内查找正交直线网格，从实测边线确定方向，支持任意平面内旋转、左右反射和行列转置后的题头配置。正列轴从第一数据列指向最后一列，正行轴从第一数据行指向最后一行。局部原点取第一数据格靠近行头、列头的边线交点。配置的容差使用图面单位，描述同线、间隙、共面和边界命中的误差带。工程半宽单位另行给出。

结果中的 `frame` 保留 WCS 原点、两个有号单位向量及行列式；负行列式表示该语义轴相对 WCS 的方向。附带 `TableFrame.to_local` 和 `to_wcs`。二者恢复所选平面上的 XY，原实体的三维锚点另存于每条证据。每个 `cells` 条目保留原行列题头、数值原文、源实体句柄及原 WCS/局部锚点，还记录四边的直线/多段线句柄与段序号。重叠或接续的网格段可拥有多个句柄。

`numeric_text` 表示格内唯一数字文字，保留原样词形；`blank_unknown` 表示该格没有受支持的直接文字；`conflict`、`non_numeric_text` 和 `boundary_ambiguous` 需要复核。遇到重复候选表、边框断开或缺少题头，返回问题并拒绝选择。CLI 的 0 表示唯一候选且无定位问题，2 表示需核查。请同时读取解析器的 `source_issues` 及未展开的 `unexpanded_insert_handles`。空格和缺失从不补零。

支持模型或图纸空间中原生 TEXT/MTEXT、LINE 与 LWPOLYLINE 直线段。要求行头位于数据列前同一列，列头紧邻数据区，目标为有连续完整边界的矩形。多级题头可以位于目标范围之外。未展开的 INSERT/ATTRIB、弧形边框、不共面的三维格表、透视/斜切、图片、缺列线和合并单元格需要其他证据；异常结果不能成为正式放样依据。当前实现不提供从图名猜测船体坐标、工程单位或空白语义的能力。极大图面可由原有解析器按布局预分流。

## 将候选送入现有研究审阅层

```python
from mcis_service.agents.skills.ship_reconstruction.oriented_offsets import offsets_for_review
from mcis_service.agents.skills.ship_reconstruction.offset_bridge import prepare_offset_samples

observations = offsets_for_review(
    table_candidate,
    station_axis="row",
    stations_m_by_label={"R0": 0.0, "R1": 1.0, "R2": 2.0},
    heights_m_by_label={"Level A": 0.0, "Level B": 0.5, "Level C": 1.0},
    unit="mm",
    mapping_source={"document_id": profile_document_id, "locator": profile_locator},
)
samples = prepare_offset_samples(
    observations,
    stations_m=observations["stations_m"],
    heights_m=observations["heights_m"],
    frame_id=reviewed_ship_frame_id,
    reviews=matching_review_records,
)
```

站与水线可以在任一方向；同一批候选中行列意义、数值单位和船体工程坐标必须由调用方提供来源。适配器调用现有 normalize_row、validate_offsets，保留原文、各格界线与映射来源，负半宽和当前归一化器不支持的数字形式会被拒绝。冻结的稀疏层继续逐项核对值、坐标、来源和研究审核记录。跨文件或旋转工作副本的审核记录不会自动迁移。返回值的正式放样许可始终为 false。以上提供函数与本地 CLI；联网服务路由、运行时工具注册和签署流程需要各自接入。

从 JSON 恢复表格候选时，适配器要求源图纸的 document.sha256 是由 64 个 ASCII 十六进制字符构成的字符串，大小写均可。核实摘要确实属于输入文件时，须从原 DXF 调用 parse_drawing 或重新计算 SHA-256 后比对。
