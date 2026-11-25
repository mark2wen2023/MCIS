"""Draw the two comparisons from the experiment's measured CSV."""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("png", type=Path)
    args = parser.parse_args()
    with args.csv.open() as f:
        rows = {(int(float(r["offset_x_m"])), r["mode"]): r for r in csv.DictReader(f)
                if float(r["edge_true_m"]) == .001}
    from matplotlib import font_manager
    candidates = ["Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", "SimHei"]
    installed = {font.name for font in font_manager.fontManager.ttflist}
    plt.rcParams["font.sans-serif"] = [name for name in candidates if name in installed] + ["DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
    ax, err = axes
    offsets = [1024, 8192, 16384, 32768, 1000000]
    x = np.arange(len(offsets))
    for mode, color, label, delta in [("global", "#ad580f", "全局 float32", -.19),
                                       ("local_from_f64", "#167078", "局部 float32", .19)]:
        for i, offset in enumerate(offsets):
            r = rows[offset, mode]
            if r["export"] == "written":
                ax.bar(x[i] + delta, float(r["stored_edge_m"]) * 1000, width=.34,
                       color=color, label=label if i == 0 else None)
            else:
                ax.scatter(x[i] + delta, .04, marker="x", color=color, s=45,
                           label="拒绝写出" if i == 3 else None)
    ax.axhline(1, color=".35", linestyle=":", linewidth=1.5)
    ax.set(xticks=x, xticklabels=["1,024", "8,192", "16,384", "32,768", "100万"],
           ylabel="GLB 读回边长（毫米）", xlabel="合成全局原点 x（米）",
           title="A　实际写出的边有多长？", ylim=(0, 2.15))
    ax.legend(fontsize=9)
    offsets = [32768, 10**6, 10**8, 10**12, 2**44]
    for field, label, color, marker, line in [
        ("error_restored_global32_m", "还原为单个全局 float32", "#ad580f", "o", "-"),
        ("error_restored_global64_m", "还原为单个全局 float64", "#365caa", "s", "--"),
        ("error_split_frame_m", "原点与局部余量分别保留", "#167078", "+", ":")]:
        err.plot(range(5), [float(rows[o, "local_from_decimal"][field]) * 1000 for o in offsets],
                 label=label, marker=marker, color=color, linestyle=line, linewidth=1.6)
    err.set(yscale="log", xticks=range(5), xticklabels=["32,768", "100万", "1亿", "1万亿", "2^44"],
            ylabel="最大顶点误差（毫米，对数刻度）", xlabel="合成全局原点 x（米）",
            title="B　还原到全局时还剩多少误差？")
    from matplotlib.ticker import FuncFormatter
    err.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{y:g}"))
    err.legend(fontsize=9)
    for a in axes:
        a.grid(axis="y", alpha=.18)
        a.spines[["top", "right"]].set_visible(False)
    fig.suptitle("同一条 1 毫米短边，移远原点后的写出与读回", fontsize=16, fontweight="bold")
    fig.savefig(args.png, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
