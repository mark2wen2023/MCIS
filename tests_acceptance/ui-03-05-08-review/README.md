# 03／05／08 前端组合评审候选

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`。分支 `candidate/ui-03-05-08-review`；是精确文件组合，不是将来源分支合并入主线。各来源分支保持原固定头，未被改写。

| 页面 | 固定来源 | 产品文件 |
| --- | --- | --- |
| 03 船舶尺寸 | `9ff7a0488e30fad050d21bafc2bdc7d55d0043da` | ShipsPage.tsx、vessels/Dimensions.tsx |
| 05 CSV预览 | `59580d28681f2629c1cb558ff8033a0ea8922e1e` | trackInput/model.ts |
| 08 分析作用域 | `03a8e7867fedbaaabbf8dd12fc9041d6a1a74cd5` | AnalysisPage.tsx、analysis/useAnalysisSnapshot.ts |

三项均直接以固定main为父提交。非共享15个文件（5产品、4测试、3说明、3冻结）与各来源Git字节一致；REQUESTS/ROADMAP原main字节保留，随后逐字追加03、05、08各自后缀，再追加本组合记录。没有其他产品冲突。原三份冻结文件全部保留并sha256sum复验通过。

本候选只组合这三个前端增量；不纳入独立登记回放、报告存储、图音工厂、可信会话、浏览器设置或新依赖。来源提交不必是本分支祖先：这里记录的是精确文件来源。

## 本组合实际复跑

使用现有离线node_modules，无安装；在web目录运行如下命令。每个测试和构建均退出0：

```bash
node tests/vessel-dimensions.cjs
node tests/track-preview-time.cjs
node tests/analysis-snapshot.cjs
node tests/analysis-page-scope.cjs
./node_modules/.bin/esbuild tests/vessel-entry-w91.test.tsx --bundle --platform=node --format=esm --packages=external --outfile=tests/.tmp-vessel-entry-w91.mjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-vessel-entry-w91.mjs
./node_modules/.bin/esbuild tests/track-input-w102.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-combined-track-input.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node /tmp/mcis-combined-track-input.cjs
./node_modules/.bin/esbuild tests/track-inspection-w101.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-combined-track-inspection.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node /tmp/mcis-combined-track-inspection.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

前四项包含固定旧头反例和新组件／解析／受控生命周期检查；原W9.1 84项、W10.2 45项、W10.1 117项在本组合重新运行，数字不与历史累计。Vite8.3.8构建768模块，保留既有>1500kB警告。SSR和手写hooks/内存fetch替身不是浏览器或端到端。

未运行原W12 analysis-w12.test.tsx：其读取案例seed/历史dump，超出本轮纯合成限制。没有新增假跨页入口或以替身冒充完整选案联调。旧分析切案检查仅覆盖已实现hook的受控生命周期。

## 用户可见范围及下一关

03明确缺失/异常尺寸与未核验来源；05阻止时间矛盾的可保存预览响应；08换案/刷新停用旧分析并核对两份返回摘要。分别仍是原页面路由。

这不是可直接试用的完整系统：真实浏览器、身份/权限、HTTP、业务服务、数据库、Unity、媒体、容器均未运行；未验证跨页面真实切案。页面08仍为离线分析快照，未与登记轨迹修订实时关联；页面05没有新增修订保存。不得据此启动旧默认服务读取业务或种子资料。源码克隆不证明数据隔离。

拉取请使用交付消息中的固定提交和新worktree，不覆盖当前工作目录；本地复验需已审离线依赖。未来浏览器及业务验收另行隔离授权；不合并或部署。
