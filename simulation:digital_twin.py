# simulation/digital_twin.py
"""
Moteur de jumeau numérique.
Section 2.B : simulation réaliste avec calibration progressive.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import time
import math


class SimulationStatus(Enum):
    """Statut d'une simulation."""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    CALIBRATING = "calibrating"


@dataclass
class SimulationResult:
    """Résultat d'une simulation."""
    simulation_id: str
    status: SimulationStatus
    duration_ms: float = 0.0
    time_steps: int = 0
    
    # Données de simulation
    state_history: List[Dict[str, Any]] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    
    # Métadonnées
    model_version: str = "1.0"
    calibration_status: str = "uncalibrated"
    uncertainty_estimate: float = 0.5  # Incertitude estimée (0=precis, 1=inconnu)
    
    # Comparaison avec mesures réelles (si disponibles)
    comparison_with_measurements: Optional[Dict] = None
    
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TwinModel:
    """
    Modèle de jumeau numérique pour un appareil ou composant.
    
    Le modèle doit être progressivement calibré à partir de mesures réelles.
    Il ne doit jamais être présenté comme parfaitement fidèle sans validation.
    """
    
    def __init__(self, model_id: str, model_type: str):
        self.model_id = model_id
        self.model_type = model_type
        
        # État du modèle
        self.state: Dict[str, float] = {}
        self.parameters: Dict[str, float] = {}
        
        # Calibration
        self.calibration_data: List[Dict[str, Any]] = []
        self.is_calibrated: bool = False
        self.calibration_error: float = float('inf')
        
        # Métadonnées
        self.version: str = "1.0"
        self.domain_of_validity: Dict[str, Any] = {
            "temperature_range": (-40, 85),
            "voltage_range": (0, 48),
            "max_iterations": 100000
        }
        
        # Fonction de mise à jour
        self._update_function: Optional[Callable] = None
    
    def set_update_function(self, func: Callable[[Dict, float, Dict], Dict]):
        """
        Définit la fonction de mise à jour du modèle.
        
        Args:
            func: Fonction(state, dt, inputs) -> new_state
        """
        self._update_function = func
    
    def step(self, dt: float, inputs: Dict[str, float]) -> Dict[str, float]:
        """
        Avance le modèle d'un pas de temps.
        
        Args:
            dt: Pas de temps en secondes
            inputs: Entrées du modèle
        
        Returns:
            Nouvel état du modèle
        """
        if self._update_function:
            self.state = self._update_function(self.state, dt, inputs)
        return dict(self.state)
    
    def calibrate(self, measured_data: List[Dict[str, float]]) -> float:
        """
        Calibre le modèle à partir de mesures réelles.
        
        Returns:
            Erreur de calibration (plus petite = meilleur)
        """
        if not measured_data:
            return float('inf')
        
        # Calculer l'erreur entre simulation et mesures
        # (implémentation simplifiée)
        total_error = 0.0
        count = 0
        
        for measurement in measured_data:
            for param, measured_value in measurement.items():
                if param in self.state:
                    simulated_value = self.state[param]
                    error = abs(simulated_value - measured_value)
                    total_error += error
                    count += 1
        
        if count > 0:
            self.calibration_error = total_error / count
            self.is_calibrated = self.calibration_error < 0.1  # Seuil arbitraire
        
        self.calibration_data = measured_data
        return self.calibration_error
    
    def is_within_validity_domain(self, conditions: Dict[str, Any]) -> bool:
        """Vérifie si les conditions sont dans le domaine de validité."""
        for key, value in conditions.items():
            if key in self.domain_of_validity:
                domain = self.domain_of_validity[key]
                if isinstance(domain, tuple) and len(domain) == 2:
                    if not (domain[0] <= value <= domain[1]):
                        return False
        return True


