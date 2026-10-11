"""Pont MAVLink vers un SITL ArduPilot exécuté SUR TA MACHINE (Render ne peut pas l'héberger) :
    pip install pymavlink
    ~/ardupilot/ArduCopter $ sim_vehicle.py -v ArduCopter --map --console
Puis créer une session kind="external" avec params.url="tcp:<ton-ip>:5760" (tunnel/ngrok si besoin)."""
import math

class ExternalSITL:
    kind = "external"
    def __init__(self, url="tcp:127.0.0.1:5760", **_):
        from pymavlink import mavutil
        self.mav = mavutil.mavlink_connection(url)
        self.armed = False; self.mode = "EXTERNAL"; self.t = 0.0
        self.latest = {}; self.mission = []; self.wp = 0; self.trail = []
    def arm(self): self.mav.arducopter_arm(); self.armed = True
    def disarm(self): self.mav.arducopter_disarm(); self.armed = False
    def set_mode(self, mode, target=None): pass
    def load_mission(self, wps): pass
    def goto(self, x, y, z): pass
    def step(self, dt):
        self.t += dt
        m = self.mav.recv_match(blocking=False)
        if m:
            d = m.to_dict(); t = d.get("mavpackettype")
            if t == "GLOBAL_POSITION_INT":
                self.latest.update({"pos": [d["lat"]*1e-7, d["lon"]*1e-7, d["alt"]*1e-3],
                                    "vel": [d["vx"]*0.01, d["vy"]*0.01, d["vz"]*0.01]})
            elif t == "ATTITUDE":
                self.latest["rpy"] = [round(math.degrees(d[k]), 1) for k in ("roll", "pitch", "yaw")]
            elif t == "SYS_STATUS":
                self.latest["soc"] = round(max(0.0, d.get("battery_remaining", 0))/100.0, 3)
            if "pos" in self.latest and (not self.trail or self.t - self.trail[-1][3] if self.trail else True):
                self.trail.append([*self.latest["pos"], self.t])
    def pop_violations(self): return []
    def telemetry(self):
        base = {"kind": "external", "t": round(self.t, 1), "armed": self.armed, "mode": self.mode,
                "violations": [], "n_wp": 0, "wp": 0, "home": [0, 0, 0],
                "pos": [0, 0, 0], "vel": [0, 0, 0], "rpy": [0, 0, 0], "soc": 0, "trail": []}
        base.update(self.latest)
        return base