using System;
using System.Collections.Generic;

namespace Mcis.Core.Commands
{
    /// <summary>可撤销的领域操作命令（对应 ARCHITECTURE 6.2 节）。</summary>
    public interface IReversibleCommand
    {
        /// <summary>命令显示名称，如“恢复剔除的 AIS 样本 #1042”。</summary>
        string CommandName { get; }

        /// <summary>审计类别：TrackClean / ManualDraw / Environment / ECFC / Threshold。</summary>
        string AuditCategory { get; }

        /// <summary>执行前取值摘要。</summary>
        string BeforeValueSummary { get; }

        /// <summary>执行后取值摘要。</summary>
        string AfterValueSummary { get; }

        void Execute();

        void Undo();
    }

    /// <summary>简单的委托实现，便于单元测试与一次性封装。</summary>
    public sealed class DelegateCommand : IReversibleCommand
    {
        private readonly Action _execute;
        private readonly Action _undo;

        public string CommandName { get; }
        public string AuditCategory { get; }
        public string BeforeValueSummary { get; }
        public string AfterValueSummary { get; }

        public DelegateCommand(
            string commandName,
            string auditCategory,
            string beforeValueSummary,
            string afterValueSummary,
            Action execute,
            Action undo)
        {
            CommandName = commandName ?? string.Empty;
            AuditCategory = auditCategory ?? string.Empty;
            BeforeValueSummary = beforeValueSummary ?? string.Empty;
            AfterValueSummary = afterValueSummary ?? string.Empty;
            _execute = execute ?? throw new ArgumentNullException(nameof(execute));
            _undo = undo ?? throw new ArgumentNullException(nameof(undo));
        }

        public void Execute()
        {
            _execute();
        }

        public void Undo()
        {
            _undo();
        }
    }

    /// <summary>撤销/重做历史栈，执行时可选地向审计日志追加记录。</summary>
    public sealed class CommandHistory
    {
        private readonly Stack<IReversibleCommand> _undo = new Stack<IReversibleCommand>();
        private readonly Stack<IReversibleCommand> _redo = new Stack<IReversibleCommand>();
        private readonly Action<IReversibleCommand, string> _onExecuted;

        public CommandHistory(Action<IReversibleCommand, string> onExecuted = null)
        {
            _onExecuted = onExecuted;
        }

        public int UndoCount { get { return _undo.Count; } }
        public int RedoCount { get { return _redo.Count; } }
        public bool CanUndo { get { return _undo.Count > 0; } }
        public bool CanRedo { get { return _redo.Count > 0; } }

        public IReversibleCommand PeekUndo()
        {
            return _undo.Count > 0 ? _undo.Peek() : null;
        }

        /// <summary>执行命令，压入撤销栈并清空重做栈。</summary>
        public void Execute(IReversibleCommand command)
        {
            if (command == null)
            {
                throw new ArgumentNullException(nameof(command));
            }

            command.Execute();
            _undo.Push(command);
            _redo.Clear();
            if (_onExecuted != null)
            {
                _onExecuted(command, "Execute");
            }
        }

        public bool Undo()
        {
            if (_undo.Count == 0)
            {
                return false;
            }

            IReversibleCommand cmd = _undo.Pop();
            cmd.Undo();
            _redo.Push(cmd);
            if (_onExecuted != null)
            {
                _onExecuted(cmd, "Undo");
            }

            return true;
        }

        public bool Redo()
        {
            if (_redo.Count == 0)
            {
                return false;
            }

            IReversibleCommand cmd = _redo.Pop();
            cmd.Execute();
            _undo.Push(cmd);
            if (_onExecuted != null)
            {
                _onExecuted(cmd, "Redo");
            }

            return true;
        }

        public void Clear()
        {
            _undo.Clear();
            _redo.Clear();
        }
    }
}
