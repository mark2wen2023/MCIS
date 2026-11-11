using System;
using System.Collections.Generic;
using System.Linq;
using Mcis.Core;
using Mcis.Domain.HumanFactors;

namespace Mcis.Domain.Systemic
{
    public enum ControlComponentKind
    {
        /// <summary>控制器（人或组织，如 VTS、船长、值班驾驶员、公司）。</summary>
        Controller = 0,

        /// <summary>受控过程（如船舶操纵运动）。</summary>
        ControlledProcess = 1
    }

    /// <summary>不安全控制动作（UCA）四类（STPA/CAST）。</summary>
    public enum UcaType
    {
        /// <summary>需要时未提供。</summary>
        NotProvided = 0,

        /// <summary>提供了但导致危险。</summary>
        ProvidedCausesHazard = 1,

        /// <summary>时机过早/过迟或顺序错误。</summary>
        WrongTimingOrOrder = 2,

        /// <summary>过早停止或持续过久。</summary>
        StoppedTooSoonOrAppliedTooLong = 3
    }

    public sealed class ControlComponent : SystemicElement
    {
        public ControlComponentKind Kind { get; }

        internal ControlComponent(string id, string label, ControlComponentKind kind, EvidenceStrength strength, SystemicRefs refs, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            Kind = kind;
        }
    }

    /// <summary>控制动作：控制器 → 目标（受控过程或下级控制器）。</summary>
    public sealed class ControlAction : SystemicElement
    {
        public string ControllerId { get; }
        public string TargetId { get; }

        internal ControlAction(string id, string label, string controllerId, string targetId, EvidenceStrength strength, SystemicRefs refs, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            ControllerId = controllerId;
            TargetId = targetId;
        }
    }

    /// <summary>反馈：来源（受控过程或下级控制器）→ 控制器。</summary>
    public sealed class FeedbackLink : SystemicElement
    {
        public string SourceId { get; }
        public string ControllerId { get; }

        internal FeedbackLink(string id, string label, string sourceId, string controllerId, EvidenceStrength strength, SystemicRefs refs, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            SourceId = sourceId;
            ControllerId = controllerId;
        }
    }

    public sealed class UnsafeControlAction : SystemicElement
    {
        public string ControlActionId { get; }
        public UcaType Type { get; internal set; }

        /// <summary>情境（何时/何种条件下不安全）。必填（A8）。</summary>
        public string Context { get; internal set; }

        internal UnsafeControlAction(string id, string label, string controlActionId, UcaType type, string context, EvidenceStrength strength, SystemicRefs refs, string actorId)
            : base(id, label, strength, refs, actorId)
        {
            ControlActionId = controlActionId;
            Type = type;
            Context = context ?? string.Empty;
        }
    }

    /// <summary>
    /// STAMP/CAST 控制结构。所有元素共用一个 ID 空间。
    /// 控制动作的发出方必须是控制器；控制动作图（控制器 → 目标）不得成环（层级结构）；
    /// 反馈的接收方必须是控制器，反馈方向与控制方向相反，不参与成环判断。
    /// </summary>
    public sealed class StampModel
    {
        private readonly List<ControlComponent> _components = new List<ControlComponent>();
        private readonly List<ControlAction> _actions = new List<ControlAction>();
        private readonly List<FeedbackLink> _feedback = new List<FeedbackLink>();
        private readonly List<UnsafeControlAction> _ucas = new List<UnsafeControlAction>();
        private readonly Dictionary<string, SystemicElement> _byId = new Dictionary<string, SystemicElement>(StringComparer.Ordinal);
        private Dictionary<string, List<string>> _controlAdj = new Dictionary<string, List<string>>(StringComparer.Ordinal);

        public string Id { get; }

        /// <summary>系统级危险/损失（如“两船在窄航道内碰撞”）。</summary>
        public string Hazard { get; }

        private StampModel(string id, string hazard)
        {
            Id = id;
            Hazard = hazard;
        }

        public static Result<StampModel> Create(string id, string hazard)
        {
            if (!SystemicRules.IsValidId(id))
            {
                return Result<StampModel>.Fail(SystemicErrors.InvalidId, "模型 ID 无效：" + id);
            }

            if (string.IsNullOrWhiteSpace(hazard))
            {
                return Result<StampModel>.Fail(SystemicErrors.InvalidArgument, "危险不能为空");
            }

            return Result<StampModel>.Ok(new StampModel(id, hazard));
        }

