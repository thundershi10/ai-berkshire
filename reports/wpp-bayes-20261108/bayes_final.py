import json, numpy as np, pandas as pd
from scipy.stats import t as tdist, norm, halfnorm
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

BASE = "/workspace/reports/wpp-bayes-20261108"
H = 37
TARGET_DATE = pd.Timestamp("2026-12-31")
FX_GBPUSD = 1.3385
ADR_RATIO = 5

# ---------------- data ----------------
d = json.load(open(f"{BASE}/wpp_adr.json"))["data"]["tradesTable"]["rows"]
df = pd.DataFrame(d)
df["date"] = pd.to_datetime(df["date"])
df["close"] = df["close"].str.replace("$", "", regex=False).astype(float)
df = df.sort_values("date").reset_index(drop=True)
s = df.set_index("date")["close"]
p_now = float(s.iloc[-1])
r_all = np.log(s).diff().dropna()
r26 = r_all[r_all.index.year == 2026]
print(f"data: n={len(s)}, {s.index[0].date()}..{s.index[-1].date()}, last={p_now:.2f}")

# ---------------- A1: constant-drift Student-t, 2026 YTD ----------------
def fit_const_t(r, nu=5.0, mu0=0.0003, mu_sd=0.0008, sig_scale=0.035,
                mu_lo=-0.002, mu_hi=0.003, n_mu=201, n_sig=151, seed=7,
                n_paths=30000):
    mus = np.linspace(mu_lo, mu_hi, n_mu)
    sigs = np.linspace(0.005, 0.060, n_sig)
    MU, SG = np.meshgrid(mus, sigs, indexing="ij")
    ll = np.empty_like(MU)
    for i in range(0, n_mu, 20):
        z = (r[None, None, :] - MU[i:i+20, :, None]) / SG[i:i+20, :, None]
        ll[i:i+20] = np.sum(tdist.logpdf(z, nu) - np.log(SG[i:i+20, :, None]), axis=2)
        del z
    post = ll + norm.logpdf(MU, mu0, mu_sd) + halfnorm.logpdf(SG, scale=sig_scale)
    post -= post.max()
    w = np.exp(post); w /= w.sum()
    mu_hat = float((MU * w).sum()); sig_hat = float((SG * w).sum())
    rng = np.random.default_rng(seed)
    idx = rng.choice(w.size, size=n_paths, p=w.ravel())
    mu_s = MU.ravel()[idx]; sg_s = SG.ravel()[idx]
    shocks = mu_s[:, None] + sg_s[:, None] * rng.standard_t(nu, size=(n_paths, H))
    log_path = np.cumsum(shocks, axis=1)
    price_path = p_now * np.exp(log_path)
    return dict(paths=price_path, terminal=price_path[:, -1],
                mu=mu_hat, sig=sig_hat)

