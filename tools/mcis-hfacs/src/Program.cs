using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using Mcis.Domain.HumanFactors;
class Program {
 const string Version="mcis-hfacs/1",Taxonomy="mcis-hfacs-project/1";
 sealed class CoreFailure:Exception{public string Code;public CoreFailure(string code,string message):base(message){Code=code;}}
 static void Keys(JsonElement e,params string[] keys){
  if(e.ValueKind!=JsonValueKind.Object)throw new FormatException("Expected object");
  var seen=new HashSet<string>();foreach(var p in e.EnumerateObject())if(!seen.Add(p.Name)||!keys.Contains(p.Name))throw new FormatException("Unknown or duplicate field");
  if(seen.Count!=keys.Length)throw new FormatException("Missing field");
 }
 static string Text(JsonElement e,string key,int max=1000){
  var v=e.GetProperty(key);if(v.ValueKind!=JsonValueKind.String)throw new FormatException("Expected string");
  string s;try{s=v.GetString();}catch(InvalidOperationException){throw new FormatException("Invalid Unicode");}
  for(int i=0;i<s.Length;i++){if(char.IsHighSurrogate(s[i])){if(i+1>=s.Length||!char.IsLowSurrogate(s[++i]))throw new FormatException("Invalid Unicode");}else if(char.IsLowSurrogate(s[i]))throw new FormatException("Invalid Unicode");}
  if(s.Length==0||s.Trim()!=s||s.EnumerateRunes().Count()>max)throw new FormatException("Invalid "+key);
  return s;
 }
 static void Main(string[] args){
  try{
   if(args.Length!=0)throw new FormatException("No arguments");
   using var input=Console.OpenStandardInput();using var bytes=new MemoryStream();byte[] b=new byte[4096];int n;
   while((n=input.Read(b,0,b.Length))>0){bytes.Write(b,0,n);if(bytes.Length>65536)throw new FormatException("Input too large");}
   using var doc=JsonDocument.Parse(bytes.ToArray(),new JsonDocumentOptions{MaxDepth=8});var e=doc.RootElement;
   if(e.ValueKind!=JsonValueKind.Object||!e.TryGetProperty("action",out var action)||action.ValueKind!=JsonValueKind.String)throw new FormatException("Missing action");
   if(Text(e,"action")=="taxonomy"){
    Keys(e,"action");
    var categories=HfacsMaTaxonomy.All.Select(c=>new{code=c.Code,name=c.Name,layer=c.Layer.ToString(),parentCode=c.ParentCode,isLeaf=HfacsMaTaxonomy.ChildrenOf(c.Code).Count==0}).ToArray();
    Console.WriteLine(JsonSerializer.Serialize(new{ok=true,result=new{coreVersion=Version,taxonomyVersion=Taxonomy,categories}}));return;
   }
   if(Text(e,"action")!="validate")throw new FormatException("Unknown action");
   Keys(e,"action","draft");var draft=e.GetProperty("draft");Keys(draft,"scope","entries");string scope=Text(draft,"scope");
   var entries=draft.GetProperty("entries");if(entries.ValueKind!=JsonValueKind.Array||entries.GetArrayLength()<1||entries.GetArrayLength()>32)throw new FormatException("Expected 1 to 32 entries");
   // Validate all protocol fields before constructing a temporary analysis.
   foreach(var entry in entries.EnumerateArray()){
    Keys(entry,"id","categoryCode","description","rationale");
    if(!Regex.IsMatch(Text(entry,"id",64),@"\A[A-Za-z][A-Za-z0-9_-]{0,63}\z"))throw new FormatException("Invalid id");
    Text(entry,"categoryCode");Text(entry,"description");Text(entry,"rationale");
   }
   var analysis=new HfacsAnalysis(scope);
   foreach(var entry in entries.EnumerateArray()){
    var added=analysis.AddFinding(Text(entry,"id"),Text(entry,"categoryCode"),Text(entry,"description"),EvidenceStrength.ToBeVerified,new string[0],new string[0],ledger:null,origin:HfacsOrigin.Investigator);
    if(!added.IsSuccess)throw new CoreFailure(added.ErrorCode,added.ErrorMessage);
   }
   var output=analysis.Findings.Select(f=>new{id=f.Id,categoryCode=f.CategoryCode,layer=f.Layer.ToString(),description=f.Description,strength=f.Strength.ToString(),reviewStatus=f.ReviewStatus.ToString(),origin=f.Origin.ToString()}).ToArray();
   Console.WriteLine(JsonSerializer.Serialize(new{ok=true,result=new{coreVersion=Version,taxonomyVersion=Taxonomy,entries=output}}));
  }catch(CoreFailure ex){Console.WriteLine(JsonSerializer.Serialize(new{ok=false,error=new{code=ex.Code,message=ex.Message}}));Environment.ExitCode=4;}
  catch(Exception ex)when(ex is FormatException||ex is JsonException){Console.WriteLine(JsonSerializer.Serialize(new{ok=false,error=new{code="HFACS_INPUT",message=ex is FormatException?ex.Message:"Invalid JSON"}}));Environment.ExitCode=4;}
  catch(Exception){Console.WriteLine("{\"ok\":false,\"error\":{\"code\":\"HFACS_INTERNAL\",\"message\":\"Draft validation unavailable\"}}");Environment.ExitCode=1;}
 }
}
