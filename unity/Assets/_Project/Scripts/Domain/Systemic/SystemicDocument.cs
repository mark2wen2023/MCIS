using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using Mcis.Core;
using Mcis.Domain.Evidence;
using Mcis.Domain.HumanFactors;

namespace Mcis.Domain.Systemic
{
    /// <summary>
    /// .mcase 内 systemic.json 的内存形态：可同时包含一张 Bow-tie、一张 AcciMap、一个 STAMP/CAST 控制结构（均可为空）。
    /// JSON 往返：<see cref="ToJson"/> 输出确定性的紧凑 JSON；<see cref="FromJson"/> 通过模型的 Add/Connect 方法重放构建，
    /// 因此反序列化同样执行全部结构规则（成环、层间方向、Strong/Moderate 必须有证据等），错误码原样返回。
    /// Bow-tie 两遍加载（A11）：先建全部非升级因素节点，再挂升级因素，不依赖 elements 中的顺序。
    /// W15.1 向后兼容地扩展了 schema/1：refs 对象仍以 evidence/ecfc/hfacs/recommendations 四键开头，其他种类以 camelCase 键追加
    /// （如 statement、colregCheck、damageTrack，仅非空时写出）；节点可选 actorId；AcciMap 可选 infoFlows。旧文件可原样读取。
    /// </summary>
    public sealed class SystemicDocument
    {
        public const string Schema = "mcis.systemic/1";

        public string CaseId { get; }

        /// <summary>是否为虚构演示数据（演示案件必须为 true，界面据此显示“示例数据（虚构）”）。</summary>
        public bool IsFictionalDemo { get; }

        public BowTieModel BowTie { get; }
        public AcciMapModel AcciMap { get; }
        public StampModel Stamp { get; }

        public SystemicDocument(string caseId, bool isFictionalDemo, BowTieModel bowTie = null, AcciMapModel acciMap = null, StampModel stamp = null)
        {
            CaseId = caseId;
            IsFictionalDemo = isFictionalDemo;
            BowTie = bowTie;
            AcciMap = acciMap;
            Stamp = stamp;
        }

        /// <summary>
        /// 带校验的工厂（D03）：caseId 不符合 <see cref="EvidenceItem.IsValidCaseId"/> → sys_invalid_id。
        /// 公开构造器保留（兼容），非法 caseId 由 <see cref="Validate"/> 报告。
        /// </summary>
        public static Result<SystemicDocument> Create(string caseId, bool isFictionalDemo, BowTieModel bowTie = null, AcciMapModel acciMap = null, StampModel stamp = null)
        {
            if (!EvidenceItem.IsValidCaseId(caseId))
            {
                return Result<SystemicDocument>.Fail(SystemicErrors.InvalidId, "案件 ID 无效：" + caseId);
            }

            return Result<SystemicDocument>.Ok(new SystemicDocument(caseId, isFictionalDemo, bowTie, acciMap, stamp));
        }

        /// <summary>
        /// caseId 非法（与 Evidence 模块共用 <see cref="EvidenceItem.IsValidCaseId"/>，D03）→ sys_invalid_id；
        /// 三个模型分别校验后合并问题列表；三者皆空 → sys_empty_model。
        /// </summary>
        public SystemicValidation Validate(SystemicRefContext ctx = null)
        {
            var issues = new List<SystemicIssue>();
            if (!EvidenceItem.IsValidCaseId(CaseId))
            {
                issues.Add(new SystemicIssue(SystemicErrors.InvalidId, CaseId, "案件 ID 无效（与证据模块同一规则）"));
            }

            if (BowTie == null && AcciMap == null && Stamp == null)
            {
                issues.Add(new SystemicIssue(SystemicErrors.EmptyModel, CaseId, "文档不含任何模型"));
            }

            // W15.2：子模型的 sys_ref_not_checked 不直接合并，改为合并计数后每种 kind 只出一条。
            var notChecked = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (SystemicValidation sub in new[] { BowTie?.Validate(ctx), AcciMap?.Validate(ctx), Stamp?.Validate(ctx) })
            {
                if (sub == null)
                {
                    continue;
                }

                issues.AddRange(sub.Issues.Where(i => i.Code != SystemicErrors.RefNotChecked));
                foreach (var kv in sub.NotCheckedByKind)
                {
                    SystemicRules.Tally(notChecked, kv.Key, kv.Value);
                }
            }

            return new SystemicValidation(issues, notChecked);
        }

        // ------------------------------------------------------------------ 写

