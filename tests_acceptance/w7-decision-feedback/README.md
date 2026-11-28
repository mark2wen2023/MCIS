# W7 已登记回复意见 → 采纳决定与反馈 → 重开核对（真浏览器门槛）

独立验收候选，产品固定 `b2ecb50b32b721c9f171b74ecd576691c0048b94`。
本目录只新增验收工装，不改产品、权限、主线、CI 或合同。不重跑期限/回复/关闭原件（见 `7164675100`），也不把 `cbb3997` 的同页切轮回执当作本版本证据。不是 W7 整包。

启动前核对其 `ConsultationPanel.tsx`、`model.ts`、`recommendations/router.py` 的 Git blob 与本工装钉扎一致。

## 范围

用正式「安全建议与报告」页上的征求意见面板与真实本机服务（临时 SQLite、`seed_demo=False`）。经官方写入接口预先登记一案一轮、一条待处理合成意见；浏览器核验：

- 「部分采纳」不填理由（含仅空白）不能保存，且无写入
- 填入明确的合成反馈后只保存一次
- 重启服务并重开同一数据库后，仍显示原轮次、意见标识、决定与原样反馈
- 实际请求与新增审计一致（保存后仅多一条 `consultation.decide`，重开不再写入）

不发送、不签发、不扩到旧响应并发，不接真实数据、4A 或模型。

## 运行

```sh
timeout 150 env \
  MCIS_HOST_PYTHON=<existing service .venv/bin/python> \
  MCIS_CHROMIUM=/opt/google/chrome/google-chrome \
  MCIS_NODE_MODULES=<existing web/node_modules> \
  MCIS_BROWSER_EVIDENCE_DIR=<abs evidence dir> \
  MCIS_PORT=18794 \
  MCIS_WEB_PORT=18795 \
  /workspace/w17-pyplaywright-venv/bin/python tests_acceptance/w7-decision-feedback/run.py
```

服务与 Vite 只监听 127.0.0.1。Chrome 开沙箱，不使用 `--no-sandbox`。不安装依赖。HTTP-only 或 DOM 模拟不能代替本脚本的真浏览器路径。
