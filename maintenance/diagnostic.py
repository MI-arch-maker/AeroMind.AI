# maintenance/diagnostic.py
"""
Moteur de diagnostic et d'analyse de l'état de santé.
Section 3.I : diagnostic et maintenance prédictive.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import time
import statistics


class HealthStatus(Enum):
    """État de santé d'un composant ou système."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class DiagnosticResult:
    """Résultat d'un diagnostic."""
    component_id: str
    health_status: HealthStatus
    confidence: float  # 0.0 à 1.0
    findings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    measurements_used: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Degré d'incertitude
    uncertainty: float = 0.0  # 0.0 à 1.0
    data_sufficiency: str = "adequate"  # "insufficient", "marginal", "adequate", "excellent"


@dataclass
class ComponentBaseline:
    """
    Valeurs de référence pour un composant sain.
    Utilisées pour détecter les dérives.
    """
    component_id: str
    parameters: Dict[str, Dict[str, float]] = field(default_factory=dict)
    # Format: {"temperature": {"mean": 25.0, "std": 2.0, "min": 20.0, "max": 30.0}}
    
    # Historique de calibration
    calibration_history: List[Dict] = field(default_factory=list)
    
    def set_baseline(self, parameter: str, values: List[float]):
        """Définit la baseline à partir de mesures de référence."""
        if not values:
            return
        
        self.parameters[parameter] = {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0.0,
            "min": min(values),
            "max": max(values),
            "count": len(values)
        }
    
    def is_within_bounds(self, parameter: str, value: float, 
                        n_sigma: float = 3.0) -> bool:
        """Vérifie si une valeur est dans les limites statistiques."""
        if parameter not in self.parameters:
            return True  # Pas de baseline = pas de vérification
        
        baseline = self.parameters[parameter]
        mean = baseline["mean"]
        std = baseline["std"]
        
        if std == 0:
            return abs(value - mean) < 0.001
        
        z_score = abs(value - mean) / std
        return z_score <= n_sigma


