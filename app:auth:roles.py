# app/auth/roles.py
from enum import Enum

class Role(str, Enum):
    VIEWER = "viewer"          # lecture seule
    OPERATOR = "operator"      # lance sims, prépare vols
    ADMIN = "admin"            # approuve vols/certifications
    SUPER_ADMIN = "super_admin"  # gère clés, comptes, révocations

HIERARCHY = {Role.VIEWER: 0, Role.OPERATOR: 1,
             Role.ADMIN: 2, Role.SUPER_ADMIN: 3}

def at_least(user_role: Role, required: Role) -> bool:
    return HIERARCHY[user_role] >= HIERARCHY[required]

# Toute action de classe "high" exige DEUX approbations distinctes
# (règle des deux personnes) et expire après 10 minutes.
HIGH_RISK_ACTIONS = {"flight_authorize", "payload_arm", "cert_issue", "key_revoke"}