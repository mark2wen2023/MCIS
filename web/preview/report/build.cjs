// Offline static rendering of the actual ReportView. No app/router/API imports.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict')
const React=require('react'),{renderToStaticMarkup}=require('react-dom/server'),{buildSync}=require('esbuild')
process.chdir(path.resolve(__dirname,'../..'))
globalThis.fetch=()=>{throw Error('No network in preview build')}
const output=process.argv[2]
if(!output||!path.isAbsolute(output)||fs.existsSync(output))throw Error('Supply a new absolute output directory')
const build=buildSync({absWorkingDir:process.cwd(),entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['react','react/jsx-runtime'],write:false,metafile:true,define:{__MCIS_API__:JSON.stringify('OFFLINE-SYNTHETIC-NO-SERVICE')}})
const allowed=['src/reports/ReportView.tsx','src/components/Panel.tsx','src/config.ts','src/reports/types.ts']
assert.deepEqual(Object.keys(build.metafile.inputs).sort(),allowed.sort(),'Unexpected source dependency: stop')
const box={exports:{}}
vm.runInNewContext(build.outputFiles[0].text,{module:box,exports:box.exports,require:n=>{if(!['react','react/jsx-runtime'].includes(n))throw Error('Unexpected import');return require(n)}})
const css=['src/styles.css','src/styles/w16.css'].map(f=>fs.readFileSync(f,'utf8')).join('\n')
assert.ok(!/@import|url\s*\(|<\/style/i.test(css),'Unexpected external CSS resource')
const noop=()=>{throw Error('Static preview callback must not execute')}
const pages=[]
for(const [name,lang,modified,missing] of [['draft','zh',false,false],['modified','bilingual',true,false],['missing','en',false,true]]){
 const text=missing?'尚无合成内容':'手造合成文字：检查长文本、引用提示和章节排版。'.repeat(12)
 const sentence={sentenceId:'SYNTHETIC-S',textZh:text,textEn:missing?'Synthetic content unavailable.':'Handmade synthetic text for layout review. '.repeat(12),source:modified?'Investigator':'Generated',status:modified?'Modified':'Draft',missing,citations:missing?[]:[{kind:'evidence',id:'SYNTHETIC-E',needsReview:true}],generatedText:{textZh:'合成原始文字',textEn:'Synthetic original'}}
 const section={sectionId:'SYNTHETIC-SEC',titleZh:'合成章节',titleEn:'Synthetic section',source:sentence.source,generatedText:{textZh:'合成章节原文（修改前）',textEn:'Synthetic section original before edit'},status:sentence.status,missing,sentences:[sentence],dataSources:[]}
 const report={caseId:'SYNTHETIC',reportId:'SYNTHETIC-R',version:1,templateId:'imo-cic',lang,status:'Draft',realDataStatus:'fictional',sections:[section]}
 const gisis={caseId:'SYNTHETIC',isFictionalDemo:true,realDataStatus:'fictional',notice:'已提供手造合成字段快照；没有服务读取或后台载入，不表示已校验或提交 GISIS。',fields:[{
  id:'SYNTHETIC-FIELD',labelZh:'合成示例字段',labelEn:'Synthetic example field',required:false,sourceRefs:['手造内存示例，不是案件证据'],
  rules:{type:'string'},value:missing?null:'SYNTHETIC-LOADED-VALUE',missing,missingLabel:missing?'合成快照未提供该值':null,vesselId:null,mappingStatus:'pending',mappingNote:'仅展示样式，映射未核实'
 }]}
 const props={caseId:'SYNTHETIC',cases:[{caseId:'SYNTHETIC',label:'手造合成案件'}],realDataStatus:'fictional',report,reports:[report],templates:[],templateId:'imo-cic',lang,gisis,audit:[],selectedSectionId:section.sectionId,busy:false}
 for(const key of ['onSelectSection','onSwitchCase','onTemplate','onLang','onSelectReport','onCreate','onRegenerate','onReview','onExport','onGlossary','onGisisExport','onGisisValidate','onRefresh'])props[key]=noop
 let markup=renderToStaticMarkup(React.createElement(box.exports.ReportView,props))
 // Static artifact: native fieldset disables controls, citations carry no href.
 assert.ok(!/\b(?:href|src|action)=|<script|<iframe|<img/i.test(markup),'Unexpected navigable or executable content')
 assert.ok(!markup.includes('正在载入 GISIS 字段'),'Static preview must not claim loading')
 assert.ok(markup.includes('已提供手造合成字段快照')&&markup.includes('rpt-gisis-SYNTHETIC-FIELD'))
 if(missing)assert.ok(markup.includes('合成快照未提供该值')&&markup.includes(' · null'))
 else assert.ok(markup.includes('value="SYNTHETIC-LOADED-VALUE"'))
 if(modified){
  assert.ok(markup.includes('inherited-citation-notice'))
  const original=markup.match(/<details class="rpt-original">([\s\S]*?)<\/details>/)
  assert.ok(original,'Modified preview must render original text disclosure')
  assert.ok(original[1].includes('合成章节原文（修改前）')&&original[1].includes('Synthetic section original before edit'))
 }else assert.ok(!markup.includes('class="rpt-original"'))
 const html='<!doctype html><html lang="zh"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; form-action \'none\'; base-uri \'none\'"><title>合成报告只读预览</title><style>'+css+'\nbody{padding:24px}fieldset{border:0;padding:0;min-width:0}.preview-warning{padding:16px;border:3px solid orange}</style><body><header class="preview-warning"><h1>合成数据 · 只读视觉预览</h1><p>复用实际 ReportView；不是应用启动。所有业务按钮、选项和引用跳转不可操作。LIVE 是原组件标签，不表示连接服务。未生成报告、未核验原件、未保存或批准。三个文件分别展示中文草稿、双语修改、英文缺失。</p></header><fieldset disabled aria-label="不可操作的合成报告">'+markup+'</fieldset></body></html>'
 pages.push([name+'.html',html])
}
fs.mkdirSync(output)
for(const [name,html] of pages)fs.writeFileSync(path.join(output,name),html)
fs.writeFileSync(path.join(output,'build-inputs.json'),JSON.stringify(build.metafile.inputs,null,2))
console.log('Built 3 static actual-ReportView pages; dependency allowlist and no-resource checks passed. Browser not verified.')
