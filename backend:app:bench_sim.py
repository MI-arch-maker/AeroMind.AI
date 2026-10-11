"""Simulateur interne : multirotor 6 DDL (mixeur + cascades PID) et voilure fixe guidée.
Aucune dépendance externe ; géorepérage, batterie, violations tracées."""
import math
import numpy as np

G = 9.81; RHO = 1.225

def _clamp(v, lo, hi): return max(lo, min(hi, v))
def _wrap(a):
    while a > math.pi: a -= 2*math.pi
    while a < -math.pi: a += 2*math.pi
    return a

class _Base:
    def _violation(self, key, msg):
        if key not in self._violated:
            self._violated.add(key); self._viol.append(f"[{self.t:7.1f}s] {msg}")
    def pop_violations(self):
        out = self._viol; self._viol = []; return out

class QuadSim(_Base):
    def __init__(self, m=2.5, arm=0.25, prop_d=0.305, e_bat_wh=160.0,
                 home=(0.0, 0.0, 0.0), fence_r=150.0, fence_z=100.0,
                 lat0=None, lon0=None, **_):
        self.kind = "quad"; self.m = m
        self.I = np.array([0.03, 0.03, 0.05])
        self.kf = 3.0e-5; self.km = 6.0e-7
        geo = [(arm, arm, -1), (-arm, arm, 1), (-arm, -arm, -1), (arm, -arm, 1)]
        self.M = np.array([[1.0, 1.0, 1.0, 1.0],
                           [g[1]*arm for g in geo],
                           [-g[0]*arm for g in geo],
                           [-g[2]*self.km for g in geo]])
        self.A_disk = 4*math.pi*(prop_d/2)**2
        self.e_bat = e_bat_wh*3600.0
        self.home = np.array(home, float); self.lat0, self.lon0 = lat0, lon0
        self.pos = self.home.copy(); self.vel = np.zeros(3)
        self.rpy = np.zeros(3); self.rates = np.zeros(3); self.w = np.zeros(4)
        self.soc = 1.0; self.armed = False; self.mode = "IDLE"
        self.target = None; self.mission = []; self.wp = 0
        self.fence_r = fence_r; self.fence_z = fence_z
        self.trail = []; self.t = 0.0
        self._viol = []; self._violated = set()

    def arm(self):
        self.armed = True; self.mode = "HOLD"
        self.target = self.pos + np.array([0, 0, 2.0])
    def disarm(self):
        self.armed = False; self.mode = "IDLE"; self.target = None
    def set_mode(self, mode, target=None):
        if not self.armed and mode != "IDLE": raise ValueError("armement requis")
        self.mode = mode
        if mode == "RTL":
            self.target = np.array([self.home[0], self.home[1], max(self.pos[2], 20.0)])
        elif target is not None:
            self.target = np.array([target["x"], target["y"], target["z"]], float)
    def load_mission(self, wps):
        self.mission = [np.array([w["x"], w["y"], w["z"]], float) for w in wps]
        self.wp = 0
        if self.armed: self.mode = "MISSION"
    def goto(self, x, y, z):
        self.target = np.array([x, y, z], float)
        if self.armed: self.mode = "HOLD"

    def step(self, dt):
        self.t += dt
        if self.armed and self.mode == "MISSION" and self.mission:
            w = self.mission[self.wp]
            if np.linalg.norm(w[:2]-self.pos[:2]) < 2.0 and abs(w[2]-self.pos[2]) < 3.0:
                self.wp = min(self.wp+1, len(self.mission)-1)
        if self.armed and self.mode == "RTL" and np.linalg.norm(self.pos[:2]-self.home[:2]) < 3.0:
            self.mode = "LAND"
        if self.armed and self.mode == "LAND":
            self.target = np.array([self.pos[0], self.pos[1], 0.0])
        # ---- autopilote (position → vitesse → attitude → rates → mixeur) ----
        T, tau = 0.0, np.zeros(3)
        if self.armed and self.target is not None and self.mode != "IDLE":
            tgt = self.target if not (self.mode == "MISSION" and self.mission) else self.mission[self.wp]
            err = tgt - self.pos
            vel_cmd = np.clip(1.2*err, -6.0, 6.0); vel_cmd[2] = _clamp(err[2], -1.2, 2.0)
            acc = np.clip(1.5*(vel_cmd - self.vel), -4.0, 4.0)
            rpy_d = np.array([_clamp(-acc[1]/G, -0.45, 0.45), _clamp(acc[0]/G, -0.45, 0.45), self.rpy[2]])
            rate_d = np.clip(8.0*(rpy_d - self.rpy), -4.0, 4.0)
            rate_d[2] = _clamp(2.0*_wrap(-self.rpy[2]), -1.5, 1.5)
            tau = np.clip(self.I*10.0*(rate_d - self.rates), -3.0, 3.0)
            T = _clamp(self.m*G + self.m*acc[2], 0.0, 2.2*self.m*G)
        elif self.armed:
            T = self.m*G
        if self.armed:
            f = np.clip(np.linalg.solve(self.M, np.array([T, tau[0], tau[1], tau[2]])), 0.0, 2.2*self.m*G)
            w_cmd = np.sqrt(f/self.kf)
        else:
            w_cmd = np.zeros(4)
        self.w += (w_cmd - self.w)*min(1.0, dt/0.06)
        f = self.kf*self.w**2
        T_r = float(f.sum()); tau_r = self.M[1:4] @ f
        # ---- dynamique 6 DDL ----
        cp, sp = math.cos(self.rpy[0]), math.sin(self.rpy[0])
        co, so = math.cos(self.rpy[1]), math.sin(self.rpy[1])
        cy, sy = math.cos(self.rpy[2]), math.sin(self.rpy[2])
        R = (np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]]) @ np.array([[co,0,so],[0,1,0],[-so,0,co]])
             @ np.array([[1,0,0],[0,cp,-sp],[0,sp,cp]]))
        thrust_w = R @ np.array([0, 0, T_r])
        drag = -0.10*self.vel*np.abs(self.vel)
        self.vel += ((thrust_w + np.array([0, 0, -self.m*G]) + drag)/self.m)*dt
        self.pos += self.vel*dt
        self.rates += ((tau_r - np.cross(self.rates, self.I*self.rates))/self.I)*dt
        self.rpy += self.rates*dt
        # ---- sol / atterrissage ----
        if self.pos[2] <= 0:
            self.pos[2] = 0.0
            if self.vel[2] < 0: self.vel[2] = 0.0
            self.vel[:2] *= 0.9
            if self.armed and self.mode == "LAND":
                self.armed = False; self.mode = "LANDED"
        # ---- géorepérage + batterie ----
        r_xy = float(np.linalg.norm(self.pos[:2]-self.home[:2]))
        if r_xy > self.fence_r: self._violation("fr", f"Géorepérage horizontal dépassé ({r_xy:.0f} m) — RTL")
        if self.pos[2] > self.fence_z: self._violation("fz", f"Plafond dépassé ({self.pos[2]:.0f} m) — RTL")
        if (r_xy > self.fence_r or self.pos[2] > self.fence_z) and self.armed and self.mode not in ("RTL","LAND"):
            self.mode = "RTL"
        P_e = 1.15*(T_r**1.5/math.sqrt(2*RHO*self.A_disk) if T_r > 0 else 0.0)/0.75
        self.soc = max(0.0, self.soc - P_e*dt/self.e_bat)
        if self.soc < 0.05 and self.armed and self.mode != "LAND":
            self._violation("batt", "Batterie < 5% — atterrissage imposé"); self.mode = "LAND"
        if not self.trail or self.t - self.trail[-1][3] > 0.5:
            if len(self.trail) < 600: self.trail.append([*self.pos, self.t])

    def telemetry(self):
        return {"kind": "quad", "t": round(self.t, 2), "armed": self.armed, "mode": self.mode,
                "pos": self.pos.round(2).tolist(), "vel": self.vel.round(2).tolist(),
                "rpy": [round(math.degrees(a), 1) for a in self.rpy],
                "motors_rpm": [round(w*60/2/math.pi) for w in self.w],
                "thrust_n": round(self.kf*float((self.w**2).sum()), 1),
                "soc": round(self.soc, 3), "vbat": round(4*(3.0+1.0*self.soc), 1),
                "wp": self.wp, "n_wp": len(self.mission),
                "violations": self._viol[-10:], "home": self.home.round(2).tolist(),
                "trail": [p[:3] for p in self.trail[-250:]]}

