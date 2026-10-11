"""CFD 2D — méthode de panneaux Hess–Smith (sources + tourbillon global + condition de Kutta).
Toujours disponible (léger, rapide) ; sert les balayages CL/CD et le champ de vitesse (VTP).
Validation attendue : NACA 2412 à α=4° → Cl ≈ 0,55–0,75 ; NACA 0012 → pente ≈ 2π/rad."""
import math
import numpy as np

def naca4(code="2412", n_half=60):
    """Contour fermé : TE → extrados → LE → intrados → TE (coeff. -0.1036 : TE fermé)."""
    m, p, t = int(code[0])/100.0, int(code[1])/10.0, int(code[2:])/100.0
    b = np.linspace(0.0, math.pi, n_half+1)
    x = 0.5*(1.0-np.cos(b))
    yt = 5*t*(0.2969*np.sqrt(x)-0.1260*x-0.3516*x**2+0.2843*x**3-0.1036*x**4)
    if m > 0 and p > 0:
        yc = np.where(x < p, m/p**2*(2*p*x-x**2), m/(1-p)**2*((1-2*p)+2*p*x-x**2))
        dy = np.where(x < p, 2*m/p**2*(p-x), 2*m/(1-p)**2*(p-x))
    else:
        yc = np.zeros_like(x); dy = np.zeros_like(x)
    th = np.arctan(dy)
    xu, yu = x - yt*np.sin(th), yc + yt*np.cos(th)
    xl, yl = x + yt*np.sin(th), yc - yt*np.cos(th)
    up = np.column_stack([xu[::-1], yu[::-1]])      # TE -> LE
    lo = np.column_stack([xl, yl])[1:-1]            # LE+ -> TE-
    return np.vstack([up, lo])

def _puv(px, py, x1, y1, x2, y2, eps=1e-12):
    """Vitesses unitaires (source, tourbillon) au point (px,py) — feuilles sur le segment."""
    dx, dy = x2-x1, y2-y1
    L = math.hypot(dx, dy); ct, st = dx/L, dy/L
    ex, ey = px-x1, py-y1
    xi = ex*ct + ey*st; eta = -ex*st + ey*ct; xiL = xi - L
    r1 = xi*xi + eta*eta + eps; r2 = xiL*xiL + eta*eta + eps
    t1 = math.atan2(eta, xi); t2 = math.atan2(eta, xiL)
    lr = 0.25/math.pi*math.log(r1/r2)
    usl, vsl = lr, (t2-t1)/(2*math.pi)
    uvl, vvl = (t1-t2)/(2*math.pi), lr
    return (usl*ct - vsl*st, usl*st + vsl*ct,
            uvl*ct - vvl*st, uvl*st + vvl*ct)

def _puv_np(px, py, x1, y1, x2, y2, eps=1e-12):
    dx, dy = x2-x1, y2-y1
    L = math.hypot(dx, dy); ct, st = dx/L, dy/L
    ex, ey = px-x1, py-y1
    xi = ex*ct + ey*st; eta = -ex*st + ey*ct; xiL = xi - L
    r1 = xi*xi + eta*eta + eps; r2 = xiL*xiL + eta*eta + eps
    t1 = np.arctan2(eta, xi); t2 = np.arctan2(eta, xiL)
    lr = 0.25/np.pi*np.log(r1/r2)
    usl, vsl = lr, (t2-t1)/(2*np.pi)
    uvl, vvl = (t1-t2)/(2*np.pi), lr
    return usl*ct - vsl*st, usl*st + vsl*ct, uvl*ct - vvl*st, uvl*st + vvl*ct

