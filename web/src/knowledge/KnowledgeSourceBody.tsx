import type {Content} from './model'

/** Presentation only: no card lifecycle, identity, requests or callbacks. */
export function KnowledgeSourceBody({body,applicability,source,notice='来源链接和摘录需人工确认，系统没有抓取或比对原文。'}:
 Pick<Content,'body'|'applicability'|'source'> & {notice?:string}){
 return <><p className="w19-text">{body}</p><h4>适用范围与限制</h4><p>{applicability}</p><h4>原始来源</h4><p>{source.title} · {source.locator}</p>{source.url&&<a href={source.url} target="_blank" rel="noopener noreferrer">打开人工登记的公开来源（未自动核验）</a>}<blockquote>{source.excerpt}</blockquote><p>使用权说明：{source.rightsNote}</p><p>{notice}</p></>
}
