/** Bounded strict JSON comparison. No candidate correction; numbers retain exact lexemes. */
export function strictJsonFingerprint(text){
 if(typeof text!=='string'||Buffer.byteLength(text)>65536)throw new Error('MCIS_FINAL_JSON_INVALID');
 let i=0;const ws=()=>{while(/[ \t\r\n]/.test(text[i]||'x'))i++;};
 const fail=()=>{throw new Error('MCIS_FINAL_JSON_INVALID');};
 const string=()=>{const start=i;if(text[i++]!=='"')fail();let escaped=false;
  while(i<text.length){const c=text[i++];if(!escaped&&c==='"'){try{return JSON.parse(text.slice(start,i));}catch{fail();}}
   if(!escaped&&c==='\\')escaped=true;else escaped=false;}fail();};
 const value=depth=>{
  if(depth>64)fail();ws();const c=text[i];
  if(c==='"')return ['string',string()];
  if(c==='{'){
   i++;ws();const keys=new Set(),entries=[];if(text[i]==='}'){i++;return ['object',entries];}
   for(;;){ws();if(text[i]!=='"')fail();const k=string();if(keys.has(k))fail();keys.add(k);ws();if(text[i++]!==':')fail();entries.push([k,value(depth+1)]);ws();const end=text[i++];if(end==='}')break;if(end!==',')fail();}
   entries.sort((a,b)=>a[0]<b[0]?-1:a[0]>b[0]?1:0);return ['object',entries];
  }
  if(c==='['){i++;ws();const items=[];if(text[i]===']'){i++;return ['array',items];}for(;;){items.push(value(depth+1));ws();const end=text[i++];if(end===']')break;if(end!==',')fail();}return ['array',items];}
  for(const literal of ['true','false','null'])if(text.startsWith(literal,i)){i+=literal.length;return [literal];}
  const m=/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?/.exec(text.slice(i));
  if(!m)fail();i+=m[0].length;return ['number',m[0]];
 };
 const parsed=value(0);ws();if(i!==text.length)fail();return JSON.stringify(parsed);
}
export function equivalentFinal(payload,validated){
 if(validated===null)return false;
 try{return strictJsonFingerprint(payload)===strictJsonFingerprint(validated);}catch{return false;}
}
