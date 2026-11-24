import {strict as assert} from 'node:assert'
import {isValidElement,type ReactElement,type ReactNode} from 'react'
import {renderToStaticMarkup} from 'react-dom/server'
import {UnprotectedPaths} from '../src/bowtiePreview/UnprotectedPaths'
import type {PathWitness} from '../src/bowtiePreview/pathWitnesses'

const paths:PathWitness[]=[
 {side:'prevention',endpointId:'T',nodes:[{id:'T',label:'Synthetic same label'},{id:'TOP',label:'Synthetic top'}]},
 {side:'mitigation',endpointId:'C',nodes:[{id:'TOP',label:'Synthetic top'},{id:'C',label:'Synthetic same label'}]},
]
const calls:string[]=[]
const nav={onLocateNode:(id:string)=>calls.push(id),onLocateSources:()=>calls.push('sources')}
assert.equal(renderToStaticMarkup(<UnprotectedPaths paths={null} {...nav}/>),'')
assert.doesNotMatch(renderToStaticMarkup(<UnprotectedPaths paths={[]} {...nav}/>),/<button/)
const html=renderToStaticMarkup(<UnprotectedPaths paths={paths} {...nav}/>)
assert.match(html,/待核验；参考资料仅属于整份草稿，未与路径或节点绑定/)
assert.match(html,/定位草稿端点（T）/)
assert.match(html,/定位草稿端点（C）/)
assert.match(html,/定位整份草稿参考资料/)
assert.doesNotMatch(html,/<a\b/)
assert.deepEqual(calls,[])

function visit(node:ReactNode):ReactElement<{children?:ReactNode;onClick?:()=>void}>[]{
 if(Array.isArray(node))return node.flatMap(visit)
 if(!isValidElement<{children?:ReactNode;onClick?:()=>void}>(node))return []
 if(node.type==='button')return [node]
 return visit(node.props.children)
}
const buttons=visit(UnprotectedPaths({paths,...nav}))
assert.equal(buttons.length,3)
for(const button of buttons)button.props.onClick!()
assert.deepEqual(calls,['T','C','sources'])
console.log('PASS Bow-tie local navigation SSR/callback; no mounted keyboard/focus or network')
