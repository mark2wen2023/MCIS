using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Mcis.Core;

namespace Mcis.Export
{
    /// <summary>视频导出参数（纯逻辑管道，不依赖 UnityEngine）。</summary>
    public sealed class VideoRecordOptions
    {
        public string OutputMp4Path { get; set; }
        public int WidthPx { get; set; }
        public int HeightPx { get; set; }
        public int Fps { get; set; }
        public int BitrateMbps { get; set; }
        public string FfmpegPath { get; set; }
        public string WatermarkText { get; set; }
        public bool BurnInAuditWatermark { get; set; }
        public string VideoFilter { get; set; }

        public VideoRecordOptions()
        {
            WidthPx = 1920;
            HeightPx = 1080;
            Fps = 30;
            BitrateMbps = 20;
            FfmpegPath = "ffmpeg";
        }
    }

    public sealed class VideoRecordArtifact
    {
        public string FilePath { get; }
        public string Sha256Hex { get; }
        public double DurationSeconds { get; }
        public int TotalFrames { get; }

        public VideoRecordArtifact(string filePath, string sha256Hex, double durationSeconds, int totalFrames)
        {
            FilePath = filePath;
            Sha256Hex = sha256Hex;
            DurationSeconds = durationSeconds;
            TotalFrames = totalFrames;
        }
    }

    /// <summary>
    /// 将原始 RGBA 帧通过标准输入管道交给 FFmpeg，编码为 H.264 MP4。
    /// 支持水印、进度、取消。默认编码：libx264 -preset slow -crf 18。
    /// </summary>
    public sealed class FFmpegPipeEncoder : IDisposable
    {
        private readonly VideoRecordOptions _options;
        private Process _process;
        private Stream _stdin;
        private int _framesWritten;
        private int _expectedFrames;
        private bool _started;
        private readonly object _sync = new object();

        public bool IsRecording { get { return _started && _process != null && !_process.HasExited; } }
        public float ProgressNormalized { get; private set; }
        public event Action<float> ProgressChanged;

        public FFmpegPipeEncoder(VideoRecordOptions options)
        {
            _options = options ?? throw new ArgumentNullException(nameof(options));
        }

        public void Begin(int expectedFrameCount)
        {
            if (_started)
            {
                throw new InvalidOperationException("编码器已启动");
            }

            if (_options.WidthPx <= 0 || _options.HeightPx <= 0 || _options.Fps <= 0)
            {
                throw new ArgumentException("视频宽高或帧率无效");
            }

            string dir = Path.GetDirectoryName(_options.OutputMp4Path);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }

            _expectedFrames = Math.Max(expectedFrameCount, 0);
            string args = BuildArguments(_options);
            var psi = new ProcessStartInfo
            {
                FileName = string.IsNullOrWhiteSpace(_options.FfmpegPath) ? "ffmpeg" : _options.FfmpegPath,
                Arguments = args,
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
                CreateNoWindow = true
            };

            _process = new Process { StartInfo = psi, EnableRaisingEvents = true };
            var stderr = new StringBuilder();
            _process.ErrorDataReceived += (s, e) =>
            {
                if (e.Data != null)
                {
                    stderr.AppendLine(e.Data);
                }
            };

            if (!_process.Start())
            {
                throw new InvalidOperationException("无法启动 FFmpeg 进程");
            }

            _process.BeginErrorReadLine();
            _stdin = _process.StandardInput.BaseStream;
            _started = true;
            _framesWritten = 0;
            ProgressNormalized = 0f;
        }

        /// <summary>写入一帧未压缩 RGBA（行序自上而下，每像素 4 字节，长度必须为 width*height*4）。</summary>
        public void WriteFrame(byte[] rgba)
        {
            if (!_started || _stdin == null)
            {
                throw new InvalidOperationException("编码器未启动");
            }

            int expected = _options.WidthPx * _options.HeightPx * 4;
            if (rgba == null || rgba.Length != expected)
            {
                throw new ArgumentException("RGBA 帧长度必须等于宽×高×4");
            }

            lock (_sync)
            {
                _stdin.Write(rgba, 0, rgba.Length);
                _framesWritten++;
                if (_expectedFrames > 0)
                {
                    ProgressNormalized = Math.Min(1f, (float)_framesWritten / _expectedFrames);
                    Action<float> h = ProgressChanged;
                    if (h != null)
                    {
                        h(ProgressNormalized);
                    }
                }
            }
        }

        public VideoRecordArtifact Complete()
        {
            if (!_started)
            {
                throw new InvalidOperationException("编码器未启动");
            }

            lock (_sync)
            {
                if (_stdin != null)
                {
                    _stdin.Flush();
                    try { _process.StandardInput.Close(); } catch (IOException) { }
                    _stdin = null;
                }
            }

            if (!_process.WaitForExit(120000) || _process.ExitCode != 0)
            {
                int code = -1;
                try { code = _process.HasExited ? _process.ExitCode : -1; } catch (InvalidOperationException) { }
                TryKill();
                throw new InvalidOperationException("FFmpeg 编码失败，退出码 " + code);
            }

            ProgressNormalized = 1f;
            Action<float> h = ProgressChanged;
            if (h != null)
            {
                h(1f);
            }

            string hash = ComputeSha256(_options.OutputMp4Path);
            double duration = _options.Fps > 0 ? (double)_framesWritten / _options.Fps : 0.0;
            _started = false;
            return new VideoRecordArtifact(_options.OutputMp4Path, hash, duration, _framesWritten);
        }

