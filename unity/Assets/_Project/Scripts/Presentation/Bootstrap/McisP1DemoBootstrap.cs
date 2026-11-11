#if UNITY_5_3_OR_NEWER
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;
using Mcis.Core;
using Mcis.Domain.Ais;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Domain.Tracks;
using Mcis.Presentation.Ships;
using Mcis.Simulation;
using Mcis.Simulation.Cpa;
using Mcis.Simulation.Ships;
using Mcis.UI.SimHud;
using Object = UnityEngine.Object;

namespace Mcis.Presentation.Bootstrap
{
    /// <summary>
    /// MCIS P1 原型演示场景引导器（MonoBehaviour，Unity 6 LTS API）。
    /// 负责流式加载示例数据（CSV/NMEA）并执行完整调用链：
    /// 解码 → 清洗 → Hermite 插值 → CPA 预计算 → 确定性 SimClock 构造 → 双船控制器/视图挂接 → 主仿真驱动器与 HUD 绑定。
    /// </summary>
    [AddComponentMenu("MCIS/Presentation/Demo Bootstrap")]
    public sealed class McisP1DemoBootstrap : MonoBehaviour
    {
        [Header("Data Source")]
        [Tooltip("StreamingAssets 相对路径（支持 .csv 或 .nmea）")]
        [SerializeField] private string _dataSourceRelativePath = "Mcis/Demo/lily_mary_demo.csv";

        [Tooltip("案件仿真时间原点 UTC 纪元（默认 2026-05-18T10:00:00Z）")]
        [SerializeField] private string _caseEpochUtcString = "2026-05-18T10:00:00Z";

        [Tooltip("显示时区相对 UTC 分钟偏移（默认 480 即 UTC+8 北京时间）")]
        [SerializeField] private int _displayTimeZoneOffsetMinutes = 480;

        [Header("Geographic Reference")]
        [Tooltip("原点经度（十进制度，东经为正，默认 113.70）")]
        [SerializeField] private double _originLonDeg = 113.70;

        [Tooltip("原点纬度（十进制度，北纬为正，默认 21.78）")]
        [SerializeField] private double _originLatDeg = 21.78;

        [Tooltip("原点高程（米，默认 0.0）")]
        [SerializeField] private double _originAltitudeM = 0.0;

        [Tooltip("是否优先使用 Cesium 适配器（若勾选且组件有效则使用，否则回退 LocalEnuGeoConverter）")]
        [SerializeField] private bool _useCesiumAdapter = false;

        [Tooltip("Cesium 地理参考适配器组件（需实现 IGeoConverter 的 MonoBehaviour，例如 CesiumGeoreferenceAdapter；为空则回退 LocalEnuGeoConverter）")]
        [SerializeField] private MonoBehaviour _cesiumAdapter;

        [Header("Vessels & Prefabs")]
        [Tooltip("Lily 轮 (散货船) 3D 模型预制体（可选；为空时动态创建空物体载体）")]
        [SerializeField] private GameObject _lilyPrefab;

        [Tooltip("Mary 轮 (集装箱船) 3D 模型预制体（可选；为空时动态创建空物体载体）")]
        [SerializeField] private GameObject _maryPrefab;

        [Header("UI & Simulation")]
        [Tooltip("主仿真 HUD 控制器（可选；为空时自动在场景中检索）")]
        [SerializeField] private SimHudController _hudController;

        [Tooltip("初始仿真播放倍速（默认 1.0x，支持 0.5, 1, 2, 4, 8, 16）")]
        [SerializeField] private float _initialPlaybackRate = 1.0f;

        [Tooltip("是否在 Start 初始化完成后自动启动时钟播放")]
        [SerializeField] private bool _autoPlay = true;

        private SimClock _clock;
        private CpaService _cpaService;
        private IGeoConverter _geoConverter;
        private ShipController _lilyController;
        private ShipController _maryController;
        private ShipView _lilyView;
        private ShipView _maryView;

        /// <summary>当前驱动的确定性仿真时钟。</summary>
        public ISimClock Clock => _clock;

        /// <summary>两船全时段预计算 CPA 服务。</summary>
        public ICpaService CpaService => _cpaService;

        /// <summary>场景地理参考转换器。</summary>
        public IGeoConverter GeoConverter => _geoConverter;

