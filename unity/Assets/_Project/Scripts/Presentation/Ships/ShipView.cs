#if UNITY_5_3_OR_NEWER
using System;
using UnityEngine;
using Mcis.Domain.Common;
using Mcis.Domain.Geo;
using Mcis.Domain.Models;
using Mcis.Simulation.Ships;

namespace Mcis.Presentation.Ships
{
    /// <summary>
    /// 船舶三维视觉呈现组件（MonoBehaviour）。
    /// 监听 <see cref="ShipController"/> 状态推进，负责：
    /// 1. 通过 <see cref="IGeoConverter"/> 将 ENU/大地坐标映射至 Unity 场景坐标；
    /// 2. 位置与船首向（Yaw = Quaternion.Euler(0, hdg, 0)）的平滑插值插帧；
    /// 3. 时间轴 Seek/跳转瞬间位置突变与尾迹清理；
    /// 4. 依据船舶实际总长（LOA）自适应等比缩放 3D 船体模型；
    /// 5. 可选航向尾迹 <see cref="TrailRenderer"/> 状态管理。
    /// </summary>
    [AddComponentMenu("MCIS/Presentation/Ship View")]
    public sealed class ShipView : MonoBehaviour
    {
        [Header("Model & Hierarchy")]
        [Tooltip("船体 3D 模型根节点（为空时使用当前 GameObject Transform）")]
        [SerializeField] private Transform _modelRoot;

        [Tooltip("航行尾迹渲染器（可选）")]
        [SerializeField] private TrailRenderer _trailRenderer;

        [Header("Scaling")]
        [Tooltip("是否根据船舶资料总长 LOA 自动缩放模型")]
        [SerializeField] private bool _autoScaleByLoa = true;

        [Tooltip("模型原始资产对应的物理长度（米，默认 100m）")]
        [SerializeField] private float _modelBaseLengthM = 100f;

        [Header("Smoothing")]
        [Tooltip("是否开启平滑位移插值")]
        [SerializeField] private bool _smooth = true;

        [Tooltip("位置平滑插值速率")]
        [SerializeField] private float _positionSmoothSpeed = 15f;

        [Tooltip("航向旋转平滑插值速率")]
        [SerializeField] private float _rotationSmoothSpeed = 12f;

        [Tooltip("吃水/水面高程微调（米）")]
        [SerializeField] private float _waterHeightOffsetM = 0f;

        private ShipController _controller;
        private IGeoConverter _geoConverter;
        private Vector3 _targetPosition;
        private Quaternion _targetRotation = Quaternion.identity;
        private bool _hasTarget;
        private Vector3 _baseLocalScale = Vector3.one;

        /// <summary>当前绑定的船舶控制器。</summary>
        public ShipController Controller
        {
            get { return _controller; }
        }

        /// <summary>坐标转换器。</summary>
        public IGeoConverter GeoConverter
        {
            get { return _geoConverter; }
            set { _geoConverter = value; }
        }

        private Transform EffectiveModelRoot
        {
            get { return _modelRoot != null ? _modelRoot : transform; }
        }

        private void Awake()
        {
            if (_modelRoot == null)
            {
                _modelRoot = transform;
            }
            _baseLocalScale = _modelRoot.localScale;
        }

        /// <summary>绑定船舶控制器并初始化模型缩放与初始位姿。</summary>
        public void BindController(ShipController controller, IGeoConverter geoConverter = null)
        {
            if (ReferenceEquals(_controller, controller) && controller != null)
            {
                return;
            }

            UnbindController();
            _controller = controller;
            _geoConverter = geoConverter ?? controller?.GeoConverter;

            if (_controller != null)
            {
                _controller.StateUpdated += OnControllerStateUpdated;
                ApplyScale(_controller.LoaM);
                UpdateTransformFromSample(_controller.CurrentSample, isSeek: true);
            }
        }

        /// <summary>解除与船舶控制器的绑定。</summary>
        public void UnbindController()
        {
            if (_controller != null)
            {
                _controller.StateUpdated -= OnControllerStateUpdated;
                _controller = null;
            }
        }

        /// <summary>按总长调整模型缩放比例。</summary>
        public void ApplyScale(float loaM)
        {
            if (!_autoScaleByLoa || loaM <= 0f) return;
            float baseLen = _modelBaseLengthM > 0.1f ? _modelBaseLengthM : 100f;
            float scaleFactor = loaM / baseLen;
            EffectiveModelRoot.localScale = _baseLocalScale * scaleFactor;
        }

        private void OnControllerStateUpdated(ShipController controller, TrackSample sample, bool isSeek)
        {
            UpdateTransformFromSample(sample, isSeek);
        }

        private void UpdateTransformFromSample(TrackSample sample, bool isSeek)
        {
            bool visible = _controller != null ? _controller.IsVisible : true;
            if (EffectiveModelRoot.gameObject.activeSelf != visible)
            {
                EffectiveModelRoot.gameObject.SetActive(visible);
            }
            if (_trailRenderer != null && _trailRenderer.emitting != visible)
            {
                _trailRenderer.emitting = visible;
            }

            if (!visible) return;

            Double3 worldPosD;
            if (_geoConverter != null)
            {
                worldPosD = _geoConverter.EnuToUnityWorld(sample.EnuCenter);
            }
            else if (_controller != null)
            {
                worldPosD = _controller.CurrentUnityPosition;
            }
            else
            {
                worldPosD = new Double3(sample.EnuCenter.EastM, sample.EnuCenter.UpM, sample.EnuCenter.NorthM);
            }

            Vector3 unityPos = new Vector3(
                (float)worldPosD.X,
                (float)(worldPosD.Y + _waterHeightOffsetM),
                (float)worldPosD.Z);

            float hdgDeg = sample.HdgDeg;
            if (float.IsNaN(hdgDeg) || hdgDeg < 0f)
            {
                hdgDeg = sample.CogDeg;
            }
            if (float.IsNaN(hdgDeg))
            {
                hdgDeg = 0f;
            }

            // Unity 左手系 (x=East, y=Up, z=North)，正北为 +Z，向东顺时针偏航对应绕 Y 轴正向旋转
            Quaternion unityRot = Quaternion.Euler(0f, hdgDeg, 0f);

            _targetPosition = unityPos;
            _targetRotation = unityRot;

            if (isSeek || !_hasTarget || !_smooth)
            {
                transform.position = _targetPosition;
                transform.rotation = _targetRotation;
                _hasTarget = true;
                if (_trailRenderer != null)
                {
                    _trailRenderer.Clear();
                }
            }
        }

        private void LateUpdate()
        {
            if (!_hasTarget) return;

            if (_smooth)
            {
                float dt = Time.deltaTime;
                float distSq = (transform.position - _targetPosition).sqrMagnitude;
                if (distSq > 2500f) // 距离跳跃超 50m，直接对齐避免长距离飞跃拉扯尾迹
                {
                    transform.position = _targetPosition;
                    transform.rotation = _targetRotation;
                    if (_trailRenderer != null) _trailRenderer.Clear();
                }
                else
                {
                    transform.position = Vector3.Lerp(transform.position, _targetPosition, dt * _positionSmoothSpeed);
                    transform.rotation = Quaternion.Slerp(transform.rotation, _targetRotation, dt * _rotationSmoothSpeed);
                }
            }
            else
            {
                transform.position = _targetPosition;
                transform.rotation = _targetRotation;
            }
        }

        private void OnDestroy()
        {
            UnbindController();
        }
    }
}
#endif
