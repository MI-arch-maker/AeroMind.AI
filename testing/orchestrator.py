# testing/orchestrator.py
"""
Orchestrateur de tests automatisés.
Section 7 : chaque test doit comporter identifiant, objectif, conditions,
instruments, configuration, étapes, résultats attendus et mesurés.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Any
from datetime import datetime, timezone
import time
import json


class TestStatus(Enum):
    """Statut possible d'un test."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"       # Impossible d'exécuter
    SKIPPED = "skipped"       # Ignoré volontairement
    NOT_EXECUTED = "not_executed"
    INCONCLUSIVE = "inconclusive"  # Résultat non concluant


class TestPriority(Enum):
    """Priorité d'un test."""
    P0 = "P0"  # Critique - bloquant
    P1 = "P1"  # Important
    P2 = "P2"  # Souhaitable
    P3 = "P3"  # Optionnel


@dataclass
class TestStep:
    """
    Étape individuelle d'un scénario de test.
    """
    step_id: str
    description: str
    expected_result: str
    
    # Fonction d'exécution
    execution_function: Optional[Callable[[], Any]] = None
    
    # Fonction de validation
    validation_function: Optional[Callable[[Any], bool]] = None
    
    # Tolérance
    tolerance: Optional[float] = None
    expected_value: Optional[float] = None
    measured_value: Optional[float] = None
    
    # Résultat
    status: TestStatus = TestStatus.PENDING
    execution_time_ms: float = 0.0
    error_message: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Prérequis
    depends_on: Optional[str] = None  # ID d'une étape précédente


@dataclass
class TestScenario:
    """
    Scénario de test complet.
    
    Section 7 du cahier des charges :
    Chaque test doit comporter :
    - Un identifiant et une version
    - Un objectif précis
    - Les conditions et hypothèses
    - Les instruments employés
    - La configuration matérielle et logicielle
    - Les étapes d'exécution
    - Les résultats attendus et les tolérances
    - Un statut
    - Les preuves associées
    - Le nom du responsable et la date
    """
    
    scenario_id: str
    name: str
    version: str = "1.0"
    description: str = ""
    objective: str = ""
    
    # Classification
    priority: TestPriority = TestPriority.P1
    test_type: str = "functional"  # functional, safety, performance, endurance, regression
    
    # Conditions et hypothèses
    preconditions: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    environmental_conditions: Dict[str, Any] = field(default_factory=dict)
    
    # Instruments et configuration
    required_instruments: List[str] = field(default_factory=list)
    hardware_config: Dict[str, Any] = field(default_factory=dict)
    software_config: Dict[str, Any] = field(default_factory=dict)
    
    # Étapes
    steps: List[TestStep] = field(default_factory=list)
    
    # Résultats
    overall_status: TestStatus = TestStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    total_duration_ms: float = 0.0
    
    # Responsable
    responsible: str = ""
    date: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Preuves et notes
    evidence: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)
    
    # Décision et actions correctives
    decision: str = ""  # "accepted", "rejected", "conditional"
    corrective_actions: List[str] = field(default_factory=list)
    
    def add_step(self, step: TestStep):
        """Ajoute une étape au scénario."""
        self.steps.append(step)
    
    def is_blocking(self) -> bool:
        """Vérifie si ce test est bloquant (P0)."""
        return self.priority == TestPriority.P0


@dataclass
class TestResult:
    """Résultat consolidé d'un scénario de test exécuté."""
    scenario_id: str
    status: TestStatus
    steps_passed: int = 0
    steps_failed: int = 0
    steps_skipped: int = 0
    steps_blocked: int = 0
    total_steps: int = 0
    
    # Détails
    failed_step_ids: List[str] = field(default_factory=list)
    execution_duration_ms: float = 0.0
    
    # Preuves
    measurements: Dict[str, Any] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)
    
    # Timestamp
    executed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    @property
    def pass_rate(self) -> float:
        """Taux de réussite des étapes."""
        if self.total_steps == 0:
            return 0.0
        return self.steps_passed / self.total_steps


