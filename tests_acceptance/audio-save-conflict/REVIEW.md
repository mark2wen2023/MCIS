# 音频保存版本冲突 — 开发限定检查

基线 `331a0ed885f41058e8b83dc36dd884533f3794cc`，candidate/media-demo-lazy-factory。本轮仅音频，图片仍使用原保守错误语义，未改其成功校验。

静态依据：audio_review/app.py:revise 在追加Revision前检查 expectedRevision，不符抛412/AUDIO_REVISION_STALE；_app_shell.py:http_exc 将字典detail原样作为顶层JSON。没有执行这些后端代码。

生产json()仅将数值HTTP412、对象body、精确code、非空字符串message组合标为专用错误；保存catch还要求选择代次和case/run仍属本次当前请求。符合才显示“版本已变化，本次未保存，保留草稿，请人工重新核对”，不增加unknown、不清既有unknown、不改revision/草稿/URL、不读取或重试。其它错误、可疑成功体、缺失/畸形体、解析失败、丢响应继续未知。迟到响应即使精确412也继续记录原运行未知，但不改新目标的公共status；旧行反馈及累计未知标签仍归属原记录。

实跑：

```
python tests_acceptance/audio-save-conflict/check.py
node --test tests_acceptance/audio-save-context/page.test.cjs
python tests_acceptance/media-review-capability/check.py
```

新17个场景分别在完整/限定HTML通过；真正执行生产json()、合成fetch的status/ok/json()，不替换json函数。全部是内存对象，没有真实HTTP、权限拒绝或数据库故障测试。包括精确组合/已有未知、错误code/状态、缺message/null/array、字符串状态、可疑200、丢响应、解析失败、切案/切运行/切走返回后迟到、等待中修改草稿。4个相邻保存上下文检查通过；其中旧“迟到错误覆盖status”断言按本次要求改为保持新目标提示并核对累计原记录unknown，原草稿/修订断言保留。既有能力、限定重开及地址回归通过。首次相邻运行因稀疏检出缺少检查脚本未执行，补齐明确受管路径后成功。

反例：固定基线review.html保存为/tmp/audio-conflict-baseline.html后：

```
AUDIO_PAGE_SOURCE=/tmp/audio-conflict-baseline.html node --test --test-name-pattern='exact current 412.*false' tests_acceptance/audio-save-conflict/page.test.cjs
```

实际预期失败：旧头unknown计数1而非0；候选通过。未声称多用户一致性或持久回执能力。无浏览器/服务/HTTP/DB/ORM/权限/模型/原始资料验收，启动暂停不解除，无合并部署。
