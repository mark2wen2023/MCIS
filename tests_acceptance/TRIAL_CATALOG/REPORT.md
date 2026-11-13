# 受保护案件／来源清单试验：独立验收

独立审查者未修改产品，新增 `test_trial_catalog_independent.py` 25项。
最终与主测试11项合跑：36 passed，零跳过，17.05秒；一项既有Starlette/httpx弃用警告。

命令：

```sh
PYTHONPATH=protected-catalog/service mcis-work/service/.venv/bin/pytest -q \
 protected-catalog/service/tests/test_trial_catalog_independent.py \
 protected-catalog/service/tests/test_trial_catalog.py --disable-warnings
```

## 发现与修复

首批独立20/20通过。随后新增“来源响应最后materialization期间会话到期”探针，实际复现返回200和items，而不是403。问题是最终authorize_read在最后load_case读取之前。实现者调整为先构建完整response，再最终重验会话／成员授权；该失败用例保留，最终通过。

实现者另先发现不存在案件与已有无权案件状态差异并统一入口授权异常403。本独立测试实际新建另一案件，验证其无权来源读取与不存在案件均403且相同错误JSON；案件列表无该案件ID。

## 最终覆盖

- 案件当前成员和来源权限均从同库session而来，去掉保存授权仍可读取。
- 整份案件策略改为ReadOnly也可列清单，非隐含写权限。
- session撤销／主体禁用／会话到期返回403；没有成员或禁用成员案件列表为空、来源403，无案件或证据元数据。
- 来源内容政策拒绝使案件不列出、来源403；伪角色／操作人头不改变合法会话身份，仅伪头不能授权。
- 输出仅白名单字段，不含标题、原路径、操作人、token、原文；no-store。
- Cookie／Origin／非零Content-Length／Transfer-Encoding／重复Authorization拒绝。
- 恢复历史案件重新授权后来源列表为空，历史source SHA未被激活。
- 一份坏来源和“先有好来源、后坏来源”均整批409，不返回好项或部分元数据。
- 案件／来源最终materialization后到期拒绝；未知异常脱敏，无路径或token。
- 旧案件列表、证据、docs、openapi未因此挂到试验入口。

## 范围

真实临时SQLite、登记字节、ASGI TestClient验证；案件／证据准备仍用旧测试入口，主体和会话由可信host直接配置。没有生产登录、真实浏览器、网络socket、IdP、LLM、W2或全系统验收声称。清单只包含当前本地受支持候选，不是全部历史证据浏览、媒体语义验证或事实批准；源文件仍可变化、获取列表不是后续写入授权。

使用SQLite保留写事务序列化授权与构建读取结果，不代表调用业务写入。最终校验之后的撤权无法召回已获授权发送的数据。默认拒绝入口不因本切片开放；独立试验工厂之外的旧服务没有被自动认证。

最终未发现本切片范围内剩余阻断项。无推送、合并、部署。

## 最终产品SHA-256

- catalog.py: `9c284466978417cdd6204568857d6c32ca9d7f49499615f13ef000e2cd1dbb3a`
- local.py: `37737de85771acdfb06c2a482689e7b29095eeaaf8ed942cb5e6791a18f88c6d`
- http_trial.py: `92c50add55c5e76c2136143fc807a5bae5e6ed587db923adadbafe6927ecbf11`
