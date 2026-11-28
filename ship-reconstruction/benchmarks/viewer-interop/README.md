# 关节坐标对照

用 make_case.py 生成 local 和 baked 两个数据目录（命令行依次传目录、编码）。刚体父节点按三轴旋转并平移，其下三个关节具有不同支点、正反斜轴及一个坐标轴；每个关节测量四个角度，包括采样点之间的角度。解析真值通过 Rodrigues 公式直接计算离轴测点的空间位置。local 的船舶参考原点写入 GLB，baked 将同一原点换轴后预加进父节点，两者代表同一组实物位置。

将 Unity 查看模板和 JointProbe.cs 放入项目 Assets。每次将某一种编码的生成文件放入 StreamingAssets，用 HullBuild.Build 构建独立程序。运行时传 --verify-world，将日志另存为 unity-local.log 或 unity-baked.log。探针调用现有播放器的 Pose，对实际载入的世界节点求坐标，同时检查固定构件的变换。Blender 使用相同 GLB 和关节采样，以后台方式运行 blender_probe.py，两个附加参数是案例目录和 CSV 路径。命名为 blender-local.csv 和 blender-baked.csv。compare.py 接收这两组案例及日志所在的目录，统一交换轴并用坐标契约恢复参考原点；容差为 0.00002 m。这个外部验收器承担绝对坐标恢复，普通查看器显示局部场景。

synthetic_hydro.py 接收输出目录，对有解析排水体积和浮心的封闭长方体运行既有 hydro 和 GLB 读回逻辑。两项试验均为虚构几何。
