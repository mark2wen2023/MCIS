import { createRoot } from 'react-dom/client'
import { AcciMapDraftDiagram, type SyntheticAcciMapDraft } from '../../web/src/accimapPreview/Diagram'
import { downloadAcciMapSvg } from './svgExport'

const LONG = '这是必须完整保留且不能只显示十个汉字的合成节点说明'
const draft: SyntheticAcciMapDraft = {
  caseId: 'SYN-ACCIMAP-SKETCH-1',
  isFictionalDemo: true,
  nodes: [
    { id: 'SYN-GOV-LONG-IDENTIFIER-001', label: '政府层必须完整保留的合成长名称甲', level: 'Government' },
    { id: 'SYN-REG-LONG-IDENTIFIER-001', label: '监管层必须完整保留的合成长名称乙', level: 'Regulatory' },
    { id: 'SYN-CO-LONG-IDENTIFIER-001', label: LONG, level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-002', label: '公司层合成节点丙必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-003', label: '公司层合成节点丁必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-004', label: '公司层合成节点戊必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-005', label: '公司层合成节点己必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-006', label: '公司层合成节点庚必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-007', label: '公司层合成节点辛必须完整显示', level: 'Company' },
    { id: 'SYN-CO-LONG-IDENTIFIER-008', label: '公司层合成节点壬必须完整显示', level: 'Company' },
    { id: 'SYN-MGT-LONG-IDENTIFIER-001', label: '船舶管理层必须完整保留的合成长名称癸', level: 'ShipManagement' },
    { id: 'SYN-CREW-LONG-IDENTIFIER-001', label: '船员行为层必须完整保留的合成长名称子', level: 'CrewActs' },
    { id: 'SYN-EQ-LONG-IDENTIFIER-001', label: '设备与环境层必须完整保留的合成长名称丑', level: 'EquipmentEnvironment' },
  ],
  edges: [
    { fromId: 'SYN-GOV-LONG-IDENTIFIER-001', toId: 'SYN-REG-LONG-IDENTIFIER-001' },
    { fromId: 'SYN-CO-LONG-IDENTIFIER-001', toId: 'SYN-MGT-LONG-IDENTIFIER-001' },
  ],
  informationFlows: [
    { fromId: 'SYN-MGT-LONG-IDENTIFIER-001', toId: 'SYN-CREW-LONG-IDENTIFIER-001' },
  ],
}

function downloadRenderedSketch(): void {
  const svg = document.querySelector('svg[role="img"]')
  if (!(svg instanceof SVGSVGElement)) throw new Error('missing rendered AcciMap sketch SVG')
  downloadAcciMapSvg(svg)
}

createRoot(document.getElementById('root')!).render(
  <main>
    <h1>AcciMap 合成草图本地 SVG 导出验收</h1>
    <p>仅合成测试页、现有六层草图组件与独立导出模块；未改预览接口，未接产品主入口、病例读取、身份或契约，不是完整 W15，也不重跑已过核心。</p>
    <p>
      <button type="button" onClick={downloadRenderedSketch}>下载 SVG</button>
    </p>
    <AcciMapDraftDiagram caseId={draft.caseId} draft={draft} />
  </main>,
)