def solve_panels(P, alpha_deg, Vinf=20.0):
    N = len(P)
    a = math.radians(alpha_deg)
    Vv = np.array([Vinf*math.cos(a), Vinf*math.sin(a)])
    X1, Y1 = P[:, 0], P[:, 1]
    X2, Y2 = np.roll(P, -1, axis=0)[:, 0], np.roll(P, -1, axis=0)[:, 1]
    L = np.hypot(X2-X1, Y2-Y1)
    ct, st = (X2-X1)/L, (Y2-Y1)/L
    nx, ny = st, -ct                       # normales sortantes
    tx, ty = ct, st
    mx, my = 0.5*(X1+X2), 0.5*(Y1+Y2)
    A = np.zeros((N+1, N+1)); b = np.zeros(N+1)
    for i in range(N):
        for j in range(N):
            if i == j:
                Ans, Ats, Ang, Atg = -0.5, 0.0, 0.0, -0.5
            else:
                usx, usy, uvx, uvy = _puv(mx[i], my[i], X1[j], Y1[j], X2[j], Y2[j])
                Ans = nx[i]*usx + ny[i]*usy; Ats = tx[i]*usx + ty[i]*usy
                Ang = nx[i]*uvx + ny[i]*uvy; Atg = tx[i]*uvx + ty[i]*uvy
            A[i, j] += Ans; A[i, N] += Ang
            if i == 0:      A[N, j] += Ats; A[N, N] += Atg      # Kutta (panneau TE extrados)
            elif i == N-1:  A[N, j] -= Ats; A[N, N] -= Atg      # Kutta (panneau TE intrados)
        b[i] = -(Vv[0]*nx[i] + Vv[1]*ny[i])
    b[N] = -(Vv[0]*tx[0]+Vv[1]*ty[0]) - (Vv[0]*tx[N-1]+Vv[1]*ty[N-1])
    sol = np.linalg.solve(A, b)
    sigma, gamma = sol[:N], sol[N]
    vt = np.zeros(N)
    for i in range(N):
        u, v = Vv[0], Vv[1]
        for j in range(N):
            if i == j: continue
            usx, usy, uvx, uvy = _puv(mx[i], my[i], X1[j], Y1[j], X2[j], Y2[j])
            u += usx*sigma[j] + uvx*gamma; v += usy*sigma[j] + uvy*gamma
        vt[i] = u*tx[i] + v*ty[i] - 0.5*gamma
    cp = 1.0 - (vt/Vinf)**2
    Fy = float(np.sum(-cp*ny*L)); Fx = float(np.sum(-cp*nx*L))
    return dict(N=N, sigma=sigma, gamma=gamma, cp=cp,
                cl=Fy*math.cos(a) - Fx*math.sin(a),
                cdp=Fx*math.cos(a) + Fy*math.sin(a),
                cl_gamma=2.0*gamma*float(np.sum(L))/Vinf,
                X1=X1, Y1=Y1, X2=X2, Y2=Y2, mx=mx, my=my,
                alpha_deg=alpha_deg, Vinf=Vinf)

def cd_estimate(cl, alpha_deg, re, tc, ar=None, e=0.85):
    """CD = frottement (plaque plane turbulente + facteur de forme) + induit + décrochage empirique."""
    a = math.radians(alpha_deg)
    cf = 0.074/max(re, 1e4)**0.2
    cd0 = 2*cf*(1.0 + 2.0*tc + 60.0*tc**4)
    cdi = cl**2/(math.pi*ar*e) if ar else 0.0
    a_stall = math.radians(8.0 + 40.0*tc)
    s = 0.0 if a <= a_stall else min(1.0, (a-a_stall)/math.radians(8.0))
    cl_eff = cl + s*(math.sin(2*a) - cl)
    return cd0 + cdi + 1.1*math.sin(a)**2*s, cl_eff, s

def solve_full(code, alpha_deg, re=1e6, ar=None, n_half=60):
    r = solve_panels(naca4(code, n_half), alpha_deg)
    cd, cl_eff, stall = cd_estimate(r["cl"], alpha_deg, re, int(code[2:])/100.0, ar)
    return {"code": code, "alpha_deg": alpha_deg, "re": re, "ar": ar,
            "cl": round(r["cl"], 4), "cl_kutta_gamma": round(r["cl_gamma"], 4),
            "cl_eff": round(cl_eff, 4), "cd_est": round(cd, 5),
            "cd_pressure": round(abs(r["cdp"]), 5), "stall_blend": round(stall, 3),
            "x_mid": [round(float(v), 4) for v in r["mx"]],
            "cp": [round(float(v), 4) for v in r["cp"]],
            "method": "Hess–Smith (sources + tourbillon, Kutta) — inviscide + corrections empiriques"}

