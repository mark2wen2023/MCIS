import {createElement} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {VersionBindingPreview} from './Preview'
import fixed from '../version_binding/results.json'

console.log('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>W19 合成来源核对</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:960px;margin:32px auto;padding:0 20px;color:#172331;background:#f5f7f8}article{background:white;border:1px solid #c8d2dc;padding:20px;margin:20px 0}code{overflow-wrap:anywhere}blockquote{border-left:3px solid #75859a;margin-left:0;padding-left:16px}h3{color:#364d66}</style></head><body>'+renderToStaticMarkup(createElement(VersionBindingPreview,{receipt:fixed}))+'</body></html>')
