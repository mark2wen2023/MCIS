# 合成报告来源隔离：供审核草案，尚不可执行

基线 `3fed64892327c59902cd6b339d23b1fd2f5f2486`，产品来源为 UI+PR104
`9cc3ecee7251b6f19a739c14ce316740c048594e`。本轮只有审核材料，没有产品修改、
源码副本、数据库、应用启动、报告生成或测试。初版交付四份审核材料；本增量修订草案并增加请求驱动，
不代表批准执行。

## 已交付的具体材料

- `copy-allowlist.tsv`：170个精确源码/schema路径及当前字节SHA256。复制器逐项核对，
  不递归复制目录、不自动纳入新文件。由本基线tracked Python源码和schema路径展开；
  排除 `build_seed.py` 和 `__main__.py`。完整应用导入需要多模块，故不是最小业务依赖集。
- `prepare.py.txt`：仅准备文件的脚本草案；入口硬停止。源HEAD及各源文件digest必须匹配；
  拒绝任何路径组件软链、非普通源文件、重复成员和已存在目标。先全部核对再写新目录；
  中断不删除、不自动重试。仅调用git读HEAD，不导入MCIS。清单摘要已硬编码为
  `9e261e44cc7820724579f7f1fc0f3639b46150bc91f467d299c3022a1cd487cd`，不接受调用者替换信任根。
- 不接收外部种子路径；准备草案仅从内置审阅字典生成精确JSON字节及旁注。
  未交付任何实际种子文件或案例原文，原本本地seed.synthetic.json不再作为执行输入。
- `verify-imports.py.txt`：新进程预检草案，入口硬停止；真实load_seed直接读取并核对，
  不经吞异常的_whatif，不创建应用。导入前核对完整精确文件集合及所有文件摘要；
  拒绝额外目录、源码、字节码、缓存及软链。manifest先核路径/类型，再与内置字段和
  规范化字节逐字比较，不能用来增加允许成员。**不是已执行或证明安全的脚本。**
- `request-driver.py.txt`：实际正常请求及断言的具体草案；固定预检脚本摘要，先预检再
  导入MCIS，现因运行时锁未完成必然阻断。全部安全及结果检查使用显式need失败，不用assert。

原种子、其旁注、reports目录、samples、DB、附件、.env、模型、CLI产物、缓存、
node_modules、测试目录均不复制。源码中已存在的案例常量不是原件；包含这些源码是为了
保持原导入图，不能据此宣称完整源码没有任何公开案例字面值。

## 必须先完成的执行门槛

1. 审核170项清单及完整导入期副作用/资源需求。当前只静态核对已知主链，尚未证明
   全部间接导入不读取其它资源；缺依赖时停止，不临时扩大清单或回退原checkout。
2. 核对已固定清单/草案摘要，使用自己控制且没有并发写入者的临时父目录。脚本的路径检查
   不是对恶意并发替换路径的安全证明，也不提供OS隔离或访问拦截。
3. 明确可信依赖路径。不得安装或联网。新进程应使用已有解释器 `-I -S`，以避免
   PYTHONPATH、用户site、sitecustomize和`.pth`启动注入；随后仅显式加入经审核的第三方
   site-packages目录及副本/service。**该第三方目录清单本轮尚未固定**；不可简单恢复
   原repo路径、执行`.pth`或只用`-I`就声称完整隔离。真正执行命令必须补齐此项并另行审核。
4. 实际准备完成后，必须存在真实合成source.txt字节、seed及旁注、preparation.json；
   检查大小/摘要/唯一案件、源码清单与副本没有额外文件。不能只拿文档中的digest占位
   或声明运行生成。当前尚无这些准备产物，禁止进入请求阶段。
5. 新进程在导入前确认无mcis_service缓存；检查模块解析搜索路径优先且仅有副本包。
   导入后核对所有mcis_service模块__file__、PROJECT_ROOT、SCHEMA_DIR、load_seed默认
   参数都在副本且无软链，sources.load_seed与router.load_seed是同一个真实函数。
   事后检查不能证明导入前没有访问；需要先完成步骤1和3，不能只靠事后断言。
6. 显式临时Settings.data_dir/db_url/seed_demo=False；禁用环境回退，不覆写权限策略、
   require函数或来源适配器。现有角色头仅测试接口协议，不是生产认证。

## 精确请求与断言计划（未运行）

仅在上述门槛全部确认后创建TestClient，无监听端口。使用唯一案件
`CASE-SYNTHETIC-REPORT-ISOLATION`（下称C），已有允许正常路径的
`X-MCIS-Role: LeadInvestigator`、合成operator；不测试任何拒绝分支。
任何非预期响应立即终止，不换角色、不重试或放宽策略。

1. `POST /api/v1/cases`：以下纯合成schema字段；预期201，返回值逐字段相等：
   `schemaVersion=1.0.0, caseId=C, title=Synthetic isolation only, accidentType=Collision,
   caseEpochUtc=2026-01-01T00:00:00Z, incidentTimeUtc=2026-01-01T00:00:00Z,
   incidentLocation={lonDeg:0,latDeg:0,heightM:0}, displayTimeZoneOffsetMinutes=0,
   isFictionalDemo=true`。
2. `GET /api/v1/cases`：200，唯一列表项caseId=C、标题及虚构标记一致；这是大厅数据
   接口，不是大厅组件点击验证。`GET /api/v1/cases/C`与创建返回一致。
