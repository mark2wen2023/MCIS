import type { EvidenceItem } from '../types'

/** Describes only the known file-registration step, never downstream analysis. */
export function OpaqueUploadStatus({caseId,evidence}:{caseId:string;evidence?:EvidenceItem}){
 if(!evidence||evidence.caseId!==caseId||typeof evidence.relativePath!=='string'||!/^raw\/evidence-intakes\/[a-f0-9]{64}\/source\.bin(?![\s\S])/.test(evidence.relativePath))return null
 return <aside className="p6-note" aria-label="文件登记与内容解析状态">
  <strong>文件副本登记步骤 · {evidence.evidenceId}</strong>
  <p>人工声明类别：{typeof evidence.category==='string'&&evidence.category?evidence.category:'未提供'}。实际文件类型未验证；文件名、扩展名或浏览器 MIME 不能证明文件类型或安全性。</p>
  <p>按登记路径显示流程说明；保存结果请核对登记回执。本登记步骤仅保存文件副本，未执行 OCR、语音转写、视觉识别或音视频解析。文件不在此处打开或执行。</p>
  <p>哈希校验状态与内容解析分开：字节一致不等于理解内容、真实性认证或事实确认。其他步骤是否另有分析，请查看其独立结果。</p>
 </aside>
}