        // 只读视图（D01）：强转 IList 后修改会抛 NotSupportedException。
        public IReadOnlyList<ControlComponent> Components { get { return _components.AsReadOnly(); } }
        public IReadOnlyList<ControlAction> ControlActions { get { return _actions.AsReadOnly(); } }
        public IReadOnlyList<FeedbackLink> Feedback { get { return _feedback.AsReadOnly(); } }
        public IReadOnlyList<UnsafeControlAction> UnsafeControlActions { get { return _ucas.AsReadOnly(); } }

        public IEnumerable<SystemicElement> AllElements
        {
            get { return _components.Cast<SystemicElement>().Concat(_actions).Concat(_feedback).Concat(_ucas); }
        }

        public SystemicElement Get(string id)
        {
            SystemicElement e;
            return id != null && _byId.TryGetValue(id, out e) ? e : null;
        }

        public IReadOnlyList<UnsafeControlAction> UcasOfType(UcaType type)
        {
            return _ucas.Where(u => u.Type == type).ToList().AsReadOnly();
        }

        public Result<ControlComponent> AddController(string id, string label, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            return AddComponent(id, label, ControlComponentKind.Controller, strength, refs, actorId);
        }

        public Result<ControlComponent> AddControlledProcess(string id, string label, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            return AddComponent(id, label, ControlComponentKind.ControlledProcess, strength, refs, actorId);
        }

        /// <summary>
        /// 添加控制动作。controller/target 不存在 → sys_unknown_node；发出方不是控制器 → sys_invalid_edge；
        /// target == controller 或使控制层级成环 → sys_cycle。
        /// </summary>
        public Result<ControlAction> AddControlAction(string id, string label, string controllerId, string targetId, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            Result<bool> ok = CheckNew(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<ControlAction>(ok);
            }

            ControlComponent c = Get(controllerId) as ControlComponent;
            ControlComponent t = Get(targetId) as ControlComponent;
            if (c == null || t == null)
            {
                return Result<ControlAction>.Fail(SystemicErrors.UnknownNode, "控制器或目标不存在：" + controllerId + " → " + targetId);
            }

            if (c.Kind != ControlComponentKind.Controller)
            {
                return Result<ControlAction>.Fail(SystemicErrors.InvalidEdge, "控制动作只能由控制器发出：" + controllerId);
            }

            if (controllerId == targetId || SystemicRules.Reaches(_controlAdj, targetId, controllerId))
            {
                return Result<ControlAction>.Fail(SystemicErrors.Cycle, "控制层级成环：" + controllerId + " → " + targetId);
            }

            var a = new ControlAction(id, label, controllerId, targetId, strength, refs, actorId);
            _actions.Add(a);
            _byId[id] = a;
            SystemicRules.AddEdge(_controlAdj, controllerId, targetId);
            return Result<ControlAction>.Ok(a);
        }

        /// <summary>添加反馈。不存在 → sys_unknown_node；接收方不是控制器 → sys_invalid_edge；source == controller → sys_cycle。</summary>
        public Result<FeedbackLink> AddFeedback(string id, string label, string sourceId, string controllerId, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            Result<bool> ok = CheckNew(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<FeedbackLink>(ok);
            }

            ControlComponent s = Get(sourceId) as ControlComponent;
            ControlComponent c = Get(controllerId) as ControlComponent;
            if (s == null || c == null)
            {
                return Result<FeedbackLink>.Fail(SystemicErrors.UnknownNode, "反馈来源或控制器不存在：" + sourceId + " → " + controllerId);
            }

            if (c.Kind != ControlComponentKind.Controller)
            {
                return Result<FeedbackLink>.Fail(SystemicErrors.InvalidEdge, "反馈只能送达控制器：" + controllerId);
            }

            if (sourceId == controllerId)
            {
                return Result<FeedbackLink>.Fail(SystemicErrors.Cycle, "反馈不能指向自身：" + sourceId);
            }

            var f = new FeedbackLink(id, label, sourceId, controllerId, strength, refs, actorId);
            _feedback.Add(f);
            _byId[id] = f;
            return Result<FeedbackLink>.Ok(f);
        }

