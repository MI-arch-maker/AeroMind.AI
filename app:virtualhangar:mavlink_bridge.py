# app/virtualhangar/mavlink_bridge.py (squelette)
# pip install pymavlink  |  côté sim : docker run -it --rm -p 5760:5760 swallow"+sitl
from pymavlink import mavutil
import threading, json, asyncio

class MavBridge:
    """Relais télémétrie SITL → WebSocket dashboard.
       ARM moteur soumis à la règle des deux personnes (cf. 4.1)."""
    def __init__(self, conn_str="tcp:127.0.0.1:5760"):
        self.mav = mavutil.mavlink_connection(conn_str)
        self.latest = {}

    def stream(self):                      # appelé en tâche de fond
        while True:
            m = self.mav.recv_match(blocking=True)
            self.latest = {"type": m.get_type(), **{k: getattr(m, k)
                     for k in dir(m) if not k.startswith("_")}}

    def arm_motors(self, dual_ok: bool):   # moteurs UNIQUEMENT
        if not dual_ok:
            raise PermissionError("double approbation humaine requise")
        self.mav.arducopter_arm()