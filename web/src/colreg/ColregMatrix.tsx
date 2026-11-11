// W6.1：原型第 11 页上半部分——会遇局面/适用规则、分船责任、分船实际操纵、DCPA/TCPA 曲线，共用一条时间轴。
import { simToClock } from '../format'
import type { CaseDef, ColregBand, ColregCheck, CpaSeries, TimelineEvent, Vessel } from '../types'
import { incidentSec, maneuvers, minDcpa, responsibility } from './derive'
import { SITUATION_COLOR, situationLabel, stageLabel } from './labels'

export interface MatrixProps {
  caseDef: CaseDef
  vessels: Vessel[]
  bands: ColregBand[]
  checks: ColregCheck[]
  timeline?: TimelineEvent[]
  cpa?: CpaSeries | null
  cpaError?: string | null
  focusVesselId?: string | 'all'
  onSelectCheck?: (checkId: string) => void
}

export function ColregMatrix(props: MatrixProps) {
  const { caseDef, vessels, bands, checks, timeline = [], cpa, cpaError, focusVesselId = 'all', onSelectCheck } = props
  const t0 = bands[0]?.startTimeSec ?? 0
  const t1 = bands.length ? Math.max(...bands.map((b) => b.endTimeSec)) : 1
  const span = Math.max(1, t1 - t0)
  const pct = (t: number) => `${Math.min(100, Math.max(0, ((t - t0) / span) * 100))}%`
  const wid = (a: number, b: number) => `${Math.max(0.8, ((Math.min(b, t1) - Math.max(a, t0)) / span) * 100)}%`
  const ticks = Array.from({ length: 7 }, (_, i) => t0 + (span * i) / 6)
  const shown = focusVesselId === 'all' ? vessels : vessels.filter((v) => v.vesselId === focusVesselId)
  return (
    <div className="colreg-matrix" data-testid="colreg-matrix">
      <div className="cm-row cm-axis">
        <div className="cm-label" />
        <div className="cm-track">
          {ticks.map((t) => <span key={t} style={{ left: pct(t) }}>{simToClock(caseDef.caseEpochUtc, t, false)}</span>)}
        </div>
      </div>
      <div className="cm-row" data-testid="row-situation">
        <div className="cm-label">会遇局面 / 适用规则</div>
        <div className="cm-track">
          {bands.map((b) => (
            <div key={b.bandId} className={`cm-seg ${b.doubt ? 'doubt' : ''}`} style={{ left: pct(b.startTimeSec), width: wid(b.startTimeSec, b.endTimeSec), borderColor: SITUATION_COLOR[b.situation] }}
              title={`${situationLabel(b.situation)} · ${stageLabel(b.dangerStage || 'None')}${b.doubt ? ' · 存疑' : ''}`}>
              {situationLabel(b.situation)}{(b.applicableRules || []).length ? ` · ${(b.applicableRules || []).join('+')}` : ''}{b.doubt ? ' ?' : ''}
            </div>
          ))}
        </div>
      </div>
      {shown.map((v) => (
        <div key={`r-${v.vesselId}`} className="cm-row" data-testid={`row-resp-${v.vesselId}`}>
          <div className="cm-label" style={{ color: v.colorHex }}>{v.nameCn || v.name} 责任</div>
          <div className="cm-track">
            {bands.map((b) => (
              <div key={b.bandId} className="cm-seg resp" style={{ left: pct(b.startTimeSec), width: wid(b.startTimeSec, b.endTimeSec), borderColor: v.colorHex }}
                title={responsibility(b, v.vesselId)}>
                {responsibility(b, v.vesselId)}
              </div>
            ))}
          </div>
        </div>
      ))}
      {shown.map((v) => {
        const ms = maneuvers(v.vesselId, checks, timeline)
        return (
          <div key={`m-${v.vesselId}`} className="cm-row" data-testid={`row-act-${v.vesselId}`}>
            <div className="cm-label" style={{ color: v.colorHex }}>{v.nameCn || v.name} 实际操纵</div>
            <div className="cm-track">
              {ms.length === 0 && <span className="cm-empty">无记录的操纵</span>}
              {ms.map((m) => (
                <span key={`${m.from}-${m.ref}`} className={`cm-mark ${m.bad ? 'bad' : ''}`} style={{ left: pct(m.timeSec) }}
                  title={`${simToClock(caseDef.caseEpochUtc, m.timeSec)} ${m.label}`}
                  onClick={() => m.from === 'check' && onSelectCheck?.(m.ref)}>
                  ● {m.label}
                </span>
              ))}
            </div>
          </div>
        )
      })}
      <DcpaChart caseDef={caseDef} bands={bands} cpa={cpa} cpaError={cpaError} t0={t0} t1={t1} />
    </div>
  )
}