def sweep(code, a0=-6.0, a1=16.0, step=1.0, re=1e6, ar=None, n_half=50):
    P = naca4(code, n_half)
    tc = int(code[2:])/100.0
    alphas, cls, cleffs, cds, ldrs = [], [], [], [], []
    for a in np.arange(a0, a1 + 1e-9, step):
        r = solve_panels(P, float(a))
        cd, cl_eff, _ = cd_estimate(r["cl"], float(a), re, tc, ar)
        alphas.append(round(float(a), 2)); cls.append(round(r["cl"], 4))
        cleffs.append(round(cl_eff, 4)); cds.append(round(cd, 5))
        ldrs.append(round(cl_eff/cd, 2) if cd > 0 else None)
    return {"code": code, "re": re, "ar": ar, "alpha": alphas, "cl": cls,
            "cl_eff": cleffs, "cd": cds, "ldr": ldrs}

def field_file(code, alpha_deg, n_half=60, nx=28, ny=22):
    """Champ de vitesse autour du profil → fichier VTP (ParaView Glance)."""
    r = solve_panels(naca4(code, n_half), alpha_deg)
    xs, ys = np.meshgrid(np.linspace(-0.5, 1.8, nx), np.linspace(-0.9, 0.9, ny))
    a = math.radians(alpha_deg); V = r["Vinf"]
    U = np.full(xs.shape, V*math.cos(a)); W = np.full(xs.shape, V*math.sin(a))
    for j in range(r["N"]):
        usx, usy, uvx, uvy = _puv_np(xs, ys, r["X1"][j], r["Y1"][j], r["X2"][j], r["Y2"][j])
        U += usx*r["sigma"][j] + uvx*r["gamma"]; W += usy*r["sigma"][j] + uvy*r["gamma"]
    from .core import register_file
    return register_file("cfd", f"champ-{code}-{alpha_deg:+.1f}deg.vtp", _vtp(r, xs, ys, U, W))

def _vtp(r, xs, ys, U, W):
    N, G = r["N"], xs.size
    pts = [f"{r['mx'][i]:.6f} {r['my'][i]:.6f} 0" for i in range(N)]
    pts += [f"{x:.6f} {y:.6f} 0" for x, y in zip(xs.ravel(), ys.ravel())]
    cps = [f"{c:.4f}" for c in r["cp"]] + ["0"]*G
    vecs = ["0 0 0"]*N + [f"{u:.4f} {v:.4f} 0" for u, v in zip(U.ravel(), W.ravel())]
    line_conn = " ".join(str(i) for i in range(N)) + " 0"
    vert_conn = " ".join(str(N+i) for i in range(G))
    vert_off = " ".join(str(i+1) for i in range(G))
    return f"""<?xml version="1.0"?>
<VTKFile type="PolyData" version="0.1" byte_order="LittleEndian">
<PolyData>
<Piece NumberOfPoints="{N+G}" NumberOfVerts="{G}" NumberOfLines="1" NumberOfStrips="0" NumberOfPolys="0">
<Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">{' '.join(pts)}</DataArray></Points>
<Verts><DataArray type="Int64" Name="connectivity" format="ascii">{vert_conn}</DataArray><DataArray type="Int64" Name="offsets" format="ascii">{vert_off}</DataArray></Verts>
<Lines><DataArray type="Int64" Name="connectivity" format="ascii">{line_conn}</DataArray><DataArray type="Int64" Name="offsets" format="ascii">{N+1}</DataArray></Lines>
<PointData Scalars="Cp"><DataArray type="Float64" Name="Cp" format="ascii">{' '.join(cps)}</DataArray><DataArray type="Float64" Name="U" NumberOfComponents="3" format="ascii">{' '.join(vecs)}</DataArray></PointData>
</Piece>
</PolyData>
</VTKFile>"""