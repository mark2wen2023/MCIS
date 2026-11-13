// Experiment only. Factory may wrap four Pi Agents; no real provider is configured here.
export const ROLES=Object.freeze(['regulation','navigation','investigation','vessel']);
const text=(x,n=2000)=>{if(typeof x!=='string'||!x.trim()||x.length>n)throw Error('invalid text');return x;};
export function createMeeting({actor,panelFactory,config,operationBudget=12}) {
  if(actor!=='investigator')throw Error('human start required');
  if(!Number.isSafeInteger(operationBudget)||operationBudget<4||operationBudget>64)throw Error('budget');
  const panel=panelFactory({...config,actor});
  let stage='independent',paused=false,busy=false,remaining=operationBudget,agenda=[],active=null,suggestions=null,closure=null;
  const reviews={},turns=[],audit=[];
  const human=a=>{if(a!=='investigator')throw Error('human required');};
  const allowed=()=>{if(stage==='cancelled')throw Error('cancelled');if(paused)throw Error('paused');if(busy)throw Error('busy');};
  async function invoke(fn,save){allowed();if(remaining===0)throw Error('budget exhausted');busy=true;remaining--;try{const r=await fn();if(stage==='cancelled')throw Error('cancelled');save(structuredClone(r));return structuredClone(r);}finally{busy=false;}}
  return {
    async review(role){allowed();if(stage!=='independent'||!ROLES.includes(role)||reviews[role])throw Error('phase or role');return invoke(()=>panel.review(role),r=>{reviews[role]=r;if(Object.keys(reviews).length===4)stage='agenda';audit.push({event:'review',role});});},
    setAgenda(actor,items){human(actor);allowed();if(stage!=='agenda'||!Array.isArray(items)||items.length<1||items.length>12)throw Error('agenda');const ids=new Set();const next=items.map(i=>{if(!i||Object.keys(i).sort().join(',')!=='id,title')throw Error('issue');text(i.id,80);text(i.title,500);if(ids.has(i.id))throw Error('duplicate');ids.add(i.id);return {...i};});agenda=next;active=next[0].id;stage='discussion';audit.push({event:'agenda_confirmed',ids:[...ids]});},
    focus(actor,id){human(actor);allowed();if(stage!=='discussion'||!agenda.some(x=>x.id===id))throw Error('issue');active=id;audit.push({event:'focus',id});},
    async challenge(role,target){allowed();if(stage!=='discussion'||!ROLES.includes(role)||!ROLES.includes(target)||role===target)throw Error('phase or role');const issue=active;return invoke(()=>panel.challenge(role,target),r=>{turns.push({candidate:r?.candidate,issue,speaker:role,target});audit.push({event:'challenge',issue,role,target});});},
    closeDiscussion(actor,reason){human(actor);allowed();if(stage!=='discussion')throw Error('phase');const unaddressed=agenda.filter(i=>!turns.some(t=>t.issue===i.id)).map(i=>i.id);if(unaddressed.length)text(reason,1000);closure={kind:unaddressed.length?'human_early_close':'human_close',unaddressed,reason:reason===undefined?null:text(reason,1000),coverage:'turn_presence_only_not_resolved'};stage='report_suggestions';audit.push({event:'discussion_closed',...structuredClone(closure)});},
    recordSuggestions(actor,value){human(actor);allowed();if(stage!=='report_suggestions')throw Error('phase');suggestions={text:text(value,8000),status:'candidate_requires_human_review',scope:'whole_report'};stage='completed';audit.push({event:'suggestions_recorded'});},
    pause(actor){human(actor);if(stage==='cancelled'||stage==='completed')throw Error('phase');paused=true;audit.push({event:'pause'});},
    resume(actor){human(actor);if(busy)throw Error('busy');if(!paused||stage==='cancelled')throw Error('phase');paused=false;audit.push({event:'resume'});},
    cancel(actor){human(actor);panel.cancel(actor);stage='cancelled';paused=false;audit.push({event:'cancel'});},
    view(actor){human(actor);return structuredClone({mode:'synthetic-workflow-no-llm',host:'海青君',stage,paused,busy,remaining,experts:ROLES,agenda,active,reviewCount:Object.keys(reviews).length,closure,turns:stage==='cancelled'?[]:turns,suggestions:stage==='cancelled'?null:suggestions,audit});}
  };
}
export function renderView(v){const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));return `<!doctype html><html lang="zh"><meta charset="utf-8"><title>海青君专家会诊 · 实验</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;background:#edf3f6;color:#18344a}section{background:white;padding:20px;margin:14px 0;border-radius:12px}small{color:#546b78}</style><h1>海青君 · 专家会诊管理</h1><p>合成实验 · 无真实 LLM · 非生产界面 · 以下为只读管理快照</p><section><h2>会前：四专家独立整体审阅</h2><p>${v.experts.map(esc).join(' / ')}</p><p>已审阅 ${esc(v.reviewCount)} / 4</p><small>扩展或减少专家须调查员确认；本原型尚未支持。</small></section><section><h2>会中：按争点交叉质询</h2><p>阶段 ${esc(v.stage)} · ${v.paused?'暂停':'未暂停'} · 剩余操作预算 ${esc(v.remaining)}</p><ol>${v.agenda.map(x=>`<li>${esc(x.id)}：${esc(x.title)}</li>`).join('')}</ol><p>当前争点：${esc(v.active??'未确定')} · 已记录 ${esc(v.turns.length)} 次质询</p></section><section><h2>会后：回到整份报告</h2><p>结束状态：${esc(v.closure?.kind??'未结束')}；未讨论争点：${esc(v.closure?.unaddressed.join(', ')??'尚未结算')}。有质询不代表问题已解决。</p><p>${esc(v.suggestions?.text??'尚无建议')}</p><small>仅供人工审核，不能自动改定稿。暂停/恢复/聚焦由业务接口执行，本页无操作按钮。</small></section></html>`;}
