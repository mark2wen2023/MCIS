using System;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using Mcis.Export;
using Xunit;

namespace Mcis.Pure.Tests
{
    public class FfmpegEncoderTests
    {
        [Fact]
        public async Task EncodeSyntheticFrames_WritesH264Mp4_WithWatermarkAndHash()
        {
            string dir = Path.Combine(Path.GetTempPath(), "mcis-ff-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(dir);
            string mp4 = Path.Combine(dir, "demo.mp4");
            try
            {
                const int w = 320, h = 180, fps = 10, frames = 20;
                var options = new VideoRecordOptions
                {
                    OutputMp4Path = mp4,
                    WidthPx = w,
                    HeightPx = h,
                    Fps = fps,
                    BitrateMbps = 2,
                    FfmpegPath = "ffmpeg",
                    BurnInAuditWatermark = true,
                    WatermarkText = "示例数据 / 虚构案例（仅供演示）"
                };

                float lastProgress = 0f;
                using (var encoder = new FFmpegPipeEncoder(options))
                {
                    encoder.ProgressChanged += p => lastProgress = p;
                    var result = await encoder.EncodeFramesAsync(i => MakeFrame(w, h, i, frames), frames, CancellationToken.None);
                    Assert.True(result.IsSuccess, result.ErrorMessage);
                    Assert.True(File.Exists(mp4));
                    Assert.True(new FileInfo(mp4).Length > 500);
                    Assert.Equal(frames, result.Value.TotalFrames);
                    Assert.Equal(64, result.Value.Sha256Hex.Length);
                    Assert.InRange(result.Value.DurationSeconds, 1.9, 2.1);
                    Assert.Equal(1f, lastProgress);
                }
            }
            finally
            {
                try { Directory.Delete(dir, true); } catch (IOException) { }
            }
        }

        [Fact]
        public async Task Cancel_StopsEncoding()
        {
            string mp4 = Path.Combine(Path.GetTempPath(), "mcis-ff-cancel-" + Guid.NewGuid().ToString("N") + ".mp4");
            var cts = new CancellationTokenSource();
            var options = new VideoRecordOptions
            {
                OutputMp4Path = mp4,
                WidthPx = 160,
                HeightPx = 90,
                Fps = 10,
                BitrateMbps = 1,
                FfmpegPath = "ffmpeg"
            };
            using (var encoder = new FFmpegPipeEncoder(options))
            {
                cts.Cancel();
                var result = await encoder.EncodeFramesAsync(i => MakeFrame(160, 90, i, 30), 30, cts.Token);
                Assert.False(result.IsSuccess);
                Assert.Equal("REC-CANCEL", result.ErrorCode);
            }
        }

        internal static byte[] MakeFrame(int w, int h, int index, int total)
        {
            var px = new byte[w * h * 4];
            int barX = (int)((w - 20) * (index / (double)Math.Max(total - 1, 1)));
            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    int i = (y * w + x) * 4;
                    px[i] = 12;
                    px[i + 1] = 24;
                    px[i + 2] = 48;
                    px[i + 3] = 255;
                    if (x >= barX && x < barX + 20)
                    {
                        px[i] = 60;
                        px[i + 1] = 227;
                        px[i + 2] = 255;
                    }
                }
            }

            FFmpegPipeEncoder.BurnWatermark(px, w, h, "MCIS DEMO FICTIONAL", 8, 8);
            FFmpegPipeEncoder.BurnWatermark(px, w, h, "示例数据", 8, h - 16);
            return px;
        }
    }
}
