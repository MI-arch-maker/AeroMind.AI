# main.py
"""
AeroMind AI — Point d'entrée principal
Orchestration de tous les modules selon l'architecture 5 couches.
"""

import sys
import json
from datetime import datetime, timezone

# Import des modules
from core.identity import DeviceIdentity, ProjectIdentity, IdentityType
from core.parameters import ParameterRepository, Parameter, ParameterCategory, ParameterStatus
from core.state_machine import DeviceStateMachine, DeviceState
from hardware.profiles import HardwareProfile, DeviceCategory, create_esp32_profile, create_stm32_profile
from hardware.compatibility import CompatibilityEngine, CompatibilityLevel
from hardware.gateway import DeviceGateway, GatewayEvent, GatewayEventType
from safety.supervisor import SafetySupervisor, SafetyLevel
from safety.interlocks import InterlockManager, Interlock, InterlockType, InterlockStatus
from control.execution_engine import ExecutionEngine, ExecutionMode, CommandType
from control.pid_controller import PIDController, PIDGains, PIDLimits
from testing.orchestrator import TestOrchestrator, TestScenario, TestStep, TestStatus, TestPriority
from maintenance.diagnostic import DiagnosticEngine, HealthStatus
from maintenance.predictive import PredictiveMaintenance, WearIndicator
from security.authentication import AuthenticationManager, UserRole, Permission
from security.audit import AuditLogger, AuditEventType
from simulation.digital_twin import DigitalTwinEngine, TwinModel
from simulation.physics_models import ThermalModel, ElectricalModel, MechanicalModel
from ai_copilot.engineering_assistant import EngineeringCopilot, SuggestionType
from ai_copilot.validation_gate import ValidationGate, GateStatus


