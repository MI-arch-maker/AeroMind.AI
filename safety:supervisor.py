# safety/supervisor.py
"""
Superviseur de sécurité indépendant.
Section 3.H : doit être développé dès le départ, indépendant de l'IA.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
import time
import threading


class SafetyLevel(Enum):
    """Niveaux de sécurité/criticité."""
    NORMAL = "normal"
    CAUTION = "caution"       # Attention, surveillance renforcée
    WARNING = "warning"       # Avertissement, action corrective recommandée
    CRITICAL = "critical"     # Critique, arrêt recommandé
    EMERGENCY = "emergency"   # Urgence, arrêt immédiat obligatoire


class SafetyViolationType(Enum):
    """Types de violations de sécurité."""
    OVERCURRENT = "overcurrent"
    OVERVOLTAGE = "overvoltage"
    OVERTEMPERATURE = "overtemperature"
    OVERSPEED = "overspeed"
    OVERPRESSURE = "overpressure"
    SENSOR_FAILURE = "sensor_failure"
    SENSOR_CONTRADICTION = "sensor_contradiction"
    COMMUNICATION_LOSS = "communication_loss"
    INTERLOCK_VIOLATION = "interlock_violation"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    FIRMWARE_MISMATCH = "firmware_mismatch"
    SAFE_STATE_VIOLATION = "safe_state_violation"
    EMERGENCY_STOP_ACTIVATED = "emergency_stop_activated"


@dataclass
class SafetyViolation:
    """Représente une violation de sécurité détectée."""
    violation_type: SafetyViolationType
    level: SafetyLevel
    description: str
    device_id: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    measured_value: Optional[float] = None
    limit_value: Optional[float] = None
    unit: str = ""
    action_taken: str = ""
    requires_acknowledgment: bool = True
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None


@dataclass
class SafetyLimit:
    """Limite de sécurité surveillée."""
    name: str
    parameter: str
    soft_limit: float  # Seuil d'avertissement
    hard_limit: float  # Seuil d'arrêt
    unit: str
    comparison: str = "greater"  # "greater", "less", "absolute"
    is_enabled: bool = True
    
    # Statistiques
    current_value: float = 0.0
    violation_count: int = 0
    last_violation_time: Optional[float] = None


class SafetySupervisor:
    """
    Superviseur de sécurité indépendant de l'IA.
    
    Règle d'architecture fondamentale :
    "Les fonctions de sécurité critiques doivent rester indépendantes de l'IA
    et, lorsque nécessaire, utiliser des dispositifs matériels certifiés."
    
    Ce superviseur fonctionne comme un watchdog indépendant qui :
    1. Surveille les paramètres critiques en continu
    2. Déclenche des actions de sécurité automatiques
    3. Journalise toutes les violations
    4. Ne peut pas être contourné par l'IA
    """
    
    def __init__(self):
        self._limits: Dict[str, SafetyLimit] = {}
        self._violations: List[SafetyViolation] = []
        self._safety_callbacks: Dict[SafetyLevel, List[Callable]] = {}
        self._emergency_stop_active: bool = False
        self._monitoring_active: bool = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # Callbacks d'action
        self._shutdown_callback: Optional[Callable[[], None]] = None
        self._safe_state_callback: Optional[Callable[[], None]] = None
        
        # Statistiques
        self._total_violations: int = 0
        self._start_time: float = time.time()
    
    def set_shutdown_callback(self, callback: Callable[[], None]):
        """Définit la fonction à appeler pour un arrêt propre."""
        self._shutdown_callback = callback
    
    def set_safe_state_callback(self, callback: Callable[[], None]):
        """Définit la fonction à appeler pour entrer en état sûr."""
        self._safe_state_callback = callback
    
    def register_limit(self, limit: SafetyLimit):
        """Enregistre une limite de sécurité à surveiller."""
        self._limits[limit.name] = limit
    
    def register_safety_callback(self, level: SafetyLevel, callback: Callable):
        """Enregistre un callback pour un niveau de sécurité donné."""
        if level not in self._safety_callbacks:
            self._safety_callbacks[level] = []
        self._safety_callbacks[level].append(callback)
    
    def update_parameter(self, parameter_name: str, value: float):
        """
        Met à jour la valeur d'un paramètre surveillé.
        Appelé par le système d'acquisition de données.
        """
        with self._lock:
            for name, limit in self._limits.items():
                if limit.parameter == parameter_name and limit.is_enabled:
                    limit.current_value = value
                    self._check_limit(name, limit, value)
    
    def _check_limit(self, name: str, limit: SafetyLimit, value: float):
        """Vérifie si une valeur dépasse une limite."""
        is_soft_violation = False
        is_hard_violation = False
        
        if limit.comparison == "greater":
            is_soft_violation = value > limit.soft_limit
            is_hard_violation = value > limit.hard_limit
        elif limit.comparison == "less":
            is_soft_violation = value < limit.soft_limit
            is_hard_violation = value < limit.hard_limit
        elif limit.comparison == "absolute":
            is_soft_violation = abs(value) > limit.soft_limit
            is_hard_violation = abs(value) > limit.hard_limit
        
        if is_hard_violation:
            self._trigger_violation(name, limit, value, SafetyLevel.EMERGENCY)
        elif is_soft_violation:
            self._trigger_violation(name, limit, value, SafetyLevel.WARNING)
    
    def _trigger_violation(self, name: str, limit: SafetyLimit, 
                          value: float, level: SafetyLevel):
        """Déclenche une violation de sécurité."""
        violation = SafetyViolation(
            violation_type=self._map_to_violation_type(name),
            level=level,
            description=f"Limite '{name}' dépassée: {value} {limit.unit} "
                       f"(limite: {limit.hard_limit} {limit.unit})",
            measured_value=value,
            limit_value=limit.hard_limit,
            unit=limit.unit
        )
        
        limit.violation_count += 1
        limit.last_violation_time = time.time()
        self._total_violations += 1
        self._violations.append(violation)
        
        # Déclencher les actions appropriées
        if level == SafetyLevel.EMERGENCY:
            self._handle_emergency(violation)
        elif level == SafetyLevel.CRITICAL:
            self._handle_critical(violation)
        elif level == SafetyLevel.WARNING:
            self._handle_warning(violation)
        
        # Notifier les callbacks
        callbacks = self._safety_callbacks.get(level, [])
        for callback in callbacks:
            try:
                callback(violation)
            except Exception:
                pass  # Un callback ne doit jamais faire échouer la sécurité
    
    def _map_to_violation_type(self, limit_name: str) -> SafetyViolationType:
        """Mappe un nom de limite vers un type de violation."""
        mapping = {
            "current": SafetyViolationType.OVERCURRENT,
            "voltage": SafetyViolationType.OVERVOLTAGE,
            "temperature": SafetyViolationType.OVERTEMPERATURE,
            "speed": SafetyViolationType.OVERSPEED,
            "pressure": SafetyViolationType.OVERPRESSURE,
        }
        for key, violation_type in mapping.items():
            if key in limit_name.lower():
                return violation_type
        return SafetyViolationType.SAFE_STATE_VIOLATION
    
    def _handle_emergency(self, violation: SafetyViolation):
        """Gère une violation de niveau urgence."""
        violation.action_taken = "Arrêt d'urgence déclenché automatiquement"
        self._emergency_stop_active = True
        
        if self._safe_state_callback:
            try:
                self._safe_state_callback()
            except Exception:
                pass
    
    def _handle_critical(self, violation: SafetyViolation):
        """Gère une violation de niveau critique."""
        violation.action_taken = "Arrêt propre initié"
        
        if self._shutdown_callback:
            try:
                self._shutdown_callback()
            except Exception:
                pass
    
    def _handle_warning(self, violation: SafetyViolation):
        """Gère une violation de niveau avertissement."""
        violation.action_taken = "Surveillance renforcée"
    
    def trigger_emergency_stop(self, reason: str = "Manual emergency stop"):
        """
        Déclenche manuellement un arrêt d'urgence.
        Cette action est toujours autorisée et prioritaire.
        """
        violation = SafetyViolation(
            violation_type=SafetyViolationType.EMERGENCY_STOP_ACTIVATED,
            level=SafetyLevel.EMERGENCY,
            description=f"Arrêt d'urgence: {reason}",
            action_taken="Arrêt d'urgence activé"
        )
        self._violations.append(violation)
        self._emergency_stop_active = True
        self._total_violations += 1
        
        if self._safe_state_callback:
            try:
                self._safe_state_callback()
            except Exception:
                pass
    
    def clear_emergency_stop(self, operator: str) -> bool:
        """
        Acquitte et efface un arrêt d'urgence.
        Nécessite une confirmation explicite de l'opérateur.
        """
        if not self._emergency_stop_active:
            return True
        
        # Marquer toutes les violations d'urgence comme acquittées
        for v in self._violations:
            if v.level == SafetyLevel.EMERGENCY and not v.acknowledged:
                v.acknowledged = True
                v.acknowledged_by = operator
        
        self._emergency_stop_active = False
        return True
    
    def acknowledge_violation(self, index: int, operator: str) -> bool:
        """Acquitte une violation spécifique."""
        if 0 <= index < len(self._violations):
            violation = self._violations[index]
            if not violation.acknowledged:
                violation.acknowledged = True
                violation.acknowledged_by = operator
                return True
        return False
    
    def get_active_violations(self) -> List[SafetyViolation]:
        """Retourne les violations non acquittées."""
        return [v for v in self._violations if not v.acknowledged]
    
    def get_all_violations(self, limit: int = 100) -> List[SafetyViolation]:
        """Retourne l'historique des violations."""
        return self._violations[-limit:]
    
    @property
    def is_emergency_stop_active(self) -> bool:
        """Vérifie si un arrêt d'urgence est actif."""
        return self._emergency_stop_active
    
    def get_safety_status(self) -> Dict[str, Any]:
        """Retourne le statut de sécurité global."""
        active = self.get_active_violations()
        
        current_level = SafetyLevel.NORMAL
        if self._emergency_stop_active:
            current_level = SafetyLevel.EMERGENCY
        elif any(v.level == SafetyLevel.CRITICAL for v in active):
            current_level = SafetyLevel.CRITICAL
        elif any(v.level == SafetyLevel.WARNING for v in active):
            current_level = SafetyLevel.WARNING
        
        return {
            "current_level": current_level.value,
            "emergency_stop_active": self._emergency_stop_active,
            "active_violations": len(active),
            "total_violations": self._total_violations,
            "uptime_seconds": time.time() - self._start_time,
            "monitored_limits": len(self._limits)
        }
    
    def initialize_default_limits(self):
        """Initialise les limites de sécurité par défaut."""
        
        self.register_limit(SafetyLimit(
            name="max_current", parameter="current",
            soft_limit=4.0, hard_limit=5.5, unit="A",
            comparison="greater"
        ))
        
        self.register_limit(SafetyLimit(
            name="max_voltage", parameter="voltage",
            soft_limit=13.0, hard_limit=14.5, unit="V",
            comparison="greater"
        ))
        
        self.register_limit(SafetyLimit(
            name="max_temperature", parameter="temperature",
            soft_limit=60.0, hard_limit=75.0, unit="°C",
            comparison="greater"
        ))
        
        self.register_limit(SafetyLimit(
            name="min_voltage", parameter="voltage",
            soft_limit=10.0, hard_limit=8.0, unit="V",
            comparison="less"
        ))
        
        self.register_limit(SafetyLimit(
            name="max_speed", parameter="speed",
            soft_limit=2800.0, hard_limit=3200.0, unit="rpm",
            comparison="greater"
        ))