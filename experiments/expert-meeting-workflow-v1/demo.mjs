import {writeFileSync} from 'node:fs';
import {createMeeting,ROLES,renderView} from './workflow.mjs';
const meeting=createMeeting({actor:'investigator',config:{},panelFactory:()=>({review:async role=>({role,text:'合成独立审阅'}),challenge:async(speaker,target)=>({speaker,target,candidate:{text:'合成质询'}}),cancel(){}})});
for(const r of ROLES)await meeting.review(r);
meeting.setAgenda('investigator',[{id:'clock',title:'合成案例：两段视频时钟偏移是否影响判断？'}]);
await meeting.challenge('navigation','investigation');meeting.pause('investigator');
writeFileSync(new URL('./preview.html',import.meta.url),renderView(meeting.view('investigator')));
