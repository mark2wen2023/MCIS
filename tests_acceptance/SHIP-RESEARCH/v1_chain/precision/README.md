# 研究 GLB 精度与证据独立验收

全部输入是以米计的合成三角形。设置环境变量 `MCIS_SOURCE_TREE` 指向已检出的 MCIS 根目录，使用已安装 pytest、NumPy 和 trimesh 的离线 Python 环境。在本目录运行：

```sh
python -m pytest -q -p no:cacheprovider test_precision_contracts.py
python -m pytest -q -p no:cacheprovider test_open_observations.py
python readback_probe.py ./synthetic-readback
```

第一组含 29 项，覆盖三类误差预算、三轴映射、面编号和单元审核、法向翻转、原点记录与研究标志。第二组含 5 项候选约束，分别要求将原点平移损失纳入全局顶点误差，及在绑定外部资产时校验原点的类型。固定版本 fd40255 第一组全过，第二组实测五项失败。报告中将它们归为两类问题。不要将第二组标记为预期成功或跳过来改变验收口径。

脚本输出合成 GLB、输入、逐面证据、哈希清单、独立二进制读回结果和拒绝样本。三角形坐标经 trimesh 读取，按 glTF 至 MCIS 的逆变换还原。独立计算空间顶点距离、三角面面积与边长变化。此处测试门限仅用于数值边界。通用测试不提供工程公差、实船坐标或正式放样许可。
