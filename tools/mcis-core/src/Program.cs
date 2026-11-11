using System;
using System.IO;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization.Metadata;

namespace Mcis.Cli
{
    /// <summary>
    /// 用法：mcis-core &lt;子命令&gt; &lt; request.json &gt; response.json
    /// 响应统一外壳：{"ok":true,"command":"cpa","coreVersion":"...","result":{...}}
    /// 或 {"ok":false,"command":"cpa","error":{"code":"...","message":"..."}}；出错时退出码非 0。
    /// </summary>
    public static class Program
    {
        public const string CoreVersion = "mcis-core/0.1.0";

        public static int Main(string[] args)
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            string command = args.Length > 0 ? args[0] : "";
            if (command == "version" || command == "--version")
            {
                return Write(Ok("version", new JsonObject { ["coreVersion"] = CoreVersion, ["commands"] = new JsonArray("cpa", "colreg", "align", "version") }), 0);
            }

            string input;
            using (var reader = new StreamReader(Console.OpenStandardInput(), new UTF8Encoding(false)))
            {
                input = reader.ReadToEnd();
            }

            try
            {
                JsonNode req = string.IsNullOrWhiteSpace(input) ? new JsonObject() : JsonNode.Parse(input);
                switch (command)
                {
                    case "cpa":
                        return Write(Ok(command, CpaCommand.Run(req)), 0);
                    case "align":
                        return Write(Ok(command, AlignCommand.Run(req)), 0);
                    case "colreg":
                        return Write(Ok(command, ColregCommand.Run(req)), 0);
                    default:
                        return Write(Fail(command, "UNKNOWN_COMMAND", "未知子命令：" + command + "；可用：cpa, colreg, align, version"), 2);
                }
            }
            catch (JsonException ex)
            {
                return Write(Fail(command, "BAD_JSON", ex.Message), 4);
            }
            catch (RequestException ex)
            {
                return Write(Fail(command, ex.Code, ex.Message), 4);
            }
            catch (Exception ex)
            {
                return Write(Fail(command, "INTERNAL", ex.GetType().Name + ": " + ex.Message), 1);
            }
        }

        private static JsonObject Ok(string command, JsonNode result)
        {
            return new JsonObject { ["ok"] = true, ["command"] = command, ["coreVersion"] = CoreVersion, ["result"] = result };
        }

        private static JsonObject Fail(string command, string code, string message)
        {
            return new JsonObject
            {
                ["ok"] = false,
                ["command"] = command,
                ["coreVersion"] = CoreVersion,
                ["error"] = new JsonObject { ["code"] = code, ["message"] = message }
            };
        }

        private static int Write(JsonNode node, int exitCode)
        {
            // TypeInfoResolver 必填：结果树若含 JsonValueCustomized（如 string 数组），
            // 只设 Encoder 的 Options 会被标为只读并抛 InvalidOperationException。
            var options = new JsonSerializerOptions
            {
                WriteIndented = false,
                Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
                TypeInfoResolver = new DefaultJsonTypeInfoResolver()
            };
            Console.Out.Write(node.ToJsonString(options));
            Console.Out.Write('\n');
            Console.Out.Flush();
            return exitCode;
        }
    }

    public sealed class RequestException : Exception
    {
        public string Code { get; }
        public RequestException(string code, string message) : base(message) { Code = code; }
    }
}
