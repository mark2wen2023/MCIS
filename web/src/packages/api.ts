import { ApiError, getOperator, getRole } from '../api'
import { caseIdentity } from '../cases/identity'
import { canUsePackages, packageFileError, parsePackageCheck, type PackageCheck } from './model'

async function packageRequest(path: string, who: string, signal: AbortSignal, file?: File): Promise<Response> {
  if (caseIdentity() !== who || !canUsePackages(getRole())) throw new Error('身份已变化或当前身份无权限。')
  const response = await fetch('/api/v1' + path, {
    method: file ? 'POST' : 'GET', signal,
    headers: { 'X-MCIS-Role': getRole(), 'X-MCIS-Operator': encodeURIComponent(getOperator()), ...(file ? {'Content-Type':'application/zip'} : {}) },
    body: file,
  })
  if (!response.ok) {
    let code = 'HTTP_' + response.status
    try { const error = await response.json(); if (typeof error?.code === 'string') code = error.code } catch { /* no free-text server errors */ }
    throw new ApiError(response.status, code, '案件包请求失败', null)
  }
  return response
}
export async function verifyPackage(file: File, who: string, signal: AbortSignal): Promise<PackageCheck> {
  const error = packageFileError(file)
  if (error) throw new Error(error)
  const response = await packageRequest('/packages:verify', who, signal, file)
  return parsePackageCheck(await response.json())
}
export async function exportPackage(caseId: string, who: string, signal: AbortSignal): Promise<Blob> {
  const response = await packageRequest('/cases/' + encodeURIComponent(caseId) + '/export', who, signal)
  if (response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'application/zip') throw new Error('导出响应不是 ZIP，未启动下载。')
  const blob = await response.blob()
  if (!blob.size) throw new Error('导出文件为空，未启动下载。')
  return blob
}
export function packageError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409 && error.code === 'ARCHIVE_RESTORE_UNSUPPORTED') return '本案件包含当前案件包尚不支持完整恢复的笔录、已存报告或操作快照，整个案件包导出已拒绝，不会成功遗漏这些内容。重试不能解决此版本限制；请独立保管原始资料，不要绕过限制。'
    if (error.status === 409 && error.code === 'INTERVIEW_RECEIPTS_BACKUP_UNSUPPORTED') return '本案件包含人工笔录请求回执，当前版本不支持完整导出，整个案件包导出已拒绝。重试不能解决此版本限制；请独立保管原始资料，不要绕过限制。'
    if (error.status === 403) return '当前身份无权限。未自动重试，请核实身份。'
    if (error.status === 404) return '案件不存在，请刷新案件列表。'
    if (error.status === 422) return '服务拒绝案件包：格式损坏或不受支持。未导入任何案件。'
  }
  return '请求失败或响应无效，请检查服务连接后重试。未导入任何案件。'
}
