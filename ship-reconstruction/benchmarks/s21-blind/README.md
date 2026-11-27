# S2.1 三船独立验收基准

所有输入由离线解析方程生成。这里没有实船材料。独立盲测的 7 张 DXF 与真值在同一包内分目录保存；接口运行时只传入 casebook/inputs/A、B 或 C。SHA-256 固定最初盲测输入、设计方程、真值和预登记评分器。仅为重跑时请直接使用已归档的 DXF；重新生成 CAD 时文件标识和生成时间可能变化。

建议 Python 3.13.2、ezdxf 1.4.5、NumPy 2.5.5；研发侧被冻结在 Git 中，通过本机预装的离线解释器运行。已有提交及依赖时无需联网。三船运行及三维回读如下。

```sh
python run_independent.py /path/to/repo a6ecfd4820e2fad5efc15dd7439f7173c37c0484 clean-run
python verify_cad.py clean-run
python score_submission.py selfcheck score-selfcheck.json
python score_submission.py queries queries.json
python score_submission.py score scores.json --predictions predictions.json
```

S3 下游的预测 JSON 是三元素列表，每个元素含 case、holdout、areas、hydro。holdout 按 queries.json 的 id 提供 y_m；areas 按相应 id 提供 area_m2；hydro 提供 draft_m、volume_m3、LCB_m、TCB_m、KB_m、waterplane_m2、BMt_m。船轴 Y 是带符号的米制横坐标。未来重建器不得读取包含真值的测试文件；已有公开结果的本套数据适合回归。冻结积分及采样的生成源码为 forms.py、build.py、analytic.py，S3 还没有曲面验收结论。
