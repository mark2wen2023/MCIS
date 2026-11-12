using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Ecfc;
class Program {
 static void Fail(string s){throw new FormatException(s);}
 static void Keys(JsonElement e,params string[] keys){
  if(e.ValueKind!=JsonValueKind.Object)Fail("Expected object");
  var seen=new HashSet<string>();foreach(var p in e.EnumerateObject()){string name;try{name=p.Name;}catch(InvalidOperationException){throw new FormatException("Invalid Unicode key");}if(!seen.Add(name)||!keys.Contains(name))Fail("Unknown or duplicate field");}
  if(seen.Count!=keys.Length)Fail("Missing field");
 }
 static string String(JsonElement v,int max=1000){
  if(v.ValueKind!=JsonValueKind.String)Fail("Expected string");
  string s;try{s=v.GetString();}catch(InvalidOperationException){throw new FormatException("Invalid Unicode");}
  for(int i=0;i<s.Length;i++){if(char.IsHighSurrogate(s[i])){if(i+1>=s.Length||!char.IsLowSurrogate(s[++i]))Fail("Invalid Unicode");}else if(char.IsLowSurrogate(s[i]))Fail("Invalid Unicode");}
  if(string.IsNullOrWhiteSpace(s)||s.Trim()!=s||s.EnumerateRunes().Count()>max)Fail("Invalid string");return s;
 }
 static string Text(JsonElement e,string key,int max=1000)=>String(e.GetProperty(key),max);
 static string Id(JsonElement e,string key){var s=Text(e,key,64);if(!Regex.IsMatch(s,@"\A[A-Za-z][A-Za-z0-9_-]{0,63}\z"))Fail("Invalid id");return s;}
 static bool Bool(JsonElement e,string key){var v=e.GetProperty(key);if(v.ValueKind!=JsonValueKind.True&&v.ValueKind!=JsonValueKind.False)Fail("Expected boolean");return v.GetBoolean();}
 static JsonElement Array(JsonElement e,string key,int max){var v=e.GetProperty(key);if(v.ValueKind!=JsonValueKind.Array||v.GetArrayLength()>max)Fail("Array budget");return v;}
 static void Main(string[] args){
  try{
   if(args.Length!=0)Fail("No arguments");
   using var input=Console.OpenStandardInput();using var bytes=new MemoryStream();byte[] b=new byte[4096];int n;
   while((n=input.Read(b,0,b.Length))>0){bytes.Write(b,0,n);if(bytes.Length>131072)Fail("Input too large");}
   // Strict UTF-8 validation before JSON parsing; no replacement decoding.
   new UTF8Encoding(false,true).GetString(bytes.ToArray());
   using var doc=JsonDocument.Parse(bytes.ToArray(),new JsonDocumentOptions{MaxDepth=8});var e=doc.RootElement;
   Keys(e,"action","draft");if(Text(e,"action")!="validate")Fail("Unknown action");
   var d=e.GetProperty("draft");Keys(d,"scope","nodes","edges");Text(d,"scope");
   var nodes=new List<EcfcNode>();var byId=new Dictionary<string,EcfcNode>(StringComparer.Ordinal);
   foreach(var j in Array(d,"nodes",40).EnumerateArray()){
    Keys(j,"id","kind","text","timeSeconds","lane","isPrimaryIncident","evidenceIds");
    var id=Id(j,"id");var kind=Text(j,"kind");if(kind!="Event"&&kind!="Condition")Fail("Invalid kind");
    var text=Text(j,"text");var t=j.GetProperty("timeSeconds");SimTime? time=null;
    if(t.ValueKind!=JsonValueKind.Null){if(t.ValueKind!=JsonValueKind.Number||!t.TryGetDouble(out double seconds)||!double.IsFinite(seconds)||Math.Abs(seconds)>315576000)Fail("Invalid time");time=new SimTime(t.GetDouble());}
    var l=j.GetProperty("lane");if(l.ValueKind!=JsonValueKind.Number||!l.TryGetInt32(out int lane)||lane< -5||lane>5)Fail("Invalid lane");
    var evidence=new List<string>();foreach(var v in Array(j,"evidenceIds",8).EnumerateArray()){var ev=String(v,64);if(!Regex.IsMatch(ev,@"\AEV-[0-9]{3,}\z")||evidence.Contains(ev))Fail("Invalid evidence id");evidence.Add(ev);}
    var node=new EcfcNode(id,kind=="Event"?EcfcNodeKind.Event:EcfcNodeKind.Condition,text,time:time,lane:l.GetInt32(),isPrimaryIncident:Bool(j,"isPrimaryIncident"),isPresumptive:true,evidenceIds:evidence);
    if(!byId.TryAdd(id,node))Fail("Duplicate node id");nodes.Add(node);
   }
   var edges=new List<EcfcEdge>();var edgeIds=new HashSet<string>();var pairs=new HashSet<string>();var indegree=nodes.ToDictionary(x=>x.NodeId,x=>0);var outgoing=nodes.ToDictionary(x=>x.NodeId,x=>new List<string>());
   foreach(var j in Array(d,"edges",80).EnumerateArray()){
    Keys(j,"id","from","to");var id=Id(j,"id");var from=Id(j,"from");var to=Id(j,"to");
    if(!edgeIds.Add(id)||!pairs.Add(from+"\0"+to)||from==to||!byId.ContainsKey(from)||!byId.ContainsKey(to))Fail("Invalid edge structure");
    var derived=EcfcValidator.DeriveEdgeKind(byId[from],byId[to]);if(!derived.IsSuccess)Fail("Event to condition unsupported");
    edges.Add(new EcfcEdge(id,from,to,derived.Kind,derived.IsPrimarySequenceBold));indegree[to]++;outgoing[from].Add(to);
   }
   var queue=new Queue<string>(indegree.Where(x=>x.Value==0).Select(x=>x.Key));int visited=0;
   while(queue.Count>0){var id=queue.Dequeue();visited++;foreach(var to in outgoing[id])if(--indegree[to]==0)queue.Enqueue(to);}
   if(visited!=nodes.Count)Fail("Cycle unsupported");
   var issues=EcfcValidator.Validate(nodes,edges).Select(i=>new{code=i.RuleCode,isError=i.IsError,message=i.Message,nodeId=i.RelatedNodeId,edgeId=i.RelatedEdgeId}).ToArray();
   var outputNodes=nodes.Select(x=>new{id=x.NodeId,kind=x.Kind.ToString(),text=x.Text,timeSeconds=x.Time.HasValue?(double?)x.Time.Value.Seconds:null,lane=x.Lane,isPrimaryIncident=x.IsPrimaryIncident,evidenceIds=x.EvidenceIds,isPresumptive=true}).ToArray();
   var outputEdges=edges.Select(x=>new{id=x.EdgeId,from=x.FromNodeId,to=x.ToNodeId,kind=x.Kind.ToString(),bold=x.IsPrimarySequenceBold}).ToArray();
   var output=JsonSerializer.Serialize(new{ok=true,result=new{coreVersion="mcis-ecfc-draft/1",nodes=outputNodes,edges=outputEdges,issues}});
   if(Encoding.UTF8.GetByteCount(output)+1>1048576)throw new IOException("Output budget exceeded");
   Console.WriteLine(output);
  }catch(Exception ex)when(ex is FormatException||ex is JsonException||ex is DecoderFallbackException){Console.WriteLine(JsonSerializer.Serialize(new{ok=false,error=new{code="ECFC_INPUT",message=ex is FormatException?ex.Message:"Invalid JSON or Unicode"}}));Environment.ExitCode=4;}
  catch(Exception){Console.WriteLine("{\"ok\":false,\"error\":{\"code\":\"ECFC_INTERNAL\",\"message\":\"Draft validation unavailable\"}}");Environment.ExitCode=1;}
 }
}
