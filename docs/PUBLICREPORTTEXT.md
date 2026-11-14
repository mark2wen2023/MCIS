# 公开事故报告待解析交接

基线 main `3aba2bf03e393909c611489ae573a887087637ac`。W4.2 保存原字节，无 OCR/文本提取任务（contracts/W4.2-evidence-intake.md）。现有证据 status 是字节核对状态，不代表正文已提取。本片只在正式文件登记回执的 Document 分类下增加状态和显式本地交接，不新增解析能力。

操作：登记文件或只读调阅已有回执 → 文本提取状态“本入口未解析” → 准备公开报告交接 → 填公开 HTTPS 来源 → 声明文件和所列字段均适合公开资料处理 → 导出 JSON。非公开材料不得用于该流程；公开性只能由操作人声明，系统无法认证。URL只作为字符串，不打开、不抓取、不上传。原存储 Restricted 不变。原件、提取人、登记人及备注不放入交接 JSON；标题/原来源等自由文本仍可能有人名，必须人工核查。

JSON profile `mcis-public-report-text-handoff-v1`：original 包含 caseId/evidenceId/requestDigest/sourceSha256/fileName/byteLength/title/sourceDeclaration/registeredUtc，绑定当前已验证结构的回执；publicMaterial 包含原样来源地址与 user-declaration-only/verified=false；extraction 固定 this-intake-entry-only/not-run/text=null/modelCalled=false；review 固定 unverified/factsConfirmed=false/authorAuthenticated=false；preservation 固定 Restricted、originalIncluded=false、originalModified=false。这是未签名本地交接记录，不是完整回执、真实性认证或可恢复备份；两个摘要引用已有登记，不额外签署文件。后续工具须重新取得原件、核对摘要并自行记录版本、页码与提取结果，本片没有导入/消费器。

失败：下载准备或点击异常仅显示失败，保留回执和交接输入；不会重复上传、删除原件或自动重试。浏览器请求下载成功也不证明磁盘保存成功。取消清空交接声明/地址，不撤销原登记。重复导出相同声明产生相同 JSON，不增服务登记。切案/身份关闭原面板，回执版本/元信息改变重置交接。其他工具是否解析过为未知，不宣称全局未解析或实际解析失败。

## 复跑

在 web 执行 npm ci；Node 24。DOM 测试需已有 happy-dom，或在仓库外单独准备并用 MCIS_HAPPY_DOM_MODULE 指向其 lib/index.js（本环境使用 /tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js）。

```
MCIS_HAPPY_DOM_MODULE=/tmp/mcis-ui-deps/node_modules/happy-dom/lib/index.js bash web/tests/run-report-text-handoff.sh
bash web/tests/run-evidence-intake-w42.sh
npm --prefix web run build
```

35 项新断言（纯模型和合成 DOM），旧 W4.2 88 项，TypeScript/Vite build。无模型、OCR或真实报告文本能力验收。正式浏览器下载和真实生产身份认证另列未验证。继承 main 文件访问/授权安全问题不在本片修复范围，本片不得因此宣称可部署。