        /// <summary>添加 UCA。控制动作不存在 → sys_unknown_node；类型无效或情境为空（A8）→ sys_invalid_argument。</summary>
        public Result<UnsafeControlAction> AddUnsafeControlAction(string id, string label, string controlActionId, UcaType type, string context, EvidenceStrength strength, SystemicRefs refs = null, string actorId = null)
        {
            if (!Enum.IsDefined(typeof(UcaType), type))
            {
                return Result<UnsafeControlAction>.Fail(SystemicErrors.InvalidArgument, "未知 UCA 类型：" + (int)type);
            }

            Result<bool> ok = CheckNew(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<UnsafeControlAction>(ok);
            }

            if (!(Get(controlActionId) is ControlAction))
            {
                return Result<UnsafeControlAction>.Fail(SystemicErrors.UnknownNode, "控制动作不存在：" + controlActionId);
            }

            if (string.IsNullOrWhiteSpace(context))
            {
                return Result<UnsafeControlAction>.Fail(SystemicErrors.InvalidArgument, "UCA 情境不能为空（何时/何种条件下不安全）：" + id);
            }

            var u = new UnsafeControlAction(id, label, controlActionId, type, context, strength, refs, actorId);
            _ucas.Add(u);
            _byId[id] = u;
            return Result<UnsafeControlAction>.Ok(u);
        }

        /// <summary>
        /// 整体校验：没有控制动作 → sys_empty_model；
        /// 控制动作没有从目标回到该控制器的反馈 → sys_missing_feedback（CAST 典型发现：控制回路不闭合）；
        /// 受控过程没有任何控制动作作用 → sys_isolated_node；
        /// 控制器既不发出/接收控制动作，也不发出/接收反馈 → 警告 sys_isolated_controller（A7，不影响 IsValid）；
        /// UCA 情境为空 → sys_invalid_argument（A8，防御性复查）；
        /// 另按 ctx 校验引用、Strong/Moderate 必须有证据。
        /// </summary>
        public SystemicValidation Validate(SystemicRefContext ctx = null)
        {
            var issues = new List<SystemicIssue>();
            if (_actions.Count == 0)
            {
                issues.Add(new SystemicIssue(SystemicErrors.EmptyModel, Id, "控制结构没有控制动作"));
            }

            foreach (ControlAction a in _actions)
            {
                if (!_feedback.Any(f => f.SourceId == a.TargetId && f.ControllerId == a.ControllerId))
                {
                    issues.Add(new SystemicIssue(SystemicErrors.MissingFeedback, a.Id, "控制回路缺少反馈：" + a.TargetId + " → " + a.ControllerId));
                }
            }

            foreach (ControlComponent p in _components.Where(c => c.Kind == ControlComponentKind.ControlledProcess))
            {
                if (!_actions.Any(a => a.TargetId == p.Id))
                {
                    issues.Add(new SystemicIssue(SystemicErrors.IsolatedNode, p.Id, "受控过程没有任何控制动作：" + p.Label));
                }
            }

            foreach (ControlComponent c in _components.Where(c => c.Kind == ControlComponentKind.Controller))
            {
                bool linked = _actions.Any(a => a.ControllerId == c.Id || a.TargetId == c.Id)
                    || _feedback.Any(f => f.SourceId == c.Id || f.ControllerId == c.Id);
                if (!linked)
                {
                    issues.Add(new SystemicIssue(SystemicErrors.IsolatedController, c.Id, "控制器没有任何控制动作或反馈：" + c.Label, SystemicIssueSeverity.Warning));
                }
            }

            foreach (UnsafeControlAction u in _ucas.Where(u => string.IsNullOrWhiteSpace(u.Context)))
            {
                issues.Add(new SystemicIssue(SystemicErrors.InvalidArgument, u.Id, "UCA 情境为空"));
            }

            var notChecked = new Dictionary<string, int>(StringComparer.Ordinal);
            SystemicRules.CheckElements(AllElements, ctx, issues, notChecked);
            return new SystemicValidation(issues, notChecked);
        }

