# -*- coding: utf-8 -*-
"""Re-plot the posterior fan chart with a clean, non-overlapping legend."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

BASE = "/workspace/reports/wpp-bayes-20261108"
H = 37
TARGET_DATE = pd.Timestamp("2026-12-31")

for cand in ["Noto Sans CJK SC", "Noto Sans CJK JP", "WenQuanYi Micro Hei"]:
    if any(cand == f.name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.sans-serif"] = [cand]
        break
plt.rcParams["axes.unicode_minus"] = False

rows = json.load(open(f"{BASE}/wpp_adr.json"))["data"]["tradesTable"]["rows"]
df = pd.DataFrame(rows)
df["date"] = pd.to_datetime(df["date"])
df["close"] = df["close"].str.replace("$", "", regex=False).astype(float)
s = df.sort_values("date").set_index("date")["close"]
p_now = float(s.iloc[-1])

paths = np.load(f"{BASE}/paths.npy")
qs = np.percentile(paths, [2.5, 10, 25, 50, 75, 90, 97.5], axis=0)

hist = s[s.index >= "2024-11-01"]
dates = pd.bdate_range(s.index[-1] + pd.Timedelta(days=1), TARGET_DATE)[:H]

fig, ax = plt.subplots(figsize=(12, 6.4), dpi=170)
ax.plot(hist.index, hist.values, color="#1f2937", lw=1.5, label="WPP ADR 收盘价")
ax.axvline(s.index[-1], color="#9ca3af", lw=0.9, ls="--")
ax.fill_between(dates, qs[0], qs[6], color="#93c5fd", alpha=0.22, label="95% 可信区间")
ax.fill_between(dates, qs[1], qs[5], color="#60a5fa", alpha=0.30, label="80% 可信区间")
ax.fill_between(dates, qs[2], qs[4], color="#2563eb", alpha=0.36, label="50% 可信区间")
ax.plot(dates, qs[3], color="#1d4ed8", lw=2.0, label="后验中位数")
ax.scatter([dates[-1]], [qs[3][-1]], color="#1d4ed8", zorder=5, s=30)
ax.annotate(f"中位 ${qs[3][-1]:.2f}  ({(qs[3][-1]/p_now-1)*100:+.1f}%)",
            xy=(dates[-1], qs[3][-1]), xytext=(8, -22), textcoords="offset points",
            fontsize=10.5, color="#1d4ed8", fontweight="bold")
ax.axhline(26.05, color="#ef4444", lw=1.1, ls=":", label="卖方 12 个月目标均值 $26.05")

ax.set_title("WPP (NYSE: WPP) 贝叶斯后验预测：截至 2026-12-31", fontsize=15, pad=14)
ax.set_ylabel("美元 / ADR", fontsize=11)
ax.set_ylim(10, 60)
ax.grid(alpha=0.25, lw=0.6)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(loc="lower left", fontsize=9.5, frameon=True, framealpha=0.92,
          edgecolor="#e5e7eb", ncol=2, columnspacing=1.4)
plt.tight_layout()
plt.savefig(f"{BASE}/wpp_bayes_fan.png", bbox_inches="tight")
print("saved chart", fig.get_size_inches())
