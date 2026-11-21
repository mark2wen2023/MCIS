# T+100：解析相同的两份JSON原件必须各自固定

独立候选以 `afc72a1180ae345556a85fb63a4020a476893d14` 为父。核对原business/business_query/reopen：已有不同正文原件和重建Database检查，未有仅改变JSON空白/键序的同内容对照。本次只新增测试，不改产品、契约、权限或旧冻结。

```sh
/workspace/mcis/service/.venv/bin/python -I tests_acceptance/registered-trajectory-pair/byte_identity.py
```

使用已有离线依赖与原工装的固定生产源码白名单 `db90fdf73de7bd26ba75819f0102fc03d0789faf`。逐文件Git字节核对、临时目录和导入来源限制不变。不安装或联网、不导入全量app/registry。本轮4项通过、退出0：原工装3项及新增1项，非4条新增产品流程。

新增检查实际调用原preview_input/commit_input、_query_registered_pair、_load_registered_pair、load_receipt、Database及审计链实现。案例/策略与Ctx沿原工装为显式合成前置，不验证登录、服务器身份或report grant；仅请求Body传输是替身。

- 原紧凑JSON与新indent/sort_keys JSON解析对象相同、字节不同；登记请求除contentBase64外元数据一致。正常独立登记，不改写任何已登记文件。
- evidenceId/requestDigest/sourceSha256不同；各sourceSha256确为各自原字节摘要。两者规范化重序列化摘要相同，因此不能用其替代原件身份。
- T+100=`2026-02-01T12:01:40.000Z`，原件`A-t100`、`/points/7`，position.kind为recorded只是合成来源质量标签，不认证观测真实。HDG仍null，COG不补艏向。
- 两份查询除original pin外全部相等。重建Database后各pin仍原样重读，不取latest；通过真实读取检查原件字节和点位。共3次Register、6次双份读取产生12次Access，custody/audit各15行，Access顺序与两个哈希链一致。
- 未来句子“A 船在此 UTC 有一条已登记的位置记录”的小型输入只在测试内存保留旧pin/UTC/pointer/质量，不保存、不发放权限、不冒充报告引用。

报告侧固定参考 `94014643c02a1dd046ee8b0bfb76ae3b36631509`：`reports/generation_snapshot.py:15–74 generation_sentence` 能从完整生成审计与唯一句复制冻结状态；既有 `tests_acceptance/report-generation-snapshot/check.py` 已使用手造RA验证两代句，不应重复造一份称为业务接通。当前 `sentence_binding.py:172–213` 只支持audio pin，且没有生产BindingReadScope。不能把本次轨迹输入变为音频run/revision/segment，也不能为取得报告句扩report grant。本轮没有执行报告解析/保存/归档/导出，未合并R。

下一项仍需经批准的轨迹引用合同与可信报告/证据授权交集、同事务调用点；本次补的是原字节身份的真实合成持久化证明，不是报告产品闭环。无服务、浏览器、容器、模型、真实资料或4A；未改main/mcis-3d。
