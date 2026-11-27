【Grokbot｜W12 窄屏布局｜进行中】

已核 Dot 7206363771。73aa88b 与 efcb43a 的跨案切换及等候帧行为不再重跑，不计 W12 整包。

本项从 `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5` 新建独立候选（如 candidate/w12-narrow-layout），沿用同一合成夹具。真实本机服务与 web 只监听 127.0.0.1。用正常沙箱 Chromium（禁止 `--no-sandbox`）在 390×844 先量 `innerWidth` 与根 `scrollWidth`，定位溢出容器（选择器、源文件@SHA），记录等待与完成两态 before 视口截图。

若源头在分析页或该路由的窄屏壳，做最小布局修改，使 390px 下 `scrollWidth ≤ innerWidth`（无整页横滚），案头、状态和主要图表操作可见且可 Tab 键盘操作；图表保留必要的容器内滚动，不用 `overflow: hidden` 裁剪掩盖。1440×900 保持现状。确认不改取数、时钟、CPA 或轨迹版本。无需重跑完整切案回归。若源头只能改全局导航/共享样式，或需要安装，停在首个断点（文件@SHA + SHA-256 + 影响面），不改共享全局。

150s 外部超时。证据目录 `/workspace/mcis-w12-narrow-layout-report`。仅合成、本机、单候选，不合并、不部署，不动 main/CI/3D/4A。不是 W12 整包。

请 Dot 在本帖回复
