using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Mcis.Domain.HumanFactors;

namespace Mcis.RestCli
{
 public static class Program
 {
  static readonly JsonSerializerOptions JsonOptions = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
  static void Fields(JsonElement value, params string[] expected) {
   if(value.ValueKind != JsonValueKind.Object) throw new ArgumentException("Expected object");
   var seen = new HashSet<string>(StringComparer.Ordinal);
   foreach(var p in value.EnumerateObject()) if(!seen.Add(p.Name) || !expected.Contains(p.Name)) throw new ArgumentException("Duplicate or unknown field");
   if(seen.Count != expected.Length) throw new ArgumentException("Missing field");
  }
  static string Text(JsonElement v) { if(v.ValueKind!=JsonValueKind.String) throw new ArgumentException("Expected string"); return v.GetString(); }
  static DateTimeOffset Utc(JsonElement value) {
   string s=Text(value);
   if(!Regex.IsMatch(s,@"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\z") ||
      !DateTimeOffset.TryParseExact(s,"yyyy-MM-dd'T'HH:mm:ss'Z'",CultureInfo.InvariantCulture,DateTimeStyles.AssumeUniversal|DateTimeStyles.AdjustToUniversal,out var d) || d.Year<1900 || d.Year>2100)
      throw new ArgumentException("Expected UTC seconds Z, year 1900..2100");
   return d;
  }
  static string Stamp(DateTimeOffset d) => d.ToUniversalTime().ToString("yyyy-MM-dd'T'HH:mm:ss.fffffff'Z'",CultureInfo.InvariantCulture);
  static object Finding(RestHourViolation f) => new { rule=f.Rule.ToString(),windowStartUtc=Stamp(f.WindowStart),windowEndUtc=Stamp(f.WindowEnd), actualHours=f.Actual.TotalHours,limitHours=f.Limit.TotalHours,violatingFromUtc=Stamp(f.ViolatingFrom),violatingToUtc=Stamp(f.ViolatingTo),clause=f.Clause,detail=f.Detail };
  static int Write(object o,int code) { Console.WriteLine(JsonSerializer.Serialize(o,JsonOptions));return code; }
  public static int Main() {
   Console.OutputEncoding=new UTF8Encoding(false);
   try {
    using var input=Console.OpenStandardInput(); using var memory=new MemoryStream();var buffer=new byte[8192];int n;
    while((n=input.Read(buffer,0,buffer.Length))>0) { if(memory.Length+n>131072) throw new ArgumentException("Input exceeds 128KiB");memory.Write(buffer,0,n); }
    using var document=JsonDocument.Parse(memory.ToArray(),new JsonDocumentOptions { MaxDepth=8 });var root=document.RootElement;
    Fields(root,"recordStartUtc","recordEndUtc","intervals");
    var start=Utc(root.GetProperty("recordStartUtc"));var end=Utc(root.GetProperty("recordEndUtc"));
    if(end<=start || end-start>TimeSpan.FromDays(14)) throw new ArgumentException("Record must be positive and no longer than 14 days");
    var rows=root.GetProperty("intervals");if(rows.ValueKind!=JsonValueKind.Array||rows.GetArrayLength()<1||rows.GetArrayLength()>256) throw new ArgumentException("Expected 1..256 intervals");
    var intervals=new List<DutyInterval>();
    foreach(var row in rows.EnumerateArray()) {
     Fields(row,"startUtc","endUtc","kind");var kind=Text(row.GetProperty("kind"));
     if(kind!="Watch"&&kind!="OtherWork"&&kind!="Rest") throw new ArgumentException("Invalid interval kind");
     intervals.Add(new DutyInterval(Utc(row.GetProperty("startUtc")),Utc(row.GetProperty("endUtc")),(WorkKind)Enum.Parse(typeof(WorkKind),kind)));
    }
    var schedule=WorkRestSchedule.Create(start,end,intervals);
    if(!schedule.IsSuccess) return Write(new { ok=false,error=new {code=schedule.ErrorCode,message=schedule.ErrorMessage}},4);
    var result=new RestHourChecker(new RestHourRules { ApplyWorkHourLimits=false }).Check(schedule.Value);
    if(!result.IsSuccess) return Write(new {ok=false,error=new {code=result.ErrorCode,message=result.ErrorMessage}},4);
    var report=result.Value;
    return Write(new {ok=true,result=new {
     coreVersion="mcis-rest/1", mode="rest-baseline-no-exceptions",
     totals=new {restHours=report.TotalRest.TotalHours,workHours=report.TotalWork.TotalHours,unknownHours=report.TotalUnknown.TotalHours},
     coverage=new {recordHours=(end-start).TotalHours,has24hWindow=end-start>=TimeSpan.FromHours(24),has7dWindow=end-start>=TimeSpan.FromDays(7),unknownHours=report.TotalUnknown.TotalHours},
     findings=report.Violations.Select(Finding).ToArray(),insufficientData=report.InsufficientData.Select(Finding).ToArray(),
     assumptions=report.Assumptions.Concat(new[]{"本切片未启用工作时长上限；核心原假设中工作规则表述不适用于此模式。","仅技术基线预览，不评估授权例外、紧急情况、补休及船旗国适用性；未发现偏差不等于合规。"}).ToArray()
    }},0);
   } catch(Exception e) when(e is JsonException||e is ArgumentException||e is InvalidOperationException||e is FormatException||e is OverflowException) {
    return Write(new {ok=false,error=new {code="REST_INPUT_INVALID",message=e.Message}},4);
   } catch(Exception) { return Write(new {ok=false,error=new {code="REST_INTERNAL",message="Rest calculation failed"}},1); }
  }
 }
}
