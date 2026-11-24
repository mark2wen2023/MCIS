import {KINDS,STATUSES,type Status} from './model'
export interface SearchContext {status:Status;kind:string;q:string;tag:string}
/** Describes applied server filters, not a second search algorithm or evidence judgment. */
export function SearchReason({context}:{context:SearchContext}){
 const hasQ=!!context.q.trim(),hasTag=!!context.tag.trim()
 return <details aria-label="本次返回原因"><summary>为什么返回这张卡</summary>
 <p>本卡来自这次已完成的服务端检索；以下是当次条件，不是相关度评分。</p>
 <dl><dt>资料状态</dt><dd>{STATUSES[context.status]}</dd><dt>类型筛选</dt><dd>{context.kind?KINDS[context.kind as keyof typeof KINDS]:'不限类型'}</dd>
 {hasQ&&<><dt>字面子串条件</dt><dd>{context.q}</dd></>}
 {hasTag&&<><dt>精确标签条件</dt><dd>{context.tag}</dd></>}</dl>
 {hasQ&&<p>字面检索范围是标题、摘要、正文、适用范围和标签；来源摘录不是单独检索字段。服务端去除首尾空白并统一大小写。</p>}
 {hasTag&&<p>标签条件是完整单标签匹配，不是语义相似度。</p>}
 {hasQ&&hasTag&&<p>字面条件与标签条件同时成立才返回，不是二者取并集。</p>}
 {!hasQ&&!hasTag&&<p>本次没有字面或标签条件，只按状态及可选类型列出；不能视为相关性推荐。</p>}
 <p>结果按登记顺序倒序分页，不按语义相似度排序。</p>
 <p>检索命中不证明原文支持卡内陈述。服务端未返回逐项证据核验结果；缺少依据、反例和不确定性仍需人工核查。</p>
 </details>
}