class FixedWingSim(_Base):
    def __init__(self, m=3.0, v_cruise=18.0, home=(0.0, 0.0, 60.0), ld=10.0,
                 e_bat_wh=220.0, fence_r=500.0, lat0=None, lon0=None, **_):
        self.kind = "fw"; self.m = m; self.V = v_cruise; self.V_cmd = v_cruise
        self.ld = ld; self.home = np.array(home, float); self.e_bat = e_bat_wh*3600.0
        self.fence_r = fence_r; self.lat0, self.lon0 = lat0, lon0
        self.pos = self.home.copy(); self.psi = 0.0; self.gamma = 0.0
        self.alt_cmd = home[2]; self.psi_cmd = 0.0
        self.armed = False; self.mode = "IDLE"; self.mission = []; self.wp = 0
        self.soc = 1.0; self.t = 0.0; self.trail = []; self._viol = []; self._violated = set()

    def arm(self): self.armed = True; self.mode = "HOLD"
    def disarm(self): self.armed = False; self.mode = "IDLE"
    def set_mode(self, mode, target=None):
        if not self.armed and mode != "IDLE": raise ValueError("armement requis")
        self.mode = mode
        if mode == "RTL":
            d = self.home[:2]-self.pos[:2]
            self.psi_cmd = math.atan2(d[1], d[0]); self.alt_cmd = max(self.home[2], self.pos[2])
    def load_mission(self, wps):
        self.mission = [np.array([w["x"], w["y"], w["z"]], float) for w in wps]
        self.wp = 0
        if self.armed: self.mode = "MISSION"
    def goto(self, x, y, z):
        self.psi_cmd = math.atan2(y-self.pos[1], x-self.pos[0]); self.alt_cmd = z
        if self.armed: self.mode = "HOLD"

    def step(self, dt):
        self.t += dt
        if self.armed:
            if self.mode == "MISSION" and self.mission:
                w = self.mission[self.wp]
                if np.linalg.norm(w[:2]-self.pos[:2]) < 40.0:
                    self.wp = min(self.wp+1, len(self.mission)-1)
                w = self.mission[self.wp]
                self.psi_cmd = math.atan2(w[1]-self.pos[1], w[0]-self.pos[0]); self.alt_cmd = w[2]
            if self.mode == "RTL" and np.linalg.norm(self.home[:2]-self.pos[:2]) < 60.0:
                self.psi_cmd += 0.5*dt                      # attente en orbite
            phi = _clamp(0.8*_wrap(self.psi_cmd - self.psi), -0.6, 0.6)
            self.gamma = _clamp(0.010*(self.alt_cmd - self.pos[2]), -0.20, 0.20)
            self.V += (self.V_cmd - self.V)*dt/3.0
            self.psi += G*math.tan(phi)/max(self.V, 5.0)*dt
            cg, sg = math.cos(self.gamma), math.sin(self.gamma)
            cp, sp = math.cos(self.psi), math.sin(self.psi)
            self.pos += self.V*np.array([cg*cp, cg*sp, sg])*dt
            if self.pos[2] < 5.0: self._violation("alt", "Altitude < 5 m (voilure fixe)")
            r_xy = float(np.linalg.norm(self.pos[:2]-self.home[:2]))
            if r_xy > self.fence_r:
                self._violation("fr", "Géorepérage dépassé — RTL"); self.mode = "RTL"
            self.soc = max(0.0, self.soc - (self.m*G*self.V/self.ld/0.7)*dt/self.e_bat)
            if self.soc < 0.05: self._violation("batt", "Batterie < 5% — RTL"); self.mode = "RTL"
        if not self.trail or self.t - self.trail[-1][3] > 0.5:
            if len(self.trail) < 600: self.trail.append([*self.pos, self.t])

    def telemetry(self):
        v = self.V*np.array([math.cos(self.psi)*math.cos(self.gamma),
                             math.sin(self.psi)*math.cos(self.gamma), math.sin(self.gamma)])
        return {"kind": "fw", "t": round(self.t, 2), "armed": self.armed, "mode": self.mode,
                "pos": self.pos.round(2).tolist(), "vel": v.round(2).tolist(),
                "rpy": [0.0, round(math.degrees(self.gamma), 1), round(math.degrees(self.psi), 1)],
                "v_mps": round(self.V, 1), "soc": round(self.soc, 3),
                "vbat": round(6*(3.0+1.0*self.soc), 1),
                "wp": self.wp, "n_wp": len(self.mission),
                "violations": self._viol[-10:], "home": self.home.round(2).tolist(),
                "trail": [p[:3] for p in self.trail[-250:]]}