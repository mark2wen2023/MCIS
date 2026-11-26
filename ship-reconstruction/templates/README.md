# 配置起点
复制 benchmarks/witness-v2/A.json 可在配套合成图上直接运行。换图时重新登记源文件指纹、文字表头、坐标、尺度及来源。schemas/profile.schema.json 给出可用字段。extrusions 的 outline_handle 与 measure_handle 分别指向同图的闭合多段线和“厚度=数值 单位”或“高度=数值 单位”的文字；positive_normal 给出船轴内的正挤出方向，source 说明轮廓与标注的工程关联。每个独立构件使用单独的图层选择或轮廓记录。
