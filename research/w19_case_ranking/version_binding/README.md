# W19：同名旧版本与缺绑定（纯合成研究）

本目录是独立开发可见控制，不补写旧 27 卡证据，不读取盲评答案。
仅检查字节、版本选择、定位；不运行排名，不改标签、阈值或分母，
不宣称改善 5/9 召回、语义支持、专业判断或模型能力。

## 复跑

Python 3 标准库，无安装、网络、模型或服务。候选 checkout 已包含父提交的校验器：

```sh
python3 -I -B research/w19_case_ranking/version_binding/check.py
cd research/w19_case_ranking/version_binding
sha256sum -c SHA256SUMS
```

无仓库导出可显式提供：
```sh
python3 -I -B check.py --verifier /path/to/pinned-check.py
```

依赖：MCIS `d1c1d378f8ec21e3cf8a01fe446df81770395a9e`
的 `research/w19_case_ranking/source_traceability/check.py`；
Git blob 必须为 `44fc5d82279db5fa3a3c748161f3122708e85668`。
执行前核对实际字节 blob；不联网自动获取，不提交依赖副本。
原 `locate` 原样加载，只将其 ROOT 指向自动清理的合成临时目录，
不调用原 main，不改其允许文件名、文本或定位规则。

## 固定输入与新增覆盖

`current.txt` / `stale.txt` 是 UTF-8、LF 结尾、TAB 分隔的真实小文件，
依次为记录 ID、标题、原文。相同 SYN-01、相同标题；只变原文里的日期/时分。
这是文本版本变化，不是校时、时序或事故事实判断。
`fixture.json` 将 v2 摘要及 SYN-01 固定为合成宿主选择；卡不能改宿主选择。
`INPUTS.sha256` 在运行前核对两个文件和夹具。

三条回执：当前记录 LOCATED；同名旧 v1 SOURCE_VERSION_MISMATCH；
缺绑定 BINDING_MISSING。均 support/causation=NOT_ASSESSED、
review=PENDING、authenticatedReview=false。回执 binding 是原来件声明，
不是认证；hostSelection 单列，仅为固定测试宿主上下文。

共 9 项断言，结果见 results.json：
1. 当前 UTF-8 记录定位成功。
2. 同标题旧版本被拒绝。
3. 缺绑定显式待审。
4. 原 locate 对当前字节＋旧摘要返回 SOURCE_HASH_MISMATCH。
5. 原 locate 对自洽旧文件可返回 LOCATED；外围版本选择仍拒绝。
6. 把旧卡版本改称 v2，旧摘要仍不获当前资格。
7. 非宿主选定记录 ID 被拒绝。
8. 当前绑定搭配旧时间引文被原 locate 拒绝。
9. 三条回执均未评估、未认证、待审。

第 5 项区别于原先“把摘要改成全零”负例：完整旧文件也可定位，
但可定位不等于当前宿主选择版本。第 3 项补充原 locate 要求绑定必有的边界。
本研究薄包装只接受这里冻结的开发控制结构，不是通用输入解析器或产品接口。

## 实跑与限制

初次显式依赖运行和干净仓库相对布局运行均退出 0，输出逐字一致，9 项通过。
未运行真实认证/版本登记/原件权限读取；宿主权威来源仍未接入。
未确认任何事实，不生成推荐理由或保存人审记录。
不触 W20、产品路由、共享契约、旧冻结控制或正式资料。
