"""
SupplyShield - Person C, item 4: does planning WITH uncertainty beat planning WITHOUT it?

For a lane closure we compare four plans on the core graph (all flows share hub capacity, as in c_multiflow.py).
Only the lane travel-time MULTIPLIERS differ between the plans:
    deterministic : every lane cost x 1.0                      (no risk information)
    point         : every lane cost x mult_pred                (B's point prediction)
    expected      : every lane cost x mean of sampled multipliers
    CVaR          : minimises the average cost of the worst (1 - ALPHA) share of sampled scenarios
Multiplier of a lane = predicted (or realized) ratio / the lane's TRAINING-period baseline ratio, so the cost of a
lane in a scenario = median travel time (hours) x multiplier, and the objective is
    sum over lanes ( cost_e x m_e x flow_e )  +  PENALTY_HOURS x (legs never delivered).

SAMPLING (finalised by Person C): ln(m) ~ Normal( ln(mult_pred), sd ),  sd = (ln mult_hi90 - ln mult_lo90) / (2 x 1.645).
No truncation, lanes independent (a limitation: correlated bad days are ignored). mult_pred is the MEDIAN of the draw.
Planning scenarios: S per run (seed s). Scoring scenarios: 1000 fresh draws (seed 1000 + s). A plan has no recourse:
its flows are fixed before the multipliers are known.

SCORING on the realized test-day multipliers (never used for planning):
    primary    : lanes with an observed test outcome use their realized multiplier, all other lanes use 1.0
    sens_5legs : only lanes with >= 5 test legs use the realized multiplier, all others 1.0
    sens_pred  : lanes without an observed outcome use their PREDICTED multiplier instead of 1.0

Run from the project root:
    python opt/c_uncertainty.py --closures 3 --seeds 5 --scenarios 200
Inputs : models/outputs/risk_table_lane.csv, models/outputs/realized_test_lane.csv, A's core files.
Outputs: experiments/c_uncertainty_results.csv, c_uncertainty_summary.csv, c_uncertainty_intervals.csv
NOTE: the interval widths are weighted averages of representative-route conformal intervals; they are NOT formally
calibrated lane-level intervals, and results must be described that way.
"""
import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

import c_real_graph as rg

RISK = "models/outputs/risk_table_lane.csv"
REAL = "models/outputs/realized_test_lane.csv"
Z90 = 1.6448536269514722
KEY = ["source_center", "destination_center"]


def pick(df, candidates, what, required=True):
    for c in candidates:
        if c in df.columns:
            return c
    if required:
        raise SystemExit(f"Could not find the {what} column. Columns are: {df.columns.tolist()}")
    return None


# ---------------------------------------------------------------- inputs
def load_lane_inputs(G, risk_path=RISK, real_path=REAL):
    edges = list(G.edges)
    base = pd.DataFrame(edges, columns=KEY)
    risk = pd.read_csv(risk_path)
    if risk.duplicated(KEY).any():
        raise SystemExit("risk table has duplicate lanes: it must have exactly one row per directed lane")
    for col in ["mult_pred", "mult_lo90", "mult_hi90"]:
        if col not in risk.columns:
            raise SystemExit(f"{risk_path} has no column {col}. Columns are: {risk.columns.tolist()}")
    d = base.merge(risk, on=KEY, how="left")
    missing = d["mult_pred"].isna()
    print(f"risk table: {len(risk)} lanes; core lanes without a risk row: {int(missing.sum())} (multiplier 1.0, sd 0)")
    pred = d["mult_pred"].fillna(1.0).to_numpy()
    lo = d["mult_lo90"].fillna(1.0).to_numpy()
    hi = d["mult_hi90"].fillna(1.0).to_numpy()
    sd = np.where(missing, 0.0, np.maximum(np.log(hi) - np.log(lo), 0.0) / (2 * Z90))
    lo50 = d["mult_lo50"].to_numpy() if "mult_lo50" in d else np.full(len(d), np.nan)
    hi50 = d["mult_hi50"].to_numpy() if "mult_hi50" in d else np.full(len(d), np.nan)

    real = pd.read_csv(real_path)
    r_col = pick(real, ["realized_mult", "realized_multiplier", "mult_realized"], "realized multiplier")
    n_col = pick(real, ["n_test_legs", "test_legs", "n_test"], "number of test legs", required=False)
    r = base.merge(real[KEY + [r_col] + ([n_col] if n_col else [])], on=KEY, how="left")
    realized = r[r_col].to_numpy(dtype=float)
    n_test = r[n_col].fillna(0).to_numpy() if n_col else np.full(len(r), np.nan)
    observed = ~np.isnan(realized)
    if n_col:
        observed &= n_test > 0
    print(f"realized table: {int(observed.sum())} of {len(edges)} core lanes have an observed test outcome"
          + (f", {int((observed & (n_test >= 5)).sum())} with >= 5 test legs" if n_col else ""))
    score = {"primary": np.where(observed, realized, 1.0),
             "sens_pred": np.where(observed, realized, pred)}
    if n_col:
        score["sens_5legs"] = np.where(observed & (n_test >= 5), realized, 1.0)
    return dict(pred=pred, sd=sd, lo90=lo, hi90=hi, lo50=lo50, hi50=hi50, realized=realized, observed=observed,
                n_test=n_test, score=score, n_col=n_col)


