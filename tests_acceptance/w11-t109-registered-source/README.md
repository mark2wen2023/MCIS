# W11 T+109 原件登记与定位：隔离合成候选

纯合成，非生产接口；不保存报告/草稿，不启动HTTP/浏览器/模型，不修改生产源码。
把本目录复制到任意位置，已有兼容Python 3.12/SQLAlchemy/FastAPI/jsonschema环境下运行：

```sh
/path/to/existing/venv/bin/python -I -B /path/to/package/check.py --repo /path/to/existing/MCIS
```

不要使用-O。repo可以是任意检出，必须已预置以下完整固定Git对象和文件，不fetch、不安装；入口先设GIT_NO_LAZY_FETCH=1：
- db90fdf73de7bd26ba75819f0102fc03d0789faf：真实生产白名单源码/schema。
- c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24：business.py的PATHS（排除其测试数据），不执行原双船工装。
- 194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0：已有纯locate定位器。
- 2048c60fd6650c6f2c99a76a16be463a3895655d：原样A/B，仅读取静态核对，不转换、不重新登记。
本新脚本从已核0cc0624a31a08f81684ac9b0ddc42971c25670da的测试模式局部改写，没有新增生产逻辑。临时仅物化普通Git blob并核SHA；运行后检查实际mcis_service模块路径。此后置检查不是系统隔离证明。

communication.txt为固定手造UTF-8/LF字节，SHA418be9609b46a00062c41fb49073911986098e9a61e010f4311aa86946ecd3ea。脚本硬编码核验，不接受工具/模型宣称来源。现有Document通道preview_input/commit_input正式登记，原_read_original_for_access完整保留权限/完整性/容器/Access守门。

新库固定回执预期caseId SYN-XREPO-001，evidenceId EV-001，requestDigest 3614bb7f78bc8f89a2434a6b5c5ddde2215fd6371cf6222adcc9beda6aade6df；该ID只在独立空测试库成立，不是生产全局ID。回执由正式处理器生成后断言，不直接插入回执。案件和默认策略沿原测试工装构造；Ctx显式Investigator/ExternalExpert是合成调用身份，不是真实登录。

同案实际读取在事务内核对测试宿主固定pin，事务成功退出才交付bytes。错案404、ExternalExpert403不交付不新增Access。错evidenceId/错SHA调用真实helper后，测试宿主比较回执发现不符并抛ValueError，整个事务回滚；这不是生产已有精确pin API，也不是权限拒绝。两次错误pin可能已物理读取原件，但不会提交Access；不声称“从未读取”或撤权竞态闭环。正例提交唯一1条Access并核保管链/审计链。

定位仅使用成功已读bytes+回执SHA，不重读原件：段3、Unicode字符[6,30)，全源字符[49,73)，UTF-8字节[97,121)，文本2026-02-01T12:01:49.000Z。T100/T110替代引文拒绝；此后计数仍Evidence/Custody/Audit=1/2/2，无报告/绑定表。

T+100仅游标；A-t100 /points/7缺HDG，A无T109精确点。T109只是独立通联原件写下的合成时间，校时依据/人审未提供，不能推先后或事件真实性。locator.authorityVerified仍false（定位器本身不验权）。不制造坐标、不用轨迹近邻，不建立ECFC图版本/边到原件的生产关联；真正跨仓/UI/身份未验。

本包检查1项集成用例，含以上正负断言；stdout为纯合成回执摘要。临时SQLite/原件退出清理。仅发布独立测试候选，不合并、不部署。

交付父提交：`0cc0624a31a08f81684ac9b0ddc42971c25670da`。根目录复跑：

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/w11-t109-registered-source/check.py --repo .
```

脚本和communication.txt与已独审ZIP原字节一致。独立验收侧已核字节/源码，缺固定Git对象未实跑；作者实跑1项集成用例退出0。不是独立执行器复跑、真实账号或跨仓/UI验收。发布不包含ZIP、RESULT日志或临时库。
