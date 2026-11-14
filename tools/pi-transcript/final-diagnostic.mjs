/** Classification only. Never grants acceptance or returns candidate text. */
function outsideWhitespace(text){
 let quoted=false,escaped=false,out='';
 for(const c of text){
  if(quoted){out+=c;if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;}
  else if(c==='"'){quoted=true;out+=c;}
  else if(!' \t\r\n'.includes(c))out+=c;
 }
 return out;
}
export function finalDiagnostic(payload,validated){
 if(validated===null)return 'MCIS_FINAL_UNVALIDATED_NO_VALIDATION';
 if(payload===validated)return null;
 try{
  JSON.parse(payload);JSON.parse(validated);
  if(outsideWhitespace(payload)===outsideWhitespace(validated))return 'MCIS_FINAL_UNVALIDATED_FORMATTING';
 }catch{}
 return 'MCIS_FINAL_UNVALIDATED_CHANGED';
}