3. `POST /api/v1/cases/C/evidence`：
   `title=Synthetic evidence only, source=Constructed regression fixture,
   extractedBy=Synthetic collector, extractedUtc=2026-01-01T00:00:00Z,
   category=Other, confidentiality=Normal, fileName=source.txt,
   contentBase64=base64(实际读取且已核对的临时source.txt), note=Not a real incident`。
   预期201，保存返回的E（不硬编码编号），caseId=C，sha256等于真实合成字节摘要，
   状态Unverified。不得调用verify/verify-all或原件权限探测。
   `GET /api/v1/cases/C/evidence`仅含E；`GET .../evidence/E`与登记返回字段一致。
   这是已有登记接口，不证明新intake面板及回执流程或原件真实性。
4. 生成前再次直接调用真实load_seed核对完整字典、唯一C和digest/旁注一致；核对
   public_text常量案件不等于C、C.isFictionalDemo=true，模板为imo-cic。
   `_whatif`吞异常，报告中的“缺数据”本身不能代替这一步成功。
5. `POST /api/v1/cases/C/reports` JSON `{"templateId":"imo-cic","lang":"bilingual"}`：
   预期201，记录R，caseId=C、status=Draft、isFictionalDemo=true、realDataStatus=fictional。
   所有章节/句子保持Draft，合同validate(report)通过。不得stub build_sections、load_seed
   或SOURCE_ADAPTERS；这才能称“合成来源下实际报告生成正常路径”。
6. 找句子`facts-evidence-E`与`appendix-evidence-E`：sourceStatus=Unverified，引用
   kind=evidence,id=E,registration=registered,sourceRef=evidence/E；解析href必须是
   `#/evidence`，query仅case=C/id=E。不把registered当已核实，不声称固定历史版本。
   标题/来源包含合成值；whatif章节为缺数据，不出现合成推理数字或公开原文句。
7. `GET /api/v1/cases/C/reports/R`：200，与POST返回完整对象相等。
   从实际引用解析C/E，再正常GET该证据；返回仍为同一登记项。这是API层回溯，
   不是浏览器跳转、选中、PDF跳页、引文真实性或历史原件核验。
8. `GET .../reports/R/audit`：200，包含该R的report.generate事件及关联快照；
   返回列表应有且仅有一项：entry.reportId=R，entry.beforeValue=null，
   entry.afterValue与生成/GET报告完整相等，entry.snapshotRef以report-snapshot:开头；
   entry.auditEvent.action=report.generate、caseId=C、entityId=R。
   依据reports/service.py:125及229–239。不进行篡改、故障注入、恢复、拒写或链攻击测试。

不调用分析路由（最小种子未提供其_meta字段），不调用生成COLREG分析、HFACS、
推演引擎、LLM、导出/恢复、下载、浏览器。app初始化会注册全部ORM表/既有触发器，
含HFACS表，不能写成“未涉及任何HFACS代码导入”；业务/核心不应执行。

## 证据及限制

依据：analysis/router.py:18–46（相对模块路径、定义时默认参数、摘要与缓存）；
reports/sources.py:44–85、190–225、270–288、355–359、443（加载、引用和原文入口）；
reports/public_text.py:22–27（先检查案件/模板再读原文）；reports/router.py:28–42、74–80
（权限与真实生成调用）；main.py:49–59（显式settings及seed开关）；
common/contracts.py:14–25（副本schema目录）。

先前调查曾因rg没有限定文件类型，意外搜索并输出原种子中的公开案例内容；已如实
报告。不能声称此前全程未读取真实案例。本轮只读取源码、schema以编制清单，不读取
原种子或案例文件。所有未来步骤是待审核计划，不是已运行结果或生产安全保证。


## 独审后修订及仍未满足的执行前置

本增量只静态编辑，没有执行或编译任何草案、没有生成或测试。
新增检查并不意味着已经验证安全；主入口仍全部REVIEW HOLD。

- 已固定复制清单摘要；准备不再读取任何外部seed；精确集合包括170成员、内部合成
  seed/旁注、合成source.txt及固定字段manifest。预检不接受额外源码/目录或缓存。
- 所有原assert已改为显式失败。保持检查前后受控目录均无并发写入；不承诺TOCTOU防御。
- 请求驱动列出真实正常POST/GET、合同/引用/审计断言，不替换生成器/适配器或权限。
  每次非预期响应立即失败，错误只报路径和状态，不输出正文或自动重试。
- **运行时锁尚未完成，执行继续阻断**：只读readlink观察到现有venv解释器目标为
  `/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12`；
  pyvenv.cfg声明3.12.14。这只是开发环境记录，不是受信任来源或运行时完整性认证。
  尚未批准其二进制摘要、完整sys.version、标准库启动路径、第三方文件哈希及版本清单。
  `RUNTIME_LOCK_SHA256=None`保证在任何MCIS导入之前显式失败；不得填任意值运行。
- 待审核锁应逐文件固定依赖根（纯库和扩展库）、版本元数据与哈希；不得指向原checkout、
  editable安装，或含自动执行.pth/sitecustomize/usercustomize/egg-link。草案目前拒绝含
  缓存的依赖树，因此可能无法直接复用现有site-packages；不准为了通过而删除环境文件，
  需另审受控依赖副本方案。标准库/解释器外部验证须在启动前进行，进程内自检不能替代。
- 预定启动形式仅为`<已核验绝对解释器> -I -S -B <已核验bootstrap>`，不是当前可运行命令。
  bootstrap路径、摘要、依赖锁摘要及全部启动路径仍待固定，不能冒称已满足“固定可信命令”。
  草案在这一项不完整，应再次静态审核；此轮不安装、下载、执行或更改环境安全设置。
- 旧文档中的精确请求计划为意图；新增驱动仍须审查返回形状与所有导入副作用。
  产物只供审核，不声称浏览器、真实模型、原件、权限安全或完整报告生成验收。
