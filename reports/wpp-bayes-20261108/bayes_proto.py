import json, numpy as np, pandas as pd
from scipy.stats import t as tdist, norm, halfnorm
from scipy.special import gammaln

PATH = "/workspace/reports/wpp-bayes-20261108/wpp_adr.json"
H = 37  # trading days from 2026-11-06 to 2026-12-31

# ---------- data ----------
d = json.load(open(PATH))["data"]["tradesTable"]["rows"]
df = pd.DataFrame(d)
df["date"] = pd.to_datetime(df["date"])
df["close"] = df["close"].str.replace("$", "", regex=False).astype(float)
df = df.sort_values("date").reset_index(drop=True)
s = df.set_index("date")["close"]
r_all = np.log(s).diff().dropna()
r26 = r_all[r_all.index.year == 2026]
p_now = float(s.iloc[-1])
print(f"n={len(s)} last={s.index[-1].date()} p={p_now:.2f} r26_n={len(r26)}")

# ---------- Model A: constant-drift Student-t, grid posterior ----------
def fit_const_t(r, nu=5.0, mu0=0.0003, mu_sd=0.0008, sig_scale=0.035,
                mu_lo=-0.002, mu_hi=0.003, n_mu=201, n_sig=151, seed=7):
    mus = np.linspace(mu_lo, mu_hi, n_mu)
    sigs = np.linspace(0.005, 0.060, n_sig)
    MU, SG = np.meshgrid(mus, sigs, indexing="ij")
    # log likelihood in chunks to limit memory
    ll = np.empty_like(MU)
    for i in range(0, n_mu, 20):
        mu_chunk = MU[i:i+20]
        z = (r[None, None, :] - mu_chunk[:, :, None]) / SG[i:i+20, :, None]
        ll[i:i+20] = np.sum(tdist.logpdf(z, nu) - np.log(SG[i:i+20, :, None]), axis=2)
        del z
    # priors
    lp = norm.logpdf(MU, mu0, mu_sd) + halfnorm.logpdf(SG, scale=sig_scale)
    post = ll + lp
    post -= post.max()
    w = np.exp(post); w /= w.sum()
    # posterior summaries
    mu_hat = float((MU * w).sum()); sig_hat = float((SG * w).sum())
    # predictive: weighted parameter draws + t errors
    rng = np.random.default_rng(seed)
    flat_w = w.ravel(); idx = rng.choice(len(flat_w), size=40000, p=flat_w)
    mu_s = MU.ravel()[idx]; sg_s = SG.ravel()[idx]
    sims = mu_s[:, None] + sg_s[:, None] * rng.standard_t(nu, size=(len(idx), H))
    term = p_now * np.exp(sims.sum(axis=1))
    return dict(mu=mu_hat, sig=sig_hat, term=term, name=f"const-t ({len(r)} obs)")

# ---------- Model B: local linear trend DLM, marginal-likelihood grid ----------
def dlm_loglik(y, obs_sd, lev_sd, tr_sd):
    n = len(y)
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    Q = np.diag([lev_sd**2, tr_sd**2])
    H = np.array([[1.0, 0.0]])
    R = obs_sd**2
    x = np.array([y[0], 0.0])
    P = np.diag([0.5, 0.01])
    ll = 0.0
    for t in range(1, n):
        x = F @ x
        P = F @ P @ F.T + Q
        v = y[t] - (H @ x)[0]
        S = (H @ P @ H.T)[0, 0] + R
        ll += -0.5 * (np.log(2 * np.pi * S) + v * v / S)
        K = (P @ H.T / S).ravel()
        x = x + K * v
        P = P - np.outer(K, H @ P)
        P = 0.5 * (P + P.T)
    return ll, x, P

def fit_dlm(y, seed=11):
    obs = np.linspace(0.015, 0.045, 12)
    lev = np.geomspace(0.00003, 0.003, 10)
    tr = np.geomspace(1e-7, 0.00025, 10)
    recs = []
    for o in obs:
        for l in lev:
            for t in tr:
                ll, x, P = dlm_loglik(y, o, l, t)
                lp = halfnorm.logpdf(o, scale=0.03) + halfnorm.logpdf(l, scale=0.001) + halfnorm.logpdf(t, scale=0.0001)
                recs.append((ll + lp, o, l, t, x.copy(), P.copy()))
    recs.sort(key=lambda z: z[0], reverse=True)
    top = recs[:40]
    mx = max(z[0] for z in top)
    w = np.array([np.exp(z[0] - mx) for z in top]); w /= w.sum()
    rng = np.random.default_rng(seed)
    term = []
    for (_, o, l, t, x, P), wt in zip(top, w):
        k = max(1, int(round(20000 * wt)))
        # draw state from posterior at T
        L = np.linalg.cholesky(P + 1e-12 * np.eye(2))
        xd = x[None, :] + rng.standard_normal((k, 2)) @ L.T
        F = np.array([[1.0, 1.0], [0.0, 1.0]])
        Q = np.diag([l**2, t**2])
        for _ in range(H):
            xd = xd @ F.T + rng.standard_normal((k, 2)) @ np.linalg.cholesky(Q + 1e-16 * np.eye(2)).T
        # terminal observed price = exp(latent log-price level + observation noise)
        y_term = xd[:, 0] + rng.standard_normal(k) * o
        term.append(np.exp(y_term))
    term = np.concatenate(term)
    # current trend estimate (weighted)
    tr_hat = float(sum(wt * z[4][1] for z, wt in zip(top, w)))
    return dict(term=term, trend=tr_hat, name="DLM local-linear-trend")

def summarize(name, term):
    q = np.percentile(term, [2.5, 5, 10, 25, 50, 75, 90, 95, 97.5])
    prob_up = (term > p_now).mean()
    return dict(name=name, q=q, prob_up=prob_up, mean=term.mean(),
                exp_ret=term.mean()/p_now-1,
                p10=q[2]/p_now-1, p50=q[4]/p_now-1, p90=q[6]/p_now-1)

a1 = fit_const_t(r26.values)
a2 = fit_const_t(r_all.values)
b = fit_dlm(np.log(s.values).astype(float))
res = []
res.append(summarize("A1 常数漂移+Student-t (2026YTD)", a1["term"]))
res.append(summarize("A2 常数漂移+Student-t (5年)", a2["term"]))
res.append(summarize("B 局部线性趋势DLM (5年)", b["term"]))
for x in res:
    print("\n", x["name"])
    print("  mean %.2f (%+.1f%%) prob_up %.1f%%" % (x["mean"], x["exp_ret"]*100, x["prob_up"]*100))
    print("  q2.5/10/50/90/97.5:", " ".join(f"{v:.2f}" for v in x["q"][[0,2,4,6,8]]))
    print("  ret p10/p50/p90: %+.1f%% / %+.1f%% / %+.1f%%" % (x["p10"]*100, x["p50"]*100, x["p90"]*100))
print("\nDLM current trend (daily): %.5f  (annualized %.1f%%)" % (b["trend"], b["trend"]*252*100))
print("A1 mu %.5f annual %.1f%%, sig %.5f" % (a1["mu"], a1["mu"]*252*100, a1["sig"]))
print("A2 mu %.5f annual %.1f%%, sig %.5f" % (a2["mu"], a2["mu"]*252*100, a2["sig"]))

np.save("/workspace/reports/wpp-bayes-20261108/term_A1.npy", a1["term"])
np.save("/workspace/reports/wpp-bayes-20261108/term_A2.npy", a2["term"])
np.save("/workspace/reports/wpp-bayes-20261108/term_B.npy", b["term"])
