# 1 毫米短边的写出与恢复

从冻结提交取出原始导出器。实验用 4 个顶点和 2 个三角形组成的矩形，长 1 米，宽分别为 1 毫米、10 毫米。在 11 个已知 X 偏移上重复试验。每次只改动输入坐标的表示顺序。轴变换沿用 MCIS 的 (x,y,z) → glTF 的 (x,z,−y)，读回时执行逆变换。

| CSV 中的方式 | 写入原导出器前的操作 |
|---|---|
| global | 全局绝对坐标以 float64 进入原导出器，再存为 float32。 |
| local_from_f64 | 全局 float64 减去已知原点，再导出局部坐标。 |
| late_recentre | 全局坐标已量化成 float32，再减原点。用于检验改变顺序能否弥补损失。 |
| local_from_decimal | 从十进制精确输入取得局部余量，再转为浮点。原点单独保存在实验清单。 |

真值来自十进制字符串。用 75 位十进制运算计算恢复误差，用 NumPy 预测位置量化，用 trimesh 独立读取实际 GLB 的面索引和顶点。每个成功样本均以读回顶点再次调用原导出器，并核对两次文件字节。局部原点保存在实验旁件；本实验只调用原导出器，没有实现局部坐标产品功能。例中无旋转、缩放和混合坐标系，结果限于所列输入。正式采用前，需要工程签署的坐标约定、精度预算及适用范围。

## 复现

在 MCIS 仓库中将本目录路径设为 D，空的临时工作目录设为 R，使用环境记录内的依赖版本。以下命令中的 output 和 repeat 必须是尚未创建的目录。已安装依赖后，所有计算和格式核验均可离线运行。Khronos 核验器的版本为 2.0.0-dev.3.10，NODE_PATH 指向已安装 gltf-validator 的 node_modules 目录。

```sh
PIN=4293d24f99ad1dc16fac5e6660bea467f01d6145
mkdir -p "$R/frozen"
git archive "$PIN" service contracts | tar -xf - -C "$R/frozen"
python3 "$D/coordinate_experiment.py" "$R/frozen" "$R/output"
python3 "$D/coordinate_experiment.py" "$R/frozen" "$R/repeat"
diff -qr "$R/output" "$R/repeat"
node "$D/validate_models.cjs" "$R/output/models" "$R/格式核验.json"
python3 "$D/plot_results.py" "$R/output/metrics.csv" "$R/一毫米往返对照.png"
```

## 读数

- 对于正的正规 float32，某个二进制数量级内，相邻可表示值的间距为 2^(floor(log2(x))−23)。在 16,384 米处向上的间距恰为 1.953125 毫米。1 毫米略大于半间距，写出后被舍入到下一个可表示值。两片三角面的面积同时增大 95.3125%，文件成功写出。
- 在 32,768 米处，向上的间距变为 3.90625 毫米。1 毫米不足半间距，绝对坐标写法合并顶点，修复后的导出器拒绝。先减原点的样本保留 1.000000047497 毫米，最大顶点恢复误差约 4.75×10⁻¹¹ 米。先量化再减原点的样本同样被拒绝。
- 在 10¹² 米的压力样本中，只还原成一个全局 float64 会产生 0.0234375 毫米误差。在 2⁴⁴ 米的极端样本中，即使源坐标已是 float64，做差时也可能只得到零；直接从精确源取得局部余量仍能写出 1 毫米边。此时将原点和余量再合为一个全局 float64，误差可回到 1 毫米。图 B 中全局 float32 在 10¹² 米处的突峰还包含原点本身不能精确表示的偏差。
- 在 88 次对照中，67 个真实 GLB 经独立读取且二次写出字节一致；21 次由导出器拒绝。“往返一致”保留的是已经量化的坐标。对于 21 次拒绝行，面积与量化坐标属于预测列，文件路径和真实往返误差空置。

## 数据字典

`input.json` 保存单位、精确原点与局部顶点、三角拓扑、轴变换和代码标识。`observations.json` 保存逐顶点实际输入、float32 预测和可读取的输出。`metrics.csv` 中距离单位为米，面积为平方米；`max_area_relative_change` 是无符号相对误差，乘 100 得百分数。`glb_round_trip_vs_export_input_m` 衡量实际文件读回相对导出器输入的最大三维距离。`glb_restored_vs_exact_m` 衡量恢复为全局 float64 后相对原始真值的最大误差。`error_split_frame_m` 则以高精度分别保留原点和余量。每个写出文件的 SHA-256 均记录在 CSV 内。

GLB 2.0 的结构、坐标约定和访问器定义可对照 [Khronos glTF 2.0 规范](https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html)。