# ---------------------------------------------------------------- the linear program
def solve(G, closed, cost_mult=None, scen=None, alpha=0.8):
    """Multi-flow LP. cost_mult (E,) scales the lane costs. scen (S,E): CVaR over these multiplier scenarios.
    Returns (f, U): total flow on each lane (legs/day) and total undelivered legs/day."""
    nodes, edges = list(G.nodes), list(G.edges)
    nidx = {n: i for i, n in enumerate(nodes)}
    N, E = len(nodes), len(edges)
    K = E
    src = np.array([nidx[u] for u, _ in edges])
    dst = np.array([nidx[v] for _, v in edges])
    cost = np.array([G.edges[e]["cost"] for e in edges])
    q = np.array([G.edges[e]["trips"] / rg.TRAIN_DAYS for e in edges])       # flow k = lane k, legs/day
    S = 0 if scen is None else scen.shape[0]
    iu, iF, iU, it, iz = K * E, K * E + K, K * E + K + E, K * E + K + E + 1, K * E + K + E + 2
    nvar = iz + S

    ks, es = np.repeat(np.arange(K), E), np.tile(np.arange(E), K)
    col = ks * E + es
    karr = np.arange(K)
    rows = np.concatenate([ks * N + src[es], ks * N + dst[es], karr * N + src, karr * N + dst])
    cols = np.concatenate([col, col, iu + karr, iu + karr])
    vals = np.concatenate([np.ones(K * E), -np.ones(K * E), np.ones(K), -np.ones(K)])
    # f_e = sum_k x[k, e]   and   U = sum_k u_k
    rows = np.concatenate([rows, K * N + es, K * N + np.arange(E), K * N + E + np.zeros(K, int), np.full(1, K * N + E)])
    cols = np.concatenate([cols, col, iF + np.arange(E), iu + karr, [iU]])
    vals = np.concatenate([vals, -np.ones(K * E), np.ones(E), -np.ones(K), [1.0]])
    A_eq = coo_matrix((vals, (rows, cols)), shape=(K * N + E + 1, nvar)).tocsr()
    b_eq = np.zeros(K * N + E + 1)
    b_eq[karr * N + src] += q
    b_eq[karr * N + dst] -= q

    ub_rows = [coo_matrix((np.ones(K * E), (src[es], col)), shape=(N, nvar))]       # hub capacity (outgoing legs)
    b_ub = [np.array([G.nodes[n]["cap"] for n in nodes])]
    if S:
        r_idx = np.repeat(np.arange(S), E)
        c_idx = np.tile(iF + np.arange(E), S)
        v = (scen * cost).ravel()                                                    # c_e * m_se
        m = coo_matrix((np.concatenate([v, np.full(S, rg.PENALTY_HOURS), -np.ones(S), -np.ones(S)]),
                        (np.concatenate([r_idx, np.arange(S), np.arange(S), np.arange(S)]),
                         np.concatenate([c_idx, np.full(S, iU), np.full(S, it), iz + np.arange(S)]))),
                       shape=(S, nvar))
        ub_rows.append(m)                                                            # cost_s - t - z_s <= 0
        b_ub.append(np.zeros(S))
    from scipy.sparse import vstack
    A_ub = vstack(ub_rows).tocsr()
    b_ub = np.concatenate(b_ub)

    lo, hi = np.zeros(nvar), np.full(nvar, np.inf)
    hi[iu:iF] = q
    if closed is not None:
        hi[np.arange(K) * E + edges.index(closed)] = 0.0
    obj = np.zeros(nvar)
    if S:
        lo[it], hi[it] = -np.inf, np.inf
        obj[it] = 1.0
        obj[iz:iz + S] = 1.0 / ((1 - alpha) * S)
    else:
        lo[it] = hi[it] = 0.0
        mult = np.ones(E) if cost_mult is None else cost_mult
        obj[:K * E] = np.tile(cost * mult, K)
        obj[iu:iF] = rg.PENALTY_HOURS
    res = linprog(obj, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=np.column_stack([lo, hi]), method="highs")
    if not res.success:
        raise RuntimeError(res.message)
    return res.x[iF:iF + E], float(res.x[iU])


def cvar(costs, alpha):
    k = max(1, int(round(len(costs) * (1 - alpha))))
    return float(np.sort(costs)[::-1][:k].mean())


