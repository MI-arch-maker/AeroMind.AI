# maintenance/predictive.py
"""
Maintenance prédictive et suivi de l'usure.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, timezone
import time
import statistics


@dataclass
class WearIndicator:
    """
    Indicateur d'usure pour un composant.
    
    Suivi du nombre d'heures, cycles, charges et événements.
    """
    indicator_id: str
    component_id: str
    description: str
    unit: str = "cycles"
    
    # Compteurs
    current_value: float = 0.0
    warning_threshold: float = 1000.0
    critical_threshold: float = 1500.0
    expected_lifetime: float = 2000.0
    
    # Historique
    measurements: List[Dict] = field(default_factory=list)
    
    # État
    wear_percentage: float = 0.0
    estimated_remaining_life: float = 0.0
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    def update(self, increment: float):
        """Met à jour l'indicateur d'usure."""
        self.current_value += increment
        self.wear_percentage = (self.current_value / self.expected_lifetime) * 100
        self.estimated_remaining_life = max(0, self.expected_lifetime - self.current_value)
        self.last_updated = datetime.now(timezone.utc).isoformat()
        
        self.measurements.append({
            "value": self.current_value,
            "increment": increment,
            "timestamp": time.time()
        })
    
    @property
    def status(self) -> str:
        """Retourne le statut de l'indicateur."""
        if self.current_value >= self.critical_threshold:
            return "critical"
        elif self.current_value >= self.warning_threshold:
            return "warning"
        else:
            return "normal"


class PredictiveMaintenance:
    """
    Système de maintenance prédictive.
    
    Section 3.I : estimation de l'usure, planification des entretiens,
    alertes avec niveau de criticité et procédure recommandée.
    """
    
    def __init__(self):
        self._wear_indicators: Dict[str, WearIndicator] = {}
        self._maintenance_schedule: List[Dict] = []
        self._alerts: List[Dict] = []
    
    def register_wear_indicator(self, indicator: WearIndicator):
        """Enregistre un indicateur d'usure."""
        self._wear_indicators[indicator.indicator_id] = indicator
    
    def update_indicator(self, indicator_id: str, increment: float):
        """Met à jour un indicateur d'usure."""
        indicator = self._wear_indicators.get(indicator_id)
        if indicator:
            indicator.update(increment)
            self._check_alerts(indicator)
    
    def _check_alerts(self, indicator: WearIndicator):
        """Vérifie si un indicateur nécessite une alerte."""
        if indicator.status == "critical":
            self._alerts.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "critical",
                "indicator_id": indicator.indicator_id,
                "component_id": indicator.component_id,
                "message": f"Usure critique détectée: {indicator.current_value} {indicator.unit} "
                          f"(limite: {indicator.critical_threshold})",
                "recommendation": "Remplacement immédiat du composant recommandé"
            })
        elif indicator.status == "warning":
            self._alerts.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "warning",
                "indicator_id": indicator.indicator_id,
                "component_id": indicator.component_id,
                "message": f"Usure élevée détectée: {indicator.current_value} {indicator.unit} "
                          f"(seuil: {indicator.warning_threshold})",
                "recommendation": "Planifier un entretien dans les meilleurs délais"
            })
    
    def schedule_maintenance(self, component_id: str, maintenance_type: str,
                           description: str, due_date: str):
        """Planifie une opération de maintenance."""
        self._maintenance_schedule.append({
            "component_id": component_id,
            "maintenance_type": maintenance_type,
            "description": description,
            "due_date": due_date,
            "status": "scheduled",
            "scheduled_at": datetime.now(timezone.utc).isoformat()
        })
    
    def get_active_alerts(self) -> List[Dict]:
        """Retourne les alertes actives."""
        return self._alerts
    
    def get_maintenance_schedule(self) -> List[Dict]:
        """Retourne le planning de maintenance."""
        return self._maintenance_schedule
    
    def get_wear_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'usure de tous les composants."""
        return {
            indicator.indicator_id: {
                "component_id": indicator.component_id,
                "current_value": indicator.current_value,
                "unit": indicator.unit,
                "wear_percentage": indicator.wear_percentage,
                "status": indicator.status,
                "estimated_remaining_life": indicator.estimated_remaining_life
            } for indicator in self._wear_indicators.values()
        }