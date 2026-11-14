# 操作者归档兼容守卫独立复核

结论：限定范围通过，未发现新的阻断缺陷。

## 实测
作者 test_knowledge_actor.py 27 项、独立 test_knowledge_actor_independent.py 16 项、W19 与归档既有回归，共 **120/120 通过**（22.44 秒）。记录 independent-results.txt。

独立用例通过真实 TestClient HTTP 入口验证百分号编码头解析后检查：161 字符 ASCII/中文、CR、C1/ASCII 控制字符及全空白在 create/review 均 422，卡片/审计/归档计数不变且已有归档仍可验证；160 中文、160 emoji、含组合字符与 LF/TAB 的文本原样入档；Public 角色在 actor 校验前仍 403。作者直接函数测试另覆盖非字符串与孤代理。全部数据为合成临时数据库，无模型/网络或生产写入。

## 代码核对
对照 packet-mapping-main 中 router 副本，仅新增 validate_actor 及 create/review 写前调用，不含 source host 修复。validate_content 与历史归档验证函数未改。最大字符数与归档 string(...,160) 一致；UTF-8编码检查在写前排除孤代理，复用 strings 控制字符规则。

当前 router SHA256：434cd36bfb2a5c44511d5e2ae2ecb7870bca6b022f41a8ee18c8fbc09044ec59。
副本无 git 元数据，本报告不把父线程给定主线标识当作独立远端核验。

## 限制/精确措辞
- 160 指 Python Unicode 码点数，不是 UTF-8 字节或视觉字素；LF/TAB 按既有归档协议允许，不进行规范化或裁剪。
- common.context 依旧解码调用方头、缺失/空头回退默认操作者。因此不能把“直接函数拒绝空 actor”扩写成“HTTP 必须提供身份头”。畸形百分号字节解码行为也未在本轮变更。
- 控制字符由 strings 抛 INVALID_CONTENT；超长/空值由此守卫抛 INVALID_OPERATOR。均为 422，但并非统一错误 code。
- 这只是归档兼容性约束，不是 SSO、签名身份、真实权限或防伪身份。旧档不会修复；其他业务模块无此新增校验。
- 未推送、部署或运行远端 CI，未修改产品实现，仅新增独立测试与报告。
