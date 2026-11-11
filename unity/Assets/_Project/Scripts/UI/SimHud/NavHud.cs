using System;
using System.Globalization;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    /// <summary>
    /// 航行遥测与 DCPA/TCPA 碰撞风险 HUD 视图组件（对应 ARCHITECTURE.md 4.5.6 与 9.2 节，目标 Unity 6.0 LTS）。
    /// 显示双船度分格式经纬度、SOG、COG、HDG 以及 DCPA/TCPA 与三级风险状态类（risk-safe / risk-warning / risk-danger）。
    /// </summary>
    [UxmlElement]
    public partial class NavHud : VisualElement
    {
        /// <summary>安全风险等级 USS 类名。</summary>
        public const string RiskSafeClass = "risk-safe";
        /// <summary>警告风险等级 USS 类名。</summary>
        public const string RiskWarningClass = "risk-warning";
        /// <summary>危险风险等级 USS 类名。</summary>
        public const string RiskDangerClass = "risk-danger";

        private VisualElement _cpaPanel;
        private Label _ownTitleLabel;
        private Label _ownBadgeLabel;
        private Label _ownPosLabel;
        private Label _ownSogLabel;
        private Label _ownCogLabel;
        private Label _ownHdgLabel;
        private Label _ownProvLabel;

        private Label _targetTitleLabel;
        private Label _targetBadgeLabel;
        private Label _targetPosLabel;
        private Label _targetSogLabel;
        private Label _targetCogLabel;
        private Label _targetHdgLabel;
        private Label _targetProvLabel;

        private Label _cpaRiskBadge;
        private Label _dcpaValLabel;
        private Label _tcpaValLabel;
        private Label _distValLabel;
        private Label _relVelValLabel;
        private Label _simClockLabel;

        private bool _isBound;

        /// <summary>构造航行数据 HUD 元素。</summary>
        public NavHud()
        {
            AddToClassList("nav-hud-root");
            RegisterCallback<AttachToPanelEvent>(OnAttachToPanel);
        }

        private void OnAttachToPanel(AttachToPanelEvent evt)
        {
            EnsureBound();
        }

        /// <summary>绑定现有 UXML 节点；若当前为空容器则自动按标准结构构建子元素。</summary>
        public void EnsureBound()
        {
            if (_isBound && _ownPosLabel != null)
            {
                return;
            }

            QueryElements();
            if (_ownPosLabel == null)
            {
                BuildFallbackHierarchy();
                QueryElements();
            }

            _isBound = true;
        }

        /// <summary>设置本船与目标船标题及状态徽章。</summary>
        public void SetVesselHeaders(
            string ownTitle,
            string ownStatusBadge,
            string targetTitle,
            string targetStatusBadge)
        {
            EnsureBound();
            if (_ownTitleLabel != null && !string.IsNullOrEmpty(ownTitle))
                _ownTitleLabel.text = ownTitle;
            if (_ownBadgeLabel != null && !string.IsNullOrEmpty(ownStatusBadge))
                _ownBadgeLabel.text = ownStatusBadge;
            if (_targetTitleLabel != null && !string.IsNullOrEmpty(targetTitle))
                _targetTitleLabel.text = targetTitle;
            if (_targetBadgeLabel != null && !string.IsNullOrEmpty(targetStatusBadge))
                _targetBadgeLabel.text = targetStatusBadge;
        }

        /// <summary>刷新本船运动学遥测显示（经纬度度分格式、SOG、COG、HDG、来源标记）。</summary>
        public void UpdateOwnVessel(TrackSample sample)
        {
            EnsureBound();
            ApplyVesselSample(sample, _ownPosLabel, _ownSogLabel, _ownCogLabel, _ownHdgLabel, _ownProvLabel);
        }

        /// <summary>刷新目标船运动学遥测显示（经纬度度分格式、SOG、COG、HDG、来源标记）。</summary>
        public void UpdateTargetVessel(TrackSample sample)
        {
            EnsureBound();
            ApplyVesselSample(sample, _targetPosLabel, _targetSogLabel, _targetCogLabel, _targetHdgLabel, _targetProvLabel);
        }

        /// <summary>刷新 DCPA/TCPA 数值、风险等级 USS 类（risk-safe / risk-warning / risk-danger）与仿真时间戳。</summary>
        public void UpdateCpa(CpaResult cpa, SimTime simTime, DateTimeOffset caseEpochUtc, int displayTimeZoneOffsetMinutes = 480)
        {
            EnsureBound();

            if (_dcpaValLabel != null)
            {
                _dcpaValLabel.text = string.Format(CultureInfo.InvariantCulture, "{0:0.00} nm", cpa.DcpaNm);
            }

            if (_tcpaValLabel != null)
            {
                if (cpa.IsDegenerate)
                {
                    _tcpaValLabel.text = "∞ min";
                }
                else
                {
                    _tcpaValLabel.text = string.Format(CultureInfo.InvariantCulture, "{0:0.00} min", cpa.TcpaMin);
                }
            }

            if (_distValLabel != null)
            {
                _distValLabel.text = string.Format(CultureInfo.InvariantCulture, "{0:0.00} nm", cpa.CurrentDistanceNm);
            }

            if (_relVelValLabel != null)
            {
                double relSpeedKn = cpa.RelativeSpeedMps / HudFormatters.MetersPerSecondPerKnot;
                _relVelValLabel.text = string.Format(
                    CultureInfo.InvariantCulture,
                    "{0:0.0}kn / {1:000}°",
                    relSpeedKn,
                    cpa.TrueBearingDeg);
            }

            if (_simClockLabel != null)
            {
                DateTimeOffset displayTime = simTime.ToUtc(caseEpochUtc).ToOffset(TimeSpan.FromMinutes(displayTimeZoneOffsetMinutes));
                _simClockLabel.text = displayTime.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
            }

            ApplyRiskLevelClasses(cpa.RiskLevel);
        }

        /// <summary>根据风险等级切换 risk-safe / risk-warning / risk-danger 样式类与徽章文本。</summary>
        public void ApplyRiskLevelClasses(RiskLevel level)
        {
            EnsureBound();
            VisualElement targetPanel = _cpaPanel ?? this;

            targetPanel.RemoveFromClassList(RiskSafeClass);
            targetPanel.RemoveFromClassList(RiskWarningClass);
            targetPanel.RemoveFromClassList(RiskDangerClass);

            RemoveFromClassList(RiskSafeClass);
            RemoveFromClassList(RiskWarningClass);
            RemoveFromClassList(RiskDangerClass);

            string activeClass = level == RiskLevel.Danger
                ? RiskDangerClass
                : (level == RiskLevel.Warning ? RiskWarningClass : RiskSafeClass);

            targetPanel.AddToClassList(activeClass);
            AddToClassList(activeClass);

            if (_cpaRiskBadge != null)
            {
                _cpaRiskBadge.RemoveFromClassList("mcis-badge-cyan");
                _cpaRiskBadge.RemoveFromClassList("mcis-badge-amber");
                _cpaRiskBadge.RemoveFromClassList("mcis-badge-danger");

                switch (level)
                {
                    case RiskLevel.Danger:
                        _cpaRiskBadge.text = "DANGER · 紧迫碰撞危险";
                        _cpaRiskBadge.AddToClassList("mcis-badge-danger");
                        break;
                    case RiskLevel.Warning:
                        _cpaRiskBadge.text = "WARNING · 警戒态势";
                        _cpaRiskBadge.AddToClassList("mcis-badge-amber");
                        break;
                    default:
                        _cpaRiskBadge.text = "SAFE · 安全态势";
                        _cpaRiskBadge.AddToClassList("mcis-badge-cyan");
                        break;
                }
            }
        }
    }
}
