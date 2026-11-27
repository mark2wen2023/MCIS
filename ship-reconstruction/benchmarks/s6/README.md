# S3 船轴、静水力与依赖门禁独立复验

原始源码为 Chat 提交 `c9883e3060c1cee7a427a814d3a7735608e6c18b`，上游 S2.1 使用其运行器要求的 `0cfbcb74ae7749e83a02baccab4ec68d71b134a4`。独立分支 `qa/s6-s3-frame` 按历史补丁应用于原始提交，生成 `a247407618b177e10135f14e04bf707962091b87`。两处源码变化分别位于写出 GLB 和确认闭合实体的检查。实验在 macOS arm64、CPython 3.13.2、禁网环境中执行。

## 结论

| 已实测的读取方式 | 合成箱体 1 m 吃水排水量 | 水线面积 | 浮心 |
| --- | ---: | ---: | --- |
| S3 在内存中重建的直接网格 | 18 m³ | 18 m² | (3, 0, 0.5) m |
| 原版 GLB 经过正式船轴读取函数 | 30 m³ | 12 m² | (3, −1, −0.25) m |
| 修补后 GLB 经过同一个读取函数 | 18 m³ | 18 m² | (3, 0, 0.5) m |

原版采用原生船轴写 GLB，因此通用 GLB 解码器读出的文件坐标恰好与原网格一致。正式接收方执行 glTF 到船轴的逆变换时导致错轴。补丁使发送和接收变换正确配对。三种读取的完整体积都为 36 m³，仅凭体积和闭合无法检出这一错位。

- 原版和补丁各跑 S3 专项 55/55、仓库全部测试 68/68。55 项包含在 68 项之中。
- 正式入口新跑 12 个场景组合。A 为全船研究案例，B 仅授权局部对称参考系，C 与另一个明确声明左右形状不同的图纸均阻止生成。两种缺依赖环境分别真实移除完整 libigl，以及仅移除 CGAL 而保留可用的 igl 核心。两者在原版均错误产出 GLB，内部闭合标志为假；补丁均返回 `blocked`、无 GLB。原运行器把受阻也视作命令完成，退出码为 0，消费方应读取 `status` 和文件是否存在。
- 三个纸面原点执行完整 DXF→S2.1→S3，合成箱体的船轴边界和静水力均一致。每个原点另对补丁产物连续五轮配对读写，顶点新增漂移均为 0。纸面平移保持原图物理坐标标注。
- 用一艘左右不等宽、带尖艏的合成船体验证交换函数。三个空间原点均保留 port +2 m 和 starboard −1 m；半吃水体积 15 m³、水线 15 m²、浮心 (38/15, 7/15, 0.5) m。已逐个顶点独立核对 glTF 坐标 `(x, z, -y)`。此船用于验收交换层。所测 S3 建模入口要求对称证据。
- 非对称四面体覆盖零原点、正负二进制可精确表示的偏移、小数偏移和 2²⁴ m 大偏移。前四组正确交换的顶点误差均在本实验 1 μm 阈值内。大偏移直接写为 FLOAT 顶点后偏差最大 1 m，实体体积由 7.5 m³ 变成 6 m³。先保存局部几何、另保留已知的双精度原点可恢复本例，但此处理仅作对照，历史补丁未实现大原点保真。毫米级工程精度仍须单独评估。

`results/direct-mesh-results.json` 对比原始生产函数在内存中重新建成的网格。`results/synthetic-results.json`、`frame-comparison.csv`、`paper-origin-results.json`、`asymmetric-hull-results.json` 保留各组数值。距离采用顶点、面心和边中点双向最近面抽样；其结果只适用于这些样本。

## 离线重新运行

以下变量分别指向 Chat 原始 Git Bundle、含 S2.1 固定提交的本地仓库、带完整依赖的 Python 3.13 解释器、对应平台 wheel 目录和本套脚本目录。每个输出目录必须是新路径。

```sh
git clone "$CHAT_BUNDLE" original
git clone "$CHAT_BUNDLE" patched
git -C patched fetch "$QA/patch-commit.bundle" refs/heads/qa/s6-s3-frame
git -C patched checkout --detach FETCH_HEAD
git clone "$S21_LOCAL" upstream
git -C upstream checkout --detach 0cfbcb74ae7749e83a02baccab4ec68d71b134a4

"$PYTHON" "$QA/prepare_controls.py" --lock upstream/ship-reconstruction/references/macos-arm64-cp313.lock --wheelhouse "$WHEELS" --dest controls
"$PYTHON" "$QA/replay.py" --original original --patched patched --upstream upstream --no-igl controls/no-igl/bin/python --no-cgal controls/no-cgal/bin/python --output primary
"$PYTHON" "$QA/direct_mesh.py" --original original --upstream upstream --cli-results primary --output direct
"$PYTHON" "$QA/origin_replay.py" --original original --patched patched --upstream upstream --output paper
"$PYTHON" "$QA/asymmetric_hull.py" --patched patched --output asymmetric
```

独立复验 ZIP 内的 `patch-commit.bundle` 只含补丁提交，使用时需已有上述 Chat 原始历史。独立效果由合成数据得出。正式工程授权在整个试验期间保持关闭。

## S6.3 交付取证

`s63-intake.json` 记录从同一 Chat 取回的 `s63.git.bundle` 和 `s63.zip` 指纹。两者指向 `b546eda61fcef3bb76393afcc73ab1eee29b268f`。Git 检查通过、ZIP 全体文件与 Git 树逐字节相同。八次提交覆盖 S5.1 到 S6.3。所附 11 项原始测试离线全部通过。该历史与上述 S3 补丁实验独立计数。
