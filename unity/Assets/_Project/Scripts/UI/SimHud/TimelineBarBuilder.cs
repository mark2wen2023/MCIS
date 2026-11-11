using UnityEngine.UIElements;

namespace Mcis.UI.SimHud
{
    public partial class TimelineBar
    {
        private void BuildFallbackHierarchy()
        {
            VisualElement trackWrap = new VisualElement { name = "timeline-track-wrap" };
            trackWrap.AddToClassList("timeline-track-wrap");

            VisualElement markersLayer = new VisualElement { name = "tl-markers-layer" };
            markersLayer.AddToClassList("timeline-markers-layer");

            Slider scrubber = new Slider(0f, 900f) { name = "tl-scrubber", value = 0f };
            scrubber.AddToClassList("timeline-slider");

            trackWrap.Add(markersLayer);
            trackWrap.Add(scrubber);

            VisualElement controlsRow = new VisualElement { name = "timeline-controls-row" };
            controlsRow.AddToClassList("timeline-controls-row");

            VisualElement leftBtns = new VisualElement();
            leftBtns.AddToClassList("timeline-left-buttons");
            leftBtns.Add(CreateBtn("btn-tl-play", "▶ 播放", "mcis-btn-primary"));
            leftBtns.Add(CreateBtn("btn-tl-step-back", "« -10s", null));
            leftBtns.Add(CreateBtn("btn-tl-step-fwd", "+10s »", null));
            leftBtns.Add(CreateBtn("btn-tl-jump-cpa", "💥 最小会遇点", "mcis-btn-danger"));
            leftBtns.Add(CreateBtn("btn-tl-reset", "↺ 重置", null));

            VisualElement centerTime = new VisualElement();
            centerTime.AddToClassList("timeline-center-time");
            Label caption = new Label("仿真进度:");
            caption.AddToClassList("tl-time-caption");
            Label elapsed = new Label("00:00.0") { name = "tl-elapsed-label" };
            elapsed.AddToClassList("tl-elapsed-num");
            elapsed.AddToClassList("mcis-mono");
            Label slash = new Label(" / ");
            slash.AddToClassList("tl-duration-num");
            slash.AddToClassList("mcis-mono");
            Label duration = new Label("15:00.0") { name = "tl-duration-label" };
            duration.AddToClassList("tl-duration-num");
            duration.AddToClassList("mcis-mono");
            Label div = new Label("|");
            div.AddToClassList("tl-divider");
            Label utc = new Label("14:15:00") { name = "tl-utc-label" };
            utc.AddToClassList("tl-utc-num");
            utc.AddToClassList("mcis-mono");

            centerTime.Add(caption);
            centerTime.Add(elapsed);
            centerTime.Add(slash);
            centerTime.Add(duration);
            centerTime.Add(div);
            centerTime.Add(utc);

            VisualElement speedGroup = new VisualElement { name = "speed-group" };
            speedGroup.AddToClassList("speed-group");
            Label speedCap = new Label("倍速:");
            speedCap.AddToClassList("speed-caption");
            speedGroup.Add(speedCap);

            string[] labels = new string[] { "0.5x", "1x", "2x", "4x", "8x", "16x" };
            for (int i = 0; i < SpeedButtonNames.Length; i++)
            {
                Button sb = new Button { name = SpeedButtonNames[i], text = labels[i] };
                sb.AddToClassList("speed-btn");
                sb.AddToClassList("mcis-mono");
                if (i == 1) sb.AddToClassList("active");
                speedGroup.Add(sb);
            }

            controlsRow.Add(leftBtns);
            controlsRow.Add(centerTime);
            controlsRow.Add(speedGroup);

            Add(trackWrap);
            Add(controlsRow);
        }

        private static Button CreateBtn(string name, string text, string extraClass)
        {
            Button btn = new Button { name = name, text = text };
            btn.AddToClassList("mcis-btn");
            if (!string.IsNullOrEmpty(extraClass))
            {
                btn.AddToClassList(extraClass);
            }
            return btn;
        }
    }
}
