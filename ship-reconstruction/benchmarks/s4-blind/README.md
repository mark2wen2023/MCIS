# S4 独立合成基准

建议 Python 3.13.2、ezdxf 1.4.5、NumPy 2.5.5，并安装被测发布包附带的离线依赖。输入、真值和预登记评分冻结于 freeze.json，SHA-256 为 2589cf17690f5bb5bc76d5c7024f1f0201d66e89b2fba8449ec30b4221a452ac。已交付冻结的实际 DXF；重新生成 DXF 会有 CAD 文件标识或时间差异。全套可运行 python all_checks.py /path/to/repo 提交号 clean-run。总入口退出 0 表示全部预期相符，1 表示实测有未通过项，2 表示入口错误；原始结果均留存。

```sh
python run.py /path/to/repo d1d262cf22dd9ea7bc7af2a7bd1a5a45a71e9d72 clean-run
python legacy.py /path/to/repo d1d262cf22dd9ea7bc7af2a7bd1a5a45a71e9d72 clean-run
python arrays.py run /path/to/repo d1d262cf22dd9ea7bc7af2a7bd1a5a45a71e9d72 extra-array runs/clean-run/阵列补充
python extra_audit.py clean-run
python panel_controls.py run /path/to/repo d1d262cf22dd9ea7bc7af2a7bd1a5a45a71e9d72 extra-panels runs/clean-run/局部板件控制
python asset_controls.py /path/to/repo d1d262cf22dd9ea7bc7af2a7bd1a5a45a71e9d72 clean-run
```

run.py 只向普通程序传入每组 DXF 目录和新输出目录。失败、缺失观测和证据不足分别保留。逐轮 ZIP 含完整结构结果、各项断言及 CLI 回执。scorer-control.json 是对评分器本身的阳性与伪来源负控，不能作为生产软件通过的凭证。旧版 9 项、原始 48 项、阵列 4 项与工程复核 6 项各自列分母。
