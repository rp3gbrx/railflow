"""Station-to-station trip distribution with region-level deterrence functions.

Model A (synthetic gravity model, as in the ETC 2018 RailWatch paper):

    T_ij = A_i B_j O_i D_j f_k(c_ij)

  * O_i, D_j  - station trip ends (ORR Table 1410).
  * c_ij      - network cost (km) on the OSM rail graph.
  * f_k       - one deterrence function per government region (11 ITL1 regions)
                and direction (internal-to-internal, internal-to-external) = 22
                functions. Form follows Calibrate_Synthetic_ParmsNew.R: the
                log-normal density dlnorm(c; mu, sigma); external functions also
                carry a level term exp(gamma) that sets the region's internal /
                external split. For a pair in two different regions r, s the
                external function is the geometric mean sqrt(f_r f_s), which keeps
                the all-day matrix symmetric.
  * Calibration targets (replacing the MND TLDs of the paper): observed trip
    length distributions per segment, built from ORR Table 1595 (journeys between
    local authorities, Apr-2024 to Mar-2025). To compare like with like, both the
    observed and the modelled journeys are binned on the journey-weighted
    network distance between the two local authorities. Parameters are fitted
    jointly with a Levenberg-Marquardt-type least-squares solver (the same idea
    as the technical note, but with all segments calibrated together and the
    Furness re-run at every evaluation).

Model B (improvement - data fusion): Model A is used as the prior for a
matrix that also reproduces every observed number ORR publishes:
  * the 2,540 station 'main origin/destination' flows in Table 1410
    (41% of all journeys) are fixed cells;
  * the remaining cells are balanced (tri-proportional fitting) to the
    remaining station trip ends and to the observed LA-to-LA totals of Table 1595.
So Model B keeps the gravity pattern only where no observation exists.

Both are produced for the full year and for an average weekday (AWD).
"""
import json
import time
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.sparse import csr_matrix
from . import config as C

BANDS = np.array([0, 2.5, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 70, 80, 100, 120, 140, 160, 180,
                  200, 250, 300, 350, 400, 500, 600, 800, 1500.0])
NB = len(BANDS) - 1
LOG2PI = 0.5 * np.log(2 * np.pi)


class Data:
    def __init__(self):
        st = pd.read_csv(C.WORK / "stations.csv")
        sl = pd.read_csv(C.WORK / "station_la.csv")[["crs", "la"]]
        st = st.merge(sl, on="crs", how="left")
        self.st = st
        self.S = len(st)
        self.O_ann = st.ee_all.to_numpy() / 2
        self.O_awd = st.ee_awd.to_numpy() / 2
        self.reg_names = C.REGIONS
        self.reg = st.region.map({r: k for k, r in enumerate(C.REGIONS)}).to_numpy()
        self.R = len(C.REGIONS)
        d = np.load(C.WORK / "skim_cost_km.npy")
        d = np.maximum(d, C.MIN_DIST_KM)
        self.d = d
        self.logd = np.log(d)
        self.same = self.reg[:, None] == self.reg[None, :]
        self.offdiag = ~np.eye(self.S, dtype=bool)

        # local authorities
        las = sorted(st.la.unique())
        self.las = las
        self.la = st.la.map({l: k for k, l in enumerate(las)}).to_numpy()
        self.L = len(las)
        self.P = csr_matrix((np.ones(self.S), (np.arange(self.S), self.la)), shape=(self.S, self.L))
        la_reg = st.groupby("la").region.agg(lambda s: s.mode().iat[0])
        self.la_reg = la_reg.reindex(las).map({r: k for k, r in enumerate(C.REGIONS)}).to_numpy()

        # journey-weighted LA-to-LA network distance
        W = np.outer(self.O_ann, self.O_ann) * self.offdiag
        num = (self.P.T @ (W * d) @ self.P)
        den = (self.P.T @ W @ self.P)
        self.d_la = np.asarray(num) / np.maximum(np.asarray(den), 1e-9)
        self.band_la = np.clip(np.searchsorted(BANDS, self.d_la, side="right") - 1, 0, NB - 1)

        # observed LA-to-LA journeys (undirected, annual)
        fl = pd.read_csv(C.WORK / "la_flows_2425.csv")
        idx = {l: k for k, l in enumerate(las)}
        a = fl.la1.map(idx); b = fl.la2.map(idx)
        ok = a.notna() & b.notna()
        self.obs_la = np.zeros((self.L, self.L))
        np.add.at(self.obs_la, (a[ok].astype(int), b[ok].astype(int)), fl.journeys[ok].to_numpy())
        self.obs_la = np.triu(self.obs_la + self.obs_la.T - np.diag(np.diag(self.obs_la)))  # undirected, upper triangle
        self.obs_la = np.maximum(self.obs_la, 0.0)   # a few published cells are small negatives (ORR adjustments)
        self.obs_tld = self.tld_from_la(self.obs_la)

    def undirected_la(self, T):
        """Aggregate a station matrix to undirected LA pairs (upper triangle incl. diagonal)."""
        M = np.asarray(self.P.T @ T @ self.P)
        U = np.triu(M + M.T)
        np.fill_diagonal(U, np.diag(M))
        return U

    def tld_from_la(self, U):
        """Journeys by (region, internal/external, band) from an undirected LA matrix."""
        out = np.zeros((self.R, 2, NB))
        ri = self.la_reg[:, None] * np.ones((1, self.L), int)
        rj = self.la_reg[None, :] * np.ones((self.L, 1), int)
        iu = np.triu_indices(self.L)
        v = U[iu]; b = self.band_la[iu]; r1 = ri[iu]; r2 = rj[iu]
        same = r1 == r2
        np.add.at(out, (r1[same], 0, b[same]), v[same])
        np.add.at(out, (r1[~same], 1, b[~same]), v[~same])
        np.add.at(out, (r2[~same], 1, b[~same]), v[~same])
        return out


