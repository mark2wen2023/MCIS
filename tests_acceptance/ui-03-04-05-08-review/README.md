# 03/04/05/08 前端组合评审

父提交 `b965f140a6da58c229753050e7141672d17b376e`，main基线 `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。本分支只摘取环境候选 `813f9464849e621cfc6dcf2ba6a8f5717ce43c8e` 相对main的10个Web文件；不是merge或整串cherry-pick。4个产品文件为 environment/CreateObservationPanel.tsx、OriginGuidance.tsx、model.ts、pages/EnvironmentPage.tsx；其余6个为对应测试。每份逐字等于固定来源，且与03/05/08修改路径无重叠。原三页产品、测试、说明及冻结均原样继承，来源见 ../ui-03-05-08-review/README.md。

04增加已实现的来源口径提示、显式来源选择和表单事件代次保护；没有添加真实性审核字段、推算/假设、默认数值或改变方向。未改变深蓝主题、任何权限、API或服务注册。报告权限不在本次范围。

## 复跑（已有离线依赖，不安装）

在web目录执行，临时输出位于忽略的测试目录或/tmp；每一步失败即停止。

```sh
set -e
node tests/vessel-dimensions.cjs
node tests/track-preview-time.cjs
node tests/analysis-snapshot.cjs
node tests/analysis-page-scope.cjs
node tests/environment-explicit-origin.cjs
node tests/environment-pending-input.cjs
node tests/environment-input-generation.cjs
for name in vessel-entry-w91 environment-w92 environment-origin-guidance; do
  ./node_modules/.bin/esbuild tests/$name.test.tsx --bundle --platform=node --format=esm --packages=external --outfile=tests/.tmp-$name.mjs --jsx=automatic --loader:.css=empty --log-level=warning
  node tests/.tmp-$name.mjs
  rm tests/.tmp-$name.mjs
done
for name in track-input-w102 track-inspection-w101; do
  ./node_modules/.bin/esbuild tests/$name.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/four-$name.cjs --jsx=automatic --loader:.css=empty --log-level=warning
  node /tmp/four-$name.cjs
done
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

本组合实际上述12测试入口、TS及Vite均退出0。W9.1 84、W9.2 103、W10.2 45、W10.1 117为各脚本输出，不能与过去轮次累计；环境三个受控生命周期入口分别3/4/6场景，来源提示使用真实组件SSR。Vite8.3.8共769模块，原>1500kB警告保留。模拟hook/SSR不证明真实React事件重放或浏览器。

环境6份测试之一 environment-w92.browser.cjs 仅按来源逐字保留（显式选择来源的步骤），**未运行**。原analysis-w12历史测试涉及seed/旧dump，也未运行。本次不启服务、浏览器、HTTP、DB/ORM、容器、Unity、媒体、模型或4A，不读真实数据。不是一条已实跑的跨页业务链，未知提交核查不证明服务端未写入。03/05/08各原有未验边界继续有效；没有整合登记回放/报告存储/可信试用身份。

根目录可复核：
```sh
sha256sum -c logs/ui-03-04-05-08-impl-hashes-frozen.txt
sha256sum -c logs/vessel-dimension-status-impl-hashes-frozen.txt
sha256sum -c logs/track-preview-time-consistency-impl-hashes-frozen.txt
sha256sum -c logs/analysis-snapshot-scope-impl-hashes-frozen.txt
```
本轮4份清单均通过。原环境分阶段历史冻结不冒称匹配最终组合；新清单只冻结实际摘取的10文件。源候选和main不变，不合并部署；源码克隆不能证明资料净化或许可启动。
