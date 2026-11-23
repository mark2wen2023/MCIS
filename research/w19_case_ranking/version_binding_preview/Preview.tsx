import {KnowledgeSourceBody} from '../../../web/src/knowledge/KnowledgeSourceBody'
import fixed from '../version_binding/results.json'
import fixture from '../version_binding/fixture.json'

const labels=['当前合成字节定位一致（不代表支持）','旧版本拒绝：不可作为当前出处','缺少绑定：无法核对出处']

/** Only the pinned developer control is supported, not an arbitrary receipt parser. */
export function VersionBindingPreview({receipt}:{receipt:unknown}){
 if(receipt===undefined||receipt===null)return <section aria-label="W19 合成来源核对"><p role="status">未配置合成回执，未展示来源；未保存。</p></section>
 let matches=false
 try{matches=JSON.stringify(receipt)===JSON.stringify(fixed)}catch{/* malformed input stays rejected */}
 if(!matches)return <section aria-label="W19 合成来源核对"><p role="alert">回执不是固定合成控制，整份拒绝展示；未保存。</p></section>
 return <section aria-label="W19 合成来源核对"><h2>合成来源核对 · 开发只读预览</h2><p>未运行检索或模型。不代表推荐、事实或责任认定；没有认证、审批或保存入口。</p>
 {fixed.receipts.map((r,i)=>{const c=fixture.cards[i].content;return <article key={r.cardId} aria-label={r.cardId}>
 <h3>{labels[i]}</h3><p>支持未评估 · 因果未评估 · 待人工复核 · 未认证 · 未保存</p>
 <p>定位状态：<code>{r.traceability}</code></p>
 <p>宿主合成选择：{fixed.hostSelection.version} · {fixed.hostSelection.recordId} · <code>{fixed.hostSelection.sha256}</code></p>
 {r.binding?<p>来件声明（不是认证）：{r.binding.version} · {r.binding.recordId} · <code>{r.binding.sha256}</code></p>:<p>来件没有版本绑定；下方仅为卡内声明。</p>}
 <KnowledgeSourceBody body={c.body} applicability="仅供开发者核对固定合成来源状态，不用于正式调查。"
 source={{type:'Synthetic',title:c.title,locator:c.source.locator,excerpt:c.source.excerpt,rightsNote:'开发者手造合成文本；非真实事故。'}}
 notice="上方定位状态仅针对固定合成控制；摘录不构成语义支持或因果结论。定位为纯文本，不提供来源跳转。"/>
 </article>})}</section>
}
