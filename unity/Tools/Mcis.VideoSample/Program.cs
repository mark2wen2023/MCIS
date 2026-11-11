using System;
using System.IO;
using System.Threading;
using Mcis.Export;

// Note: MakeFrame is internal in tests - we duplicate a simple generator here.
internal static class Program
{
    private static int Main(string[] args)
    {
        string mp4 = args.Length > 0 ? args[0] : "/workspace/maritime-sim-design/samples/Demo_LilyMary_合成帧.mp4";
        const int w = 640, h = 360, fps = 15, frames = 45;
        var options = new VideoRecordOptions
        {
            OutputMp4Path = mp4,
            WidthPx = w,
            HeightPx = h,
            Fps = fps,
            BitrateMbps = 4,
            FfmpegPath = "ffmpeg",
            BurnInAuditWatermark = true,
            WatermarkText = "示例数据 / 虚构案例（仅供演示）"
        };
        using (var encoder = new FFmpegPipeEncoder(options))
        {
            var result = encoder.EncodeFramesAsync(i => Frame(w, h, i, frames), frames, CancellationToken.None).GetAwaiter().GetResult();
            if (!result.IsSuccess)
            {
                Console.Error.WriteLine(result.ErrorCode + " " + result.ErrorMessage);
                return 1;
            }
            Console.WriteLine("MP4=" + result.Value.FilePath);
            Console.WriteLine("FRAMES=" + result.Value.TotalFrames);
            Console.WriteLine("DURATION=" + result.Value.DurationSeconds.ToString("F2"));
            Console.WriteLine("SHA256=" + result.Value.Sha256Hex);
            Console.WriteLine("BYTES=" + new FileInfo(result.Value.FilePath).Length);
        }
        return 0;
    }

    private static byte[] Frame(int w, int h, int index, int total)
    {
        var px = new byte[w * h * 4];
        int barX = (int)((w - 40) * (index / (double)Math.Max(total - 1, 1)));
        for (int y = 0; y < h; y++)
        {
            for (int x = 0; x < w; x++)
            {
                int i = (y * w + x) * 4;
                px[i] = 12; px[i + 1] = 24; px[i + 2] = 40; px[i + 3] = 255;
                if (x >= barX && x < barX + 40)
                {
                    px[i] = 60; px[i + 1] = 227; px[i + 2] = 255;
                }
            }
        }
        FFmpegPipeEncoder.BurnWatermark(px, w, h, "MCIS DEMO FICTIONAL", 16, 16);
        FFmpegPipeEncoder.BurnWatermark(px, w, h, "LILY / MARY", 16, h - 24);
        return px;
    }
}
