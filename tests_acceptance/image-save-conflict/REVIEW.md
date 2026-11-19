# 图片保存版本冲突反馈（待独验）

基线：`4e1e1a9cec2815f8662fbe7d6d11e7c3138bff5d`。

只修改图片内联前端：当前请求的数值 HTTP 412、顶层 OCR_REVISION、非空字符串 message 才明确本次未保存。其余不完整或可疑响应保守记未知；迟到响应不覆盖新目标提示。保留输入、版本、地址与累计未知，不重试或重读。既有成功校验及更新块经字节对照未改。

源码依据：image_review/app.py 的 review 在 append 前返回该错误；_app_shell.py 将 HTTPException.detail 作为顶层 JSON。未执行这些后端代码。

## 本轮开发方实跑

```sh
python tests_acceptance/image-save-conflict/check.py
node --test tests_acceptance/image-save-context/page.test.cjs
node --test tests_acceptance/image-reopen-address/page.test.cjs
python tests_acceptance/media-review-capability/check.py
```

- 新脚本对完整/限定 HTML 各20场景通过。实际生产 json/fetch 包装，全部响应由受控内存 Promise 提供；覆盖精确冲突、旧未知、错配/畸形/丢失响应、切案/运行/切回迟到、等待中编辑与正常成功。
- 相邻保存上下文4、完整图片地址21场景通过；能力脚本 AST/假挂载及四种页面模式通过，并运行限定图片 URL9/地址21、限定音频 URL7/地址19。不同模式重复不算独立全量覆盖。
- 修改前直接运行新测试 `node --test --test-name-pattern='exact current 412.*false' tests_acceptance/image-save-conflict/page.test.cjs`，失败为未知计数1而预期0，证明旧头反例。
- 既有迟到保存测试保留原草稿/版本/请求次数断言，提示断言改为不覆盖新目标并核对原记录未知提醒。

未运行真实浏览器、HTTP、服务、DB/ORM、权限、模型或暂停测试；无真实资料/种子读取。替身不是端到端或授权验收。未改变后端、原件保护、API或成功接受策略；不表示已具备安全启动环境。