class TestOrchestrator:
    """
    Orchestrateur de tests automatisés.
    
    Gère l'exécution de scénarios de test, la collecte de preuves
    et la génération de rapports de validation.
    """
    
    def __init__(self):
        self._scenarios: Dict[str, TestScenario] = {}
        self._results: List[TestResult] = []
        self._execution_log: List[Dict] = []
    
    def register_scenario(self, scenario: TestScenario):
        """Enregistre un scénario de test."""
        self._scenarios[scenario.scenario_id] = scenario
    
    def get_scenario(self, scenario_id: str) -> Optional[TestScenario]:
        """Récupère un scénario par son ID."""
        return self._scenarios.get(scenario_id)
    
    def execute_scenario(self, scenario_id: str, 
                        operator: str = "system") -> TestResult:
        """
        Exécute un scénario de test complet.
        """
        scenario = self._scenarios.get(scenario_id)
        if not scenario:
            return TestResult(
                scenario_id=scenario_id,
                status=TestStatus.BLOCKED,
                logs=[f"Scénario '{scenario_id}' introuvable"]
            )
        
        # Journaliser le début
        scenario.start_time = datetime.now(timezone.utc).isoformat()
        scenario.overall_status = TestStatus.RUNNING
        
        start_timer = time.time()
        result = TestResult(
            scenario_id=scenario_id,
            status=TestStatus.RUNNING,
            total_steps=len(scenario.steps)
        )
        
        # Exécuter chaque étape
        for step in scenario.steps:
            step_result = self._execute_step(step, scenario)
            
            if step_result == TestStatus.PASSED:
                result.steps_passed += 1
            elif step_result == TestStatus.FAILED:
                result.steps_failed += 1
                result.failed_step_ids.append(step.step_id)
                if scenario.is_blocking():
                    # Arrêter l'exécution si test bloquant
                    break
            elif step_result == TestStatus.SKIPPED:
                result.steps_skipped += 1
            elif step_result == TestStatus.BLOCKED:
                result.steps_blocked += 1
        
        # Déterminer le statut global
        if result.steps_failed > 0:
            result.status = TestStatus.FAILED
            scenario.overall_status = TestStatus.FAILED
        elif result.steps_blocked > 0:
            result.status = TestStatus.BLOCKED
            scenario.overall_status = TestStatus.BLOCKED
        elif result.steps_passed == len(scenario.steps):
            result.status = TestStatus.PASSED
            scenario.overall_status = TestStatus.PASSED
        else:
            result.status = TestStatus.INCONCLUSIVE
            scenario.overall_status = TestStatus.INCONCLUSIVE
        
        # Finaliser
        result.execution_duration_ms = (time.time() - start_timer) * 1000
        scenario.end_time = datetime.now(timezone.utc).isoformat()
        scenario.total_duration_ms = result.execution_duration_ms
        
        # Collecter les preuves
        for step in scenario.steps:
            if step.evidence:
                result.measurements[step.step_id] = step.evidence
        
        self._results.append(result)
        
        return result
    
    def _execute_step(self, step: TestStep, 
                     scenario: TestScenario) -> TestStatus:
        """Exécute une étape individuelle de test."""
        step.status = TestStatus.RUNNING
        start_time = time.time()
        
        # Vérifier les dépendances
        if step.depends_on:
            dep_step = next(
                (s for s in scenario.steps if s.step_id == step.depends_on), 
                None
            )
            if dep_step and dep_step.status != TestStatus.PASSED:
                step.status = TestStatus.BLOCKED
                step.error_message = f"Dépendance '{step.depends_on}' non satisfaite"
                return step.status
        
        # Exécuter la fonction d'étape
        if step.execution_function:
            try:
                raw_result = step.execution_function()
                step.execution_time_ms = (time.time() - start_time) * 1000
                
                # Valider le résultat
                if step.validation_function:
                    if step.validation_function(raw_result):
                        step.status = TestStatus.PASSED
                    else:
                        step.status = TestStatus.FAILED
                        step.error_message = "Validation échouée"
                else:
                    # Si pas de validation, considérer comme réussi si pas d'exception
                    step.status = TestStatus.PASSED
                
                # Enregistrer la preuve
                step.evidence = {
                    "raw_result": str(raw_result),
                    "execution_time_ms": step.execution_time_ms,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
            except Exception as e:
                step.status = TestStatus.FAILED
                step.error_message = str(e)
                step.execution_time_ms = (time.time() - start_time) * 1000
        else:
            # Pas de fonction d'exécution = étape manuelle
            step.status = TestStatus.NOT_EXECUTED
            step.error_message = "Étape manuelle (pas de fonction automatique)"
        
        return step.status
    
    def execute_all_scenarios(self, operator: str = "system") -> List[TestResult]:
        """Exécute tous les scénarios enregistrés."""
        results = []
        for scenario_id in self._scenarios:
            result = self.execute_scenario(scenario_id, operator)
            results.append(result)
        return results
    
    def generate_test_report(self) -> Dict[str, Any]:
        """Génère un rapport de test complet."""
        total = len(self._results)
        passed = sum(1 for r in self._results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self._results if r.status == TestStatus.FAILED)
        blocked = sum(1 for r in self._results if r.status == TestStatus.BLOCKED)
        
        return {
            "summary": {
                "total_scenarios": total,
                "passed": passed,
                "failed": failed,
                "blocked": blocked,
                "pass_rate": passed / max(1, total),
                "report_generated_at": datetime.now(timezone.utc).isoformat()
            },
            "detailed_results": [
                {
                    "scenario_id": r.scenario_id,
                    "status": r.status.value,
                    "steps_passed": r.steps_passed,
                    "steps_failed": r.steps_failed,
                    "total_steps": r.total_steps,
                    "pass_rate": r.pass_rate,
                    "duration_ms": r.execution_duration_ms,
                    "failed_steps": r.failed_step_ids
                } for r in self._results
            ],
            "blocking_issues": [
                {
                    "scenario_id": r.scenario_id,
                    "failed_steps": r.failed_step_ids
                } for r in self._results if r.status == TestStatus.FAILED
            ]
        }
    
    def create_standard_test_suite(self) -> List[TestScenario]:
        """
        Crée une suite de tests standard pour validation d'un appareil.
        Section 7 : tests à automatiser.
        """
        scenarios = []
        
        # Test 1 : Autotest au démarrage
        autotest = TestScenario(
            scenario_id="AUTOTEST_001",
            name="Autotest au démarrage",
            version="1.0",
            objective="Vérifier que l'appareil démarre correctement et que tous les composants répondent",
            priority=TestPriority.P0,
            test_type="functional"
        )
        autotest.add_step(TestStep(
            step_id="AT_001",
            description="Vérifier la présence de tous les composants",
            expected_result="Tous les composants détectés et identifiés"
        ))
        autotest.add_step(TestStep(
            step_id="AT_002",
            description="Vérifier la version du firmware",
            expected_result="Version firmware correspond à la version attendue"
        ))
        autotest.add_step(TestStep(
            step_id="AT_003",
            description="Vérifier l'état des capteurs",
            expected_result="Tous les capteurs renvoient des valeurs dans leurs plages"
        ))
        scenarios.append(autotest)
        
        # Test 2 : Test de sécurité
        safety_test = TestScenario(
            scenario_id="SAFETY_001",
            name="Test des dispositifs de sécurité",
            version="1.0",
            objective="Vérifier que tous les dispositifs de sécurité fonctionnent correctement",
            priority=TestPriority.P0,
            test_type="safety"
        )
        safety_test.add_step(TestStep(
            step_id="ST_001",
            description="Tester l'arrêt d'urgence",
            expected_result="Arrêt d'urgence déclenche l'état sûr immédiatement"
        ))
        safety_test.add_step(TestStep(
            step_id="ST_002",
            description="Tester les interverrouillages",
            expected_result="Ouverture d'un interverrouillage arrête le système"
        ))
        safety_test.add_step(TestStep(
            step_id="ST_003",
            description="Tester la détection de surintensité",
            expected_result="Surintensité détectée et coupe l'alimentation"
        ))
        scenarios.append(safety_test)
        
        # Test 3 : Test de communication
        comm_test = TestScenario(
            scenario_id="COMM_001",
            name="Test de communication et reconnexion",
            version="1.0",
            objective="Vérifier la fiabilité de la communication et la reconnexion après perte",
            priority=TestPriority.P1,
            test_type="functional"
        )
        comm_test.add_step(TestStep(
            step_id="CT_001",
            description="Tester la communication normale",
            expected_result="Toutes les commandes et réponses fonctionnent"
        ))
        comm_test.add_step(TestStep(
            step_id="CT_002",
            description="Tester la déconnexion et reconnexion",
            expected_result="Reconnexion automatique après coupure"
        ))
        scenarios.append(comm_test)
        
        # Test 4 : Test de performance
        perf_test = TestScenario(
            scenario_id="PERF_001",
            name="Test de performance et consommation",
            version="1.0",
            objective="Mesurer les performances et la consommation énergétique",
            priority=TestPriority.P1,
            test_type="performance"
        )
        perf_test.add_step(TestStep(
            step_id="PT_001",
            description="Mesurer la consommation au repos",
            expected_result="Consommation inférieure à la spécification"
        ))
        perf_test.add_step(TestStep(
            step_id="PT_002",
            description="Mesurer la consommation en charge",
            expected_result="Consommation dans les limites spécifiées"
        ))
        scenarios.append(perf_test)
        
        # Enregistrer tous les scénarios
        for scenario in scenarios:
            self.register_scenario(scenario)
        
        return scenarios