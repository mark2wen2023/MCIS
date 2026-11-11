// 用 web/node_modules 的 esbuild 打包到 /tmp 并运行（不写 web/ 目录）
import { createRequire } from 'node:module'
import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
const here = path.dirname(fileURLToPath(import.meta.url))
const webNm = path.resolve(here, '../../../web/node_modules')
const require = createRequire(path.join(webNm, 'x.js'))
const esbuild = require('esbuild')
const out = '/tmp/w6-acceptance-web.cjs'
await esbuild.build({ entryPoints: [path.join(here, 'w6-view.test.tsx')], bundle: true, platform: 'node', format: 'cjs',
  outfile: out, jsx: 'automatic', nodePaths: [webNm], logLevel: 'error', define: { 'import.meta.env': '{}' } })
process.stdout.write(execFileSync(process.execPath, [out]).toString())
