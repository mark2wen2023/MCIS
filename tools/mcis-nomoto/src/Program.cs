using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Collections.Generic;
using System.Globalization;
using Mcis.Simulation.WhatIf;
class Program {
 static string Str(JsonElement e,string k){
  var p=e.GetProperty(k);if(p.ValueKind!=JsonValueKind.String)throw new FormatException("Expected string: "+k);
  string s;try{s=p.GetString();}catch(InvalidOperationException){throw new FormatException("Invalid Unicode");}
  for(int i=0;i<s.Length;i++){if(char.IsHighSurrogate(s[i])){if(i+1>=s.Length||!char.IsLowSurrogate(s[++i]))throw new FormatException("Invalid Unicode");}else if(char.IsLowSurrogate(s[i]))throw new FormatException("Invalid Unicode");}return s;
 }
 static double Num(JsonElement e,string k,double lo,double hi){
  string s=Str(e,k);
  if(!Regex.IsMatch(s,@"\A-?(0|[1-9][0-9]*)(\.[0-9]{1,6})?\z")||s.Length>24||!double.TryParse(s,NumberStyles.AllowLeadingSign|NumberStyles.AllowDecimalPoint,CultureInfo.InvariantCulture,out double n)||!double.IsFinite(n)||n<lo||n>hi||(n==0&&s.StartsWith("-")))throw new FormatException("Invalid "+k);return n;
 }
 // Compatibility-only fields are not vessel estimates. No speed-change/anchor/body branches are invoked.
 internal static ManeuverParams Parameters(double k,double t,double reference,double max,double rate,double inactive=1)
 =>new ManeuverParams(k,t,reference,max,rate,inactive,inactive,inactive,0,inactive,inactive,inactive,new AnchorParams(0,0,0,inactive,inactive));
 static object Point(KinematicState s,int second){
  double[] values={s.TimeSeconds,s.EastM,s.NorthM,s.HeadingDeg,s.SpeedKn,s.RotDegPerSec,s.RudderDeg};
  if(values.Any(v=>!double.IsFinite(v)||Math.Abs(v)>1e9)||Math.Abs(s.TimeSeconds-second)>1e-7)throw new InvalidOperationException("Invalid output");
  return new{timeSeconds=second,eastM=s.EastM,northM=s.NorthM,headingDeg=s.HeadingDeg,speedKn=s.SpeedKn,rotDegPerSec=s.RotDegPerSec,rudderDeg=s.RudderDeg};
 }
 static void Main(string[] args){
  try{
   if(args.Length>0)throw new FormatException("No arguments");
   using var input=Console.OpenStandardInput();using var bytes=new MemoryStream();byte[] b=new byte[4096];int n;while((n=input.Read(b,0,b.Length))>0){bytes.Write(b,0,n);if(bytes.Length>65536)throw new FormatException("Input too large");}
   using var doc=JsonDocument.Parse(bytes.ToArray(),new JsonDocumentOptions{MaxDepth=4});var e=doc.RootElement;
   string[] keys={"headingDeg","speedKn","k","tSeconds","referenceSpeedKn","maxRudderDeg","rudderRateDegPerSec","commandRudderDeg","durationSeconds","provenanceNote","uncertaintyNote"};
   if(e.ValueKind!=JsonValueKind.Object)throw new FormatException("Expected object");var seen=new HashSet<string>();
   foreach(var p in e.EnumerateObject())if(!seen.Add(p.Name)||!keys.Contains(p.Name))throw new FormatException("Duplicate or unknown field");
   if(seen.Count!=keys.Length)throw new FormatException("Missing field");
   foreach(string key in new[]{"provenanceNote","uncertaintyNote"}){string s=Str(e,key);if(s.Length==0||s.Trim()!=s||s.EnumerateRunes().Count()>1000)throw new FormatException("Invalid note");}
   double heading=Num(e,"headingDeg",0,360),speed=Num(e,"speedKn",0,40),k=Num(e,"k",.000001,.5),t=Num(e,"tSeconds",1,1000),reference=Num(e,"referenceSpeedKn",.1,40),max=Num(e,"maxRudderDeg",.1,45),rate=Num(e,"rudderRateDegPerSec",.01,20),command=Num(e,"commandRudderDeg",-max,max);
   if(heading>=360||speed/reference>5)throw new FormatException("Heading or speed ratio outside engineering envelope");
   int duration=(int)Num(e,"durationSeconds",1,300);if(!Regex.IsMatch(Str(e,"durationSeconds"),@"\A[1-9][0-9]*\z"))throw new FormatException("Duration must be integer string");
   var parameters=Parameters(k,t,reference,max,rate);var initial=new KinematicState(0,0,0,heading,speed,0,0);
   var turn=new[]{new Intervention(InterventionKind.Turn,0,rudderDeg:command,headingChangeDeg:0)};
   var baseline=NomotoSimulator.Simulate(initial,parameters,new Intervention[0],duration,.1);
   var response=NomotoSimulator.Simulate(initial,parameters,turn,duration,.1);
   var fine=NomotoSimulator.Simulate(initial,parameters,turn,duration,.05);
   object[] Sample(IReadOnlyList<KinematicState> states)=>Enumerable.Range(0,duration+1).Select(i=>Point(states[i*10],i)).ToArray();
   var a=response[response.Count-1];var z=fine[fine.Count-1];
   double distance=Math.Sqrt(Math.Pow(a.EastM-z.EastM,2)+Math.Pow(a.NorthM-z.NorthM,2)),hd=Math.Abs(KinematicState.NormalizeDeg180(a.HeadingDeg-z.HeadingDeg)),rot=Math.Abs(a.RotDegPerSec-z.RotDegPerSec);
   if(new[]{distance,hd,rot}.Any(v=>!double.IsFinite(v)||v>1e9))throw new InvalidOperationException();
   Console.WriteLine(JsonSerializer.Serialize(new{ok=true,result=new{coreVersion="mcis-nomoto/1",mode="fixed-rudder-hypothesis",stepSeconds=.1,comparisonStepSeconds=.05,baseline=Sample(baseline),response=Sample(response),numericalDifference=new{endpointDistanceM=distance,endpointHeadingDifferenceDeg=hd,endpointRotDifferenceDegPerSec=rot},assumptions=new[]{
    "Both tracks are hypothetical; initial relative position, time, ROT and actual rudder are zero.",
    "Manual K/T and active parameters are uncalibrated assumptions, not verified vessel attributes.",
    "No wind/current/waves, drift, shallow-water/bank effects, interactions, speed change or anchoring.",
    "Compatibility-only inactive constructor values are 1 (minimum speed 0), explicit anchor values 0/0/0/1/1; not ship data.",
    "Fixed-step motion RK4 with stepwise rudder update; endpoint step differences are not error bounds or confidence intervals.",
    "No collision, avoidance, risk, safety, causality or legal verdict."
   }}}));
  }catch(Exception ex)when(ex is FormatException||ex is JsonException){Console.WriteLine(JsonSerializer.Serialize(new{ok=false,error=new{code="NOMOTO_INPUT",message=ex is JsonException?"Invalid JSON":ex.Message}}));Environment.ExitCode=4;}
  catch(Exception){Console.WriteLine("{\"ok\":false,\"error\":{\"code\":\"NOMOTO_INTERNAL\",\"message\":\"Preview unavailable\"}}");Environment.ExitCode=1;}
 }
}
