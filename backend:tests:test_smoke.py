import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.app import cfd_panel

def test_naca2412_cl():
    r = cfd_panel.solve_full("2412", 4.0)
    assert 0.45 < r["cl"] < 0.85                    # XFOIL ≈ 0.63
    assert abs(r["cl"] - r["cl_kutta_gamma"]) < 0.15

def test_slope_0012():
    s = cfd_panel.sweep("0012", -2, 6, 2, n_half=30)
    assert s["cl"][0] < s["cl"][-1]                 # pente positive ≈ 2π/rad