class AeroMindAI:
    """
    Application principale AeroMind AI.
    
    Orchestre les 5 couches de l'architecture :
    1. Conception et ingénierie
    2. Simulation et jumeau numérique
    3. Intégration matériel-logiciel
    4. Bancs d'essai et validation
    5. Exploitation et maintenance
    """
    
    def __init__(self):
        print("╔══════════════════════════════════════════════════════════╗")
        print("║          AeroMind AI — Engineering Laboratory             ║")
        print("║          Version 2.0.0 — Architecture 5 couches          ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print()
        
        # === Couche 1 : Conception et ingénierie ===
        self.parameter_repo = ParameterRepository()
        self.parameter_repo.initialize_default_parameters()
        
        # === Sécurité (transversal, initialisé en premier) ===
        self.safety_supervisor = SafetySupervisor()
        self.safety_supervisor.initialize_default_limits()
        self.interlock_manager = InterlockManager()
        
        # === Couche 2 : Simulation et jumeau numérique ===
        self.digital_twin = DigitalTwinEngine()
        
        # === Couche 3 : Intégration matériel-logiciel ===
        self.compatibility_engine = CompatibilityEngine()
        self.device_gateway = DeviceGateway()
        
        # === Machine à états et contrôle ===
        self.state_machine = DeviceStateMachine("main_device")
        self.execution_engine = ExecutionEngine(
            self.state_machine, self.safety_supervisor
        )
        
        # === Couche 4 : Bancs d'essai et validation ===
        self.test_orchestrator = TestOrchestrator()
        self.test_orchestrator.create_standard_test_suite()
        
        # === Couche 5 : Exploitation et maintenance ===
        self.diagnostic_engine = DiagnosticEngine()
        self.predictive_maintenance = PredictiveMaintenance()
        
        # === Sécurité informatique ===
        self.auth_manager = AuthenticationManager()
        self.audit_logger = AuditLogger()
        
        # === IA ===
        self.copilot = EngineeringCopilot()
        self.validation_gate = ValidationGate()
        
        # Configuration
        self._setup_safety_callbacks()
        self._setup_audit()
        self._register_default_profiles()
        
        print("✓ Tous les modules initialisés")
        print(f"✓ Paramètres transversaux : {len(self.parameter_repo._parameters)}")
        print(f"✓ Limites de sécurité : {len(self.safety_supervisor._limits)}")
        print(f"✓ Scénarios de test : {len(self.test_orchestrator._scenarios)}")
        print()
    
    def _setup_safety_callbacks(self):
        """Configure les callbacks de sécurité."""
        def on_emergency():
            print("⚠️  ARRÊT D'URGENCE DÉCLENCHÉ — ÉTAT SÛR APPLIQUÉ")
            self.state_machine.emergency_stop()
            self.audit_logger.log(
                AuditEventType.EMERGENCY_STOP,
                "safety_system",
                "Arrêt d'urgence automatique",
                severity="critical"
            )
        
        self.safety_supervisor.set_safe_state_callback(on_emergency)
    
    def _setup_audit(self):
        """Configure le journal d'audit."""
        # Connecter l'authentification à l'audit
        self.auth_manager.set_audit_callback(
            lambda event: self.audit_logger.log(
                AuditEventType.AUTHENTICATION,
                event.get("username", "unknown"),
                event.get("event", "unknown"),
                details=event
            )
        )
    
    def _register_default_profiles(self):
        """Enregistre les profils matériels par défaut."""
        esp32 = create_esp32_profile()
        stm32 = create_stm32_profile()
        
        self.compatibility_engine.register_profile(esp32)
        self.compatibility_engine.register_profile(stm32)
    
    # === Méthodes publiques ===
    
    def create_project(self, name: str, project_type: str = "") -> ProjectIdentity:
        """Crée un nouveau projet d'ingénierie."""
        project = ProjectIdentity()
        project.project_name = name
        project.project_type = project_type
        
        self.audit_logger.log(
            AuditEventType.SYSTEM_EVENT,
            "system",
            f"Projet créé: {name}",
            target=project.project_id
        )
        
        return project
    
    def check_compatibility(self, profile_a_id: str, profile_b_id: str) -> Dict:
        """Vérifie la compatibilité entre deux composants."""
        profile_a = self.compatibility_engine.get_profile(profile_a_id)
        profile_b = self.compatibility_engine.get_profile(profile_b_id)
        
        if not profile_a or not profile_b:
            return {"error": "Profil introuvable"}
        
        result = self.compatibility_engine.check_compatibility(profile_a, profile_b)
        
        return {
            "status": result.get_summary(),
            "level": result.level.value,
            "issues": [
                {
                    "type": i.issue_type.value,
                    "severity": i.severity,
                    "description": i.description,
                    "recommendation": i.recommendation
                } for i in result.issues
            ],
            "shared_protocols": result.shared_protocols
        }
    
    def run_safety_check(self) -> Dict:
        """Effectue une vérification complète de sécurité."""
        safety_status = self.safety_supervisor.get_safety_status()
        interlock_status = self.interlock_manager.get_status_summary()
        
        return {
            "safety": safety_status,
            "interlocks": interlock_status,
            "all_safe": (
                safety_status["current_level"] == "normal" and 
                interlock_status["all_safe"]
            )
        }
    
    def execute_test_suite(self) -> Dict:
        """Exécute la suite de tests standard."""
        results = self.test_orchestrator.execute_all_scenarios()
        report = self.test_orchestrator.generate_test_report()
        
        # Journaliser
        self.audit_logger.log(
            AuditEventType.TEST_EXECUTION,
            "system",
            f"Suite de tests exécutée: {report['summary']['passed']}/{report['summary']['total_scenarios']} réussis"
        )
        
        return report
    
    def run_simulation(self, model_id: str, duration: float = 1.0) -> Dict:
        """Exécute une simulation avec le jumeau numérique."""
        result = self.digital_twin.run_simulation(
            model_id, duration, dt=0.001
        )
        
        return {
            "status": result.status.value,
            "duration_ms": result.duration_ms,
            "time_steps": result.time_steps,
            "final_state": result.final_state,
            "calibration_status": result.calibration_status,
            "uncertainty": result.uncertainty_estimate
        }
    
    def get_system_status(self) -> Dict:
        """Retourne le statut global du système."""
        return {
            "state_machine": self.state_machine.get_state_summary(),
            "safety": self.safety_supervisor.get_safety_status(),
            "execution_stats": self.execution_engine.get_statistics(),
            "audit_stats": self.audit_logger.get_statistics(),
            "audit_integrity": self.audit_logger.verify_integrity()
        }
    
    def create_default_user(self):
        """Crée un utilisateur administrateur par défaut."""
        self.auth_manager.create_user(
            username="admin",
            password="changeme_immediately",
            role=UserRole.ADMINISTRATOR,
            full_name="Administrateur"
        )
        print("⚠️  Utilisateur 'admin' créé avec mot de passe par défaut")
        print("   → Changez-le immédiatement après le premier démarrage")


def main():
    """Fonction principale."""
    app = AeroMindAI()
    
    # Créer un utilisateur par défaut
    app.create_default_user()
    
    # Exemple : vérification de compatibilité
    print("\n=== Test de compatibilité ESP32 ↔ STM32 ===")
    compat = app.check_compatibility("esp32_devkit_v1", "stm32f4_discovery")
    print(json.dumps(compat, indent=2, ensure_ascii=False))
    
    # Exemple : vérification de sécurité
    print("\n=== Vérification de sécurité ===")
    safety = app.run_safety_check()
    print(json.dumps(safety, indent=2, ensure_ascii=False))
    
    # Exemple : statut du système
    print("\n=== Statut global du système ===")
    status = app.get_system_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    print("\n✓ AeroMind AI initialisé avec succès")


if __name__ == "__main__":
    main()