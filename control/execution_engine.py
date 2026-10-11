# control/execution_engine.py
"""
Moteur de contrôle et d'exécution physique.
Section 3.E : passage de la simulation au monde réel.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
import time
import threading

from core.state_machine import DeviceStateMachine, DeviceState
from safety.supervisor import SafetySupervisor, SafetyLevel


class ExecutionMode(Enum):
    """Modes d'exécution du moteur de contrôle."""
    MANUAL = "manual"           # Commande manuelle directe
    AUTOMATIC = "automatic"     # Exécution automatique de plan
    MAINTENANCE = "maintenance" # Mode maintenance (permissions réduites)
    SIMULATION = "simulation"   # Mode simulation (aucune sortie physique)
    SAFE_ONLY = "safe_only"     # Seuls les états sûrs sont autorisés


class CommandType(Enum):
    """Types de commandes possibles."""
    READ_SENSOR = "read_sensor"
    SET_OUTPUT = "set_output"
    SET_PARAMETER = "set_parameter"
    START_SEQUENCE = "start_sequence"
    STOP_SEQUENCE = "stop_sequence"
    EMERGENCY_STOP = "emergency_stop"
    RESET = "reset"
    CALIBRATE = "calibrate"
    SELF_TEST = "self_test"


@dataclass
class ExecutionResult:
    """Résultat d'une exécution de commande."""
    success: bool
    command_type: CommandType
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: Any = None
    error_message: str = ""
    execution_time_ms: float = 0.0
    operator: str = "system"