def unpack(theta, R):
    t = theta.reshape(R, 5)
    return t[:, 0], t[:, 1], t[:, 2], t[:, 3], t[:, 4]   # mu_int, sig_int, mu_ext, sig_ext, gamma


def log_f(D, theta):
    mu_i, s_i, mu_e, s_e, g = unpack(theta, D.R)
    r = D.reg
    ld = D.logd
    lf_int = -((ld - mu_i[r][:, None]) ** 2) / (2 * s_i[r][:, None] ** 2) - np.log(s_i[r])[:, None] - ld - LOG2PI
    lf_er = -((ld - mu_e[r][:, None]) ** 2) / (2 * s_e[r][:, None] ** 2) - np.log(s_e[r])[:, None] - ld - LOG2PI + g[r][:, None]
    lf_ext = 0.5 * (lf_er + lf_er.T)
    lf = np.where(D.same, lf_int, lf_ext)
    lf[~D.offdiag] = -np.inf
    return lf


def furness(F, O, Dd, B=None, tol=1e-5, maxit=500):
    if B is None:
        B = np.ones(len(O))
    for it in range(maxit):
        A = O / np.maximum(F @ B, 1e-300)
        B = Dd / np.maximum(F.T @ A, 1e-300)
        err = np.abs(A * (F @ B) - O).sum() / O.sum()
        if err < tol:
            break
    return A, B, it + 1, err


class Model:
    def __init__(self, D):
        self.D = D
        self.B = None
        self.nev = 0

    def matrix(self, theta, O=None):
        D = self.D
        O = D.O_ann if O is None else O
        lf = log_f(D, theta)
        F = np.exp(lf - np.nanmax(lf[np.isfinite(lf)]))
        A, B, it, err = furness(F, O, O, self.B)
        self.B = B
        return A[:, None] * F * B[None, :]

    def residuals(self, theta):
        D = self.D
        T = self.matrix(theta)
        self.nev += 1
        mod = D.tld_from_la(D.undirected_la(T))
        obs = D.obs_tld
        res = []
        for r in range(D.R):
            for k in range(2):
                o = obs[r, k] / obs[r, k].sum(); m = mod[r, k] / max(mod[r, k].sum(), 1e-9)
                res.append((m - o) * 10)   # band shares
            sh_o = obs[r, 0].sum() / (obs[r, 0].sum() + obs[r, 1].sum())
            sh_m = mod[r, 0].sum() / (mod[r, 0].sum() + mod[r, 1].sum())
            res.append(np.array([(sh_m - sh_o) * 20]))          # internal share
        return np.concatenate(res)


