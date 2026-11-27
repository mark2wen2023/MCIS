# S2.1 独立复验与 S4 预研交接

生产源码冻结 a6ecfd4820e2fad5efc15dd7439f7173c37c0484；S2 上轮交付 370addfd617737aa1b0efd515d2c277a8696c2dd 是其祖先。接口规范及三示例首次冻结于 0cfbcb74ae7749e83a02baccab4ec68d71b134a4。源文件 schemas/geometry.schema.json 在生产冻结中保持同一字节序列。后续 Git 归档提交用于附带独立合成基准、实验回执和说明。

|分类|可复现实验与结果|
|---|---|
|正常通过|三份开发接口样例均从其合成 DXF 重读。三艘隔离的陌生合成船在提取阶段 3/3，127 个有依据格、68 个原生曲线实例和 170 个控制点均与独立真值对齐。S3 曲面拟合未纳入本阶段验收。|
|正确拒绝|冲突单元保留多个原文和句柄。删去投影控制点的三份副本均拒绝确定变换。伪造正、负两个舷别决定均被正式入口拒绝。具备正反控制的跨图舷别试验 9/9。|
|证据不足|历史 54 工况有 53 个通过原预登记全部检查。其余一案 15 格的单位出现在另一布局，缺少适用范围证明，继续保留未知。三艘盲船的观测符合预期，但均缺少本版规则要求的全船域依据。|
|算法失败及修正|首版忽略平底同高段的外缘和近切点，导致站剖误配。原生样条逐段求根并检查水平段内的极值后，仍发现栅线方向取整会改变基线交点。现从有文字对应的真实刻度线拟合法向。中途将整船站位覆盖要求套用于单支水线，造成既有定位退化；改为曲线可见范围并统一端点容差。公开回归保留有理平段、切点、站位竞争和端点漂移合成例。|
|环境阻塞|缺少 libigl 或 CGAL 扩展时，预检退出 4、网格闭合不予确认。提供正确软件包后同一环境可恢复。Python 3.13 的 macOS arm64 与 Linux amd64 分别有锁和实跑记录；其他系统尚未验收。|
|结构预研|复用原有挤出与质量检查，在两图各自有配准、相互引用、尺寸和法向明确的条件下生成十种合成棱柱构件。独立 S4 正负控 9 项。缺尺寸、投影矛盾、两图无可验证引用等情形会留下缺项并阻止生成对应实体。通用原始工程结构图的任意注记识读、复杂型钢、焊接和壳体布尔相贯尚未验收。|

## 软件环境与失败恢复

scripts/geometry.py 的网格拓扑及绕序采用既有几何检查及 trimesh，面积和带符号体积由 trimesh 计算。libigl 判断顶点流形性；其 CGAL 扩展检测三角面自交。reconstruct.py 和结构试验还使用 libigl 的点到三角网格距离。可计算体积的网格可能仍不满足闭合、自交或体积实体的联合验收条件。

从 Skill 目录复验。需要 Python 3.13 及目标平台 wheel。没有本地 wheel 时可在获准联网的设备用对应锁执行 pip download --only-binary=:all: --require-hashes。安装入口默认用本机平台和 Python 版本选择已测锁。源码包不含第三方编译库。

```sh
python3.13 scripts/install_env.py --venv /tmp/ship-test-env --wheelhouse /path/to/wheels
/tmp/ship-test-env/bin/python scripts/preflight.py
/tmp/ship-test-env/bin/python -m unittest discover -s tests -v
/tmp/ship-test-env/bin/python scripts/s2.py run examples/s21/A/input.dxf --out /tmp/ship-example-new
/tmp/ship-test-env/bin/python scripts/s2.py geometry_data_validate /tmp/ship-example-new/geometry.json --out /tmp/ship-check-new
```

运行历史 54 工况使用 benchmarks/s2/run_suite.py，随后运行同目录 independent.py。三船评分所需独立入口、Git 冻结方式、几何方程及真值均在 benchmarks/s21-blind。生产入口只接收对应船型的图纸目录。已公开的三船资料可作回归，新适用范围仍需要新留出样本。

## 交付边界

跨图坐标消歧需有独立同名非中线特征、图号引用、参考视图经核验的控制域和船轴约定。registration_decision 有明确见证才有符号结论；原矩阵候选保持可追溯。缺少跨图结合点时，不同视图可各自有局部舷别证据。古典左右各画半组站位的横剖图不能直接给出两侧实际外形。侧视同一条曲线经多个格网得到的观测应按源图、曲线及文字句柄去重计数。

A 的 full_research 可驱动下游研究级重建。validation.eligible_for_automatic_full_loft 和 engineering_approved 是原有正式授权字段，始终关闭。只有明确、可识别的原点及船体范围声明能满足本版保守准入。B 有双符号候选，仅允许明示对称区域。C 的重复标数阻塞整船。继续保留空白、未批准值和源曲线。
