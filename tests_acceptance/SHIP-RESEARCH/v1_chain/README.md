# 船舶研究模型的独立贯通验收

在具有所需 Git 对象和依赖的 MCIS 仓库根目录运行。仅合成图层使用本实验的布局及模拟审核约定。原生提取和放样模块之间的数据整理在 run_chain.py 内明示。图面位置、原始文字、实体引用、逐站样点、几何、审查旁件和 GLB 均写入新目录。研究授权与正式授权分别记录。

```sh
R=$(mktemp -d)
mkdir "$R/frozen"
git archive fd40255e956ef579ba7ed7c8aa41b722388ad1a4 service contracts | tar -xf - -C "$R/frozen"
D="$PWD/tests_acceptance/SHIP-RESEARCH/v1_chain"
export MCIS_SOURCE_TREE="$R/frozen" PYTHONHASHSEED=0 PYTHONDONTWRITEBYTECODE=1
python3 "$D/run_chain.py" "$R/frozen" "$R/experiment"
python3 "$D/check_interfaces.py" "$R/frozen" "$R/experiment" "$R/interfaces.json"
python3 -m pytest -q -p no:cacheprovider "$D/precision/test_precision_contracts.py"
python3 -m pytest -q -p no:cacheprovider "$D/precision/test_open_observations.py"
```

Python 3.13、ezdxf 1.4.5、NumPy、trimesh 4.8.3、jsonschema 和 pytest。无需网路调用。设定 PYTHONHASHSEED=0 使 DXF 类记录的顺序及来源指纹可复现。最后一组保留五条当前失败断言，详见 precision/README.md。

七个 DXF 文件中，完整型、单格变更、单格缺失、异型小表分别写出 48、48、32、16 个三角面。改动 125 毫米从文件传递到了正确顶点。待审、同格重复和整行空白三组停止。整行空白与直接将 SI 型值记录送入横剖面入口的复现实验在 fd40255 和 4293d24 结果相同。测试脚本的工程预算只服务于这些虚构样本；真实项目需要选择本船基准与验证指标。