        /// <summary>
        /// 删除元素（A9），级联：删除控制组件 → 一并删除以它为发出方/目标的控制动作、以它为来源/接收方的反馈；
        /// 删除控制动作 → 一并删除其 UCA。不存在 → sys_unknown_node。返回实际删除的 ID（本元素在首位）。
        /// </summary>
        public Result<IReadOnlyList<string>> RemoveElement(string id)
        {
            SystemicElement e = Get(id);
            if (e == null)
            {
                return Result<IReadOnlyList<string>>.Fail(SystemicErrors.UnknownNode, "元素不存在：" + id);
            }

            var removed = new List<string> { id };
            var actionIds = new HashSet<string>(StringComparer.Ordinal);
            if (e is ControlComponent)
            {
                foreach (ControlAction a in _actions.Where(a => a.ControllerId == id || a.TargetId == id))
                {
                    actionIds.Add(a.Id);
                    removed.Add(a.Id);
                }

                removed.AddRange(_feedback.Where(f => f.SourceId == id || f.ControllerId == id).Select(f => f.Id));
            }
            else if (e is ControlAction)
            {
                actionIds.Add(id);
            }

            removed.AddRange(_ucas.Where(u => actionIds.Contains(u.ControlActionId) && u.Id != id).Select(u => u.Id));
            var set = new HashSet<string>(removed, StringComparer.Ordinal);
            _components.RemoveAll(x => set.Contains(x.Id));
            _actions.RemoveAll(x => set.Contains(x.Id));
            _feedback.RemoveAll(x => set.Contains(x.Id));
            _ucas.RemoveAll(x => set.Contains(x.Id));
            foreach (string r in removed)
            {
                _byId.Remove(r);
            }

            _controlAdj = SystemicRules.BuildAdj(_actions.Select(a => new SystemicEdge(a.ControllerId, a.TargetId)));
            return Result<IReadOnlyList<string>>.Ok(removed.AsReadOnly());
        }

        /// <summary>修改任一元素的公共字段（A9）：给出的字段才改，按新增规则校验（含 A6）。clearActor = true 清除责任方。</summary>
        public Result<SystemicElement> UpdateElement(string id, string label = null, EvidenceStrength? strength = null, SystemicRefs refs = null, string actorId = null, bool clearActor = false)
        {
            SystemicElement e = Get(id);
            if (e == null)
            {
                return Result<SystemicElement>.Fail(SystemicErrors.UnknownNode, "元素不存在：" + id);
            }

            Result<bool> ok = SystemicRules.ApplyUpdate(e, label, strength, refs, actorId, clearActor);
            return ok.IsSuccess ? Result<SystemicElement>.Ok(e) : SystemicRules.Fail<SystemicElement>(ok);
        }

        /// <summary>修改 UCA 的类型 / 情境（A9）。情境给出时不得为空白（A8）；类型须有效。</summary>
        public Result<UnsafeControlAction> UpdateUca(string id, UcaType? type = null, string context = null)
        {
            UnsafeControlAction u = Get(id) as UnsafeControlAction;
            if (u == null)
            {
                return Result<UnsafeControlAction>.Fail(SystemicErrors.UnknownNode, "UCA 不存在：" + id);
            }

            if ((type.HasValue && !Enum.IsDefined(typeof(UcaType), type.Value)) || (context != null && string.IsNullOrWhiteSpace(context)))
            {
                return Result<UnsafeControlAction>.Fail(SystemicErrors.InvalidArgument, "UCA 类型无效或情境为空：" + id);
            }

            u.Type = type ?? u.Type;
            u.Context = context ?? u.Context;
            return Result<UnsafeControlAction>.Ok(u);
        }

        private Result<ControlComponent> AddComponent(string id, string label, ControlComponentKind kind, EvidenceStrength strength, SystemicRefs refs, string actorId)
        {
            Result<bool> ok = CheckNew(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return SystemicRules.Fail<ControlComponent>(ok);
            }

            var c = new ControlComponent(id, label, kind, strength, refs, actorId);
            _components.Add(c);
            _byId[id] = c;
            return Result<ControlComponent>.Ok(c);
        }

        private Result<bool> CheckNew(string id, string label, EvidenceStrength strength, SystemicRefs refs, string actorId)
        {
            Result<bool> ok = SystemicRules.CheckElement(id, label, strength, refs, actorId);
            if (!ok.IsSuccess)
            {
                return ok;
            }

            if (_byId.ContainsKey(id))
            {
                return Result<bool>.Fail(SystemicErrors.DuplicateId, "ID 重复：" + id);
            }

            return Result<bool>.Ok(true);
        }
    }
}
