# S2 → S3 几何观测契约 2.1

规范文件为 schemas/geometry.schema.json，标识 urn:mcis:ship-reconstruction:geometry:2.1.0。S3 消费方先按该规范验证，再运行 scripts/s2.py geometry_data_validate，最后读取 modeling_admission。历史 2.0 仅支持原验证流程。此包提供提取端与示例，曲面适配由下游负责。

- 目标系为右手船轴，X 向艏、Y 向左舷、Z 向上，长度为米。原点和轴注记按图记录。没有原点证据时不得将相对坐标升格为全局位置。
- tables[].cells 保留站位 station_m、水线 level_m、印刷数值 value、米值 value_m、字段及分组。半宽是无符号量。不同单位和高度列必须单独核对。blank_unknown 等状态的数值为 null，明示零保留数字和文字句柄。
- curves[].geometry 保留 DXF 原生参数。样条的控制点、拟合点、阶数、节点、权重和块变换用于回读。samples 是图面采样。DWG 经转换时参数来源为转换件；保留原图、转换件各自的指纹。
- alignment[].frames 中 verified 配准带控制点及留一残差。paper_to_ship_m 是三行三列，左乘列向量 [纸面 X, 纸面 Y, 1]，输出三维米坐标，仅在登记的控制域内使用。ship_coordinate_candidates 保留固定轴、符号、测得刻度及比较残差。两个镜像解不得自动选一。
- topology_features 指向折角、龙骨、甲板边等候选的原生曲线。每条 evidence 的 source_sha256 加 instance 定位具体图纸以及嵌套 CAD 实例。不能凭实体外形补造拓扑连接。
- conflicts 记录重复值和甲板高度与端点冲突；25 mm 为研究筛查阈值。uncertainties 登记纸面与船轴的差别。blocked_regions 指明受影响的局部构件或全船。valid 只表示数据包一致。
- full_research 仅授权研究曲面入口。2.1 自动批准规则仅涵盖单资料组、有明示边界和平盖、矩形型值域完整、明示对称、有带原点的轴向注记的半宽表。local_symmetric 仅在明示对称和边界的条件下放行局部无符号外壳。blocked 拒绝整船，所有工程认证权限关闭。
- examples/s21/A、B、C 均包含原始合成 DXF 及从普通入口提取的完整 JSON；三者依次为研究准入、局部准入及冲突拒绝。必须将证据与原图指纹和句柄复核，JSON 一致性检查无法证明第三方数据的真实性。
