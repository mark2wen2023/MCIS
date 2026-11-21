# ECFC 关联原始位置：离线展示适配研究

基线 d3fd9542249f214a5aa3776d7c0b8c7609ad81a7。只新增研究文件，未挂 UI、路由、保存、报告或 Seek。

`display.py` 消费经 ECFC `parseEnvelope` 验证的对象、可信本地工装显式关联、当前案件时基、真实精确查询帧和原字节。显示标签固定为 **原始位置记录，非事件发生证据**；保留 Draft/ToBeVerified、isPresumptive 和手工 timeSeconds。关联不从手工时间推导；无关联、来源失效、案件/时基/修订/摘要不符只返回元数据状态，不返回旧原件定位。缺轨、无精确记录不生成点。HDG 缺失保持未知，COG 独立。

此函数不是不可信输入解析器或授权边界；只能供受控研究宿主调用。普通 JSON、同值 pin、通过解析均不能证明业务授权、真实原件、已保存 ECFC 或事件发生。内部输出包含受保护定位信息，不可作为公开 API 或读取凭证。没有生产调用方。

## 复跑

需要本地已有以下精确 Git 对象（缺失直接失败，不联网补取）：
- d3fd954 的现有原字节工装及 business.py；它继续使用 db90fdf73de7bd26ba75819f0102fc03d0789faf 的明列生产文件，并核对当前文件等价。
- dc261c6b18c88c4942c8511d5948a679cc1539d8 的 `web/src/ecfcDrafts/model.ts`，仅临时编译并执行实际 `parseEnvelope`。
- 2048c60fd6650c6f2c99a76a16be463a3895655d 的合成 A/B JSON，原样正常 preview/commit 登记，不重编码。

```bash
MCIS_ESBUILD=/absolute/existing/web/node_modules/.bin/esbuild \
  /absolute/existing/service/.venv/bin/python -I research/ecfc_associated_position/check.py
```

须已有 Node、esbuild、Python 与既有业务测试依赖；不安装、不启动服务。仅新临时目录、SQLite、合成文件，结束清理。6 项退出 0：3 项原业务检查，3 项新适配检查；子断言不累计为独立场景数量。

真实执行：生产登记 preview/commit、固定字节完整性、原件访问/策略判断、SQLite 事务、精确点投影；每次成功双船查询增加两条 Access。适配仅消费该次测试输出，不再读取或写审计。

合成替身/声明：Ctx 与案件/策略行沿原测试工装构造，非真实登录；ECFC envelope（包括 persisted、savedRole 和 digest）及关联均由工装构造并经过真实格式解析，不声称经过 ECFC 保存。`caseEpochUtc` 固定取自该工装案件配置；它是单独关联约束，不参与转换 manual timeSeconds。原点仅由固定 UTC 查询决定。

## 实测边界与下一关

正例 A T+100 /points/7 的 position.kind=recorded 仅表示合成合同质量；HDG 为 null。适配不改变 17 秒、0 或 null，也不把它们变成事件 UTC。拒绝普通错误关联、换版、不同空白重编码原字节；长缺口和 B 无精确记录不返回点。测试没有真实浏览器/三维弹卡、HTTP、身份提供者、生产权限或 ECFC 持久化。

第一产品阻塞：ECFC 当前仅登记元数据关联，没有经授权建立/读取“节点—固定原件—精确UTC/指针—案件时基”的生产映射。后续需单独批准其来源与访问生命周期，才能将此展示接入真实页面；不得直接把本工装关联或帧作为长期授权缓存。
