using Mcis.Domain.Common;
using Mcis.Domain.Models;
using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    public partial class NavHud
    {
        private void QueryElements()
        {
            _cpaPanel = this.Q<VisualElement>("cpa-hud-panel");

            _ownTitleLabel = this.Q<Label>("own-ship-title");
            _ownBadgeLabel = this.Q<Label>("own-ship-badge");
            _ownPosLabel = this.Q<Label>("own-pos-val");
            _ownSogLabel = this.Q<Label>("own-sog-val");
            _ownCogLabel = this.Q<Label>("own-cog-val");
            _ownHdgLabel = this.Q<Label>("own-hdg-val");
            _ownProvLabel = this.Q<Label>("own-prov-val");

            _targetTitleLabel = this.Q<Label>("target-ship-title");
            _targetBadgeLabel = this.Q<Label>("target-ship-badge");
            _targetPosLabel = this.Q<Label>("target-pos-val");
            _targetSogLabel = this.Q<Label>("target-sog-val");
            _targetCogLabel = this.Q<Label>("target-cog-val");
            _targetHdgLabel = this.Q<Label>("target-hdg-val");
            _targetProvLabel = this.Q<Label>("target-prov-val");

            _cpaRiskBadge = this.Q<Label>("cpa-risk-badge");
            _dcpaValLabel = this.Q<Label>("hud-dcpa-val");
            _tcpaValLabel = this.Q<Label>("hud-tcpa-val");
            _distValLabel = this.Q<Label>("hud-dist-val");
            _relVelValLabel = this.Q<Label>("hud-relv-val");
            _simClockLabel = this.Q<Label>("hud-sim-clock");
        }

        private static void ApplyVesselSample(
            TrackSample sample,
            Label posLabel,
            Label sogLabel,
            Label cogLabel,
            Label hdgLabel,
            Label provLabel)
        {
            if (posLabel != null)
                posLabel.text = HudFormatters.FormatGeoDegMin(sample.Geo);
            if (sogLabel != null)
                sogLabel.text = HudFormatters.FormatSogKnots(sample.SogMps);
            if (cogLabel != null)
                cogLabel.text = HudFormatters.FormatAngleDeg(sample.CogDeg);
            if (hdgLabel != null)
                hdgLabel.text = HudFormatters.FormatAngleDeg(sample.HdgDeg);
            if (provLabel != null)
                provLabel.text = FormatProvenance(sample.Provenance);
        }

        private static string FormatProvenance(SampleProvenance provenance)
        {
            switch (provenance)
            {
                case SampleProvenance.Measured:
                    return "AIS 实测";
                case SampleProvenance.Interpolated:
                    return "Hermite 插值";
                case SampleProvenance.LowConfidence:
                    return "缺口内插";
                case SampleProvenance.DeadReckoned:
                    return "DR 推算";
                case SampleProvenance.ManualDrawn:
                    return "手绘样条";
                case SampleProvenance.Presumed:
                    return "推定数据";
                default:
                    return "未知";
            }
        }

        private void BuildFallbackHierarchy()
        {
            VisualElement leftStack = new VisualElement { name = "nav-hud-left" };
            leftStack.AddToClassList("nav-hud-left-stack");

            leftStack.Add(CreateShipCard(
                "own-ship-card", "own-ship",
                "own-ship-title", "LILY 轮 (本船 / 散货船)", "hud-ship-title-own",
                "own-ship-badge", "压载出港", "mcis-badge-cyan",
                "own-pos-val", "own-sog-val", "own-cog-val", "own-hdg-val", "own-prov-val"));

            leftStack.Add(CreateShipCard(
                "target-ship-card", "target-ship",
                "target-ship-title", "MARY 轮 (他船 / 集装箱船)", "hud-ship-title-target",
                "target-ship-badge", "满载进港", "mcis-badge-amber",
                "target-pos-val", "target-sog-val", "target-cog-val", "target-hdg-val", "target-prov-val"));

            VisualElement cpaPanel = new VisualElement { name = "cpa-hud-panel" };
            cpaPanel.AddToClassList("cpa-hud-panel");
            cpaPanel.AddToClassList(RiskSafeClass);

            VisualElement headerRow = new VisualElement();
            headerRow.AddToClassList("cpa-header-row");
            VisualElement headerLeft = new VisualElement();
            headerLeft.AddToClassList("cpa-header-left");
            Label title = new Label("ARPA / 会遇风险实时解算 (论文 3.4 节)");
            title.AddToClassList("cpa-panel-title");
            Label demoBadge = new Label("示例数据（虚构）");
            demoBadge.AddToClassList("mcis-badge");
            demoBadge.AddToClassList("mcis-badge-amber");
            headerLeft.Add(title);
            headerLeft.Add(demoBadge);

            Label riskBadge = new Label("SAFE · 安全态势") { name = "cpa-risk-badge" };
            riskBadge.AddToClassList("mcis-badge");
            riskBadge.AddToClassList("mcis-badge-cyan");
            headerRow.Add(headerLeft);
            headerRow.Add(riskBadge);

            VisualElement metricsRow = new VisualElement();
            metricsRow.AddToClassList("cpa-metrics-row");
            metricsRow.Add(CreateMetricBox("DCPA (最近会遇距离)", "hud-dcpa-val", "0.00 nm", true, false));
            metricsRow.Add(CreateMetricBox("TCPA (最近会遇时间)", "hud-tcpa-val", "0.00 min", true, false));
            metricsRow.Add(CreateMetricBox("当前间距 |r|", "hud-dist-val", "0.00 nm", false, false));
            metricsRow.Add(CreateMetricBox("相对速度 |v| / 方位", "hud-relv-val", "0.0kn / 000°", false, true));

            VisualElement footerRow = new VisualElement();
            footerRow.AddToClassList("cpa-footer-row");
            Label formula = new Label("r=P_t-P_o, v=V_t-V_o, TCPA=-(r·v)/|v|², DCPA=|r+v·TCPA|") { name = "hud-formula-label" };
            formula.AddToClassList("cpa-formula-text");
            formula.AddToClassList("mcis-mono");
            Label clockLbl = new Label("2026-05-18 14:15:00") { name = "hud-sim-clock" };
            clockLbl.AddToClassList("cpa-clock-text");
            clockLbl.AddToClassList("mcis-mono");
            footerRow.Add(formula);
            footerRow.Add(clockLbl);

            cpaPanel.Add(headerRow);
            cpaPanel.Add(metricsRow);
            cpaPanel.Add(footerRow);

            Add(leftStack);
            Add(cpaPanel);
        }

        private static VisualElement CreateShipCard(
            string cardName, string shipModClass,
            string titleName, string titleText, string titleClass,
            string badgeName, string badgeText, string badgeClass,
            string posName, string sogName, string cogName, string hdgName, string provName)
        {
            VisualElement card = new VisualElement { name = cardName };
            card.AddToClassList("hud-ship-box");
            card.AddToClassList(shipModClass);

            VisualElement header = new VisualElement();
            header.AddToClassList("hud-ship-header");
            Label title = new Label(titleText) { name = titleName };
            title.AddToClassList(titleClass);
            Label badge = new Label(badgeText) { name = badgeName };
            badge.AddToClassList("mcis-badge");
            badge.AddToClassList(badgeClass);
            header.Add(title);
            header.Add(badge);

            VisualElement row1 = new VisualElement();
            row1.AddToClassList("hud-telemetry-row");
            row1.Add(CreateCell("GPS 位置 (WGS-84 度分)", posName, "--°--.--'N ---°--.--'E", true, false));
            row1.Add(CreateCell("SOG 对地航速", sogName, "0.0 kn", false, true));

            VisualElement row2 = new VisualElement();
            row2.AddToClassList("hud-telemetry-row");
            row2.Add(CreateCell("COG 对地航向", cogName, "000.0°", false, false));
            row2.Add(CreateCell("HDG 船首向", hdgName, "000.0°", false, false));
            row2.Add(CreateCell("数据来源", provName, "AIS 实测", false, true));

            card.Add(header);
            card.Add(row1);
            card.Add(row2);
            return card;
        }

        private static VisualElement CreateCell(string keyText, string valName, string defaultVal, bool isWide, bool isLast)
        {
            VisualElement cell = new VisualElement();
            cell.AddToClassList("telemetry-cell");
            if (isWide) cell.AddToClassList("telemetry-cell-wide");
            if (isLast) cell.AddToClassList("telemetry-cell-last");
            Label k = new Label(keyText);
            k.AddToClassList("telemetry-key");
            Label v = new Label(defaultVal) { name = valName };
            v.AddToClassList("telemetry-val");
            v.AddToClassList("mcis-mono");
            cell.Add(k);
            cell.Add(v);
            return cell;
        }

        private static VisualElement CreateMetricBox(string lblText, string valName, string defaultVal, bool isAccent, bool isLast)
        {
            VisualElement box = new VisualElement();
            box.AddToClassList("cpa-metric-box");
            if (isLast) box.AddToClassList("cpa-metric-box-last");
            Label lbl = new Label(lblText);
            lbl.AddToClassList("cpa-metric-lbl");
            Label num = new Label(defaultVal) { name = valName };
            num.AddToClassList("cpa-metric-num");
            if (isAccent) num.AddToClassList("cpa-metric-accent");
            num.AddToClassList("mcis-mono");
            box.Add(lbl);
            box.Add(num);
            return box;
        }
    }
}