        public string ToJson()
        {
            var sb = new StringBuilder();
            sb.Append("{\"schema\":").Append(SystemicJson.Quote(Schema));
            sb.Append(",\"caseId\":").Append(SystemicJson.Quote(CaseId));
            sb.Append(",\"isFictionalDemo\":").Append(IsFictionalDemo ? "true" : "false");
            sb.Append(",\"bowTie\":");
            if (BowTie == null) sb.Append("null"); else WriteBowTie(sb, BowTie);
            sb.Append(",\"acciMap\":");
            if (AcciMap == null) sb.Append("null"); else WriteAcciMap(sb, AcciMap);
            sb.Append(",\"stamp\":");
            if (Stamp == null) sb.Append("null"); else WriteStamp(sb, Stamp);
            sb.Append('}');
            return sb.ToString();
        }

        private static void WriteElementCommon(StringBuilder sb, SystemicElement e)
        {
            sb.Append("\"id\":").Append(SystemicJson.Quote(e.Id));
            sb.Append(",\"label\":").Append(SystemicJson.Quote(e.Label));
            sb.Append(",\"strength\":").Append(SystemicJson.Quote(e.Strength.ToString()));
            sb.Append(",\"refs\":{\"evidence\":");
            WriteStrings(sb, e.Refs.EvidenceIds);
            sb.Append(",\"ecfc\":");
            WriteStrings(sb, e.Refs.EcfcNodeIds);
            sb.Append(",\"hfacs\":");
            WriteStrings(sb, e.Refs.HfacsFindingIds);
            sb.Append(",\"recommendations\":");
            WriteStrings(sb, e.Refs.RecommendationIds);
            foreach (string kind in e.Refs.Kinds.Where(k => !SystemicRefKinds.IsBuiltIn(k)))
            {
                sb.Append(',').Append(SystemicJson.Quote(RefKey(kind))).Append(':');
                WriteStrings(sb, e.Refs.Ids(kind));
            }

            sb.Append('}');
            if (e.ActorId != null)
            {
                sb.Append(",\"actorId\":").Append(SystemicJson.Quote(e.ActorId));
            }
        }

        /// <summary>非内置种类的 JSON 键：种类名首字母小写（camelCase）。</summary>
        private static string RefKey(string kind)
        {
            return char.ToLowerInvariant(kind[0]) + kind.Substring(1);
        }

        private static void WriteStrings(StringBuilder sb, IEnumerable<string> items)
        {
            sb.Append('[').Append(string.Join(",", items.Select(SystemicJson.Quote))).Append(']');
        }

        private static void WriteEdges(StringBuilder sb, IEnumerable<SystemicEdge> edges)
        {
            sb.Append('[').Append(string.Join(",", edges.Select(e => "[" + SystemicJson.Quote(e.FromId) + "," + SystemicJson.Quote(e.ToId) + "]"))).Append(']');
        }

        private static void WriteBowTie(StringBuilder sb, BowTieModel m)
        {
            sb.Append("{\"id\":").Append(SystemicJson.Quote(m.Id));
            sb.Append(",\"hazard\":").Append(SystemicJson.Quote(m.Hazard));
            sb.Append(",\"topEvent\":{");
            WriteElementCommon(sb, m.TopEvent);
            sb.Append("},\"elements\":[");
            bool first = true;
            foreach (BowTieElement e in m.Elements.Where(x => x.Kind != BowTieElementKind.TopEvent))
            {
                if (!first) sb.Append(',');
                first = false;
                sb.Append('{');
                WriteElementCommon(sb, e);
                sb.Append(",\"kind\":").Append(SystemicJson.Quote(e.Kind.ToString()));
                if (e.State.HasValue) sb.Append(",\"state\":").Append(SystemicJson.Quote(e.State.Value.ToString()));
                if (e.BarrierId != null) sb.Append(",\"barrierId\":").Append(SystemicJson.Quote(e.BarrierId));
                sb.Append('}');
            }

            sb.Append("],\"edges\":");
            WriteEdges(sb, m.Edges);
            sb.Append('}');
        }

