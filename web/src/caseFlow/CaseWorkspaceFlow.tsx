import { Link } from 'react-router-dom'
import { caseFlow } from './model'
import '../styles/case-workspace-flow.css'

export function CaseWorkspaceFlow({ pathname, search }: { pathname: string; search: string }) {
  const flow = caseFlow(pathname, search)
  if (!flow) return <nav className="case-workspace-flow" aria-label="案件流程导航">
    <p>案件流程导航：当前页面无明确的按案流程上下文。请从<Link to="/lobby">案件大厅</Link>选择案件。</p>
  </nav>
  const next = flow.steps[flow.stage + 1]
  return <nav className="case-workspace-flow" aria-label="案件流程导航">
    <div className="case-flow-heading">
      <strong>当前案号（URL）：<span className="case-flow-id">{flow.caseId}</span></strong>
      <span>当前阶段：{flow.steps[flow.stage].label}</span>
      <span>仅导航 · 完成状态未评估</span>
    </div>
    <ol className="case-flow-steps">
      {flow.steps.map((step, index) => <li key={step.label}>
        {step.href ? <Link to={step.href} aria-current={index === flow.stage ? 'step' : undefined}>{step.label}</Link>
          : <span>{step.label}（后续）</span>}
      </li>)}
    </ol>
    {flow.steps[flow.stage].label === '取证' && <aside aria-label="图音工作流接入范围">
      <strong>图音核对尚未接入本工作台</strong>
      <p>当前证据页支持已有文件副本登记；登记文件副本不等于导入识别结果或保存核对修订。本工作台尚无图音结果导入、逐项核对及按运行重开的入口。</p>
      <p>查看已登记原件：返回本案“取证”页，选择对应证据，再使用“查看登记原件”；仍受身份、案件策略及原件完整性检查限制。这不是重开图音核对运行，也不表示已保存核对或完成报告引用。</p>
    </aside>}
    <p>{next?.href ? <>建议前往：<Link to={next.href}>{next.label}</Link>（可选）。</>
      : <>后续：沉淀需另行核对与人工处理，不自动入库。</>} 可随时返回前面阶段补证；链接不代表访问授权。</p>
  </nav>
}
