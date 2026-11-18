// Synthetic SSR only: no HTTP, refusal path, model, file evidence or browser.
const assert=require('node:assert/strict'),vm=require('node:vm'),React=require('react')
const {renderToStaticMarkup}=require('react-dom/server'),{buildSync}=require('esbuild')
const code=buildSync({entryPoints:['src/reports/ReportView.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',external:['react','react/jsx-runtime'],write:false}).outputFiles[0].text
const box={exports:{}};vm.runInNewContext(code,{module:box,exports:box.exports,require})
const sentence={sentenceId:'SYNTHETIC-S',textZh:'合成修改',textEn:'Synthetic edit',source:'Investigator',sourceStatus:'PublicReportExcerpt',status:'Modified',missing:false,citations:[{kind:'evidence',id:'SYNTHETIC-E',href:'#/evidence?case=SYNTHETIC&id=SYNTHETIC-E',needsReview:true}],generatedText:{textZh:'合成原文',textEn:'Synthetic original'}}
const section={sectionId:'SYNTHETIC-SEC',titleZh:'合成章节',titleEn:'Synthetic section',source:'Investigator',status:'Modified',missing:false,generatedText:sentence.generatedText,sentences:[sentence],dataSources:[]}
const report={caseId:'SYNTHETIC',reportId:'SYNTHETIC-R',version:1,templateId:'imo-cic',status:'Draft',realDataStatus:'fictional',sections:[section]}
const original=JSON.stringify(report),noop=()=>{}
for(const lang of ['zh','en','bilingual']){
 const html=renderToStaticMarkup(React.createElement(box.exports.ReportView,{caseId:'SYNTHETIC',realDataStatus:'fictional',report,reports:[report],templates:[],templateId:'imo-cic',lang,gisis:null,audit:[],selectedSectionId:section.sectionId,busy:false,onSelectSection:noop,onSwitchCase:noop,onTemplate:noop,onLang:noop,onSelectReport:noop,onCreate:noop,onRegenerate:noop,onReview:noop,onExport:noop,onGlossary:noop,onGisisExport:noop,onGisisValidate:noop}))
 const visible=html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g,'')
 assert.ok(visible.includes('inherited-citation-notice'))
 assert.equal(visible.includes('不自动证明修改文字'),lang!=='en')
 assert.equal(visible.includes('References are inherited'),lang!=='zh')
 assert.ok(visible.includes('SYNTHETIC-E'))
 assert.equal(JSON.stringify(report),original)
}
console.log('Combined report inherited citation: 3 synthetic SSR cases / 15 assertions passed')
