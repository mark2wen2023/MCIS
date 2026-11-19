# 图音导入请求摘要指引（待独验）

基线 `79614d26ae36837006b40371261c51b967037e81`。仅两份 HTML 导入区文字及 aria-describedby；全部可执行 JS 与基线逐字一致，原归档确认文字未变。

图片逐份标出 PDF、页图 PNG、原始 OCR 输出 JSON、候选 JSON；音频标出原音 WAV、机器草稿 JSON。要求从同案“已核对登记回执”复制 requestDigest，不用 sourceSha256 或尚未确认预览；不按64位格式猜测含义。

源码依据：web/src/evidenceIntake/EvidenceIntakePanel.tsx 的预览和回执均显示原件 SHA-256/请求摘要；image_review/app.py receipts 与 audio_review/app.py receipt/source 使用登记摘要读取。仅静态阅读，无应用导入。

## 开发方离线实跑

```sh
python tests_acceptance/media-receipt-guidance/check.py
python tests_acceptance/media-review-capability/check.py
python tests_acceptance/image-save-conflict/check.py
python tests_acceptance/audio-save-conflict/check.py
```

新检查：标准库 HTMLParser 验实际标签与说明关联；两页 JS 整段字节相同保证请求构造/校验未改。对完整/限定两页共四种模式执行生产内联 JS 和实际 json/fetch 包装，人工64位值对应原请求体各字段；合成409普通失败不接纳 state/run、不改地址、不重试且保留输入。不是后端没创建的证明，不是权限测试。

相邻：能力 AST/假挂载与四模式检查；限定图片 URL9/重开地址21、音频 URL7/重开地址19；图片冲突完整/限定各20、音频各17通过。重复模式不可累计为全量覆盖。

未运行浏览器、真实 HTTP、服务、DB/ORM、权限、模型或暂停测试；未读取真实材料、seed或凭据。无新API/剪贴板/自动导入/身份或跨案传递。工作台登记回执到合成导入的真实联调仍待后续；本改动不解除启动暂停。
