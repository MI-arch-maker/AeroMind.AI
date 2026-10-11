# security/audit.py
"""
Journal d'audit protégé contre les modifications non autorisées.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json
import hashlib


class AuditEventType(Enum):
    """Types d'événements audités."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    CONFIGURATION_CHANGE = "configuration_change"
    PARAMETER_CHANGE = "parameter_change"
    DEVICE_COMMAND = "device_command"
    SAFETY_EVENT = "safety_event"
    TEST_EXECUTION = "test_execution"
    DATA_ACCESS = "data_access"
    SYSTEM_EVENT = "system_event"
    FIRMWARE_UPDATE = "firmware_update"
    EMERGENCY_STOP = "emergency_stop"


@dataclass
class AuditEvent:
    """Événement d'audit individuel."""
    event_type: AuditEventType
    actor: str  # Qui a effectué l'action
    action: str  # Qu'a-t-il fait
    target: str = ""  # Sur quoi
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    severity: str = "info"  # info, warning, error, critical
    
    # Intégrité
    previous_hash: str = ""
    event_hash: str = ""
    
    def compute_hash(self) -> str:
        """Calcule le hash de l'événement pour l'intégrité de la chaîne."""
        event_data = json.dumps({
            "event_type": self.event_type.value,
            "actor": self.actor,
            "action": self.action,
            "target": self.target,
            "details": self.details,
            "timestamp": self.timestamp,
            "severity": self.severity,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        self.event_hash = hashlib.sha256(event_data.encode()).hexdigest()
        return self.event_hash


class AuditLogger:
    """
    Journal d'audit avec chaîne de hash pour l'intégrité.
    
    Chaque événement est lié au précédent par un hash,
    rendant toute modification détectable.
    """
    
    def __init__(self):
        self._events: List[AuditEvent] = []
        self._chain_hash: str = "genesis"
        self._is_enabled: bool = True
    
    def log(self, event_type: AuditEventType, actor: str, action: str,
           target: str = "", details: Dict = None, severity: str = "info"):
        """Enregistre un événement d'audit."""
        if not self._is_enabled:
            return
        
        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            action=action,
            target=target,
            details=details or {},
            severity=severity,
            previous_hash=self._chain_hash
        )
        
        event.compute_hash()
        self._chain_hash = event.event_hash
        self._events.append(event)
    
    def verify_integrity(self) -> bool:
        """Vérifie l'intégrité de la chaîne d'audit."""
        expected_prev_hash = "genesis"
        
        for event in self._events:
            if event.previous_hash != expected_prev_hash:
                return False
            
            # Recalculer le hash
            computed_hash = event.compute_hash()
            if computed_hash != event.event_hash:
                return False
            
            expected_prev_hash = event.event_hash
        
        return True
    
    def get_events(self, event_type: Optional[AuditEventType] = None,
                  actor: Optional[str] = None,
                  severity: Optional[str] = None,
                  limit: int = 100) -> List[AuditEvent]:
        """Récupère les événements filtrés."""
        filtered = self._events
        
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        if actor:
            filtered = [e for e in filtered if e.actor == actor]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        
        return filtered[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques du journal d'audit."""
        type_counts = {}
        for event in self._events:
            etype = event.event_type.value
            type_counts[etype] = type_counts.get(etype, 0) + 1
        
        return {
            "total_events": len(self._events),
            "events_by_type": type_counts,
            "is_integrity_valid": self.verify_integrity(),
            "last_event": self._events[-1].timestamp if self._events else None
        }