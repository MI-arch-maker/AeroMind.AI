# core/parameters.py
"""
Référentiel central de paramètres transversaux.
Section 11 du cahier des charges : éviter que les modules se contredisent.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone
import json
import copy


class ParameterStatus(Enum):
    """Statut de vérification d'un paramètre."""
    UNVERIFIED = "unverified"
    AI_ESTIMATED = "ai_estimated"      # Valeur proposée par l'IA, non confirmée
    CALCULATED = "calculated"           # Calculée par un modèle validé
    MEASURED = "measured"               # Mesurée physiquement
    SPECIFIED = "specified"             # Spécifiée par le fabricant
    VALIDATED = "validated"             # Validée par un test formel


class ParameterCategory(Enum):
    """Catégories de paramètres selon le cahier des charges."""
    IDENTITY = "identity"
    CONFIGURATION = "configuration"
    ELECTRICAL = "electrical"
    MECHANICAL = "mechanical"
    REAL_TIME = "real_time"
    COMMUNICATION = "communication"
    SENSORS = "sensors"
    ACTUATORS = "actuators"
    SAFETY = "safety"
    TESTING = "testing"
    AI = "ai"
    OPERATIONS = "operations"


@dataclass
class Parameter:
    """
    Paramètre individuel avec unité, source, plage admissible et statut.
    
    Règle : les paramètres critiques ne doivent jamais être remplacés
    silencieusement par une valeur supposée par l'IA.
    """
    
    name: str
    category: ParameterCategory
    value: Any
    unit: str = ""
    
    # Source et traçabilité
    source: str = ""  # ex: "datasheet", "measurement", "calculation"
    reference_value: Optional[Any] = None
    
    # Plage admissible
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    # Statut de vérification
    status: ParameterStatus = ParameterStatus.UNVERIFIED
    
    # Version et historique
    version: str = "1.0"
    last_modified: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    modification_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Criticité
    is_critical: bool = False
    is_safety_related: bool = False
    
    # Validation
    requires_human_approval: bool = False
    approved_by: Optional[str] = None
    
    def validate_value(self) -> bool:
        """Vérifie que la valeur est dans la plage admissible."""
        if isinstance(self.value, (int, float)):
            if self.min_value is not None and self.value < self.min_value:
                return False
            if self.max_value is not None and self.value > self.max_value:
                return False
        return True
    
    def set_value(self, new_value: Any, source: str, 
                  requires_approval: bool = False) -> bool:
        """
        Modifie la valeur du paramètre avec traçabilité.
        
        Si le paramètre est critique ou sécurité, une approbation humaine
        est requise avant que la modification ne prenne effet.
        """
        old_value = self.value
        
        # Enregistrer la tentative de modification
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "old_value": old_value,
            "new_value": new_value,
            "source": source,
            "approved": not requires_approval
        }
        
        if requires_approval or self.is_critical or self.is_safety_related:
            # La modification est enregistrée mais pas appliquée
            record["approved"] = False
            self.modification_history.append(record)
            return False
        
        self.value = new_value
        self.source = source
        self.last_modified = datetime.now(timezone.utc).isoformat()
        self.modification_history.append(record)
        return True
    
    def approve_modification(self, approver: str, index: int) -> bool:
        """Approuve une modification en attente."""
        if index < len(self.modification_history):
            record = self.modification_history[index]
            if not record.get("approved", False):
                record["approved"] = True
                record["approved_by"] = approver
                record["approved_at"] = datetime.now(timezone.utc).isoformat()
                self.value = record["new_value"]
                self.source = record["source"]
                self.last_modified = datetime.now(timezone.utc).isoformat()
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category.value,
            "value": self.value,
            "unit": self.unit,
            "source": self.source,
            "reference_value": self.reference_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "status": self.status.value,
            "version": self.version,
            "last_modified": self.last_modified,
            "is_critical": self.is_critical,
            "is_safety_related": self.is_safety_related,
            "requires_human_approval": self.requires_human_approval
        }