# ---------------------------------------------------------------- experiment
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--closures", type=int, default=3)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--scenarios", type=int, default=200)
    ap.add_argument("--eval", type=int, default=1000)
    ap.add_argument("--alpha", type=float, default=0.8)
    a = ap.parse_args()

    G = rg.load_core_graph()
    edges = list(G.edges)
    E = len(edges)
    cost = np.array([G.edges[e]["cost"] for e in edges])
    inp = load_lane_inputs(G)
    pred, sd = inp["pred"], inp["sd"]
    closures = sorted(edges, key=lambda e: -G.edges[e]["trips"])[:a.closures]

    # --- interval diagnostics (observed lanes only; the realized values are never used for planning)
    obs = inp["observed"]
    diag = []
    pops = {"all observed": obs}
    if inp["n_col"]:
        pops["lanes with >= 5 test legs"] = obs & (inp["n_test"] >= 5)
    z = np.random.default_rng(0).standard_normal((2000, E))
    samp = np.exp(np.log(pred) + sd * z)
    for name, mask in pops.items():
        for lvl, lo, hi in [("90%", inp["lo90"], inp["hi90"]), ("50%", inp["lo50"], inp["hi50"])]:
            if np.isnan(lo[mask]).all():
                continue
            inside = (inp["realized"] >= lo) & (inp["realized"] <= hi)
            diag.append({"population": name, "interval": lvl, "lanes": int(mask.sum()),
                         "test_legs": (int(np.nansum(inp["n_test"][mask])) if inp["n_col"] else None),
                         "coverage_of_realized": round(float(inside[mask].mean()), 4),
                         "mean_width": round(float((hi - lo)[mask].mean()), 4),
                         "share_of_samples_inside": round(float(((samp >= lo) & (samp <= hi))[:, mask].mean()), 4)})
    diag = pd.DataFrame(diag)
    pd.set_option("display.width", 220)
    print("\nINTERVAL DIAGNOSTICS (coverage of realized test-day multipliers; share of samples inside should be "
          "about 0.90 / 0.50 if the normal approximation fits)")
    print(diag.to_string(index=False))

    # --- plan comparison
    rows = []
    t0 = time.perf_counter()
    for ci, lane in enumerate(closures, 1):
        f_det, u_det = solve(G, lane, np.ones(E))
        f_pt, u_pt = solve(G, lane, pred)
        for seed in range(a.seeds):
            plan_scen = np.exp(np.log(pred) + sd * np.random.default_rng(seed).standard_normal((a.scenarios, E)))
            f_ex, u_ex = solve(G, lane, plan_scen.mean(axis=0))
            f_cv, u_cv = solve(G, lane, scen=plan_scen, alpha=a.alpha)
            ev = np.exp(np.log(pred) + sd * np.random.default_rng(1000 + seed).standard_normal((a.eval, E)))
            for name, (f, u) in {"deterministic": (f_det, u_det), "point": (f_pt, u_pt),
                                 "expected": (f_ex, u_ex), "CVaR": (f_cv, u_cv)}.items():
                sampled = (ev * cost) @ f + rg.PENALTY_HOURS * u
                row = {"closure": f"L{ci:02d}", "lane": f"{lane[0]}->{lane[1]}", "seed": seed, "plan": name,
                       "eval_mean": sampled.mean(), "eval_cvar": cvar(sampled, a.alpha), "eval_worst": sampled.max(),
                       "unmet": u, "plan_change_vs_det": float(np.abs(f - f_det).sum() / max(f_det.sum(), 1e-12)),
                       "imputed_lanes_used": int(((f > 1e-9) & ~obs).sum())}
                for sname, m in inp["score"].items():
                    row[f"realized_{sname}"] = float((cost * m) @ f + rg.PENALTY_HOURS * u)
                rows.append(row)
            print(f"  closure {ci}/{len(closures)} seed {seed}: done ({time.perf_counter() - t0:.0f} s)")
    res = pd.DataFrame(rows)

    metrics = ["eval_mean", "eval_cvar", "eval_worst", "unmet", "plan_change_vs_det"] + \
              [c for c in res.columns if c.startswith("realized_")]
    summary = res.groupby("plan")[metrics].mean().reindex(["deterministic", "point", "expected", "CVaR"])
    print("\nAVERAGE OVER CLOSURES AND SEEDS (cost in leg-hours per day; lower is better)")
    print(summary.round(3).to_string())
    paired = res.merge(res[res.plan == "deterministic"][["closure", "seed"] + metrics],
                       on=["closure", "seed"], suffixes=("", "_det"))
    diffs = pd.DataFrame({m: paired[m] - paired[m + "_det"] for m in metrics if m not in ("unmet", "plan_change_vs_det")})
    diffs["plan"] = paired["plan"]
    d = diffs.groupby("plan").agg(["mean", "std"]).reindex(["point", "expected", "CVaR"]).round(3)
    print("\nDIFFERENCE TO THE DETERMINISTIC PLAN (negative = better than ignoring uncertainty), mean and std:")
    print(d.to_string())
    print("\nIf plan_change_vs_det is about 0, the plans are the same and any difference is noise.")

    Path("experiments").mkdir(exist_ok=True)
    res.to_csv("experiments/c_uncertainty_results.csv", index=False)
    summary.to_csv("experiments/c_uncertainty_summary.csv")
    diag.to_csv("experiments/c_uncertainty_intervals.csv", index=False)
    print("\nSaved experiments/c_uncertainty_results.csv, c_uncertainty_summary.csv, c_uncertainty_intervals.csv")


if __name__ == "__main__":
    main()
