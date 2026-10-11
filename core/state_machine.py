# core/state_machine.py
"""
Machine à états pour la gestion du cycle de vie des appareils.
Section 3.E : éteint, initialisation, prêt, actif, dégradé, arrêt, maintenance.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
import time


class DeviceState(Enum):
    """États possibles d'un appareil contrôlé."""
    OFF = "off"                     # Appareil éteint
    INITIALIZING = "initializing"   # Initialisation en cours
    READY = "ready"                 # Prêt à fonctionner
    ACTIVE = "active"               # En fonctionnement normal
    DEGRADED = "degraded"           # Fonctionnement dégradé
    STOPPING = "stopping"           # Arrêt en cours
    STOPPED = "stopped"             # Arrêté proprement
    MAINTENANCE = "maintenance"     # Mode maintenance
    EMERGENCY_STOP = "emergency_stop"  # Arrêt d'urgence
    FAULT = "fault"                 # Défaut détecté
    SAFE_STATE = "safe_state"       # État sûr appliqué


class StateTransition:
    """
    Définit une transition valide entre deux états.
    Contient les conditions préalables et les actions à effectuer.
    """
    
    def __init__(self, from_state: DeviceState, to_state: DeviceState,
                 condition: Callable[[], bool] = None,
                 pre_action: Callable[[], bool] = None,
                 post_action: Callable[[], None] = None,
                 description: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition or (lambda: True)
        self.pre_action = pre_action
        self.post_action = post_action
        self.description = description


class DeviceStateMachine:
    """
    Machine à états déterministe pour le contrôle des appareils.
    
    Règle d'architecture : l'IA propose, la machine à états dispose.
    Toutes les transitions sont vérifiées et journalisées.
    """
    
    # Transitions valides par défaut
    VALID_TRANSITIONS = {
        (DeviceState.OFF, DeviceState.INITIALIZING),
        (DeviceState.INITIALIZING, DeviceState.READY),
        (DeviceState.INITIALIZING, DeviceState.FAULT),
        (DeviceState.READY, DeviceState.ACTIVE),
        (DeviceState.READY, DeviceState.MAINTENANCE),
        (DeviceState.ACTIVE, DeviceState.STOPPING),
        (DeviceState.ACTIVE, DeviceState.DEGRADED),
        (DeviceState.ACTIVE, DeviceState.EMERGENCY_STOP),
        (DeviceState.ACTIVE, DeviceState.FAULT),
        (DeviceState.DEGRADED, DeviceState.STOPPING),
        (DeviceState.DEGRADED, DeviceState.EMERGENCY_STOP),
        (DeviceState.DEGRADED, DeviceState.FAULT),
        (DeviceState.DEGRADED, DeviceState.ACTIVE),  # Récupération
        (DeviceState.STOPPING, DeviceState.STOPPED),
        (DeviceState.STOPPING, DeviceState.FAULT),
        (DeviceState.STOPPED, DeviceState.READY),
        (DeviceState.STOPPED, DeviceState.OFF),
        (DeviceState.MAINTENANCE, DeviceState.READY),
        (DeviceState.MAINTENANCE, DeviceState.OFF),
        (DeviceState.EMERGENCY_STOP, DeviceState.SAFE_STATE),
        (DeviceState.FAULT, DeviceState.SAFE_STATE),
        (DeviceState.FAULT, DeviceState.MAINTENANCE),
        (DeviceState.SAFE_STATE, DeviceState.MAINTENANCE),
        # Arrêt d'urgence depuis n'importe quel état actif
        (DeviceState.INITIALIZING, DeviceState.EMERGENCY_STOP),
        (DeviceState.READY, DeviceState.EMERGENCY_STOP),
        (DeviceState.MAINTENANCE, DeviceState.EMERGENCY_STOP),
    }
    
    def __init__(self, device_id: str = "unknown"):
        self.device_id = device_id
        self._current_state = DeviceState.OFF
        self._previous_state = DeviceState.OFF
        self._transition_log: List[Dict[str, Any]] = []
        self._state_handlers: Dict[DeviceState, Callable[[], None]] = {}
        self._entry_time = time.time()
        self._custom_transitions: List[StateTransition] = []
        
        # Callbacks pour les observateurs
        self._state_change_callbacks: List[Callable[[DeviceState, DeviceState], None]] = []
    
    @property
    def current_state(self) -> DeviceState:
        """Retourne l'état actuel."""
        return self._current_state
    
    @property
    def time_in_state(self) -> float:
        """Retourne le temps écoulé dans l'état actuel (secondes)."""
        return time.time() - self._entry_time
    
    def register_state_handler(self, state: DeviceState, handler: Callable[[], None]):
        """Enregistre un gestionnaire pour un état spécifique."""
        self._state_handlers[state] = handler
    
    def register_state_change_callback(self, callback: Callable[[DeviceState, DeviceState], None]):
        """Enregistre un callback appelé à chaque changement d'état."""
        self._state_change_callbacks.append(callback)
    
    def add_custom_transition(self, transition: StateTransition):
        """Ajoute une transition personnalisée."""
        self._custom_transitions.append(transition)
    
    def can_transition(self, to_state: DeviceState) -> bool:
        """Vérifie si une transition est valide depuis l'état actuel."""
        pair = (self._current_state, to_state)
        
        # Vérifier les transitions standard
        if pair in self.VALID_TRANSITIONS:
            return True
        
        # Vérifier les transitions personnalisées
        for trans in self._custom_transitions:
            if trans.from_state == self._current_state and trans.to_state == to_state:
                return trans.condition()
        
        return False
    
    def transition(self, to_state: DeviceState, 
                   reason: str = "", operator: str = "system") -> bool:
        """
        Effectue une transition d'état.
        
        Retourne True si la transition a réussi, False sinon.
        Toutes les tentatives sont journalisées.
        """
        from_state = self._current_state
        
        # L'arrêt d'urgence est toujours autorisé
        if to_state == DeviceState.EMERGENCY_STOP:
            return self._force_transition(to_state, reason, operator)
        
        if not self.can_transition(to_state):
            self._log_transition(from_state, to_state, False, 
                                f"Transition invalide. Raison: {reason}")
            return False
        
        return self._force_transition(to_state, reason, operator)
    
    def _force_transition(self, to_state: DeviceState, reason: str, 
                         operator: str) -> bool:
        """Force une transition (utilisé pour l'arrêt d'urgence)."""
        from_state = self._current_state
        
        # Exécuter les actions pré-transition pour les transitions personnalisées
        for trans in self._custom_transitions:
            if trans.from_state == from_state and trans.to_state == to_state:
                if trans.pre_action:
                    if not trans.pre_action():
                        self._log_transition(from_state, to_state, False, 
                                           "Action pré-transition a échoué")
                        return False
                if trans.post_action:
                    trans.post_action()
        
        self._previous_state = from_state
        self._current_state = to_state
        self._entry_time = time.time()
        
        # Exécuter le gestionnaire d'état si défini
        if to_state in self._state_handlers:
            try:
                self._state_handlers[to_state]()
            except Exception as e:
                self._log_transition(from_state, to_state, False, 
                                    f"Erreur gestionnaire d'état: {e}")
        
        # Notifier les observateurs
        for callback in self._state_change_callbacks:
            try:
                callback(from_state, to_state)
            except Exception:
                pass
        
        self._log_transition(from_state, to_state, True, reason, operator)
        return True
    
    def emergency_stop(self, reason: str = "Emergency stop activated") -> bool:
        """
        Déclenche un arrêt d'urgence depuis n'importe quel état.
        Cette action est toujours autorisée et prioritaire.
        """
        return self._force_transition(DeviceState.EMERGENCY_STOP, reason, "safety_system")
    
    def enter_safe_state(self, reason: str = "Safe state activated") -> bool:
        """Force l'entrée en état sûr."""
        return self._force_transition(DeviceState.SAFE_STATE, reason, "safety_system")
    
    def _log_transition(self, from_state: DeviceState, to_state: DeviceState,
                       success: bool, reason: str, operator: str = "system"):
        """Journalise une transition d'état."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": self.device_id,
            "from_state": from_state.value,
            "to_state": to_state.value,
            "success": success,
            "reason": reason,
            "operator": operator,
            "time_in_previous_state": self.time_in_state
        }
        self._transition_log.append(log_entry)
    
    def get_transition_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retourne les dernières transitions journalisées."""
        return self._transition_log[-limit:]
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'état actuel."""
        return {
            "device_id": self.device_id,
            "current_state": self._current_state.value,
            "previous_state": self._previous_state.value,
            "time_in_state": self.time_in_state,
            "total_transitions": len(self._transition_log),
            "last_transition": self._transition_log[-1] if self._transition_log else None
        }