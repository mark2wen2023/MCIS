---
name: ship-reconstruction
description: 根据船舶 DWG、DXF、原始型线与可选设计排水实体，离线重建有来源证据的研究级船体、构件和舱室。用于图纸识别、曲面重建、静水力复算、模型导出、盲测和资料缺项登记。适合由支持命令执行的不同智能体调用。
---

# 船舶三维重建

仅需从陌生图纸提取几何时，先运行 `python scripts/s2.py run <图纸目录> --out <新目录>`。五项离线工具、坐标约定、证据与失败状态见 [S2 工具契约](references/s2.md)。将 geometry.json 交给后续曲面算法，并保留原始空格与镜像候选。

从当前 Skill 目录执行。使用新的本地输出目录保留每次运行。把案件资料和结果放在安装目录以外。

1. 清点同版图纸。优先识别型线、总布置、基本结构及典型剖面。保留原件及指纹。对照版本和图签，按需要引入公开来源或获授权的设计实体。
2. 先直接运行入口。DXF 可直接读取。DWG 需要本机 LibreDWG 的 dwg2dxf，亦可传入 ODA 转换器。转换工具、原件和转换件分别记录指纹。含关键块、样条或弧形多段线的图纸，须对照独立读取结果检查引用内容和几何。
3. 阅读 report.json。遇到 needs_evidence，依据 issues 定位单位、船轴、表头或证据缺口。可在新目录用带同版原件指纹的配置复跑。使用 schemas/profile.schema.json 与 templates/README.md。推断、计算与原图文字分别保留。图面局部坐标与实际船轴分别登记。
4. 分开登记训练和留出曲线。保持原始空格。先重建四角有支撑的半宽单元，再按证据增加横剖、水线、构件及舱室；适用范围参见 references/capabilities.md。在实测区域之外封盖时记录边界假设。partial_surface 可交付开片，排水指标须等待水密实体。
5. 读取逐面来源和资产指纹。复核法向、边长、面积、退化、自交、水密性与 GLB 回读。面积、体积及浮心须在同一基准面、吃水及单位下比较。读取 heldout.json 与独立评分，记录高残差、局部翻折和撤回的候选。
6. 按角色交付 display、contact、proxy、displacement 与 shell-candidate，并说明各自成立条件。复核缺失构件、舱室查验结果、研究假设和有限元待补参数。工程批准须由有权方另行签署。

## 安装与调用

将本目录完整复制到智能体可查找的 skills 目录。普通 Python 客户端也可直接运行。实测环境为 Python 3.13。预先准备与平台匹配的 wheel，可在内网安装依赖。

```sh
python -m pip install --no-index --find-links /path/to/wheels -r requirements.txt
python scripts/reconstruct.py /path/to/drawings --out /path/to/new-run
python scripts/reconstruct.py /path/to/drawings --profile /path/to/profile.json --out /path/to/new-review
python benchmarks/check.py --out /path/to/new-benchmark
python -m unittest discover -s tests
```

入口退出 4 表示待补证。对已生成的结果还须区分 bounded_model 和 partial_surface。基准程序遇到任何一项几何超限也退出 4，并保存全部评分。每项测试的失败须随交付保存。检查 references/lessons.md 中的失败判别方法后再修改算法。

### S2.1 图纸配准与 S4 构件预研

先运行 scripts/preflight.py 查看当前环境；离线安装使用 scripts/install_env.py --venv NEW --wheelhouse WHEELS。锁与已测平台见 references 下的 cp313.lock。DXF 提取仍可独立调用。涉及闭合、自交、点到网格误差的验收依赖 libigl/CGAL，无法执行时登记环境阻塞。

读取 schemas/geometry.schema.json 与 references/geometry-2.1.md，执行 geometry_data_validate 后读取 modeling_admission 及受阻区域。可参照 examples/s21 的三个完整接口样例。有争议的站位和舷别保留候选，保留甲板侧视与横剖端点各自证据。S3 消费方使用固定契约。S4 的二维构件试验入口与已支持的注记范围见 references/s4-preview.md。
