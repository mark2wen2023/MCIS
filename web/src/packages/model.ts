export interface PackageCheck {
  isValid: boolean
  tamperedFiles: string[]
  missingFiles: string[]
  extraFiles: string[]
  caseId?: string | null
  packageFormat?: string | null
  createdAtUtc?: string | null
  generatorVersion?: string | null
}
export const MAX_PACKAGE_BYTES = 100 * 1024 * 1024
export function packageFileError(file: Pick<File, 'size' | 'name'>): string | null {
  if (!/\.mcase$/i.test(file.name)) return '请选择 .mcase 案件包。'
  if (file.size === 0) return '案件包为空，请重新选择。'
  if (file.size > MAX_PACKAGE_BYTES) return '本界面仅支持不超过 100 MiB 的案件包。'
  return null
}
export function parsePackageCheck(value: unknown): PackageCheck {
  if (!value || typeof value !== 'object') throw new Error('预检响应格式无效')
  const v = value as Record<string, unknown>
  if (typeof v.isValid !== 'boolean') throw new Error('预检响应格式无效')
  for (const key of ['tamperedFiles', 'missingFiles', 'extraFiles']) {
    if (!Array.isArray(v[key]) || !(v[key] as unknown[]).every(p => typeof p === 'string')) throw new Error('预检响应格式无效')
  }
  for (const key of ['caseId', 'packageFormat', 'createdAtUtc', 'generatorVersion']) {
    if (v[key] != null && typeof v[key] !== 'string') throw new Error('预检响应格式无效')
  }
  if (v.isValid !== ((v.tamperedFiles as string[]).length === 0 && (v.missingFiles as string[]).length === 0)) throw new Error('预检响应判定不一致')
  return v as unknown as PackageCheck
}
export const canUsePackages = (role: string) => role === 'Investigator' || role === 'LeadInvestigator'
export function packageFilename(caseId: string): string {
  return (caseId.replace(/[<>:"/\\|?*\u0000-\u001f\u007f]/g, '_').replace(/[. ]+$/g, '').slice(0, 150) || 'case') + '.mcase'
}
