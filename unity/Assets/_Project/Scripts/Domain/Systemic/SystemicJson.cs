using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using Mcis.Core;

namespace Mcis.Domain.Systemic
{
    /// <summary>
    /// 最小 JSON 读写（仅供 systemic.json）。
    /// 为什么不复用仓库的 SimpleJson：它位于 Scripts/Data/CasePackage（Mcis.Data 程序集），
    /// 而 Mcis.Domain.asmdef 只引用 Mcis.Core，Domain 不能反向依赖 Data；也不改动 Core。
    /// 解析结果：对象 → Dictionary&lt;string, object&gt;（拒绝重复键），数组 → List&lt;object&gt;，
    /// 字符串 → string，数字 → double，true/false → bool，null → null。嵌套深度上限 64。
    /// </summary>
    public static class SystemicJson
    {
        private const int MaxDepth = 64;

        public static string Quote(string s)
        {
            if (s == null)
            {
                return "null";
            }

            var sb = new StringBuilder(s.Length + 2);
            sb.Append('"');
            foreach (char c in s)
            {
                switch (c)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    case '\b': sb.Append("\\b"); break;
                    case '\f': sb.Append("\\f"); break;
                    default:
                        if (c < 0x20)
                        {
                            sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
                        }
                        else
                        {
                            sb.Append(c);
                        }

                        break;
                }
            }

            sb.Append('"');
            return sb.ToString();
        }

        public static Result<object> Parse(string json)
        {
            if (json == null)
            {
                return Result<object>.Fail(SystemicErrors.JsonInvalid, "JSON 为空");
            }

            var p = new Parser(json);
            try
            {
                p.SkipWs();
                object v = p.ParseValue(0);
                p.SkipWs();
                if (p.Pos != json.Length)
                {
                    return Result<object>.Fail(SystemicErrors.JsonInvalid, "JSON 末尾有多余内容，位置 " + p.Pos);
                }

                return Result<object>.Ok(v);
            }
            catch (FormatException ex)
            {
                return Result<object>.Fail(SystemicErrors.JsonInvalid, ex.Message);
            }
        }

        private sealed class Parser
        {
            private readonly string _s;
            public int Pos;

            public Parser(string s)
            {
                _s = s;
            }

            public void SkipWs()
            {
                while (Pos < _s.Length && (_s[Pos] == ' ' || _s[Pos] == '\t' || _s[Pos] == '\n' || _s[Pos] == '\r'))
                {
                    Pos++;
                }
            }

            private FormatException Err(string msg)
            {
                return new FormatException("JSON 无效：" + msg + "，位置 " + Pos);
            }

            public object ParseValue(int depth)
            {
                if (depth > MaxDepth)
                {
                    throw Err("嵌套过深");
                }

                if (Pos >= _s.Length)
                {
                    throw Err("意外结束");
                }

                char c = _s[Pos];
                switch (c)
                {
                    case '{': return ParseObject(depth);
                    case '[': return ParseArray(depth);
                    case '"': return ParseString();
                    case 't': Expect("true"); return true;
                    case 'f': Expect("false"); return false;
                    case 'n': Expect("null"); return null;
                    default:
                        if (c == '-' || (c >= '0' && c <= '9'))
                        {
                            return ParseNumber();
                        }

                        throw Err("意外字符 '" + c + "'");
                }
            }

            private void Expect(string word)
            {
                if (string.CompareOrdinal(_s, Pos, word, 0, word.Length) != 0)
                {
                    throw Err("期望 " + word);
                }

                Pos += word.Length;
            }

            private Dictionary<string, object> ParseObject(int depth)
            {
                var d = new Dictionary<string, object>(StringComparer.Ordinal);
                Pos++;
                SkipWs();
                if (Pos < _s.Length && _s[Pos] == '}')
                {
                    Pos++;
                    return d;
                }

                while (true)
                {
                    SkipWs();
                    if (Pos >= _s.Length || _s[Pos] != '"')
                    {
                        throw Err("期望键名");
                    }

                    string key = ParseString();
                    if (d.ContainsKey(key))
                    {
                        throw Err("重复键 " + key);
                    }

                    SkipWs();
                    if (Pos >= _s.Length || _s[Pos] != ':')
                    {
                        throw Err("期望 ':'");
                    }

                    Pos++;
                    SkipWs();
                    d[key] = ParseValue(depth + 1);
                    SkipWs();
                    if (Pos < _s.Length && _s[Pos] == ',')
                    {
                        Pos++;
                        continue;
                    }

                    if (Pos < _s.Length && _s[Pos] == '}')
                    {
                        Pos++;
                        return d;
                    }

                    throw Err("期望 ',' 或 '}'");
                }
            }

            private List<object> ParseArray(int depth)
            {
                var list = new List<object>();
                Pos++;
                SkipWs();
                if (Pos < _s.Length && _s[Pos] == ']')
                {
                    Pos++;
                    return list;
                }

                while (true)
                {
                    SkipWs();
                    list.Add(ParseValue(depth + 1));
                    SkipWs();
                    if (Pos < _s.Length && _s[Pos] == ',')
                    {
                        Pos++;
                        continue;
                    }

                    if (Pos < _s.Length && _s[Pos] == ']')
                    {
                        Pos++;
                        return list;
                    }

                    throw Err("期望 ',' 或 ']'");
                }
            }

            private string ParseString()
            {
                Pos++; // 开引号
                var sb = new StringBuilder();
                while (true)
                {
                    if (Pos >= _s.Length)
                    {
                        throw Err("字符串未结束");
                    }

                    char c = _s[Pos++];
                    if (c == '"')
                    {
                        return sb.ToString();
                    }

                    if (c < 0x20)
                    {
                        throw Err("字符串含未转义控制字符");
                    }

                    if (c != '\\')
                    {
                        sb.Append(c);
                        continue;
                    }

                    if (Pos >= _s.Length)
                    {
                        throw Err("转义未结束");
                    }

                    char e = _s[Pos++];
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
                            int code;
                            if (Pos + 4 > _s.Length || !int.TryParse(_s.Substring(Pos, 4), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out code))
                            {
                                throw Err("\\u 转义无效");
                            }

                            sb.Append((char)code);
                            Pos += 4;
                            break;
                        default:
                            throw Err("未知转义 \\" + e);
                    }
                }
            }

            private double ParseNumber()
            {
                int start = Pos;
                if (_s[Pos] == '-')
                {
                    Pos++;
                }

                while (Pos < _s.Length && "0123456789.eE+-".IndexOf(_s[Pos]) >= 0)
                {
                    Pos++;
                }

                double v;
                if (!double.TryParse(_s.Substring(start, Pos - start), NumberStyles.Float, CultureInfo.InvariantCulture, out v))
                {
                    throw Err("数字无效");
                }

                return v;
            }
        }
    }
}