        private static void WriteAcciMap(StringBuilder sb, AcciMapModel m)
        {
            sb.Append("{\"id\":").Append(SystemicJson.Quote(m.Id));
            sb.Append(",\"title\":").Append(SystemicJson.Quote(m.Title));
            sb.Append(",\"allowEnvironmentToCrew\":").Append(m.AllowEnvironmentToCrew ? "true" : "false");
            sb.Append(",\"nodes\":[");
            sb.Append(string.Join(",", m.Nodes.Select(n =>
            {
                var b = new StringBuilder("{");
                WriteElementCommon(b, n);
                b.Append(",\"level\":").Append(SystemicJson.Quote(n.Level.ToString())).Append('}');
                return b.ToString();
            })));
            sb.Append("],\"edges\":");
            WriteEdges(sb, m.Edges);
            if (m.InformationFlows.Count > 0)
            {
                sb.Append(",\"infoFlows\":");
                WriteEdges(sb, m.InformationFlows);
            }

            sb.Append('}');
        }

        private static void WriteStamp(StringBuilder sb, StampModel m)
        {
            sb.Append("{\"id\":").Append(SystemicJson.Quote(m.Id));
            sb.Append(",\"hazard\":").Append(SystemicJson.Quote(m.Hazard));
            sb.Append(",\"components\":[");
            sb.Append(string.Join(",", m.Components.Select(c => Obj(c, ",\"kind\":" + SystemicJson.Quote(c.Kind.ToString())))));
            sb.Append("],\"controlActions\":[");
            sb.Append(string.Join(",", m.ControlActions.Select(a => Obj(a, ",\"controller\":" + SystemicJson.Quote(a.ControllerId) + ",\"target\":" + SystemicJson.Quote(a.TargetId)))));
            sb.Append("],\"feedback\":[");
            sb.Append(string.Join(",", m.Feedback.Select(f => Obj(f, ",\"source\":" + SystemicJson.Quote(f.SourceId) + ",\"controller\":" + SystemicJson.Quote(f.ControllerId)))));
            sb.Append("],\"ucas\":[");
            sb.Append(string.Join(",", m.UnsafeControlActions.Select(u => Obj(u,
                ",\"controlAction\":" + SystemicJson.Quote(u.ControlActionId) + ",\"type\":" + SystemicJson.Quote(u.Type.ToString()) + ",\"context\":" + SystemicJson.Quote(u.Context)))));
            sb.Append("]}");
        }

        private static string Obj(SystemicElement e, string extra)
        {
            var b = new StringBuilder("{");
            WriteElementCommon(b, e);
            b.Append(extra).Append('}');
            return b.ToString();
        }

        // ------------------------------------------------------------------ 读

        private sealed class LoadException : Exception
        {
            public string Code { get; }

            public LoadException(string code, string message)
                : base(message)
            {
                Code = code;
            }
        }

        public static Result<SystemicDocument> FromJson(string json)
        {
            Result<object> parsed = SystemicJson.Parse(json);
            if (!parsed.IsSuccess)
            {
                return Result<SystemicDocument>.Fail(parsed.ErrorCode, parsed.ErrorMessage);
            }

            try
            {
                var root = AsObject(parsed.Value, "根");
                string schema = Str(root, "schema");
                if (schema != Schema)
                {
                    return Result<SystemicDocument>.Fail(SystemicErrors.JsonUnsupportedSchema, "不支持的 schema：" + schema);
                }

                string caseId = StrOrNull(root, "caseId");
                bool demo = Bool(root, "isFictionalDemo");
                BowTieModel bt = root.ContainsKey("bowTie") && root["bowTie"] != null ? ReadBowTie(AsObject(root["bowTie"], "bowTie")) : null;
                AcciMapModel am = root.ContainsKey("acciMap") && root["acciMap"] != null ? ReadAcciMap(AsObject(root["acciMap"], "acciMap")) : null;
                StampModel st = root.ContainsKey("stamp") && root["stamp"] != null ? ReadStamp(AsObject(root["stamp"], "stamp")) : null;
                return Result<SystemicDocument>.Ok(new SystemicDocument(caseId, demo, bt, am, st));
            }
            catch (LoadException ex)
            {
                return Result<SystemicDocument>.Fail(ex.Code, ex.Message);
            }
        }

        private static T Must<T>(Result<T> r)
        {
            if (!r.IsSuccess)
            {
                throw new LoadException(r.ErrorCode, r.ErrorMessage);
            }

            return r.Value;
        }

