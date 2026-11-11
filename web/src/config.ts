// 服务地址从构建配置读取（vite.config.ts 用 MCIS_API 注入 __MCIS_API__），不在页面里写死。默认 127.0.0.1:8765。
declare const __MCIS_API__: string | undefined

export const DEFAULT_SERVICE_URL = 'http://127.0.0.1:8765'

export function serviceAddr(url: string | undefined | null): string {
  const u = (url && url.trim()) || DEFAULT_SERVICE_URL
  return u.replace(/^[a-z]+:\/\//i, '').replace(/\/+$/, '')
}

export const SERVICE_URL: string = (typeof __MCIS_API__ !== 'undefined' && __MCIS_API__) || DEFAULT_SERVICE_URL
export const SERVICE_ADDR: string = serviceAddr(SERVICE_URL)