export function DcpaChart(props: { caseDef: CaseDef; bands: ColregBand[]; cpa?: CpaSeries | null; cpaError?: string | null; t0: number; t1: number }) {
  const { caseDef, bands, cpa, cpaError, t0, t1 } = props
  const W = 1000, H = 150, padT = 10, padB = 18
  const span = Math.max(1, t1 - t0)
  const x = (t: number) => ((t - t0) / span) * W
  const pts = (cpa?.results || []).filter((p) => p.timeSec != null && p.timeSec >= t0 && p.timeSec <= t1)
  const dMax = Math.max(1.2, ...pts.map((p) => p.dcpaNm ?? 0), cpa?.thresholds?.warningDcpaNm ?? 0)
  const tMax = 20
  const yD = (d: number) => padT + (1 - Math.min(d, dMax) / dMax) * (H - padT - padB)
  const yT = (m: number) => padT + (1 - Math.min(Math.max(m, 0), tMax) / tMax) * (H - padT - padB)
  const dLine = pts.filter((p) => p.dcpaNm != null).map((p) => `${x(p.timeSec as number).toFixed(1)},${yD(p.dcpaNm as number).toFixed(1)}`).join(' ')
  const tLine = pts.filter((p) => p.tcpaMin != null && (p.tcpaMin as number) >= 0).map((p) => `${x(p.timeSec as number).toFixed(1)},${yT(p.tcpaMin as number).toFixed(1)}`).join(' ')
  const best = minDcpa(pts)
  const hit = incidentSec(caseDef)
  const danger = cpa?.thresholds?.dangerDcpaNm
  const warn = cpa?.thresholds?.warningDcpaNm
  return (
    <div className="cm-row cm-chart" data-testid="dcpa-chart">
      <div className="cm-label">DCPA / TCPA
        <div className="cm-legend"><i className="l-dcpa" />DCPA (nm)<br /><i className="l-tcpa" />TCPA (min)</div>
      </div>
      <div className="cm-track">
        {cpaError && <div className="cm-empty" data-testid="dcpa-error">DCPA 曲线暂不可用：{cpaError}</div>}
        {!cpaError && !pts.length && <div className="cm-empty">正在载入 DCPA/TCPA 序列…</div>}
        <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" role="img" aria-label="DCPA/TCPA 曲线">
          {bands.map((b) => (
            <rect key={b.bandId} x={x(b.startTimeSec)} y={0} width={Math.max(1, x(b.endTimeSec) - x(b.startTimeSec))} height={H - padB}
              fill={SITUATION_COLOR[b.situation] || '#526987'} opacity={0.12} data-band-shade={b.bandId} />
          ))}
          {bands.slice(1).map((b) => <line key={`kb-${b.bandId}`} x1={x(b.startTimeSec)} x2={x(b.startTimeSec)} y1={0} y2={H - padB} className="cm-key" />)}
          {warn != null && <line x1={0} x2={W} y1={yD(warn)} y2={yD(warn)} className="cm-thr warn" />}
          {danger != null && <line x1={0} x2={W} y1={yD(danger)} y2={yD(danger)} className="cm-thr danger" />}
          {tLine && <polyline points={tLine} className="cm-tcpa" fill="none" />}
          {dLine && <polyline points={dLine} className="cm-dcpa" fill="none" />}
          {hit != null && hit >= t0 && hit <= t1 && (
            <g data-testid="key-collision">
              <line x1={x(hit)} x2={x(hit)} y1={0} y2={H - padB} className="cm-hit" />
              <text x={Math.min(x(hit) + 4, W - 110)} y={H - padB - 4} className="cm-txt bad">碰撞 {simToClock(caseDef.caseEpochUtc, hit)}</text>
            </g>
          )}
          {best && (
            <g data-testid="key-min-dcpa">
              <circle cx={x(best.timeSec as number)} cy={yD(best.dcpaNm as number)} r={4} className="cm-min" />
              <text x={Math.min(x(best.timeSec as number) + 6, W - 170)} y={Math.max(yD(best.dcpaNm as number) - 6, 12)} className="cm-txt">
                最小 DCPA {(best.dcpaNm as number).toFixed(3)} nm @ {simToClock(caseDef.caseEpochUtc, best.timeSec as number)}
              </text>
            </g>
          )}
          <text x={4} y={12} className="cm-txt dim">{dMax.toFixed(1)} nm</text>
          {danger != null && <text x={4} y={yD(danger) - 3} className="cm-txt bad">{danger} nm</text>}
          <text x={W - 60} y={12} className="cm-txt dim">TCPA {tMax} min</text>
        </svg>
        {!caseDef.isFictionalDemo && <div className="p6-note">【推算】曲线由报告给出的航迹点线性插值后经 mcis-core cpa 计算，点稀疏处仅供参考。</div>}
      </div>
    </div>
  )
}