        private static BowTieModel ReadBowTie(Dictionary<string, object> o)
        {
            var top = AsObject(Req(o, "topEvent"), "topEvent");
            BowTieModel m = Must(BowTieModel.Create(Str(o, "id"), Str(o, "hazard"), Str(top, "id"), Str(top, "label"), Strength(top), Refs(top), Actor(top)));
            var escalation = new List<Dictionary<string, object>>();
            foreach (object item in Arr(o, "elements"))
            {
                var e = AsObject(item, "element");
                BowTieElementKind kind = EnumOf<BowTieElementKind>(e, "kind");
                string id = Str(e, "id");
                string label = Str(e, "label");
                switch (kind)
                {
                    case BowTieElementKind.Threat:
                        Must(m.AddThreat(id, label, Strength(e), Refs(e), Actor(e)));
                        break;
                    case BowTieElementKind.Consequence:
                        Must(m.AddConsequence(id, label, Strength(e), Refs(e), Actor(e)));
                        break;
                    case BowTieElementKind.PreventionBarrier:
                    case BowTieElementKind.MitigationBarrier:
                        Must(m.AddBarrier(id, label, kind, EnumOf<BarrierState>(e, "state"), Strength(e), Refs(e), Actor(e)));
                        break;
                    case BowTieElementKind.EscalationFactor:
                        escalation.Add(e); // A11：第二遍再挂，不依赖顺序
                        break;
                    default:
                        throw new LoadException(SystemicErrors.JsonInvalid, "elements 中不能再出现顶事件：" + id);
                }
            }

            foreach (var e in escalation)
            {
                Must(m.AddEscalationFactor(Str(e, "id"), Str(e, "label"), Str(e, "barrierId"), Strength(e), Refs(e), Actor(e)));
            }

            if (escalation.Count > 0)
            {
                // 恢复文件中的原始顺序，保证往返字节一致。
                m.RestoreOrder(Arr(o, "elements").Select(x => Str(AsObject(x, "element"), "id")).ToList());
            }

            foreach (var edge in Edges(o))
            {
                Must(m.Connect(edge.Key, edge.Value));
            }

            return m;
        }

        private static AcciMapModel ReadAcciMap(Dictionary<string, object> o)
        {
            AcciMapModel m = Must(AcciMapModel.Create(Str(o, "id"), Str(o, "title"), Bool(o, "allowEnvironmentToCrew")));
            foreach (object item in Arr(o, "nodes"))
            {
                var n = AsObject(item, "node");
                Must(m.AddNode(Str(n, "id"), Str(n, "label"), EnumOf<AcciMapLevel>(n, "level"), Strength(n), Refs(n), Actor(n)));
            }

            foreach (var edge in Edges(o))
            {
                Must(m.Connect(edge.Key, edge.Value));
            }

            if (o.ContainsKey("infoFlows") && o["infoFlows"] != null)
            {
                foreach (var edge in Edges(o, "infoFlows"))
                {
                    Must(m.ConnectInformationFlow(edge.Key, edge.Value));
                }
            }

            return m;
        }

        private static StampModel ReadStamp(Dictionary<string, object> o)
        {
            StampModel m = Must(StampModel.Create(Str(o, "id"), Str(o, "hazard")));
            foreach (object item in Arr(o, "components"))
            {
                var c = AsObject(item, "component");
                if (EnumOf<ControlComponentKind>(c, "kind") == ControlComponentKind.Controller)
                {
                    Must(m.AddController(Str(c, "id"), Str(c, "label"), Strength(c), Refs(c), Actor(c)));
                }
                else
                {
                    Must(m.AddControlledProcess(Str(c, "id"), Str(c, "label"), Strength(c), Refs(c), Actor(c)));
                }
            }

            foreach (object item in Arr(o, "controlActions"))
            {
                var a = AsObject(item, "controlAction");
                Must(m.AddControlAction(Str(a, "id"), Str(a, "label"), Str(a, "controller"), Str(a, "target"), Strength(a), Refs(a), Actor(a)));
            }

            foreach (object item in Arr(o, "feedback"))
            {
                var f = AsObject(item, "feedback");
                Must(m.AddFeedback(Str(f, "id"), Str(f, "label"), Str(f, "source"), Str(f, "controller"), Strength(f), Refs(f), Actor(f)));
            }

            foreach (object item in Arr(o, "ucas"))
            {
                var u = AsObject(item, "uca");
                Must(m.AddUnsafeControlAction(Str(u, "id"), Str(u, "label"), Str(u, "controlAction"), EnumOf<UcaType>(u, "type"), StrOrNull(u, "context"), Strength(u), Refs(u), Actor(u)));
            }

            return m;
        }

        private static object Req(Dictionary<string, object> o, string key)
        {
            object v;
            if (!o.TryGetValue(key, out v))
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "缺少字段 " + key);
            }

