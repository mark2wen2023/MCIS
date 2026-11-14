import {mount} from './app'
import {parseMeeting} from './meeting'
declare const __MCIS_MEETING__:unknown
const embedded=typeof __MCIS_MEETING__==='undefined'?null:__MCIS_MEETING__
mount(document.getElementById('app')!,embedded?parseMeeting(new TextEncoder().encode(JSON.stringify(embedded))):undefined)