class DiagnosticEngine:
    """
    Moteur de diagnostic intelligent.
    
    Section 3.I du cahier des charges :
    "L'IA ne doit pas annoncer qu'un composant est défectueux sur la seule
    base d'une supposition : elle doit fournir les mesures, les éléments
    de preuve, le degré d'incertitude et les tests à réaliser."
    """
    
    def __init__(self):
        self._baselines: Dict[str, ComponentBaseline] = {}
        self._measurement_history: Dict[str, List[Dict]] = {}
        self._diagnostic_rules: List[Callable] = []
        self._last_diagnostics: Dict[str, DiagnosticResult] = {}
        
        # Seuils de détection de dérive
        self.drift_threshold_sigma: float = 3.0
        self.drift_window_size: int = 100
    
    def register_baseline(self, baseline: ComponentBaseline):
        """Enregistre une baseline pour un composant."""
        self._baselines[baseline.component_id] = baseline
    
    def record_measurement(self, component_id: str, parameter: str, 
                          value: float, timestamp: float = None):
        """Enregistre une mesure pour un composant."""
        if component_id not in self._measurement_history:
            self._measurement_history[component_id] = []
        
        record = {
            "parameter": parameter,
            "value": value,
            "timestamp": timestamp or time.time()
        }
        self._measurement_history[component_id].append(record)
        
        # Limiter la taille de l'historique
        if len(self._measurement_history[component_id]) > 10000:
            self._measurement_history[component_id] = \
                self._measurement_history[component_id][-5000:]
    
    def diagnose(self, component_id: str) -> DiagnosticResult:
        """
        Effectue un diagnostic complet d'un composant.
        
        Retourne un résultat avec :
        - L'état de santé évalué
        - Le niveau de confiance
        - Les constats détaillés
        - Les recommandations
        - Les mesures utilisées
        - Le degré d'incertitude
        """
        result = DiagnosticResult(
            component_id=component_id,
            health_status=HealthStatus.UNKNOWN,
            confidence=0.0
        )
        
        # Vérifier si nous avons des données
        history = self._measurement_history.get(component_id, [])
        if not history:
            result.findings.append("Aucune donnée de mesure disponible")
            result.data_sufficiency = "insufficient"
            result.uncertainty = 1.0
            return result
        
        # Évaluer la suffisance des données
        if len(history) < 10:
            result.data_sufficiency = "insufficient"
            result.uncertainty = 0.8
        elif len(history) < 50:
            result.data_sufficiency = "marginal"
            result.uncertainty = 0.4
        else:
            result.data_sufficiency = "adequate"
            result.uncertainty = 0.1
        
        # Analyser les tendances
        baseline = self._baselines.get(component_id)
        if baseline:
            self._analyze_against_baseline(component_id, baseline, result)
        else:
            result.findings.append("Aucune baseline de référence disponible")
            result.recommendations.append(
                "Créer une baseline à partir de mesures sur un composant sain"
            )
        
        # Analyser les valeurs aberrantes
        self._detect_outliers(component_id, history, result)
        
        # Analyser les tendances temporelles
        self._analyze_trends(component_id, history, result)
        
        # Déterminer l'état de santé global
        result.health_status = self._determine_health_status(result)
        result.confidence = max(0.0, 1.0 - result.uncertainty)
        
        # Enregistrer le diagnostic
        self._last_diagnostics[component_id] = result
        
        return result
    
    def _analyze_against_baseline(self, component_id: str, 
                                 baseline: ComponentBaseline,
                                 result: DiagnosticResult):
        """Analyse les mesures par rapport à la baseline."""
        history = self._measurement_history.get(component_id, [])
        
        # Grouper par paramètre
        params_data: Dict[str, List[float]] = {}
        for record in history:
            param = record["parameter"]
            if param not in params_data:
                params_data[param] = []
            params_data[param].append(record["value"])
        
        for param, values in params_data.items():
            if param in baseline.parameters:
                recent_values = values[-self.drift_window_size:]
                
                out_of_bounds_count = sum(
                    1 for v in recent_values 
                    if not baseline.is_within_bounds(param, v, self.drift_threshold_sigma)
                )
                
                if out_of_bounds_count > 0:
                    result.findings.append(
                        f"Paramètre '{param}': {out_of_bounds_count} mesures "
                        f"hors des limites statistiques"
                    )
                    result.measurements_used[param] = {
                        "recent_values": recent_values[-10:],  # Dernières 10
                        "out_of_bounds_count": out_of_bounds_count,
                        "baseline": baseline.parameters[param]
                    }
    
    def _detect_outliers(self, component_id: str, history: List[Dict],
                        result: DiagnosticResult):
        """Détecte les valeurs aberrantes dans les mesures."""
        params_data: Dict[str, List[float]] = {}
        for record in history:
            param = record["parameter"]
            if param not in params_data:
                params_data[param] = []
            params_data[param].append(record["value"])
        
        for param, values in params_data.items():
            if len(values) < 5:
                continue
            
            # Méthode IQR pour la détection d'outliers
            sorted_vals = sorted(values)
            q1 = sorted_vals[len(sorted_vals) // 4]
            q3 = sorted_vals[3 * len(sorted_vals) // 4]
            iqr = q3 - q1
            
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = [v for v in values if v < lower_bound or v > upper_bound]
            
            if outliers:
                result.findings.append(
                    f"Paramètre '{param}': {len(outliers)} valeurs aberrantes détectées"
                )
    
    def _analyze_trends(self, component_id: str, history: List[Dict],
                       result: DiagnosticResult):
        """Analyse les tendances temporelles des mesures."""
        params_data: Dict[str, List[Tuple[float, float]]] = {}
        for record in history:
            param = record["parameter"]
            if param not in params_data:
                params_data[param] = []
            params_data[param].append((record["timestamp"], record["value"]))
        
        for param, time_series in params_data.items():
            if len(time_series) < 10:
                continue
            
            # Calcul de la pente (tendance linéaire)
            values = [v for _, v in time_series]
            n = len(values)
            
            if n > 1:
                # Régression linéaire simple
                x_mean = sum(range(n)) / n
                y_mean = statistics.mean(values)
                
                numerator = sum((i - x_mean) * (v - y_mean) 
                              for i, v in enumerate(values))
                denominator = sum((i - x_mean) ** 2 for i in range(n))
                
                if denominator > 0:
                    slope = numerator / denominator
                    
                    # Détecter une tendance significative
                    value_range = max(values) - min(values)
                    if value_range > 0:
                        normalized_slope = slope / value_range
                        if abs(normalized_slope) > 0.1:  # Tendance > 10% de la plage
                            direction = "croissante" if slope > 0 else "décroissante"
                            result.findings.append(
                                f"Paramètre '{param}': tendance {direction} détectée"
                            )
                            result.recommendations.append(
                                f"Surveiller le paramètre '{param}' : tendance {direction} "
                                f"pourrait indiquer une dérive"
                            )
    
    def _determine_health_status(self, result: DiagnosticResult) -> HealthStatus:
        """Détermine l'état de santé global à partir des constats."""
        findings = result.findings
        
        if not findings:
            return HealthStatus.EXCELLENT
        
        # Compter les problèmes par gravité
        critical_keywords = ["critique", "défaillance", "hors limites"]
        warning_keywords = ["dérive", "aberrantes", "hors des limites"]
        info_keywords = ["tendance"]
        
        critical_count = sum(
            1 for f in findings 
            if any(kw in f.lower() for kw in critical_keywords)
        )
        warning_count = sum(
            1 for f in findings 
            if any(kw in f.lower() for kw in warning_keywords)
        )
        
        if critical_count > 0:
            return HealthStatus.CRITICAL
        elif warning_count > 2:
            return HealthStatus.POOR
        elif warning_count > 0:
            return HealthStatus.FAIR
        else:
            return HealthStatus.GOOD
    
    def get_last_diagnostic(self, component_id: str) -> Optional[DiagnosticResult]:
        """Retourne le dernier diagnostic d'un composant."""
        return self._last_diagnostics.get(component_id)
    
    def get_all_diagnostics(self) -> Dict[str, DiagnosticResult]:
        """Retourne tous les derniers diagnostics."""
        return dict(self._last_diagnostics)