def initial_theta(D):
    mids = np.sqrt(np.maximum(BANDS[:-1], 1) * BANDS[1:])
    th = []
    for r in range(D.R):
        row = []
        for k in range(2):
            w = D.obs_tld[r, k] / D.obs_tld[r, k].sum()
            mu = (w * np.log(mids)).sum(); sd = np.sqrt((w * (np.log(mids) - mu) ** 2).sum())
            row += [mu, max(sd, 0.4)]
        th += row + [0.0]
    return np.array(th)


def tri_proportional(T, D, target_la, maxit=100, tol=1e-4):
    """Balance T to station rows/cols (= T's own margins) and to undirected LA-pair targets."""
    O = T.sum(1); Dd = T.sum(0)
    X = T.copy()
    P = D.P
    for it in range(maxit):
        U = D.undirected_la(X)
        with np.errstate(divide="ignore", invalid="ignore"):
            K = np.where(U > 0, target_la / U, 1.0)
        Kf = np.triu(K) + np.triu(K, 1).T                      # symmetric LA-pair factor
        X *= Kf[D.la][:, D.la]
        X *= (O / np.maximum(X.sum(1), 1e-300))[:, None]
        X *= (Dd / np.maximum(X.sum(0), 1e-300))[None, :]
        U = D.undirected_la(X)
        err = np.abs(U - target_la).sum() / target_la.sum()
        if err < tol:
            break
    return X, it + 1, err


def main_od_cells(D, keep=None):
    """Unique station main-OD pairs from Table 1410 (annual journeys, both directions)."""
    st = D.st
    ix = {c: i for i, c in enumerate(st.crs)}
    m = st.dropna(subset=["main_od_crs"])
    i = m.crs.map(ix).to_numpy(); j = m.main_od_crs.map(ix).to_numpy()
    df = pd.DataFrame({"i": np.minimum(i, j), "j": np.maximum(i, j), "J": m.main_od_journeys.to_numpy()})
    df = df[df.i != df.j].drop_duplicates(["i", "j"]).reset_index(drop=True)
    if keep is not None:
        df = df[keep(df)]
    return df


def fuse(TA, D, cells, maxit=150, tol=1e-4):
    """Model B: fixed observed cells + tri-proportional balancing of the free cells."""
    S = D.S
    F = np.zeros((S, S))
    F[cells.i, cells.j] = cells.J / 2; F[cells.j, cells.i] = cells.J / 2
    fixed = F > 0
    O = TA.sum(1)
    r_t = np.maximum(O - F.sum(1), 0.0)
    la_fixed = D.undirected_la(F)
    la_t = np.maximum(D.obs_la - la_fixed, 0.0)
    X = np.where(fixed, 0.0, TA)
    for it in range(maxit):
        U = D.undirected_la(X)
        with np.errstate(divide="ignore", invalid="ignore"):
            K = np.where(U > 0, la_t / U, 1.0)
        Kf = np.triu(K) + np.triu(K, 1).T
        X *= Kf[D.la][:, D.la]
        X *= (r_t / np.maximum(X.sum(1), 1e-300))[:, None]
        X *= (r_t / np.maximum(X.sum(0), 1e-300))[None, :]
        X = 0.5 * (X + X.T)
        err = np.abs(D.undirected_la(X) - la_t).sum() / la_t.sum()
        if err < tol:
            break
    return X + F, it + 1, err