class DigitalTwinEngine:
    """
    Moteur de jumeau numérique.
    
    Gère les modèles numériques des appareils, exécute les simulations
    et compare les résultats avec les mesures physiques.
    """
    
    def __init__(self):
        self._models: Dict[str, TwinModel] = {}
        self._simulation_results: List[SimulationResult] = []
        self._active_simulations: Dict[str, SimulationStatus] = {}
    
    def register_model(self, model: TwinModel):
        """Enregistre un modèle de jumeau numérique."""
        self._models[model.model_id] = model
    
    def get_model(self, model_id: str) -> Optional[TwinModel]:
        """Récupère un modèle par son ID."""
        return self._models.get(model_id)
    
    def run_simulation(self, model_id: str, duration: float, 
                      dt: float = 0.001,
                      inputs: Dict[str, float] = None,
                      initial_conditions: Dict[str, float] = None) -> SimulationResult:
        """
        Exécute une simulation avec le modèle spécifié.
        
        Args:
            model_id: ID du modèle à utiliser
            duration: Durée de simulation en secondes
            dt: Pas de temps en secondes
            inputs: Entrées constantes pendant la simulation
            initial_conditions: Conditions initiales
        
        Returns:
            Résultat de simulation avec historique d'états
        """
        model = self._models.get(model_id)
        if not model:
            return SimulationResult(
                simulation_id=f"sim_error",
                status=SimulationStatus.FAILED
            )
        
        # Initialiser
        if initial_conditions:
            model.state = dict(initial_conditions)
        
        inputs = inputs or {}
        result = SimulationResult(
            simulation_id=f"sim_{model_id}_{int(time.time())}",
            status=SimulationStatus.RUNNING,
            model_version=model.version,
            calibration_status="calibrated" if model.is_calibrated else "uncalibrated"
        )
        
        start_time = time.time()
        num_steps = int(duration / dt)
        
        # Boucle de simulation
        for step in range(num_steps):
            current_time = step * dt
            
            # Mettre à jour le modèle
            new_state = model.step(dt, inputs)
            
            # Enregistrer l'état (échantillonnage pour économiser la mémoire)
            if step % max(1, num_steps // 1000) == 0:
                result.state_history.append({
                    "time": current_time,
                    **new_state
                })
            
            # Vérifier le domaine de validité
            if not model.is_within_validity_domain(new_state):
                result.status = SimulationStatus.ABORTED
                result.final_state = new_state
                result.duration_ms = (time.time() - start_time) * 1000
                result.time_steps = step
                return result
        
        # Finaliser
        result.status = SimulationStatus.COMPLETED
        result.final_state = dict(model.state)
        result.duration_ms = (time.time() - start_time) * 1000
        result.time_steps = num_steps
        
        # Estimer l'incertitude
        if model.is_calibrated:
            result.uncertainty_estimate = min(0.5, model.calibration_error)
        else:
            result.uncertainty_estimate = 0.8  # Incertitude élevée sans calibration
        
        self._simulation_results.append(result)
        
        return result
    
    def compare_with_measurements(self, simulation_result: SimulationResult,
                                 measurements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare les résultats de simulation avec des mesures réelles.
        
        Retourne un rapport de comparaison détaillé.
        """
        if not simulation_result.state_history or not measurements:
            return {"error": "Données insuffisantes pour comparaison"}
        
        # Calculer les erreurs pour chaque paramètre
        errors: Dict[str, List[float]] = {}
        
        for measurement in measurements:
            timestamp = measurement.get("timestamp", 0)
            
            # Trouver le point de simulation le plus proche
            closest_sim = min(
                simulation_result.state_history,
                key=lambda s: abs(s.get("time", 0) - timestamp)
            )
            
            for param, measured_value in measurement.items():
                if param in closest_sim:
                    simulated_value = closest_sim[param]
                    error = abs(simulated_value - measured_value)
                    if param not in errors:
                        errors[param] = []
                    errors[param].append(error)
        
        # Calculer les statistiques d'erreur
        comparison = {
            "parameters_compared": list(errors.keys()),
            "errors": {},
            "overall_quality": "unknown"
        }
        
        total_rmse = 0.0
        param_count = 0
        
        for param, error_list in errors.items():
            if error_list:
                rmse = math.sqrt(sum(e**2 for e in error_list) / len(error_list))
                max_error = max(error_list)
                mean_error = sum(error_list) / len(error_list)
                
                comparison["errors"][param] = {
                    "rmse": rmse,
                    "max_error": max_error,
                    "mean_error": mean_error,
                    "sample_count": len(error_list)
                }
                
                total_rmse += rmse
                param_count += 1
        
        if param_count > 0:
            avg_rmse = total_rmse / param_count
            if avg_rmse < 0.05:
                comparison["overall_quality"] = "excellent"
            elif avg_rmse < 0.1:
                comparison["overall_quality"] = "good"
            elif avg_rmse < 0.2:
                comparison["overall_quality"] = "fair"
            else:
                comparison["overall_quality"] = "poor"
        
        return comparison
    
    def get_all_results(self) -> List[SimulationResult]:
        """Retourne tous les résultats de simulation."""
        return self._simulation_results