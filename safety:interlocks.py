# safety/interlocks.py
"""
Gestion des interverrouillages de sécurité.
Section 3.H : capots, portes et zones dangereuses.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional
from datetime import datetime, timezone


class InterlockType(Enum):
    """Types d'interverrouillages."""
    ENCLOSURE_DOOR = "enclosure_door"     # Porte de capot
    GUARD_COVER = "guard_cover"           # Capot de protection
    EMERGENCY_BUTTON = "emergency_button"  # Bouton d'arrêt d'urgence
    SAFETY_MAT = "safety_mat"             # Tapis de sécurité
    LIGHT_CURTAIN = "light_curtain"       # Barrière immatérielle
    KEY_SWITCH = "key_switch"             # Interrupteur à clé
    TWO_HAND_CONTROL = "two_hand_control" # Commande bi-manuelle
    SOFTWARE_INTERLOCK = "software_interlock"  # Interverrouillage logiciel


class InterlockStatus(Enum):
    """Statut d'un interverrouillage."""
    CLOSED = "closed"       # Fermé = sécurité active
    OPEN = "open"           # Ouvert = sécurité levée (dANGER)
    BYPASSED = "bypassed"   # Contourné (maintenance uniquement)
    FAULTY = "faulty"       # Défaut détecté
    UNKNOWN = "unknown"     # État inconnu


@dataclass
class Interlock:
    """Définit un interverrouillage individuel."""
    interlock_id: str
    interlock_type: InterlockType
    description: str
    status: InterlockStatus = InterlockStatus.UNKNOWN
    
    # Configuration
    requires_closure_for_operation: bool = True  # Doit être fermé pour fonctionner
    can_be_bypassed: bool = False  # Peut être contourné (maintenance)
    bypass_requires_authorization: bool = True
    
    # Historique
    state_changes: List[Dict] = field(default_factory=list)
    
    # Callback
    on_status_change: Optional[Callable[[InterlockStatus], None]] = None
    
    def set_status(self, new_status: InterlockStatus, operator: str = "system"):
        """Change le statut de l'interverrouillage."""
        old_status = self.status
        self.status = new_status
        
        self.state_changes.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": old_status.value,
            "to": new_status.value,
            "operator": operator
        })
        
        if self.on_status_change:
            try:
                self.on_status_change(new_status)
            except Exception:
                pass
    
    def is_safe(self) -> bool:
        """Vérifie si l'interverrouillage est dans un état sûr."""
        if self.requires_closure_for_operation:
            return self.status == InterlockStatus.CLOSED
        return self.status in (InterlockStatus.CLOSED, InterlockStatus.OPEN)


class InterlockManager:
    """
    Gestionnaire central de tous les interverrouillages.
    
    Vérifie en permanence que toutes les conditions de sécurité
    physiques sont réunies avant d'autoriser tout fonctionnement.
    """
    
    def __init__(self):
        self._interlocks: Dict[str, Interlock] = {}
        self._bypass_authorizations: Dict[str, List[str]] = {}
    
    def register_interlock(self, interlock: Interlock):
        """Enregistre un interverrouillage."""
        self._interlocks[interlock.interlock_id] = interlock
    
    def get_interlock(self, interlock_id: str) -> Optional[Interlock]:
        """Récupère un interverrouillage par son ID."""
        return self._interlocks.get(interlock_id)
    
    def update_status(self, interlock_id: str, status: InterlockStatus,
                     operator: str = "system") -> bool:
        """Met à jour le statut d'un interverrouillage."""
        interlock = self._interlocks.get(interlock_id)
        if not interlock:
            return False
        
        # Vérifier si le contournement est autorisé
        if status == InterlockStatus.BYPASSED:
            if not interlock.can_be_bypassed:
                return False
            if interlock.bypass_requires_authorization:
                authorized = self._bypass_authorizations.get(interlock_id, [])
                if operator not in authorized:
                    return False
        
        interlock.set_status(status, operator)
        return True
    
    def authorize_bypass(self, interlock_id: str, operator: str):
        """Autorise un opérateur à contourner un interverrouillage."""
        if interlock_id not in self._bypass_authorizations:
            self._bypass_authorizations[interlock_id] = []
        if operator not in self._bypass_authorizations[interlock_id]:
            self._bypass_authorizations[interlock_id].append(operator)
    
    def all_interlocks_safe(self) -> bool:
        """
        Vérifie que TOUS les interverrouillages sont dans un état sûr.
        Retourne False si au moins un n'est pas sûr.
        """
        return all(il.is_safe() for il in self._interlocks.values())
    
    def get_unsafe_interlocks(self) -> List[Interlock]:
        """Retourne la liste des interverrouillages non sûrs."""
        return [il for il in self._interlocks.values() if not il.is_safe()]
    
    def get_status_summary(self) -> Dict:
        """Retourne un résumé de tous les interverrouillages."""
        return {
            "total": len(self._interlocks),
            "all_safe": self.all_interlocks_safe(),
            "interlocks": {
                il.interlock_id: {
                    "type": il.interlock_type.value,
                    "status": il.status.value,
                    "is_safe": il.is_safe(),
                    "description": il.description
                } for il in self._interlocks.values()
            }
        }