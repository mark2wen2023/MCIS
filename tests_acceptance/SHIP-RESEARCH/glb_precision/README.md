# 研究用 GLB 的独立验收

被测 MCIS 源码固定于 `4293d24f99ad1dc16fac5e6660bea467f01d6145`。QA 与研发位于不同分支，测试时用环境变量指定冻结源树。以下命令在具有相应 Git 对象和依赖的 MCIS 仓库中执行。临时目录保存源码快照和合成输出。

```sh
D="$PWD/tests_acceptance/SHIP-RESEARCH/glb_precision"
R=$(mktemp -d)
PIN=4293d24f99ad1dc16fac5e6660bea467f01d6145
mkdir "$R/frozen"
git archive "$PIN" service contracts | tar -xf - -C "$R/frozen"
MCIS_SOURCE_TREE="$R/frozen" python3 -m pytest -q -p no:cacheprovider "$D/test_glb_fix_boundaries.py"
python3 "$D/coordinate_experiment.py" "$R/frozen" "$R/precision"
```

| 本次冻结验收 | 实测 |
|---|---|
| 跨版本复用的独立用例 | 40/40 通过 |
| 对应五项修复的上游新增用例 | 5/5 通过 |
| 冻结源码的全部船舶专项 | 78/78 通过，含上列新增 5 项 |
| 本目录的独立边界用例 | 81/81 通过 |
| 另设的五项扩展质量期望 | 5 项仍未满足 |
| 坐标表示对照 | 88 次调用，67 个写出并通过独立读取及 Khronos 格式校验，21 次受控拒绝 |

原五个触发条件均通过复验，涉及单精度写出后的折叠、缺失面来源、证据定位类型、畸形摘要以及截断容器。扩展检查记录了自由三角形法向翻转、待审单元从中间结果再次导出、布尔值用作面编号、空面记录引发未归类异常、外来 GLB 内嵌授权与旁件矛盾仍能绑定。研究接口自身的正式放样标志为 false。

1 毫米短边移至 16,384 米处后，全局 float32 实际写出 1.953125 毫米，几何仍有正面积。移至 32,768 米处时，原导出器拒绝折叠；先以局部坐标写出可读回约 1.0000000475 毫米。完整对照、依赖和字段解释见 [坐标实验](precision-study.md)。本目录所有输入均为数学构造。复验环境为 Python 3.13.2、pytest 8.4.2、NumPy 2.2.6、trimesh 4.8.3、Matplotlib 3.10.6、Node.js 22.20.0、gltf-validator 2.0.0-dev.3.10。
