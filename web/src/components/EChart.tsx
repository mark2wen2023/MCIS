import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

/** 最小 ECharts 包装：option 变化时 setOption，容器尺寸变化时 resize。 */
export function EChart({ option, height, onClick }: { option: echarts.EChartsOption; height: number; onClick?: (p: echarts.ECElementEvent) => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const chart = useRef<echarts.ECharts | null>(null)
  useEffect(() => {
    if (!ref.current) return
    const c = echarts.init(ref.current, undefined, { renderer: 'canvas' })
    chart.current = c
    const ro = new ResizeObserver(() => c.resize())
    ro.observe(ref.current)
    return () => { ro.disconnect(); c.dispose(); chart.current = null }
  }, [])
  useEffect(() => { chart.current?.setOption(option, true) }, [option])
  useEffect(() => {
    const c = chart.current
    if (!c || !onClick) return
    c.on('click', onClick)
    return () => { c.off('click', onClick) }
  }, [onClick])
  return <div ref={ref} style={{ width: '100%', height }} />
}
