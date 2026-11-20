# 同源试用工作台 → 受限图片核对页（源码接线，未运行）

基线 825ef7e3c3580c241488ba5ae9e3393648036474。
仅 create_local_review_pilot 显式 image_imports=True 时，同时装配原图片API和：
GET /pilot/image-review；GET /image-review-lab/preview.js。
最终白名单从8条增为10条；关闭图片能力仍是原3条，没有图片页。
纯服务器页面整形使用固定标记，缺失即拒绝；URL/客户端头不决定能力。
正常图片模板中能力默认保持开启，试用响应关闭任务、原件、下载及定位。

工作台：服务器授权清单→明确选案→详情身份核对通过后才创建
`/pilot/image-review?case=<当前确认案号>` 链接。无案/加载/失败无链接，
切案同步移除旧链接，迟到响应不能补回。案号只是输入，不是授权；仍需逐请求会话和操作许可。
图片页复用原 case-only 零请求预填、显式列表/选择、四回执导入、人工修订、冲突/未知保护、
replaceState 当前运行刷新重开。没有报告历史版本含义。

受限页隐藏且 inert 原图区，隐藏/禁用逐行定位，禁建下载按钮、不绑定原图加载事件；
readOriginal 首句再次拒绝，不能通过保留的内部函数误发下载请求。
任务控件沿用原服务器整形关闭，任务函数不绑定。
预览脚本仅为原页面创建/清理所需的本地代码，没有自动请求；无原图字节或解码。
受限页明确“未看过原件、不代表真实性”；请求显式 credentials:same-origin 和 redirect:error，
没有角色头、Cookie读取/写入、凭据、自动登记或模拟填充。

所有权限/历史/审计/回执/冲突/任务来源拒绝代码保持上一提交，未新增权限或下载接口。
返回工作台是普通链接，沿用图片页 beforeunload 未保存草稿提醒；真实浏览器提醒仍待验。
页面壳不含案件内容，业务接口独立授权；有入口不代表调用成功，更不代表已对外启用。

## 复跑

```
python -I tests_acceptance/pilot-pages/check.py
node tests_acceptance/pilot-workbench/check.cjs
python -I tests_acceptance/pilot-factory/check.py
python -I tests_acceptance/pilot-image-imports/check.py
```

需要已有离线 Python/Node 和本地 Git 对象 825ef7e；不联网获取、不安装。
首条仅提取纯页面函数AST，真实挂载函数去imports后给手写Path/响应/路由替身，
生成HTML存自动清理临时目录；执行生产json包装与内存fetch，覆盖入站零请求、
列表、导入→修订→地址重开、切案迟到、无效入参，以及不可用操作无请求。
随后从固定Git对象取既有image-reopen-address测试，受限页和普通页分别22项通过；
这两轮是同一用例对照，不能相加声称44个独立功能。
工作台10组、工厂5组、图片API7组分别通过，最终退出0。
首次精简子进程PATH找不到Node，改用shutil.which解析的现有绝对Node路径后复跑通过；
没有下载或安装。子进程仅提供所需测试源路径环境，不复制凭据环境。

AST/手写DOM/Promise不证明FastAPI挂载、真实Cookie/TLS、浏览器视觉/键盘、权限、ORM或持久化。
未运行服务、HTTP、浏览器、4A、模型、播放器、DB/ORM，没有读取真实资料、seed或凭据。

## 下一门槛

仍缺经批准准备的合成案件、四份原件及合法登记回执；禁止直接造数据库行。
工厂尚无登记preview/commit、音频与下载；先核实可信回执准备及新临时库/文件根，
在无业务挂载、无外网业务访问的隔离环境获得运行批准后，才验同源身份、首次导入、
保存冲突草稿、刷新重开及切案。现阶段不宣称链路跑通，不解除之前暂停。
