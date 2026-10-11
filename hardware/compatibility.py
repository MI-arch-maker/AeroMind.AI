# hardware/compatibility.py
"""
Moteur de compatibilité entre composants.
Section 2.C : déterminer si deux composants peuvent fonctionner ensemble.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
from .profiles import HardwareProfile, InterfaceType, ProtocolType, ElectricalSpecs


class CompatibilityLevel(Enum):
    """Niveau de compatibilité entre deux composants."""
    FULLY_COMPATIBLE = "fully_compatible"
    COMPATIBLE_WITH_CONDITIONS = "compatible_with_conditions"
    PARTIALLY_COMPATIBLE = "partially_compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"


class CompatibilityIssueType(Enum):
    """Types de problèmes de compatibilité."""
    VOLTAGE_MISMATCH = "voltage_mismatch"
    CURRENT_INSUFFICIENT = "current_insufficient"
    POWER_EXCEEDED = "power_exceeded"
    PROTOCOL_MISMATCH = "protocol_mismatch"
    INTERFACE_MISMATCH = "interface_mismatch"
    LOGIC_LEVEL_MISMATCH = "logic_level_mismatch"
    LATENCY_EXCEEDED = "latency_exceeded"
    THERMAL_RISK = "thermal_risk"
    SAFETY_CONFLICT = "safety_conflict"
    MISSING_INTERFACE = "missing_interface"
    DATA_RATE_MISMATCH = "data_rate_mismatch"


@dataclass
class CompatibilityIssue:
    """Représente un problème de compatibilité détecté."""
    issue_type: CompatibilityIssueType
    severity: str  # "info", "warning", "error", "critical"
    component_a: str
    component_b: str
    description: str
    recommendation: str = ""


@dataclass
class CompatibilityResult:
    """Résultat d'une analyse de compatibilité."""
    component_a_id: str
    component_b_id: str
    level: CompatibilityLevel
    issues: List[CompatibilityIssue] = field(default_factory=list)
    
    # Détails techniques
    shared_protocols: List[str] = field(default_factory=list)
    shared_interfaces: List[str] = field(default_factory=list)
    
    def has_critical_issues(self) -> bool:
        """Vérifie s'il y a des problèmes critiques."""
        return any(i.severity == "critical" for i in self.issues)
    
    def has_errors(self) -> bool:
        """Vérifie s'il y a des erreurs."""
        return any(i.severity == "error" for i in self.issues)
    
    def get_summary(self) -> str:
        """Retourne un résumé lisible."""
        if self.level == CompatibilityLevel.FULLY_COMPATIBLE:
            return "✓ Compatibilité complète"
        elif self.level == CompatibilityLevel.COMPATIBLE_WITH_CONDITIONS:
            return "⚠ Compatible avec conditions"
        elif self.level == CompatibilityLevel.PARTIALLY_COMPATIBLE:
            return "⚠ Partiellement compatible"
        elif self.level == CompatibilityLevel.INCOMPATIBLE:
            return "✗ Incompatible"
        else:
            return "? Compatibilité inconnue"