            return v;
        }

        private static Dictionary<string, object> AsObject(object v, string what)
        {
            var d = v as Dictionary<string, object>;
            if (d == null)
            {
                throw new LoadException(SystemicErrors.JsonInvalid, what + " 必须是对象");
            }

            return d;
        }

        private static string Str(Dictionary<string, object> o, string key)
        {
            var s = Req(o, key) as string;
            if (s == null)
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 必须是字符串");
            }

            return s;
        }

        private static string StrOrNull(Dictionary<string, object> o, string key)
        {
            object v;
            if (!o.TryGetValue(key, out v) || v == null)
            {
                return null;
            }

            var s = v as string;
            if (s == null)
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 必须是字符串或 null");
            }

            return s;
        }

        private static bool Bool(Dictionary<string, object> o, string key)
        {
            object v = Req(o, key);
            if (!(v is bool))
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 必须是布尔值");
            }

            return (bool)v;
        }

        private static List<object> Arr(Dictionary<string, object> o, string key)
        {
            var a = Req(o, key) as List<object>;
            if (a == null)
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 必须是数组");
            }

            return a;
        }

        private static IEnumerable<string> StrArr(Dictionary<string, object> o, string key)
        {
            object v;
            if (!o.TryGetValue(key, out v) || v == null)
            {
                return new string[0];
            }

            var a = v as List<object>;
            if (a == null || a.Any(x => !(x is string)))
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 必须是字符串数组");
            }

            return a.Cast<string>().ToArray();
        }

        private static IEnumerable<KeyValuePair<string, string>> Edges(Dictionary<string, object> o, string key = "edges")
        {
            var list = new List<KeyValuePair<string, string>>();
            foreach (object item in Arr(o, key))
            {
                var pair = item as List<object>;
                if (pair == null || pair.Count != 2 || !(pair[0] is string) || !(pair[1] is string))
                {
                    throw new LoadException(SystemicErrors.JsonInvalid, key + " 元素必须是 [from, to] 字符串对");
                }

                list.Add(new KeyValuePair<string, string>((string)pair[0], (string)pair[1]));
            }

            return list;
        }

        private static T EnumOf<T>(Dictionary<string, object> o, string key) where T : struct
        {
            string s = Str(o, key);
            if (!Enum.GetNames(typeof(T)).Contains(s, StringComparer.Ordinal))
            {
                throw new LoadException(SystemicErrors.JsonInvalid, "字段 " + key + " 取值未知：" + s);
            }

            return (T)Enum.Parse(typeof(T), s);
        }

        private static EvidenceStrength Strength(Dictionary<string, object> o)
        {
            return EnumOf<EvidenceStrength>(o, "strength");
        }

        private static SystemicRefs Refs(Dictionary<string, object> o)
        {
            object v;
            if (!o.TryGetValue("refs", out v) || v == null)
            {
                return SystemicRefs.None;
            }

            var r = AsObject(v, "refs");
            var typed = new List<SystemicRef>();
            AddTyped(typed, SystemicRefKinds.Evidence, StrArr(r, "evidence"));
            AddTyped(typed, SystemicRefKinds.Ecfc, StrArr(r, "ecfc"));
            AddTyped(typed, SystemicRefKinds.Hfacs, StrArr(r, "hfacs"));
            AddTyped(typed, SystemicRefKinds.Recommendation, StrArr(r, "recommendations"));
            foreach (string key in r.Keys.Where(k => !LegacyRefKeys.Contains(k)).ToArray())
            {
                string kind = key.Length == 0 ? key : char.ToUpperInvariant(key[0]) + key.Substring(1);
                if (!char.IsLower(key.Length == 0 ? 'X' : key[0]) || !SystemicRefKinds.IsValidKind(kind) || SystemicRefKinds.IsBuiltIn(kind))
                {
                    throw new LoadException(SystemicErrors.JsonInvalid, "refs 键无效：" + key);
                }

                AddTyped(typed, kind, StrArr(r, key));
            }

            return new SystemicRefs(typed);
        }

        private static readonly HashSet<string> LegacyRefKeys = new HashSet<string>(new[] { "evidence", "ecfc", "hfacs", "recommendations" }, StringComparer.Ordinal);

        private static void AddTyped(List<SystemicRef> list, string kind, IEnumerable<string> ids)
        {
            list.AddRange(ids.Where(x => !string.IsNullOrWhiteSpace(x)).Select(x => new SystemicRef(kind, x)));
        }

        private static string Actor(Dictionary<string, object> o)
        {
            return StrOrNull(o, "actorId");
        }
    }
}