def main():
    t0 = time.time()
    D = Data()
    print(f"data ready: {D.S} stations, {D.L} LAs ({time.time()-t0:.0f}s)")
    M = Model(D)
    th0 = initial_theta(D)
    lo = np.tile([0.0, 0.2, 0.0, 0.2, -15], D.R); hi = np.tile([7.0, 4.0, 7.5, 4.0, 15], D.R)
    th0 = np.clip(th0, lo + 1e-6, hi - 1e-6)
    import os
    cal_p = C.WORK / "calibration.json"
    cal = json.loads(cal_p.read_text()) if cal_p.exists() else {}
    if (C.WORK / "theta.npy").exists() and not os.environ.get("RECALIBRATE"):
        th = np.load(C.WORK / "theta.npy")
        print("using calibrated parameters in outputs/model/theta.npy (set RECALIBRATE=1 to re-fit)")
    else:
        r0 = M.residuals(th0)
        print(f"initial cost {0.5*(r0**2).sum():.4f}")
        sol = least_squares(M.residuals, th0, bounds=(lo, hi), method="trf", x_scale="jac",
                            diff_step=1e-3, max_nfev=60, verbose=1)
        th = sol.x
        print(f"calibrated: cost {sol.cost:.4f}, evaluations {M.nev}, {time.time()-t0:.0f}s")
        np.save(C.WORK / "theta.npy", th)
        cal.update({"initial_cost": round(0.5 * float((r0 ** 2).sum()), 4), "evaluations": int(M.nev),
                    "seconds": round(time.time() - t0), "n_parameters": int(th.size), "n_residuals": int(r0.size)})
    rf = M.residuals(th)
    print(f"final calibration cost {0.5*(rf**2).sum():.4f}")
    cal["final_cost"] = round(0.5 * float((rf ** 2).sum()), 4)

    # --- Model A matrices
    M.B = None
    TA_ann = M.matrix(th, D.O_ann)
    M.B = None
    TA_awd = M.matrix(th, D.O_awd)
    # --- Model B: data fusion (main-OD cells fixed + LA totals)
    cells = main_od_cells(D)
    TB_ann, it, err = fuse(TA_ann, D, cells)
    rerr = np.abs(TB_ann.sum(1) - D.O_ann).sum() / D.O_ann.sum()
    print(f"Model B fusion: {len(cells)} fixed cells, {it} iterations, LA error {err:.3%}, trip-end error {rerr:.3%}")
    cal.update({"fusion_fixed_cells": int(len(cells)), "fusion_iterations": int(it), "fusion_la_error": round(float(err), 5),
                "fusion_trip_end_error": round(float(rerr), 5)})
    cal_p.write_text(json.dumps(cal, indent=1))
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(TA_ann > 0, TA_awd / TA_ann, 0.0)
    TB_awd = TB_ann * ratio
    Ab, Bb, _, _ = furness(np.maximum(TB_awd, 0), D.O_awd, D.O_awd)   # re-impose weekday trip ends
    TB_awd = Ab[:, None] * TB_awd * Bb[None, :]
    np.savez_compressed(C.WORK / "matrices.npz", TA_ann=TA_ann.astype(np.float32), TA_awd=TA_awd.astype(np.float32),
                        TB_ann=TB_ann.astype(np.float32), TB_awd=TB_awd.astype(np.float32))

    # --- parameter table
    mu_i, s_i, mu_e, s_e, g = unpack(th, D.R)
    tab = pd.DataFrame({"region": D.reg_names, "mu_int": mu_i, "sigma_int": s_i, "mu_ext": mu_e, "sigma_ext": s_e, "gamma_ext": g})
    obs = D.obs_tld; modA = D.tld_from_la(D.undirected_la(TA_ann))
    mids = 0.5 * (BANDS[:-1] + BANDS[1:])
    for nm, arr in [("obs", obs), ("modelA", modA)]:
        tab[f"{nm}_int_share"] = arr[:, 0].sum(1) / (arr[:, 0].sum(1) + arr[:, 1].sum(1))
        tab[f"{nm}_mean_km_int"] = (arr[:, 0] * mids).sum(1) / arr[:, 0].sum(1)
        tab[f"{nm}_mean_km_ext"] = (arr[:, 1] * mids).sum(1) / arr[:, 1].sum(1)
    tab.to_csv(C.TAB / "deterrence_parameters.csv", index=False)
    np.save(C.WORK / "tld_obs.npy", obs); np.save(C.WORK / "tld_modelA.npy", modA)
    np.save(C.WORK / "d_la.npy", D.d_la); np.save(C.WORK / "obs_la.npy", D.obs_la)
    json.dump({"las": D.las, "bands": BANDS.tolist()}, open(C.WORK / "la_index.json", "w"))
    print(tab.round(3).to_string())
    print(f"done ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