class CompatibilityEngine:
    """
    Moteur de compatibilité universelle.
    
    Détermine si deux composants peuvent réellement fonctionner ensemble
    en analysant : tension, puissance, connectique, protocole, latence,
    capacité de calcul, pilotes et contraintes de sécurité.
    """
    
    def __init__(self):
        self._known_profiles: Dict[str, HardwareProfile] = {}
        self._compatibility_overrides: Dict[Tuple[str, str], CompatibilityLevel] = {}
    
    def register_profile(self, profile: HardwareProfile):
        """Enregistre un profil dans le moteur."""
        self._known_profiles[profile.profile_id] = profile
    
    def get_profile(self, profile_id: str) -> Optional[HardwareProfile]:
        """Récupère un profil enregistré."""
        return self._known_profiles.get(profile_id)
    
    def check_compatibility(self, profile_a: HardwareProfile, 
                           profile_b: HardwareProfile) -> CompatibilityResult:
        """
        Analyse la compatibilité entre deux profils matériels.
        
        Vérifie tous les aspects : électrique, communication, sécurité.
        """
        result = CompatibilityResult(
            component_a_id=profile_a.profile_id,
            component_b_id=profile_b.profile_id,
            level=CompatibilityLevel.FULLY_COMPATIBLE
        )
        
        # 1. Vérification électrique
        self._check_electrical(profile_a, profile_b, result)
        
        # 2. Vérification des protocoles de communication
        self._check_communication(profile_a, profile_b, result)
        
        # 3. Vérification des interfaces physiques
        self._check_interfaces(profile_a, profile_b, result)
        
        # 4. Vérification thermique
        self._check_thermal(profile_a, profile_b, result)
        
        # 5. Vérification de sécurité
        self._check_safety(profile_a, profile_b, result)
        
        # Déterminer le niveau global
        result.level = self._determine_overall_level(result)
        
        return result
    
    def _check_electrical(self, a: HardwareProfile, b: HardwareProfile,
                         result: CompatibilityResult):
        """Vérifie la compatibilité électrique."""
        # Vérifier les niveaux logiques
        if abs(a.electrical.logic_level - b.electrical.logic_level) > 0.5:
            result.issues.append(CompatibilityIssue(
                issue_type=CompatibilityIssueType.LOGIC_LEVEL_MISMATCH,
                severity="error",
                component_a=a.profile_id,
                component_b=b.profile_id,
                description=f"Niveaux logiques différents: {a.electrical.logic_level}V vs {b.electrical.logic_level}V",
                recommendation="Utiliser un convertisseur de niveau logique"
            ))
        
        # Vérifier la tension nominale
        if a.electrical.nominal_voltage != b.electrical.nominal_voltage:
            # Vérifier si l'un peut alimenter l'autre
            if not b.electrical.is_voltage_compatible(a.electrical.nominal_voltage) and \
               not a.electrical.is_voltage_compatible(b.electrical.nominal_voltage):
                result.issues.append(CompatibilityIssue(
                    issue_type=CompatibilityIssueType.VOLTAGE_MISMATCH,
                    severity="error",
                    component_a=a.profile_id,
                    component_b=b.profile_id,
                    description=f"Tensions incompatibles: {a.electrical.nominal_voltage}V vs {b.electrical.nominal_voltage}V",
                    recommendation="Utiliser un régulateur de tension ou un convertisseur DC-DC"
                ))
        
        # Vérifier le courant disponible
        # (si A alimente B, A doit pouvoir fournir le courant de B)
        if a.electrical.max_power > 0 and b.electrical.max_power > 0:
            if b.electrical.max_power > a.electrical.max_power:
                result.issues.append(CompatibilityIssue(
                    issue_type=CompatibilityIssueType.CURRENT_INSUFFICIENT,
                    severity="warning",
                    component_a=a.profile_id,
                    component_b=b.profile_id,
                    description=f"Puissance insuffisante: A fournit {a.electrical.max_power}W, B nécessite {b.electrical.max_power}W",
                    recommendation="Utiliser une alimentation externe dédiée"
                ))
    
    def _check_communication(self, a: HardwareProfile, b: HardwareProfile,
                            result: CompatibilityResult):
        """Vérifie la compatibilité des protocoles de communication."""
        protocols_a = {i.protocol for i in a.interfaces}
        protocols_b = {i.protocol for i in b.interfaces}
        shared = protocols_a & protocols_b
        
        if not shared:
            result.issues.append(CompatibilityIssue(
                issue_type=CompatibilityIssueType.PROTOCOL_MISMATCH,
                severity="error",
                component_a=a.profile_id,
                component_b=b.profile_id,
                description="Aucun protocole de communication commun",
                recommendation="Ajouter un adaptateur de protocole ou un convertisseur"
            ))
        else:
            result.shared_protocols = [p.value for p in shared]
            
            # Vérifier les débits
            for iface_a in a.interfaces:
                for iface_b in b.interfaces:
                    if iface_a.protocol == iface_b.protocol:
                        if iface_a.max_data_rate > 0 and iface_b.max_data_rate > 0:
                            min_rate = min(iface_a.max_data_rate, iface_b.max_data_rate)
                            result.shared_interfaces.append(
                                f"{iface_a.protocol.value}@{min_rate}"
                            )
    
    def _check_interfaces(self, a: HardwareProfile, b: HardwareProfile,
                         result: CompatibilityResult):
        """Vérifie la compatibilité des interfaces physiques."""
        interfaces_a = {i.interface_type for i in a.interfaces}
        interfaces_b = {i.interface_type for i in b.interfaces}
        shared_physical = interfaces_a & interfaces_b
        
        if not shared_physical and not result.shared_protocols:
            result.issues.append(CompatibilityIssue(
                issue_type=CompatibilityIssueType.INTERFACE_MISMATCH,
                severity="warning",
                component_a=a.profile_id,
                component_b=b.profile_id,
                description="Aucune interface physique commune",
                recommendation="Utiliser un adaptateur physique ou un bus de conversion"
            ))
    
    def _check_thermal(self, a: HardwareProfile, b: HardwareProfile,
                      result: CompatibilityResult):
        """Vérifie les contraintes thermiques."""
        # Si les deux composants sont proches, vérifier l'échauffement mutuel
        combined_power = a.electrical.max_power + b.electrical.max_power
        min_thermal_limit = min(a.electrical.thermal_limit, b.electrical.thermal_limit)
        
        # Heuristique : si la puissance combinée est élevée par rapport à la limite thermique
        if combined_power > 50 and min_thermal_limit < 70:
            result.issues.append(CompatibilityIssue(
                issue_type=CompatibilityIssueType.THERMAL_RISK,
                severity="warning",
                component_a=a.profile_id,
                component_b=b.profile_id,
                description=f"Puissance combinée {combined_power}W avec limite thermique {min_thermal_limit}°C",
                recommendation="Prévoir une dissipation thermique adéquate ou un refroidissement actif"
            ))
    
    def _check_safety(self, a: HardwareProfile, b: HardwareProfile,
                     result: CompatibilityResult):
        """Vérifie la cohérence des exigences de sécurité."""
        # Si un composant est à haut risque et l'autre n'a pas de protections
        high_risk = "high" in (a.safety.risk_level, b.safety.risk_level)
        has_protection = a.safety.has_overcurrent_protection or b.safety.has_overcurrent_protection
        
        if high_risk and not has_protection:
            result.issues.append(CompatibilityIssue(
                issue_type=CompatibilityIssueType.SAFETY_CONFLICT,
                severity="critical",
                component_a=a.profile_id,
                component_b=b.profile_id,
                description="Composant à haut risque sans protection de surintensité",
                recommendation="Ajouter des protections (fusible, disjoncteur) avant tout essai"
            ))
    
    def _determine_overall_level(self, result: CompatibilityResult) -> CompatibilityLevel:
        """Détermine le niveau global de compatibilité."""
        if any(i.severity == "critical" for i in result.issues):
            return CompatibilityLevel.INCOMPATIBLE
        if any(i.severity == "error" for i in result.issues):
            return CompatibilityLevel.INCOMPATIBLE
        if any(i.severity == "warning" for i in result.issues):
            if result.shared_protocols:
                return CompatibilityLevel.COMPATIBLE_WITH_CONDITIONS
            return CompatibilityLevel.PARTIALLY_COMPATIBLE
        if not result.shared_protocols and not result.shared_interfaces:
            return CompatibilityLevel.UNKNOWN
        return CompatibilityLevel.FULLY_COMPATIBLE
    
    def check_system_compatibility(self, profiles: List[HardwareProfile]) -> List[CompatibilityResult]:
        """
        Vérifie la compatibilité de tous les composants d'un système.
        
        Effectue une analyse par paires de tous les composants.
        """
        results = []
        for i in range(len(profiles)):
            for j in range(i + 1, len(profiles)):
                result = self.check_compatibility(profiles[i], profiles[j])
                results.append(result)
        return results
    
    def generate_compatibility_report(self, results: List[CompatibilityResult]) -> Dict:
        """Génère un rapport de compatibilité complet."""
        total_pairs = len(results)
        compatible = sum(1 for r in results if r.level == CompatibilityLevel.FULLY_COMPATIBLE)
        conditional = sum(1 for r in results if r.level == CompatibilityLevel.COMPATIBLE_WITH_CONDITIONS)
        incompatible = sum(1 for r in results if r.level == CompatibilityLevel.INCOMPATIBLE)
        
        all_issues = []
        for r in results:
            all_issues.extend(r.issues)
        
        return {
            "summary": {
                "total_pairs_analyzed": total_pairs,
                "fully_compatible": compatible,
                "compatible_with_conditions": conditional,
                "incompatible": incompatible,
                "unknown": total_pairs - compatible - conditional - incompatible
            },
            "critical_issues": [
                i.description for i in all_issues if i.severity == "critical"
            ],
            "errors": [
                i.description for i in all_issues if i.severity == "error"
            ],
            "warnings": [
                i.description for i in all_issues if i.severity == "warning"
            ],
            "recommendations": list(set(
                i.recommendation for i in all_issues if i.recommendation
            ))
        }