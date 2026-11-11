#if UNITY_5_3_OR_NEWER
// ---------------------------------------------------------------------------
// 本文件依赖 UnityEngine（AsyncGPUReadback、Time.captureFramerate、RenderTexture），
// 在本开发盒子上【未编译验证】。请在 Unity 6.0 LTS 工程中编译与联调。
// 职责：离线固定步长采集 RGBA 帧，交给 Mcis.Export.FFmpegPipeEncoder 编码为 H.264 MP4。
// ---------------------------------------------------------------------------
using System;
using System.Collections;
using System.Threading;
using System.Threading.Tasks;
using Mcis.Core;
using Mcis.Export;
using UnityEngine;
using UnityEngine.Rendering;

namespace Mcis.Presentation.Export
{
    /// <summary>
    /// 运行时离线帧精确采集（未编译验证）。将 Time.captureFramerate 设为导出帧率，
    /// 每帧 RenderTexture → AsyncGPUReadback → FFmpeg 标准输入管道。
    /// </summary>
    public sealed class OfflineFrameCapture : MonoBehaviour
    {
        [SerializeField] private Camera _captureCamera;
        [SerializeField] private string _ffmpegPath = "ffmpeg";

        public bool IsRecording { get; private set; }
        public float ProgressNormalized { get; private set; }

        /// <summary>
        /// 在导出状态下以固定步长采集 [start, end] 区间。调用方需自行驱动仿真时钟与 HUD 叠加。
        /// </summary>
        public IEnumerator RecordOffline(
            VideoRecordOptions options,
            float startSeconds,
            float endSeconds,
            Action<float> seekSimulation,
            CancellationToken ct,
            Action<Result<VideoRecordArtifact>> onCompleted)
        {
            if (options == null)
            {
                if (onCompleted != null)
                {
                    onCompleted(Result<VideoRecordArtifact>.Fail("REC-E01", "导出参数为空"));
                }
                yield break;
            }

            Camera cam = _captureCamera != null ? _captureCamera : Camera.main;
            if (cam == null)
            {
                if (onCompleted != null)
                {
                    onCompleted(Result<VideoRecordArtifact>.Fail("REC-E02", "找不到采集相机"));
                }
                yield break;
            }

            int fps = Math.Max(options.Fps, 1);
            int width = options.WidthPx;
            int height = options.HeightPx;
            int previousCaptureFramerate = Time.captureFramerate;
            Time.captureFramerate = fps;

            var rt = new RenderTexture(width, height, 24, RenderTextureFormat.ARGB32);
            rt.Create();
            Camera previousTarget = null;
            RenderTexture previousRt = cam.targetTexture;
            cam.targetTexture = rt;

            int total = Math.Max(1, Mathf.CeilToInt((endSeconds - startSeconds) * fps));
            var encoder = new FFmpegPipeEncoder(options);
            IsRecording = true;
            ProgressNormalized = 0f;
            Exception error = null;
            VideoRecordArtifact artifact = null;

            try
            {
                encoder.Begin(total);
                encoder.ProgressChanged += p => ProgressNormalized = p;

                for (int i = 0; i < total; i++)
                {
                    if (ct.IsCancellationRequested)
                    {
                        encoder.Cancel();
                        break;
                    }

                    float t = startSeconds + (i / (float)fps);
                    if (seekSimulation != null)
                    {
                        seekSimulation(t);
                    }

                    yield return new WaitForEndOfFrame();

                    bool done = false;
                    byte[] pixels = null;
                    AsyncGPUReadback.Request(rt, 0, TextureFormat.RGBA32, req =>
                    {
                        if (!req.hasError)
                        {
                            pixels = req.GetData<byte>().ToArray();
                        }
                        done = true;
                    });

                    while (!done)
                    {
                        yield return null;
                    }

                    if (pixels != null)
                    {
                        if (options.BurnInAuditWatermark && !string.IsNullOrEmpty(options.WatermarkText))
                        {
                            FFmpegPipeEncoder.BurnWatermark(pixels, width, height, options.WatermarkText, 16, 16);
                        }

                        encoder.WriteFrame(pixels);
                    }
                }

                if (!ct.IsCancellationRequested)
                {
                    artifact = encoder.Complete();
                }
            }
            catch (Exception ex)
            {
                error = ex;
                encoder.Cancel();
            }
            finally
            {
                Time.captureFramerate = previousCaptureFramerate;
                cam.targetTexture = previousRt;
                rt.Release();
                IsRecording = false;
                previousTarget = previousTarget;
            }

            if (onCompleted != null)
            {
                if (error != null)
                {
                    onCompleted(Result<VideoRecordArtifact>.Fail("REC-FAIL", error.Message));
                }
                else if (artifact != null)
                {
                    onCompleted(Result<VideoRecordArtifact>.Ok(artifact));
                }
                else
                {
                    onCompleted(Result<VideoRecordArtifact>.Fail("REC-CANCEL", "录制已取消"));
                }
            }
        }
    }
}
#endif
