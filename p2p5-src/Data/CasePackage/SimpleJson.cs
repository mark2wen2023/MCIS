using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Mcis.Data.CasePackage
{
    /// <summary>
    /// 极简 JSON 读写器，仅覆盖 .mcase 清单与 case.json 所需的对象/数组/标量，避免在 Unity 领域层引入 NuGet 依赖。
    /// </summary>
    public static class SimpleJson
    {
        public static string Escape(string s)
        {
            if (s == null)
            {
                return string.Empty;
            }

            var sb = new StringBuilder(s.Length + 8);
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                switch (c)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '"': sb.Append("\\\""); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (c < 32)
                        {
                            sb.Append("\\u");
                            sb.Append(((int)c).ToString("x4"));
                        }
                        else
                        {
                            sb.Append(c);
                        }
                        break;
                }
            }

            return sb.ToString();
        }

        public static string Quote(string s)
        {
            return "\"" + Escape(s ?? string.Empty) + "\"";
        }

        public static string FormatIso(DateTimeOffset dto)
        {
            return dto.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);
        }

        public static DateTimeOffset ParseIso(string s)
        {
            return DateTimeOffset.Parse(s, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);
        }

        public static string Number(double v)
        {
            return v.ToString("G17", CultureInfo.InvariantCulture);
        }

        public static string Number(int v)
        {
            return v.ToString(CultureInfo.InvariantCulture);
        }

        public static string Bool(bool v)
        {
            return v ? "true" : "false";
        }

        public static JsonValue Parse(string json)
        {
            var parser = new Parser(json ?? string.Empty);
            return parser.ParseValue();
        }

        public sealed class JsonValue
        {
            public string Kind { get; }
            public string Raw { get; }
            public List<JsonValue> Items { get; }
            public Dictionary<string, JsonValue> Fields { get; }

            private JsonValue(string kind, string raw, List<JsonValue> items, Dictionary<string, JsonValue> fields)
            {
                Kind = kind;
                Raw = raw;
                Items = items;
                Fields = fields;
            }

            public static JsonValue Null() { return new JsonValue("null", null, null, null); }
            public static JsonValue Str(string s) { return new JsonValue("string", s ?? string.Empty, null, null); }
            public static JsonValue Num(string raw) { return new JsonValue("number", raw, null, null); }
            public static JsonValue BoolVal(bool v) { return new JsonValue("bool", v ? "true" : "false", null, null); }
            public static JsonValue Arr(List<JsonValue> items) { return new JsonValue("array", null, items, null); }
            public static JsonValue Obj(Dictionary<string, JsonValue> fields) { return new JsonValue("object", null, null, fields); }

            public string AsString()
            {
                return Raw;
            }

            public bool AsBool()
            {
                return string.Equals(Raw, "true", StringComparison.OrdinalIgnoreCase);
            }

            public double AsDouble()
            {
                return double.Parse(Raw, CultureInfo.InvariantCulture);
            }

            public int AsInt()
            {
                return (int)Math.Round(AsDouble());
            }

            public JsonValue this[string key]
            {
                get
                {
                    if (Fields != null && Fields.TryGetValue(key, out JsonValue v))
                    {
                        return v;
                    }

                    return null;
                }
            }

            public string GetString(string key, string fallback = "")
            {
                JsonValue v = this[key];
                return v == null || v.Kind == "null" ? fallback : v.AsString();
            }

            public bool GetBool(string key, bool fallback = false)
            {
                JsonValue v = this[key];
                return v == null || v.Kind == "null" ? fallback : v.AsBool();
            }

            public double GetDouble(string key, double fallback = 0.0)
            {
                JsonValue v = this[key];
                return v == null || v.Kind == "null" ? fallback : v.AsDouble();
            }

            public int GetInt(string key, int fallback = 0)
            {
                JsonValue v = this[key];
                return v == null || v.Kind == "null" ? fallback : v.AsInt();
            }
        }

        private sealed class Parser
        {
            private readonly string _s;
            private int _i;

            public Parser(string s)
            {
                _s = s;
                _i = 0;
            }

            public JsonValue ParseValue()
            {
                SkipWs();
                if (_i >= _s.Length)
                {
                    return JsonValue.Null();
                }

                char c = _s[_i];
                if (c == '{') return ParseObject();
                if (c == '[') return ParseArray();
                if (c == '"') return JsonValue.Str(ParseString());
                if (c == 't' || c == 'f') return JsonValue.BoolVal(ParseLiteralBool());
                if (c == 'n') { ParseNull(); return JsonValue.Null(); }
                return JsonValue.Num(ParseNumber());
            }

            private JsonValue ParseObject()
            {
                _i++;
                var fields = new Dictionary<string, JsonValue>(StringComparer.Ordinal);
                SkipWs();
                if (Peek() == '}')
                {
                    _i++;
                    return JsonValue.Obj(fields);
                }

                while (_i < _s.Length)
                {
                    SkipWs();
                    string key = ParseString();
                    SkipWs();
                    Expect(':');
                    JsonValue val = ParseValue();
                    fields[key] = val;
                    SkipWs();
                    char c = Peek();
                    if (c == ',')
                    {
                        _i++;
                        continue;
                    }

                    if (c == '}')
                    {
                        _i++;
                        break;
                    }

                    throw new InvalidOperationException("JSON 对象格式错误，位置 " + _i);
                }

                return JsonValue.Obj(fields);
            }

            private JsonValue ParseArray()
            {
                _i++;
                var items = new List<JsonValue>();
                SkipWs();
                if (Peek() == ']')
                {
                    _i++;
                    return JsonValue.Arr(items);
                }

                while (_i < _s.Length)
                {
                    items.Add(ParseValue());
                    SkipWs();
                    char c = Peek();
                    if (c == ',')
                    {
                        _i++;
                        continue;
                    }

                    if (c == ']')
                    {
                        _i++;
                        break;
                    }

                    throw new InvalidOperationException("JSON 数组格式错误，位置 " + _i);
                }

                return JsonValue.Arr(items);
            }

            private string ParseString()
            {
                Expect('"');
                var sb = new StringBuilder();
                while (_i < _s.Length)
                {
                    char c = _s[_i++];
                    if (c == '"')
                    {
                        return sb.ToString();
                    }

                    if (c == '\\')
                    {
                        if (_i >= _s.Length)
                        {
                            break;
                        }

                        char e = _s[_i++];
                        switch (e)
                        {
                            case '"': sb.Append('"'); break;
                            case '\\': sb.Append('\\'); break;
                            case '/': sb.Append('/'); break;
                            case 'b': sb.Append('\b'); break;
                            case 'f': sb.Append('\f'); break;
                            case 'n': sb.Append('\n'); break;
                            case 'r': sb.Append('\r'); break;
                            case 't': sb.Append('\t'); break;
                            case 'u':
                                if (_i + 4 <= _s.Length)
                                {
                                    int code = int.Parse(_s.Substring(_i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
                                    sb.Append((char)code);
                                    _i += 4;
                                }
                                break;
                            default:
                                sb.Append(e);
                                break;
                        }
                    }
                    else
                    {
                        sb.Append(c);
                    }
                }

                throw new InvalidOperationException("JSON 字符串未闭合");
            }

            private string ParseNumber()
            {
                int start = _i;
                if (Peek() == '-')
                {
                    _i++;
                }

                while (_i < _s.Length && char.IsDigit(_s[_i]))
                {
                    _i++;
                }

                if (Peek() == '.')
                {
                    _i++;
                    while (_i < _s.Length && char.IsDigit(_s[_i]))
                    {
                        _i++;
                    }
                }

                if (Peek() == 'e' || Peek() == 'E')
                {
                    _i++;
                    if (Peek() == '+' || Peek() == '-')
                    {
                        _i++;
                    }

                    while (_i < _s.Length && char.IsDigit(_s[_i]))
                    {
                        _i++;
                    }
                }

                return _s.Substring(start, _i - start);
            }

            private bool ParseLiteralBool()
            {
                if (_s.Substring(_i).StartsWith("true", StringComparison.Ordinal))
                {
                    _i += 4;
                    return true;
                }

                if (_s.Substring(_i).StartsWith("false", StringComparison.Ordinal))
                {
                    _i += 5;
                    return false;
                }

                throw new InvalidOperationException("JSON 布尔字面量错误");
            }

            private void ParseNull()
            {
                if (!_s.Substring(_i).StartsWith("null", StringComparison.Ordinal))
                {
                    throw new InvalidOperationException("JSON null 字面量错误");
                }

                _i += 4;
            }

            private void SkipWs()
            {
                while (_i < _s.Length && char.IsWhiteSpace(_s[_i]))
                {
                    _i++;
                }
            }

            private char Peek()
            {
                return _i < _s.Length ? _s[_i] : '\0';
            }

            private void Expect(char c)
            {
                SkipWs();
                if (Peek() != c)
                {
                    throw new InvalidOperationException("JSON 期望 '" + c + "' 于位置 " + _i);
                }

                _i++;
            }
        }
    }
}
