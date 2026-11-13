import type {Content} from './model'

export function SuggestionSourceReview({source,checked,onChange}:{source:Content['source'];checked:boolean;onChange:(v:boolean)=>void}){
 const synthetic=source.type==='Synthetic'
 return <section aria-label="预览来源人工核查">
  <p><strong>{synthetic?'合成材料 · Synthetic':'公开来源声明 · Public'}</strong> · 未核实</p>
  <p>{synthetic?'合成示例不能作为真实事故证据。':'公开类别由录入者声明，系统未核实公开状态或使用权。'}</p>
  <dl><dt>来源标题</dt><dd>{source.title}</dd><dt>原文定位</dt><dd>{source.locator}</dd><dt>原文摘录</dt><dd className="w19-text">{source.excerpt}</dd><dt>使用权声明</dt><dd>{source.rightsNote}</dd></dl>
  <p>此预览只有一个来源；不是多来源验证、事实认定或专家意见。</p>
  <label className="w19-check"><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)}/>我已核对这次预览的来源类型、定位和摘录，同意填入草稿；这不代表批准发布</label>
 </section>
}