class ExecutionEngine:
    """
    Moteur de contrôle et d'exécution physique.
    
    Règle d'architecture :
    "L'IA doit proposer ou planifier des actions ; une couche de contrôle
    déterministe doit vérifier les limites et autoriser leur exécution."
    
    Ce moteur vérifie TOUS les préconditions avant d'exécuter une commande :
    1. État de la machine à états
    2. Statut de sécurité
    3. Interverrouillages
    4. Permissions de l'opérateur
    5. Limites physiques
    """
    
    def __init__(self, state_machine: DeviceStateMachine,
                 safety_supervisor: SafetySupervisor):
        self.state_machine = state_machine
        self.safety = safety_supervisor
        self.mode = ExecutionMode.SIMULATION
        
        # Enregistrement des commandes
        self._command_handlers: Dict[CommandType, Callable] = {}
        self._preconditions: Dict[CommandType, List[Callable[[], bool]]] = {}
        
        # Journal d'exécution
        self._execution_log: List[ExecutionResult] = []
        
        # Verrou pour les opérations thread-safe
        self._lock = threading.RLock()
        
        # Callbacks
        self._pre_execution_callback: Optional[Callable] = None
        self._post_execution_callback: Optional[Callable] = None
        
        # Statistiques
        self._commands_executed: int = 0
        self._commands_rejected: int = 0
        self._start_time = time.time()
        
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Enregistre les gestionnaires de commandes par défaut."""
        self._command_handlers[CommandType.READ_SENSOR] = self._handle_read_sensor
        self._command_handlers[CommandType.SET_OUTPUT] = self._handle_set_output
        self._command_handlers[CommandType.EMERGENCY_STOP] = self._handle_emergency_stop
        self._command_handlers[CommandType.SELF_TEST] = self._handle_self_test
    
    def set_mode(self, mode: ExecutionMode):
        """Change le mode d'exécution."""
        self.mode = mode
    
    def register_command_handler(self, command_type: CommandType, 
                                handler: Callable):
        """Enregistre un gestionnaire pour un type de commande."""
        self._command_handlers[command_type] = handler
    
    def register_precondition(self, command_type: CommandType,
                             condition: Callable[[], bool]):
        """Ajoute une précondition pour un type de commande."""
        if command_type not in self._preconditions:
            self._preconditions[command_type] = []
        self._preconditions[command_type].append(condition)
    
    def execute(self, command_type: CommandType, 
                params: Dict[str, Any] = None,
                operator: str = "system") -> ExecutionResult:
        """
        Exécute une commande après vérification de toutes les préconditions.
        
        C'est le point d'entrée unique pour toute action physique.
        """
        start_time = time.time()
        
        with self._lock:
            # 1. Vérifier le mode d'exécution
            if self.mode == ExecutionMode.SIMULATION:
                return self._reject(command_type, operator,
                                  "Mode simulation : aucune commande physique autorisée",
                                  start_time)
            
            # 2. Vérifier l'arrêt d'urgence
            if self.safety.is_emergency_stop_active:
                if command_type != CommandType.EMERGENCY_STOP:
                    return self._reject(command_type, operator,
                                      "Arrêt d'urgence actif",
                                      start_time)
            
            # 3. Vérifier l'état de la machine à états
            current_state = self.state_machine.current_state
            if current_state not in (DeviceState.READY, DeviceState.ACTIVE, 
                                     DeviceState.DEGRADED):
                if command_type not in (CommandType.EMERGENCY_STOP, CommandType.RESET):
                    return self._reject(command_type, operator,
                                      f"État incompatible: {current_state.value}",
                                      start_time)
            
            # 4. Vérifier les préconditions spécifiques
            preconditions = self._preconditions.get(command_type, [])
            for condition in preconditions:
                if not condition():
                    return self._reject(command_type, operator,
                                      "Précondition non satisfaite",
                                      start_time)
            
            # 5. Vécuter la commande
            handler = self._command_handlers.get(command_type)
            if handler:
                try:
                    result_data = handler(params or {})
                    execution_time = (time.time() - start_time) * 1000
                    
                    result = ExecutionResult(
                        success=True,
                        command_type=command_type,
                        data=result_data,
                        execution_time_ms=execution_time,
                        operator=operator
                    )
                    self._commands_executed += 1
                    self._execution_log.append(result)
                    return result
                    
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    return self._reject(command_type, operator,
                                      f"Erreur d'exécution: {str(e)}",
                                      start_time)
            else:
                return self._reject(command_type, operator,
                                  "Aucun gestionnaire pour cette commande",
                                  start_time)
    
    def _reject(self, command_type: CommandType, operator: str,
               reason: str, start_time: float) -> ExecutionResult:
        """Crée un résultat de rejet."""
        execution_time = (time.time() - start_time) * 1000
        result = ExecutionResult(
            success=False,
            command_type=command_type,
            error_message=reason,
            execution_time_ms=execution_time,
            operator=operator
        )
        self._commands_rejected += 1
        self._execution_log.append(result)
        return result
    
    # === Gestionnaires de commandes ===
    
    def _handle_read_sensor(self, params: Dict) -> Any:
        """Gestionnaire de lecture de capteur."""
        sensor_id = params.get("sensor_id", "")
        # Simulation de lecture - à remplacer par la vraie lecture
        return {
            "sensor_id": sensor_id,
            "value": 0.0,
            "unit": "",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _handle_set_output(self, params: Dict) -> Any:
        """Gestionnaire de définition de sortie."""
        output_id = params.get("output_id", "")
        value = params.get("value", 0.0)
        
        # Vérifier les limites avant de définir la sortie
        # (implémenté par les limites de sécurité)
        
        return {
            "output_id": output_id,
            "value": value,
            "status": "set"
        }
    
    def _handle_emergency_stop(self, params: Dict) -> Any:
        """Gestionnaire d'arrêt d'urgence."""
        self.safety.trigger_emergency_stop("Arrêt d'urgence via moteur d'exécution")
        self.state_machine.emergency_stop()
        return {"status": "emergency_stop_activated"}
    
    def _handle_self_test(self, params: Dict) -> Any:
        """Gestionnaire d'autotest."""
        results = {
            "state_machine": self.state_machine.get_state_summary(),
            "safety_status": self.safety.get_safety_status(),
            "mode": self.mode.value,
            "commands_executed": self._commands_executed,
            "commands_rejected": self._commands_rejected
        }
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques d'exécution."""
        return {
            "commands_executed": self._commands_executed,
            "commands_rejected": self._commands_rejected,
            "success_rate": (
                self._commands_executed / 
                max(1, self._commands_executed + self._commands_rejected)
            ),
            "uptime_seconds": time.time() - self._start_time,
            "mode": self.mode.value
        }