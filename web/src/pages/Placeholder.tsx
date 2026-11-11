import type { RouteDef } from '../routes'

export function Placeholder({ route }: { route: RouteDef }) {
  return (
    <div className="placeholder">
      <div className="num">{route.num}</div>
      <div className="page-title">{route.name} <span className="p6-tag">占位</span></div>
      <div className="p6-note">{route.desc}。本页已登记路由，尚未接入后端；界面设计见 prototype/index.html#{route.path}。</div>
    </div>
  )
}