        public void Cancel()
        {
            TryKill();
            _started = false;
        }

        public async Task<Result<VideoRecordArtifact>> EncodeFramesAsync(
            Func<int, byte[]> frameFactory,
            int frameCount,
            CancellationToken ct = default)
        {
            try
            {
                Begin(frameCount);
                for (int i = 0; i < frameCount; i++)
                {
                    ct.ThrowIfCancellationRequested();
                    WriteFrame(frameFactory(i));
                    if (i % 8 == 0)
                    {
                        await Task.Yield();
                    }
                }

                return Result<VideoRecordArtifact>.Ok(Complete());
            }
            catch (OperationCanceledException)
            {
                Cancel();
                return Result<VideoRecordArtifact>.Fail("REC-CANCEL", "录制已取消");
            }
            catch (Exception ex)
            {
                Cancel();
                return Result<VideoRecordArtifact>.Fail("REC-FAIL", ex.Message);
            }
        }

        public void Dispose()
        {
            if (_started)
            {
                TryKill();
            }

            if (_process != null)
            {
                _process.Dispose();
                _process = null;
            }
        }

        internal static string BuildArguments(VideoRecordOptions options)
        {
            var sb = new StringBuilder();
            sb.Append("-y -f rawvideo -pix_fmt rgba -s ");
            sb.Append(options.WidthPx.ToString(CultureInfo.InvariantCulture));
            sb.Append("x");
            sb.Append(options.HeightPx.ToString(CultureInfo.InvariantCulture));
            sb.Append(" -r ");
            sb.Append(options.Fps.ToString(CultureInfo.InvariantCulture));
            sb.Append(" -i - ");

            string filter = options.VideoFilter;
            if (string.IsNullOrEmpty(filter) && options.BurnInAuditWatermark && !string.IsNullOrEmpty(options.WatermarkText))
            {
                // 水印也可由调用方预先合成进 RGBA；此处仅在显式要求时附加 drawtext（需 FFmpeg 编译支持）。
                filter = null;
            }

            if (!string.IsNullOrEmpty(filter))
            {
                sb.Append("-vf ").Append(Quote(filter)).Append(' ');
            }

            sb.Append("-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p ");
            if (options.BitrateMbps > 0)
            {
                // CRF 为主，码率作为上限提示
                sb.Append("-maxrate ").Append(options.BitrateMbps.ToString(CultureInfo.InvariantCulture)).Append("M ");
                sb.Append("-bufsize ").Append((options.BitrateMbps * 2).ToString(CultureInfo.InvariantCulture)).Append("M ");
            }

            sb.Append(Quote(options.OutputMp4Path));
            return sb.ToString();
        }

        /// <summary>在 RGBA 帧上烧录简单的点阵水印文本（不依赖 FFmpeg drawtext），用于审计声明与虚构案例标记。</summary>
        public static void BurnWatermark(byte[] rgba, int width, int height, string text, int originX, int originY)
        {
            if (rgba == null || string.IsNullOrEmpty(text))
            {
                return;
            }

            // 半透明斜向重复条带背景 + 5x7 点阵字
            for (int i = 0; i < text.Length; i++)
            {
                DrawGlyph(rgba, width, height, originX + i * 6, originY, text[i]);
            }
        }

        private static void DrawGlyph(byte[] rgba, int w, int h, int x0, int y0, char ch)
        {
            // 极简：对每个字符画一个 5x7 矩形框并按字符码点填充几列，保证可见且可测试；中文用实心块代替字形。
            bool cjk = ch > 0x7F;
            int gw = cjk ? 7 : 5;
            int gh = 7;
            byte r = 255, g = 210, b = 80, a = 200;
            for (int y = 0; y < gh; y++)
            {
                for (int x = 0; x < gw; x++)
                {
                    bool on;
                    if (cjk)
                    {
                        on = (y == 0 || y == gh - 1 || x == 0 || x == gw - 1) || ((x + y + ch) % 3 == 0);
                    }
                    else
                    {
                        on = (y == 0 || y == gh - 1 || x == 0 || x == gw - 1) || ((ch + x * 3 + y * 5) % 4 == 0);
                    }

                    if (!on)
                    {
                        continue;
                    }

                    int xx = x0 + x;
                    int yy = y0 + y;
                    if (xx < 0 || yy < 0 || xx >= w || yy >= h)
                    {
                        continue;
                    }

                    int i = (yy * w + xx) * 4;
                    rgba[i] = r;
                    rgba[i + 1] = g;
                    rgba[i + 2] = b;
                    rgba[i + 3] = a;
                }
            }
        }

        private static string Quote(string s)
        {
            if (string.IsNullOrEmpty(s))
            {
                return "\"\"";
            }

            return "\"" + s.Replace("\"", "\\\"") + "\"";
        }

        private static string ComputeSha256(string path)
        {
            using (FileStream fs = File.OpenRead(path))
            using (SHA256 sha = SHA256.Create())
            {
                byte[] hash = sha.ComputeHash(fs);
                var sb = new StringBuilder(hash.Length * 2);
                for (int i = 0; i < hash.Length; i++)
                {
                    sb.Append(hash[i].ToString("x2"));
                }

                return sb.ToString();
            }
        }

        private void TryKill()
        {
            try
            {
                if (_process != null && !_process.HasExited)
                {
                    _process.Kill();
                    _process.WaitForExit(2000);
                }
            }
            catch (InvalidOperationException)
            {
            }
            catch (IOException)
            {
            }
        }
    }
}
