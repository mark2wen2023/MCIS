import type { ReactNode } from 'react'

export function Panel(props: { title: ReactNode; meta?: ReactNode; children: ReactNode; style?: React.CSSProperties; bodyStyle?: React.CSSProperties }) {
  return (
    <section className="panel" style={props.style}>
      <header className="panel-header">
        <div className="panel-title">{props.title}</div>
        {props.meta && <div className="panel-meta">{props.meta}</div>}
      </header>
      <div className="panel-body" style={props.bodyStyle}>{props.children}</div>
    </section>
  )
}

export function Metric(props: { label: string; value: ReactNode; unit?: string; tone?: '' | 'red' | 'green' | 'amber' | 'pur' }) {
  return (
    <div className={`p6-metric ${props.tone ?? ''}`}>
      <div className="lbl">{props.label}</div>
      <div className="val">{props.value}{props.unit && <small>{props.unit}</small>}</div>
    </div>
  )
}