# ---------------- B: local linear trend DLM, 2026 YTD ----------------
def fit_dlm(y, seed=11, n_paths=20000):
    obs = np.linspace(0.015, 0.055, 14)
    lev = np.geomspace(3e-5, 0.004, 12)
    tr = np.geomspace(1e-7, 0.0004, 12)
    recs = []
    for o in obs:
        for l in lev:
            for t in tr:
                F = np.array([[1.0, 1.0], [0.0, 1.0]])
                Q = np.diag([l**2, t**2]); Hh = np.array([[1.0, 0.0]]); R = o**2
                x = np.array([y[0], 0.0]); P = np.diag([0.5, 0.01]); ll = 0.0
                for i in range(1, len(y)):
                    x = F @ x; P = F @ P @ F.T + Q
                    v = y[i] - (Hh @ x)[0]; S = (Hh @ P @ Hh.T)[0, 0] + R
                    ll += -0.5 * (np.log(2 * np.pi * S) + v * v / S)
                    K = (P @ Hh.T / S).ravel()
                    x = x + K * v; P = P - np.outer(K, Hh @ P); P = 0.5 * (P + P.T)
                lp = (halfnorm.logpdf(o, scale=0.03) + halfnorm.logpdf(l, scale=0.001)
                      + halfnorm.logpdf(t, scale=0.0001))
                recs.append((ll + lp, o, l, t, x.copy(), P.copy()))
    recs.sort(key=lambda z: z[0], reverse=True)
    top = recs[:40]
    mx = top[0][0]
    w = np.array([np.exp(z[0] - mx) for z in top]); w /= w.sum()
    rng = np.random.default_rng(seed)
    paths = []
    for (_, o, l, t, x, P), wt in zip(top, w):
        k = max(1, int(round(n_paths * wt)))
        L = np.linalg.cholesky(P + 1e-12 * np.eye(2))
        xd = x[None, :] + rng.standard_normal((k, 2)) @ L.T
        F = np.array([[1.0, 1.0], [0.0, 1.0]])
        Q = np.diag([l**2, t**2])
        out = np.empty((k, H))
        for j in range(H):
            xd = xd @ F.T + rng.standard_normal((k, 2)) @ np.linalg.cholesky(Q + 1e-16 * np.eye(2)).T
            out[:, j] = xd[:, 0] + rng.standard_normal(k) * o
        paths.append(np.exp(out))
    paths = np.vstack(paths)
    trend = float(sum(wt * z[4][1] for z, wt in zip(top, w)))
    return dict(paths=paths, terminal=paths[:, -1], trend=trend)

# ---------------- C: analyst-target bridge ----------------
def analyst_bridge(seed=13, n_paths=15000, target=26.05, target_sd=5.03):
    # 12m consensus target; scale convergence to 37/252 of the year
    f = H / 252.0
    term_mean = p_now + f * (target - p_now)
    term_sd = 0.15 * p_now  # 2-month price uncertainty, deliberately wide
    rng = np.random.default_rng(seed)
    term = rng.normal(term_mean, term_sd, n_paths)
    # Brownian bridge from p_now to term, with 15% annualised vol
    vol = 0.50
    steps = np.arange(1, H + 1) / H
    log_start, log_end = np.log(p_now), np.log(np.clip(term, 1e-6, None))
    base = log_start + (log_end[:, None] - log_start) * steps[None, :]
    bridge = np.zeros((n_paths, H))
    for j in range(H):
        t = steps[j]
        bridge[:, j] = rng.normal(0, vol * np.sqrt(t * (1 - t) / 252), n_paths)
    return dict(paths=np.exp(base + bridge), terminal=term, term_mean=term_mean)

# ---------------- fit ----------------
a1 = fit_const_t(r26.values)
b = fit_dlm(np.log(s[s.index.year == 2026].values).astype(float))
c = analyst_bridge()

# sample counts for 0.50 / 0.30 / 0.20 weights
n = 40000
idx_a = np.random.default_rng(21).choice(len(a1["paths"]), int(n * 0.50), replace=True)
idx_b = np.random.default_rng(22).choice(len(b["paths"]), int(n * 0.30), replace=True)
idx_c = np.random.default_rng(23).choice(len(c["paths"]), int(n * 0.20), replace=True)
paths = np.vstack([a1["paths"][idx_a], b["paths"][idx_b], c["paths"][idx_c]])
term = paths[:, -1]

# ---------------- summary ----------------
def qstats(x):
    q = np.percentile(x, [2.5, 5, 10, 25, 50, 75, 90, 95, 97.5])
    return dict(q=q.tolist(), mean=float(np.mean(x)), sd=float(np.std(x)))

summ = qstats(term)
p_up = float((term > p_now).mean())
probs = {
    "up": p_up,
    "gt_52w_high": float((term > 28.77).mean()),
    "gt_30": float((term > 30).mean()),
    "gt_35": float((term > 35).mean()),
    "lt_25": float((term < 25).mean()),
    "lt_22": float((term < 22).mean()),
    "lt_20": float((term < 20).mean()),
}
# LSE pence equivalents
to_p = lambda usd: usd / ADR_RATIO / FX_GBPUSD * 100
q_p = [to_p(v) for v in summ["q"]]

