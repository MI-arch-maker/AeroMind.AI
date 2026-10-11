# ai_copilot/validation_gate.py
"""
Porte de validation entre l'IA et l'exécution physique.
Toute action proposée par l'IA doit passer par cette porte.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone


class GateStatus(Enum):
    """Statut de la porte de validation."""
    OPEN = "open"             # Action autorisée
    CONDITIONAL = "conditional"  # Autorisée sous conditions
    BLOCKED = "blocked"       # Bloquée, nécessite validation humaine
    REJECTED = "rejected"     # Rejetée (raison de sécurité)


@dataclass
class ValidationResult:
    """Résultat d'une validation par la porte."""
    status: GateStatus
    reason: str
    conditions: List[str] = field(default_factory=list)
    validated_by: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ValidationGate:
    """
    Porte de validation obligatoire entre l'IA et l'exécution physique.
    
    Règle : "Approbation humaine obligatoire avant toute action physique
    présentant un risque."
    
    Cette porte vérifie :
    1. Que l'action ne présente pas de risque critique
    2. Que les préconditions sont satisfaites
    3. Que l'approbation humaine est obtenue si nécessaire
    """
    
    def __init__(self):
        self._validation_rules: List[Callable[[Dict], ValidationResult]] = []
        self._pending_validations: Dict[str, ValidationResult] = {}
        self._auto_approved_types: List[str] = []  # Types d'actions auto-approuvés
    
    def add_validation_rule(self, rule: Callable[[Dict], ValidationResult]):
        """Ajoute une règle de validation."""
        self._validation_rules.append(rule)
    
    def validate_action(self, action: Dict[str, Any]) -> ValidationResult:
        """
        Valide une action avant exécution.
        
        Args:
            action: Dictionnaire décrivant l'action proposée
        
        Returns:
            ValidationResult avec le statut et les conditions
        """
        # Par défaut, bloquer toute action
        result = ValidationResult(
            status=GateStatus.BLOCKED,
            reason="Validation humaine requise par défaut"
        )
        
        # Vérifier si l'action est dans la liste des auto-approuvés
        action_type = action.get("type", "")
        if action_type in self._auto_approved_types:
            result = ValidationResult(
                status=GateStatus.OPEN,
                reason=f"Action '{action_type}' auto-approuvée"
            )
        
        # Appliquer les règles de validation personnalisées
        for rule in self._validation_rules:
            rule_result = rule(action)
            if rule_result.status == GateStatus.REJECTED:
                return rule_result  # Rejet prioritaire
            elif rule_result.status == GateStatus.BLOCKED:
                result = rule_result
            elif rule_result.status == GateStatus.CONDITIONAL:
                if result.status != GateStatus.BLOCKED:
                    result = rule_result
        
        return result
    
    def approve_action(self, action_id: str, approver: str) -> bool:
        """Approuve manuellement une action en attente."""
        if action_id in self._pending_validations:
            validation = self._pending_validations[action_id]
            validation.status = GateStatus.OPEN
            validation.validated_by = approver
            validation.reason = f"Approuvé par {approver}"
            return True
        return False
    
    def reject_action(self, action_id: str, rejector: str, reason: str) -> bool:
        """Rejette manuellement une action."""
        if action_id in self._pending_validations:
            validation = self._pending_validations[action_id]
            validation.status = GateStatus.REJECTED
            validation.validated_by = rejector
            validation.reason = f"Rejeté par {rejector}: {reason}"
            return True
        return False
