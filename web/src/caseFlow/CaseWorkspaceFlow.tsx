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
    <p>{next?.href ? <>建议前往：<Link to={next.href}>{next.label}</Link>（可选）。</>
      : <>后续：沉淀需另行核对与人工处理，不自动入库。</>} 可随时返回前面阶段补证；链接不代表访问授权。</p>
  </nav>
}
