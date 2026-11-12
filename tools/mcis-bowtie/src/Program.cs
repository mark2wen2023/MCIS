using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mcis.Domain.Systemic;
using Mcis.Domain.HumanFactors;
class Program
{
 static readonly Regex IdPattern=new Regex(@"\A[A-Za-z0-9_-]{1,64}\z");
 static void Keys(JsonElement e, params string[] allowed) {
  if(e.ValueKind!=JsonValueKind.Object) throw new FormatException("Expected object");
  var seen=new HashSet<string>();
  foreach(var p in e.EnumerateObject()) if(!seen.Add(p.Name)||!allowed.Contains(p.Name)) throw new FormatException("Duplicate or unknown field");
  if(seen.Count!=allowed.Length) throw new FormatException("Missing field");
 }
 static string Text(JsonElement e,string k,bool id=false) {
  var v=e.GetProperty(k); if(v.ValueKind!=JsonValueKind.String) throw new FormatException("Expected string");
  string s;try{s=v.GetString();}catch(InvalidOperationException){throw new FormatException("Invalid Unicode");}
  for(int i=0;i<s.Length;i++) {
   if(char.IsHighSurrogate(s[i])) {if(i+1>=s.Length||!char.IsLowSurrogate(s[i+1]))throw new FormatException("Invalid Unicode");i++;}
   else if(char.IsLowSurrogate(s[i]))throw new FormatException("Invalid Unicode");
  }
  if(id ? !IdPattern.IsMatch(s) : s.Length==0||s.EnumerateRunes().Count()>500||s.Trim()!=s) throw new FormatException("Invalid "+k);
  return s;
 }
 static void Array(JsonElement a,int max) {if(a.ValueKind!=JsonValueKind.Array||a.GetArrayLength()>max)throw new FormatException("Invalid array size");}
 static object Issue(string c,string id,string m)=>new {code=c,elementId=id,message=m};
 static void Main(string[] args) {
  try {
   if(args.Length!=0) throw new FormatException("Arguments not supported");
   using var stream=Console.OpenStandardInput(); using var bytes=new MemoryStream();
   byte[] b=new byte[4096];int n;while((n=stream.Read(b,0,b.Length))>0){bytes.Write(b,0,n);if(bytes.Length>131072)throw new FormatException("Input too large");}
   using var doc=JsonDocument.Parse(bytes.ToArray(),new JsonDocumentOptions{MaxDepth=16});
   var input=doc.RootElement;Keys(input,"hazard","topEvent","nodes","edges");
   string hazard=Text(input,"hazard");var top=input.GetProperty("topEvent");Keys(top,"id","label");string tid=Text(top,"id",true),tl=Text(top,"label");
   var nodes=input.GetProperty("nodes");Array(nodes,64);
   foreach(var node in nodes.EnumerateArray()) {
    Keys(node,"id","label","kind","barrierId");Text(node,"id",true);Text(node,"label");
    string kind=Text(node,"kind");
    if(!new[]{"Threat","PreventionBarrier","MitigationBarrier","Consequence","EscalationFactor"}.Contains(kind))throw new FormatException("Invalid kind");
    if(kind=="EscalationFactor")Text(node,"barrierId",true);else if(node.GetProperty("barrierId").ValueKind!=JsonValueKind.Null)throw new FormatException("barrierId must be null");
   }
   var edges=input.GetProperty("edges");Array(edges,128);
   foreach(var edge in edges.EnumerateArray()){Keys(edge,"fromId","toId");Text(edge,"fromId",true);Text(edge,"toId",true);}
   var created=BowTieModel.Create("preview",hazard,tid,tl);
   if(!created.IsSuccess){
    Console.WriteLine(JsonSerializer.Serialize(new{ok=true,result=new{coreVersion="mcis-bowtie/1",mode="hypothesis-structure-only",
     constructionErrors=new[]{Issue(created.ErrorCode,tid,created.ErrorMessage)},validationIssues=new object[0],structureValid=false,notCheckedRefCount=0,nodeCount=0,edgeCount=0}}));return;
   }
   var model=created.Value;
   var errors=new List<object>();
   foreach(var node in nodes.EnumerateArray().OrderBy(x=>Text(x,"kind")=="EscalationFactor"?1:0)){
    string id=Text(node,"id"),label=Text(node,"label"),kind=Text(node,"kind");
    Mcis.Core.Result<BowTieElement> added;
    switch(kind){
     case "Threat":added=model.AddThreat(id,label,EvidenceStrength.ToBeVerified);break;
     case "Consequence":added=model.AddConsequence(id,label,EvidenceStrength.ToBeVerified);break;
     case "EscalationFactor":added=model.AddEscalationFactor(id,label,Text(node,"barrierId"),EvidenceStrength.ToBeVerified);break;
     default:added=model.AddBarrier(id,label,Enum.Parse<BowTieElementKind>(kind),BarrierState.Unknown,EvidenceStrength.ToBeVerified);break;
    }
    if(!added.IsSuccess){errors.Add(Issue(added.ErrorCode,id,added.ErrorMessage));break;}
   }
   if(errors.Count==0)foreach(var edge in edges.EnumerateArray()){
    string from=Text(edge,"fromId"),to=Text(edge,"toId");var added=model.Connect(from,to);
    if(!added.IsSuccess){errors.Add(Issue(added.ErrorCode,from,added.ErrorMessage));break;}
   }
   var validation=errors.Count==0?model.Validate():null;
   Console.WriteLine(JsonSerializer.Serialize(new {ok=true,result=new {
    coreVersion="mcis-bowtie/1",mode="hypothesis-structure-only",constructionErrors=errors,
    validationIssues=validation==null?new object[0]:validation.Issues.Select(i=>(object)new{code=i.Code,elementId=i.ElementId,message=i.Message,severity=i.Severity.ToString()}).ToArray(),
    structureValid=validation!=null&&validation.IsValid,notCheckedRefCount=0,nodeCount=model.Elements.Count,edgeCount=model.Edges.Count
   }}));
  }catch(Exception ex) when(ex is FormatException||ex is JsonException){Console.WriteLine(JsonSerializer.Serialize(new{ok=false,error=new{code="BOWTIE_INPUT",message=ex is JsonException?"Invalid JSON":ex.Message}}));Environment.ExitCode=4;}
   catch(Exception){Console.WriteLine("{\"ok\":false,\"error\":{\"code\":\"BOWTIE_INTERNAL\",\"message\":\"Structure preview unavailable\"}}");Environment.ExitCode=1;}
 }
}