class ParameterRepository:
    """
    Référentiel central de tous les paramètres du système.
    
    Extrait du cahier des charges :
    "Pour éviter que les différents modules se contredisent,
    crée un référentiel central de paramètres."
    """
    
    def __init__(self):
        self._parameters: Dict[str, Parameter] = {}
        self._observers: List[Callable[[Parameter], None]] = []
    
    def register(self, parameter: Parameter):
        """Enregistre un paramètre dans le référentiel."""
        key = f"{parameter.category.value}.{parameter.name}"
        self._parameters[key] = parameter
    
    def get(self, category: ParameterCategory, name: str) -> Optional[Parameter]:
        """Récupère un paramètre par catégorie et nom."""
        key = f"{category.value}.{name}"
        return self._parameters.get(key)
    
    def get_by_category(self, category: ParameterCategory) -> List[Parameter]:
        """Récupère tous les paramètres d'une catégorie."""
        prefix = f"{category.value}."
        return [p for k, p in self._parameters.items() if k.startswith(prefix)]
    
    def get_critical_parameters(self) -> List[Parameter]:
        """Retourne tous les paramètres critiques."""
        return [p for p in self._parameters.values() 
                if p.is_critical or p.is_safety_related]
    
    def get_unverified_parameters(self) -> List[Parameter]:
        """Retourne tous les paramètres non vérifiés."""
        return [p for p in self._parameters.values() 
                if p.status == ParameterStatus.UNVERIFIED]
    
    def get_ai_estimated_parameters(self) -> List[Parameter]:
        """Retourne les paramètres estimés par l'IA (non confirmés)."""
        return [p for p in self._parameters.values() 
                if p.status == ParameterStatus.AI_ESTIMATED]
    
    def register_observer(self, callback: Callable[[Parameter], None]):
        """Enregistre un observateur pour les changements de paramètres."""
        self._observers.append(callback)
    
    def _notify_observers(self, parameter: Parameter):
        """Notifie tous les observateurs d'un changement."""
        for observer in self._observers:
            try:
                observer(parameter)
            except Exception:
                pass  # Un observateur ne doit jamais faire échouer le système
    
    def export_snapshot(self) -> Dict[str, Any]:
        """Exporte un instantané complet du référentiel."""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "parameters": {
                k: p.to_dict() for k, p in self._parameters.items()
            },
            "summary": {
                "total": len(self._parameters),
                "critical": len(self.get_critical_parameters()),
                "unverified": len(self.get_unverified_parameters()),
                "ai_estimated": len(self.get_ai_estimated_parameters())
            }
        }
    
    def validate_all(self) -> Dict[str, List[str]]:
        """Valide tous les paramètres et retourne les erreurs."""
        errors = {
            "out_of_range": [],
            "missing_unit": [],
            "unverified_critical": [],
            "invalid_status": []
        }
        
        for key, param in self._parameters.items():
            if not param.validate_value():
                errors["out_of_range"].append(key)
            if not param.unit and isinstance(param.value, (int, float)):
                errors["missing_unit"].append(key)
            if (param.is_critical or param.is_safety_related) and \
               param.status == ParameterStatus.UNVERIFIED:
                errors["unverified_critical"].append(key)
        
        return errors
    
    def initialize_default_parameters(self):
        """
        Initialise les paramètres par défaut selon le cahier des charges.
        Section 11 : Paramètres transversaux à définir.
        """
        
        # === IDENTITÉ ===
        self.register(Parameter(
            name="project_id", category=ParameterCategory.IDENTITY,
            value="", source="system", status=ParameterStatus.SPECIFIED
        ))
        self.register(Parameter(
            name="device_id", category=ParameterCategory.IDENTITY,
            value="", source="system", status=ParameterStatus.SPECIFIED
        ))
        
        # === CONFIGURATION ===
        self.register(Parameter(
            name="hardware_version", category=ParameterCategory.CONFIGURATION,
            value="v1.0", source="system", status=ParameterStatus.SPECIFIED
        ))
        self.register(Parameter(
            name="firmware_version", category=ParameterCategory.CONFIGURATION,
            value="0.1.0", source="system", status=ParameterStatus.SPECIFIED
        ))
        
        # === ÉLECTRICITÉ ===
        self.register(Parameter(
            name="supply_voltage", category=ParameterCategory.ELECTRICAL,
            value=12.0, unit="V", min_value=0.0, max_value=48.0,
            source="default", status=ParameterStatus.UNVERIFIED,
            is_critical=True
        ))
        self.register(Parameter(
            name="max_current", category=ParameterCategory.ELECTRICAL,
            value=5.0, unit="A", min_value=0.0, max_value=50.0,
            source="default", status=ParameterStatus.UNVERIFIED,
            is_critical=True, is_safety_related=True
        ))
        self.register(Parameter(
            name="power_consumption", category=ParameterCategory.ELECTRICAL,
            value=0.0, unit="W", min_value=0.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        self.register(Parameter(
            name="thermal_limit", category=ParameterCategory.ELECTRICAL,
            value=70.0, unit="°C", min_value=-40.0, max_value=150.0,
            source="default", status=ParameterStatus.UNVERIFIED,
            is_critical=True, is_safety_related=True
        ))
        
        # === MÉCANIQUE ===
        self.register(Parameter(
            name="max_load", category=ParameterCategory.MECHANICAL,
            value=100.0, unit="N", min_value=0.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        self.register(Parameter(
            name="max_speed", category=ParameterCategory.MECHANICAL,
            value=1000.0, unit="rpm", min_value=0.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        self.register(Parameter(
            name="max_torque", category=ParameterCategory.MECHANICAL,
            value=10.0, unit="N·m", min_value=0.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        
        # === TEMPS RÉEL ===
        self.register(Parameter(
            name="control_loop_frequency", category=ParameterCategory.REAL_TIME,
            value=100.0, unit="Hz", min_value=1.0, max_value=10000.0,
            source="default", status=ParameterStatus.UNVERIFIED,
            is_critical=True
        ))
        self.register(Parameter(
            name="max_latency", category=ParameterCategory.REAL_TIME,
            value=10.0, unit="ms", min_value=0.1, max_value=1000.0,
            source="default", status=ParameterStatus.UNVERIFIED,
            is_critical=True
        ))
        self.register(Parameter(
            name="communication_timeout", category=ParameterCategory.REAL_TIME,
            value=500.0, unit="ms", min_value=10.0, max_value=10000.0,
            source="default", status=ParameterStatus.SPECIFIED,
            is_safety_related=True
        ))
        
        # === COMMUNICATION ===
        self.register(Parameter(
            name="protocol", category=ParameterCategory.COMMUNICATION,
            value="serial", source="default", status=ParameterStatus.SPECIFIED
        ))
        self.register(Parameter(
            name="baud_rate", category=ParameterCategory.COMMUNICATION,
            value=115200, unit="baud", 
            source="default", status=ParameterStatus.SPECIFIED
        ))
        self.register(Parameter(
            name="data_format", category=ParameterCategory.COMMUNICATION,
            value="json", source="default", status=ParameterStatus.SPECIFIED
        ))
        
        # === SÉCURITÉ ===
        self.register(Parameter(
            name="safe_state", category=ParameterCategory.SAFETY,
            value="powered_off", source="design", 
            status=ParameterStatus.SPECIFIED,
            is_critical=True, is_safety_related=True
        ))
        self.register(Parameter(
            name="emergency_stop_threshold", category=ParameterCategory.SAFETY,
            value=1.5, unit="x_nominal", min_value=1.0, max_value=10.0,
            source="design", status=ParameterStatus.UNVERIFIED,
            is_critical=True, is_safety_related=True,
            requires_human_approval=True
        ))
        self.register(Parameter(
            name="interlock_enabled", category=ParameterCategory.SAFETY,
            value=True, source="design",
            status=ParameterStatus.SPECIFIED,
            is_critical=True, is_safety_related=True
        ))
        
        # === CAPTEURS ===
        self.register(Parameter(
            name="sensor_sampling_rate", category=ParameterCategory.SENSORS,
            value=100.0, unit="Hz", min_value=1.0, max_value=10000.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        self.register(Parameter(
            name="sensor_precision", category=ParameterCategory.SENSORS,
            value=0.1, unit="%", min_value=0.001, max_value=100.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        
        # === ACTIONNEURS ===
        self.register(Parameter(
            name="max_stroke", category=ParameterCategory.ACTUATORS,
            value=100.0, unit="mm", min_value=0.0,
            source="default", status=ParameterStatus.UNVERIFIED
        ))
        self.register(Parameter(
            name="rest_position", category=ParameterCategory.ACTUATORS,
            value=0.0, unit="mm", 
            source="default", status=ParameterStatus.SPECIFIED
        ))