        /// <summary>Lily 散货船控制器。</summary>
        public ShipController LilyController => _lilyController;

        /// <summary>Mary 集装箱船控制器。</summary>
        public ShipController MaryController => _maryController;

        /// <summary>Lily 散货船 3D 视图呈现组件。</summary>
        public ShipView LilyView => _lilyView;

        /// <summary>Mary 集装箱船 3D 视图呈现组件。</summary>
        public ShipView MaryView => _maryView;

        private void Start()
        {
            InitializeDemo();
        }

        private void InitializeDemo()
        {
            // 注意：在 Android / WebGL 平台上 StreamingAssets 位于压缩包内或远程，不能使用 File.ReadAllText，
            // 需改用 UnityWebRequest.Get 或 Unity 6 的 Awaitable 异步读取。在桌面独立平台下直接使用 File.ReadAllText 同步加载。
            string fullPath = Path.Combine(Application.streamingAssetsPath, _dataSourceRelativePath);
            if (!File.Exists(fullPath))
            {
                Debug.LogError($"[MCIS] 找不到示例数据文件: {fullPath}");
                return;
            }

            string text = File.ReadAllText(fullPath);
            AisDecoder decoder = new AisDecoder();
            Result<AisImportBatchResult> decodeResult;

            bool isNmea = _dataSourceRelativePath.EndsWith(".nmea", StringComparison.OrdinalIgnoreCase) ||
                          text.StartsWith("!", StringComparison.Ordinal) ||
                          text.StartsWith("#", StringComparison.Ordinal);

            if (isNmea)
            {
                decodeResult = decoder.DecodeNmeaText(text);
            }
            else
            {
                CsvMappingProfile profile = (text.Contains("timestamp_utc") || text.Contains("mmsi"))
                    ? new CsvMappingProfile("Demo", "mmsi", "timestamp_utc", null, 0, "lon", "lat", "sog_kn", "cog_deg", "hdg_deg", "vessel_name")
                    : CsvMappingProfile.CreateDefault();
                decodeResult = decoder.DecodeCsvText(text, profile);
            }

            if (!decodeResult.IsSuccess)
            {
                Debug.LogError($"[MCIS] 数据解码失败: {decodeResult.Error}");
                return;
            }

            AisImportBatchResult batch = decodeResult.Value;
            const string defaultLilyMmsi = "999000001";
            const string defaultMaryMmsi = "999000002";
            string lilyMmsi = batch.RecordsByMmsi.ContainsKey(defaultLilyMmsi) ? defaultLilyMmsi : null;
            string maryMmsi = batch.RecordsByMmsi.ContainsKey(defaultMaryMmsi) ? defaultMaryMmsi : null;

            if (lilyMmsi == null || maryMmsi == null)
            {
                List<string> keys = new List<string>(batch.RecordsByMmsi.Keys);
                if (keys.Count < 2)
                {
                    Debug.LogError($"[MCIS] 导入的 AIS 数据至少需包含两条船舶航迹，当前包含: {keys.Count}");
                    return;
                }
                lilyMmsi = keys[0];
                maryMmsi = keys[1];
            }

            GeoCoord origin = new GeoCoord(_originLonDeg, _originLatDeg, _originAltitudeM);
            if (_useCesiumAdapter && _cesiumAdapter is IGeoConverter adapterGeo)
            {
                adapterGeo.SetOrigin(origin, 0.0);
                _geoConverter = adapterGeo;
            }
            else
            {
                _geoConverter = new LocalEnuGeoConverter(origin, 0.0);
            }

            DateTimeOffset caseEpoch;
            if (!DateTimeOffset.TryParse(_caseEpochUtcString, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out caseEpoch))
            {
                caseEpoch = new DateTimeOffset(2026, 5, 18, 10, 0, 0, TimeSpan.Zero);
            }

            TrackCleaningConfig cleaningCfg = TrackCleaningConfig.CreateDefault();
            TrackInterpolator interpolator = new TrackInterpolator();
            IShipTrack lilyTrack = interpolator.BuildFromAisRecords(
                "lily", batch.RecordsByMmsi[lilyMmsi], AntennaOffset.Zero, caseEpoch, _geoConverter, cleaningCfg);
            IShipTrack maryTrack = interpolator.BuildFromAisRecords(
                "mary", batch.RecordsByMmsi[maryMmsi], AntennaOffset.Zero, caseEpoch, _geoConverter, cleaningCfg);

            VesselParticulars lilyPart;
            if (!batch.DiscoveredStaticParticulars.TryGetValue(lilyMmsi, out lilyPart))
            {
                lilyPart = new VesselParticulars(
                    lilyMmsi, "LILY", "莉莉轮", lilyMmsi, "IMO 9900101", "BXXX1", "中国",
                    "BulkCarrier", "bulk_handy", 189.9f, 32.26f, 5.2f, 6.8f, 18.0f, 24500f, "Ballast",
                    new AntennaOffset(152f, 37.9f, 12.1f, 20.16f), Double3.Zero, 0.095f, 38.0f);
            }

            VesselParticulars maryPart;
            if (!batch.DiscoveredStaticParticulars.TryGetValue(maryMmsi, out maryPart))
            {
                maryPart = new VesselParticulars(
                    maryMmsi, "MARY", "玛丽轮", maryMmsi, "IMO 9900202", "3FXX2", "巴拿马",
                    "ContainerShip", "container_panamax", 225.0f, 32.20f, 12.4f, 12.8f, 19.2f, 58200f, "FullLoad",
                    new AntennaOffset(165f, 60.0f, 16.1f, 16.1f), Double3.Zero, 0.068f, 62.0f);
            }

            _cpaService = new CpaService(lilyTrack, maryTrack, 1.0, RiskThresholds.Default);

            double startSec = Math.Min(lilyTrack.StartTime.Seconds, maryTrack.StartTime.Seconds);
            double endSec = Math.Max(lilyTrack.EndTime.Seconds, maryTrack.EndTime.Seconds);
            _clock = new SimClock(startSec, endSec);
            if (SimClock.IsSupportedRate(_initialPlaybackRate))
            {
                _clock.SetRate(_initialPlaybackRate);
            }

            _lilyController = new ShipController(
                lilyTrack, lilyPart, _geoConverter, _clock, "LILY", "本船 / 散货船", "压载出港");
            _maryController = new ShipController(
                maryTrack, maryPart, _geoConverter, _clock, "MARY", "他船 / 集装箱船", "满载进港");

            GameObject lilyGo = _lilyPrefab != null ? Instantiate(_lilyPrefab) : new GameObject("ShipView_Lily");
            _lilyView = lilyGo.GetComponent<ShipView>() ?? lilyGo.AddComponent<ShipView>();
            _lilyView.BindController(_lilyController, _geoConverter);

            GameObject maryGo = _maryPrefab != null ? Instantiate(_maryPrefab) : new GameObject("ShipView_Mary");
            _maryView = maryGo.GetComponent<ShipView>() ?? maryGo.AddComponent<ShipView>();
            _maryView.BindController(_maryController, _geoConverter);

            SimulationLoopRunner runner = Object.FindFirstObjectByType<SimulationLoopRunner>();
            if (runner == null)
            {
                runner = gameObject.AddComponent<SimulationLoopRunner>();
            }
            runner.BindClock(_clock);

            if (_hudController == null)
            {
                _hudController = Object.FindFirstObjectByType<SimHudController>();
            }
            if (_hudController != null)
            {
                ShipStateSourceAdapter lilySource = new ShipStateSourceAdapter(_lilyController);
                ShipStateSourceAdapter marySource = new ShipStateSourceAdapter(_maryController);
                _hudController.Bind(_clock, _cpaService, lilySource, marySource, caseEpoch, _displayTimeZoneOffsetMinutes);
            }

            if (_autoPlay)
            {
                _clock.Play();
            }

            Debug.Log("[MCIS] 示例数据（虚构），改编自论文 5.4 节。Lily(散货船)与 Mary(集装箱船)窄航道会遇至碰撞演示引导就绪。");
        }

        private void OnDestroy()
        {
            if (_clock != null)
            {
                _clock.Pause();
            }
            if (_lilyController != null)
            {
                _lilyController.Dispose();
                _lilyController = null;
            }
            if (_maryController != null)
            {
                _maryController.Dispose();
                _maryController = null;
            }
            if (_lilyView != null)
            {
                _lilyView.UnbindController();
            }
            if (_maryView != null)
            {
                _maryView.UnbindController();
            }
            _clock = null;
            _cpaService = null;
        }
    }
}
#endif