out = {
    "as_of": "2026-11-06",
    "target_date": "2026-12-31",
    "horizon_trading_days": H,
    "spot_adr_usd": p_now,
    "spot_lse_pence_implied": to_p(p_now),
    "fx_gbpusd": FX_GBPUSD,
    "adr_ratio": ADR_RATIO,
    "components": {
        "A1_const_t_2026": {"mu_daily": a1["mu"], "mu_annual": a1["mu"] * 252,
                            "sigma_daily": a1["sig"],
                            "median": float(np.median(a1["terminal"])),
                            "p10": float(np.percentile(a1["terminal"], 10)),
                            "p90": float(np.percentile(a1["terminal"], 90))},
        "B_dlm_2026": {"trend_daily": b["trend"], "trend_annual": b["trend"] * 252,
                       "median": float(np.median(b["terminal"])),
                       "p10": float(np.percentile(b["terminal"], 10)),
                       "p90": float(np.percentile(b["terminal"], 90))},
        "C_analyst_bridge": {"target_12m": 26.05, "terminal_mean": c["term_mean"],
                             "median": float(np.median(c["terminal"])),
                             "p10": float(np.percentile(c["terminal"], 10)),
                             "p90": float(np.percentile(c["terminal"], 90))},
    },
    "weights": {"A1": 0.50, "B": 0.30, "C": 0.20},
    "posterior": summ,
    "posterior_pence": q_p,
    "probabilities": probs,
    "expected_return": float(np.mean(term) / p_now - 1),
    "median_return": float(np.median(term) / p_now - 1),
}
json.dump(out, open(f"{BASE}/summary.json", "w"), indent=2, ensure_ascii=False)
np.save(f"{BASE}/paths.npy", paths)

print(json.dumps(out, indent=2, ensure_ascii=False))

# ---------------- chart ----------------
hist = s[s.index >= "2024-11-01"]
dates = pd.bdate_range(s.index[-1] + pd.Timedelta(days=1), TARGET_DATE)
dates = dates[:H]
qs = np.percentile(paths, [2.5, 10, 25, 50, 75, 90, 97.5], axis=0)

fig, ax = plt.subplots(figsize=(12, 6.2), dpi=160)
ax.plot(hist.index, hist.values, color="#1f2937", lw=1.4, label="WPP ADR 收盘价")
ax.axvline(s.index[-1], color="#9ca3af", lw=0.9, ls="--")
ax.fill_between(dates, qs[0], qs[6], color="#93c5fd", alpha=0.20, label="95% 可信区间")
ax.fill_between(dates, qs[1], qs[5], color="#60a5fa", alpha=0.28, label="80% 可信区间")
ax.fill_between(dates, qs[2], qs[4], color="#3b82f6", alpha=0.30, label="50% 可信区间")
ax.plot(dates, qs[3], color="#1d4ed8", lw=1.8, label="后验中位数")
ax.scatter([dates[-1]], [qs[3][-1]], color="#1d4ed8", zorder=5, s=28)
ax.annotate(f"中位 ${qs[3][-1]:.2f}\n({(qs[3][-1]/p_now-1)*100:+.1f}%)",
            xy=(dates[-1], qs[3][-1]), xytext=(-70, 18), textcoords="offset points",
            fontsize=9, color="#1d4ed8")
ax.axhline(26.05, color="#ef4444", lw=1.0, ls=":", label="卖方12月目标均值 $26.05")
ax.set_title("WPP (NYSE: WPP) 贝叶斯后验预测：截至 2026-12-31", fontsize=14, pad=12)
ax.set_ylabel("美元 / ADR")
ax.grid(alpha=0.25, lw=0.6)
ax.legend(loc="upper left", fontsize=8.5, frameon=False, ncol=2)
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.savefig(f"{BASE}/wpp_bayes_fan.png", bbox_inches="tight")
print("saved chart")
