# 登记 UTF-8 原件 → 未保存草稿：本地合成串验

父：`194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0`。仅测试，不挂产品，不授予身份/权限。

```sh
/path/to/existing-service-venv/bin/python -I -B tests_acceptance/registered-utf8-draft/check.py
```

需已有 SQLAlchemy、FastAPI、jsonschema 依赖及本地完整 Git 对象；不安装/联网。
入口先设置 `GIT_NO_LAZY_FETCH=1`，通过固定 commit 的普通 blob 白名单物化源码并校验 Git blob SHA：

- 登记、权限、容器保护、原件完整性、事务及审计：`db90fdf73de7bd26ba75819f0102fc03d0789faf`。
- 现有合成临时业务表/来源白名单工装：`c7f933d9d5a3fea6c4f3d706fe1f091475c3eb24` 的 `tests_acceptance/registered-trajectory-pair/business.py`。只复用白名单和建库/上下文约定，不执行其双船测试，不读取双船文件。
- UTF-8 固定夹具、原字节定位、草稿投影：`194ee6be7a4b31c0e23b5615b5d60cd9b0667ed0`。无 PDF 页码。

真实调用 `preview_input` → `commit_input` → `_read_original_for_access`，不调用下载路由。`Document` 的 `.txt` 文件走现有不解析内容的通道，不增加 MIME 或上传种类。调用仍经过原有 authorize/load_receipt/protect_container/append_custody；没有替换授权或容器逻辑。成功事务提交后才把返回 bytes 和回执 SHA 交测试侧投影。

纯合成案件/默认策略由既有测试约定建立，调用身份是明示 `Ctx`（Investigator 正例、ExternalExpert 拒绝），不是账号登录或会话验收。没有默认角色变更。第二个空合成案只作错案读取负例。源文本为固定夹具的三行，SHA-256 `aa07189b6b376ab36cf31480afa5236409c4003581839c4860f81082f781dbd9`；包含有雾/无雾两侧和停车命令，不代表观察或事实判断。

`sourceId=synthetic-report` 是测试宿主固定别名；真实 case/evidenceId/requestDigest/sourceSha256 留在局部关联表，并与读取回执核对。该表非持久化、非用户/模型输入，不把别名当生产证据身份；投影依旧 `authorityVerified=false`。还没有产品可信来源关联。

1 项集成测试内核对：登记后 Evidence/Custody/Audit 为 1/1/1；错案404、拒绝403均不交付且计数不变；成功后1/2/2，唯一 Access 的证据ID和原字节SHA相符，两条哈希链有效；投影三节点的字节区间准确，仍 Draft/无页码/不保存/无正式因果；投影后数据库计数不变。数据库仅建立既有七张测试必需表，无报告/草稿/绑定表，退出清理临时库与原件。

未验：真实账号、浏览器/HTTP、生产授权上下文与来源关联、并发撤权、PDF/OCR、正式生成器/报告保存/导出。原始文字和标注均由合成工装提供，非抽取模型。未改生产，仅此候选，不合并/不部署。

## 读取提交后的投影拒绝（候选验证）

基线 `0cc0624a31a08f81684ac9b0ddc42971c25670da`，固定生产/投影输入不变。
原正例及错案404/角色403检查保留；新用例使用另一独立临时库，正常登记并仅成功读取一次、提交 Access 后，用同一份已读 bytes 分别验证：

- 同源别名但错误 SHA 的绑定：`ValueError: host binding changed`。
- 前两条合法、末条引文错误：`ValueError: quote_location`；调用无返回，不能取得部分草稿。

这些是授权读取之后的投影拒绝，不是权限403，也不撤销已发生的读取。两次拒绝均不重读原件；逐次比较全部七表内容与提交后的快照一致，Evidence/Custody/Audit仍为1/2/2，唯一Access的证据及SHA正确，审计/保管链有效。两个用例分别有自己的1次登记和1次Access，不能将整套测试总次数称为一次。
新增用例无报告/草稿/绑定表，无持久输出。真实账号、产品来源关联及浏览器仍未验。运行命令同上；最终预期2项通过。
