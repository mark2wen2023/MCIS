# S3 船轴与闭合验证的合成对照

Chat 冻结提交为 c9883e3060c1cee7a427a814d3a7735608e6c18b。box-readback.csv 包含两组具有解析真值的合成箱体。A 使用船轴，B 使用局部坐标。以同仓的 read_exchange 回读原始 GLB，在吃水 1 m 时得到 30 m³，解析值为 18 m³。使用同仓 exchange 转换后，排水体积和水线面积分别为 18 m³ 和 18 m²。

补丁仅供该冻结提交复验。在其隔离副本上执行 git apply，重跑 scripts/s3_run.py 与单元测试。补丁还使缺少闭合验证依赖的输入返回 blocked。验收读取报告的 status 和实际资产列表。原 CLI 固定上游提交且只收单 DXF，多图接入及新版上游直连仍待 Chat 集成。
