# 工作台与 #99/#100/#101：限定 Web 增量整合

父头 a8ff69efce06fa869d8893823b8f211d6a96d97b（七阶段、明确选案与全局侧栏保护）；供体功能头 242b814bc44ba1c27d1226f9ee673abbb4a25a47；供体远端文档头78516e800bd00a94fddf4ecd796f46699dde3618；核对main为94d5e38c926fda232bb987b60fa9145e4bcf01a7。本次不是全分支合并，不引入供体后端或共享契约改动。

相对main，供体九个Web增量路径中的六个 #99/#101 文件已与父头逐字节一致（InterviewView、SourceDisclosure、OriginGuidance、EnvironmentPage及两项来源SSR）；没有重复引入。仅取供体以下三文件，逐字节与固定供体核对：

- web/src/caseMetadata/GapSummary.tsx（新增）
- web/src/pages/CaseInfoPage.tsx（只增加import和已保存快照区块）
- web/tests/case-metadata-gaps.test.tsx（新增）

其余父头Web文件不变；Layout、ReportPage、caseContext与七阶段导航保留，无产品冲突。提示仅检查已保存五项文字字段，不代表现实资料不存在、资料完整或已经核实；草稿不计入。严格parseSnapshot仍先拒绝非法快照，helper的invalid分支不代表正常页面必然可达。

## 本轮开发侧实跑

复用现有固定离线node_modules，未联网安装。Node24.22.1、TS7.0.2、Vite8.3.8、esbuild0.28.2、React/ReactDOM19.3.1。仅检出Web源码和必要report.schema.json；首次tsc因稀疏检出遗漏该既有schema而失败，补出父头原文件后两份TS项目与Vite成功，契约未修改。

在web目录运行以下8脚本，均通过：

```bash
node tests/run-case-workspace-flow.cjs
node tests/report-explicit-case.test.cjs
node tests/report-action-single-flight.test.cjs
node tests/interview-source-lifecycle.cjs
node tests/interview-parent-source-lifecycle.cjs
node tests/environment-explicit-origin.cjs
node tests/environment-pending-input.cjs
node tests/environment-input-generation.cjs
```

以下4个现有TSX脚本均以esbuild bundle/platform=node/format=esm/jsx=automatic/packages=external、CSS empty、fetch抛错的banner编译到临时.mjs执行，最后删除临时文件：case-metadata-gaps、case-metadata-w84、interview-source-disclosure、environment-origin-guidance。复现：

```bash
node --input-type=module - <<'JS'
import {buildSync} from 'esbuild';
import {spawnSync} from 'node:child_process';
import {unlinkSync} from 'node:fs';
for(const name of ['case-metadata-gaps','case-metadata-w84','interview-source-disclosure','environment-origin-guidance']) {
 const file=`tests/.tmp-workbench-${name}.mjs`;
 try {
  buildSync({entryPoints:[`tests/${name}.test.tsx`],bundle:true,platform:'node',format:'esm',jsx:'automatic',packages:'external',loader:{'.css':'empty'},outfile:file,banner:{js:"globalThis.fetch=()=>{throw Error('network forbidden')};"},logLevel:'warning'});
  const r=spawnSync(process.execPath,[file],{stdio:'inherit'});
  if(r.status!==0) throw Error(name+' failed '+r.status);
 } finally {try{unlinkSync(file)}catch{}}
}
JS
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

12项限定脚本通过，不累计历史断言。Vite774模块；原>1500kB警告保留，JS约1874.70kB（gzip606.16kB）。没有把警告隐藏或为此扩功能。

## 范围

实际组件SSR、受控hooks/Promise及纯逻辑，不等于真实React并发、浏览器点击/视觉/键盘或端到端。显式/无效案号的“无读取”是内存替身调用断言，不是HTTP/授权证明。无服务/后端/DB/权限实测、模型、种子或真实资料；未运行全量或暂停测试。新依赖安装、完整CI、生产身份、图音保存重开均未验。没有新增图音占位动作；下一轮需独立评估真实可用性，不得将此候选称为已跑通业务链。仅待独立审查候选，不合并部署。
