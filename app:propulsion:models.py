# app/propulsion/models.py
import math
RHO, G = 1.225, 9.81

SOURCES = {   # énergie spécifique SYSTÈME (Wh/kg) et rendement chaîne
    "lipo":        {"wh_per_kg": 180,  "eff": 0.80},
    "liion":       {"wh_per_kg": 250,  "eff": 0.80},
    "h2_700bar":   {"wh_per_kg": 900,  "eff": 0.45},  # réservoir type IV + PAC
    "gasoline_2t": {"wh_per_kg": 12000, "eff": 0.22},
    "gasoline_4t": {"wh_per_kg": 12000, "eff": 0.28},
}

def hover_power_w(mass_kg: float, n_props: int, prop_d_m: float, k=1.15) -> float:
    """Théorie de la quantité de mouvement : P = k·T^1.5/√(2ρA), par hélice."""
    T = mass_kg * G / n_props
    A = math.pi / 4 * prop_d_m**2
    return k * n_props * T**1.5 / math.sqrt(2 * RHO * A)

def static_thrust_n(prop_d_m: float, n_rps: float, Ct=0.09) -> float:
    return Ct * RHO * n_rps**2 * prop_d_m**4

def shaft_power_w(prop_d_m: float, n_rps: float, Cp=0.045) -> float:
    return Cp * RHO * n_rps**3 * prop_d_m**5

def endurance_h(mass_kg, n_props, prop_d_m, m_energy_kg, source: str) -> dict:
    p = hover_power_w(mass_kg, n_props, prop_d_m)
    s = SOURCES[source]
    e_wh = m_energy_kg * s["wh_per_kg"] * s["eff"]
    return {"hover_power_w": round(p, 1),
            "available_energy_wh": round(e_wh, 0),
            "endurance_h": round(e_wh / p, 2),
            "source": source}