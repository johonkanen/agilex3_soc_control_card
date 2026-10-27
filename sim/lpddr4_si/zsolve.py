"""2D field solve (finite-difference Laplace) of a single trace in the JLC08161H-3313 stack-up: Z0 and delay vs width.

  python3 zsolve.py

Inner layer In2: plane In1 0.1 mm above (core, er 4.6), trace 15.2 um embedded in the 2116 prepreg (er 4.16), next
plane below = In3 (0.357 mm) or In4 (0.672 mm) depending on what lies under the route; In5 is the mirror image.
Outer layer F.Cu: 35 um trace on 0.0994 mm 3313 prepreg (er 4.1) over In1, 30 um solder mask (er 3.5) on top.
Checked against the earlier field solve (LPDDR4_SWIZZLE_PLAN.md): In2 0.18 mm = 39.8 ohm, 0.12 mm = 48.6 ohm;
F.Cu 0.15 mm = 51 ohm. Dielectric loss is not computed (C only).
"""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

C0 = 299792458.0
EPS0 = 8.8541878128e-12


def solve(layers, w, t_cu, z_tr, dx=5e-6, dz=2.5e-6, span=3e-3):
    """layers: list of (thickness, er) from z=0 (bottom plane) upwards; top of the stack is a plane if top_plane,
    otherwise air above. Trace: width w, thickness t_cu, bottom at z_tr. Returns (Z0, eps_eff)."""
    H = sum(t for t, _ in layers)
    nx, nz = int(span / dx) + 1, int(round(H / dz)) + 1
    x = (np.arange(nx) - (nx - 1) / 2) * dx; z = np.arange(nz) * dz
    # cell permittivity (cells between nodes), from the layer list
    zc = (z[:-1] + z[1:]) / 2
    er_c = np.empty(nz - 1); zt = 0
    for t, er in layers:
        er_c[(zc >= zt) & (zc < zt + t + 1e-12)] = er; zt += t
    cond = (np.abs(x)[:, None] <= w / 2 + 1e-12) & (z[None, :] >= z_tr - 1e-12) & (z[None, :] <= z_tr + t_cu + 1e-12)

    def cap(er_cells):
        E = np.repeat(er_cells[None, :], nx - 1, axis=0)                 # (nx-1, nz-1) cells
        # edge conductances: horizontal edge (i,j)-(i+1,j) averages the cells below/above it, vertical likewise
        Eh = np.zeros((nx - 1, nz)); Eh[:, 1:] += E / 2; Eh[:, :-1] += E / 2
        Eh[:, 0] *= 2; Eh[:, -1] *= 2                                      # boundary rows: one cell only
        Ev = np.zeros((nx, nz - 1)); Ev[1:, :] += E / 2; Ev[:-1, :] += E / 2
        Ev[0, :] *= 2; Ev[-1, :] *= 2
        gh = Eh * dz / dx; gv = Ev * dx / dz                               # per unit length, times eps0
        idx = np.arange(nx * nz).reshape(nx, nz)
        fixed = np.zeros((nx, nz), bool); fixed[:, 0] = True; fixed[:, -1] = True; fixed |= cond
        V = np.where(cond, 1.0, 0.0)
        rows, cols, vals = [], [], []
        diag = np.zeros((nx, nz))
        for (a, b, g) in ((idx[:-1, :], idx[1:, :], gh), (idx[:, :-1], idx[:, 1:], gv)):
            rows += [a.ravel(), b.ravel()]; cols += [b.ravel(), a.ravel()]; vals += [-g.ravel(), -g.ravel()]
            np.add.at(diag.ravel(), a.ravel(), g.ravel()); np.add.at(diag.ravel(), b.ravel(), g.ravel())
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nx * nz,) * 2)
        A = A + sp.diags(diag.ravel())
        free = ~fixed.ravel()
        rhs = -A[free][:, ~free] @ V.ravel()[~free]
        Vf = V.ravel().copy(); Vf[free] = spla.spsolve(A[free][:, free].tocsc(), rhs)
        Q = (A @ Vf)[cond.ravel()].sum()                                   # charge on the trace (per eps0)
        return Q * EPS0
    C = cap(er_c); Ca = cap(np.ones_like(er_c))
    return 1 / (C0 * np.sqrt(C * Ca)), C / Ca


def inner(w, below='In3'):
    # z = 0 at the lower plane; trace on top of the core below In1 (layer order from the bottom)
    gap = 0.3568e-3 if below == 'In3' else 0.3568e-3 + 0.0152e-3 + 0.3e-3
    t = 0.0152e-3
    layers = [(gap, 4.16), (t, 4.16), (0.1e-3, 4.6)]
    return solve(layers, w, t, gap)


def outer(w):
    # F.Cu microstrip: plane In1 at z = 0, prepreg, trace + mask, then air (modelled as a box 1 mm high, plane on top)
    t = 0.035e-3; mask = 0.03e-3
    layers = [(0.0994e-3, 4.1), (t, 3.5), (mask, 3.5), (1.0e-3, 1.0)]
    return solve(layers, w, t, 0.0994e-3, dz=2.5e-6)


if __name__ == '__main__':
    print('In2/In5 stripline (In1 0.1 mm above):')
    for below in ('In3', 'In4'):
        for w in (0.18, 0.15, 0.12, 0.10, 0.09, 0.08, 0.075):
            z, ee = inner(w * 1e-3, below)
            print(f'  plane below {below}: w {w:.3f} mm  Z0 {z:5.1f} ohm  {np.sqrt(ee) / C0 * 1e9:.2f} ps/mm')
    print('F.Cu/B.Cu microstrip (In1/In6 0.0994 mm below, 30 um mask):')
    for w in (0.20, 0.15, 0.12, 0.10, 0.09):
        z, ee = outer(w * 1e-3)
        print(f'  w {w:.3f} mm  Z0 {z:5.1f} ohm  {np.sqrt(ee) / C0 * 1e9:.2f} ps/mm')
