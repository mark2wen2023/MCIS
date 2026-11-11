using System;
using Mcis.Core;
using Mcis.Domain.Common;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Simulation.Ships;
using Mcis.UI.SimHud;

namespace Mcis.Presentation.Ships
{
    /// <summary>
    /// 船舶状态源适配器（表现层防腐适配器）。
    /// 将 <see cref="ShipController"/> 适配封装为 UI 层所需的 <see cref="IShipStateSource"/>，
    /// 从而彻底切断 Mcis.Simulation 仿真层对 Mcis.UI 界面层的反向依赖。
    /// </summary>
    public sealed class ShipStateSourceAdapter : IShipStateSource
    {
        private readonly ShipController _controller;

        /// <summary>底层包裹的船舶仿真控制器。</summary>
        public ShipController Controller
        {
            get { return _controller; }
        }

        /// <inheritdoc />
        public string VesselId
        {
            get { return _controller.VesselId; }
        }

        /// <inheritdoc />
        public string DisplayName
        {
            get { return _controller.DisplayName; }
        }

        /// <inheritdoc />
        public string SubtitleRole
        {
            get { return _controller.SubtitleRole; }
        }

        /// <inheritdoc />
        public string StatusBadgeText
        {
            get { return _controller.StatusBadgeText; }
        }

        /// <inheritdoc />
        public VesselParticulars Particulars
        {
            get { return _controller.Particulars; }
        }

        /// <inheritdoc />
        public IShipTrack Track
        {
            get { return _controller.Track; }
        }

        /// <summary>使用船舶控制器构造适配器。</summary>
        public ShipStateSourceAdapter(ShipController controller)
        {
            _controller = controller ?? throw new ArgumentNullException(nameof(controller));
        }

        /// <inheritdoc />
        public TrackSample SampleStateAt(SimTime time)
        {
            return _controller.SampleStateAt(time);
        }
    }
}
