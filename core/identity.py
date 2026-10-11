# core/identity.py
"""
Gestion des identités uniques pour chaque appareil et projet.
Couche 1 à 5 : chaque entité possède une identité traçable.
"""

import uuid
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import json


class IdentityType(Enum):
    """Types d'entités identifiables dans le système."""
    PROJECT = "project"
    DEVICE = "device"
    COMPONENT = "component"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    TEST_BENCH = "test_bench"
    FIRMWARE = "firmware"
    TEST_SESSION = "test_session"


@dataclass
class DeviceIdentity:
    """
    Identité normalisée d'un appareil physique ou virtuel.
    
    Conforme au cahier des charges section 2.C :
    chaque appareil possède une identité unique et traçable.
    """
    
    # Identification de base
    unique_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    identity_type: IdentityType = IdentityType.DEVICE
    
    # Informations constructeur
    manufacturer: str = ""
    model: str = ""
    serial_number: str = ""
    fabrication_date: Optional[str] = None
    
    # Classification
    device_category: str = ""  # ex: microcontroller, sensor_bench, robot_arm
    application_domain: str = ""  # ex: prototyping, industrial, laboratory
    
    # Version et configuration
    hardware_version: str = ""
    firmware_version: str = ""
    driver_version: str = ""
    
    # Traçabilité
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_modified: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Dossier numérique (section 6.B du cahier des charges)
    lifecycle_records: List[Dict[str, Any]] = field(default_factory=list)
    
    # Statut d'autorisation
    is_authorized_for_service: bool = False
    authorization_records: List[Dict[str, Any]] = field(default_factory=list)
    
    def compute_checksum(self) -> str:
        """Calcule une somme de contrôle unique pour cette identité."""
        identity_data = json.dumps({
            "unique_id": self.unique_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "hardware_version": self.hardware_version,
            "firmware_version": self.firmware_version
        }, sort_keys=True)
        return hashlib.sha256(identity_data.encode()).hexdigest()
    
    def add_lifecycle_record(self, record_type: str, description: str, 
                            operator: str, details: Dict[str, Any] = None):
        """Ajoute un enregistrement au dossier de cycle de vie."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": record_type,
            "description": description,
            "operator": operator,
            "details": details or {},
            "device_checksum": self.compute_checksum()
        }
        self.lifecycle_records.append(record)
        self.last_modified = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise l'identité en dictionnaire."""
        return {
            "unique_id": self.unique_id,
            "identity_type": self.identity_type.value,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "fabrication_date": self.fabrication_date,
            "device_category": self.device_category,
            "application_domain": self.application_domain,
            "hardware_version": self.hardware_version,
            "firmware_version": self.firmware_version,
            "driver_version": self.driver_version,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "lifecycle_records": self.lifecycle_records,
            "is_authorized_for_service": self.is_authorized_for_service,
            "authorization_records": self.authorization_records,
            "checksum": self.compute_checksum()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceIdentity':
        """Reconstruit une identité à partir d'un dictionnaire."""
        identity = cls()
        identity.unique_id = data.get("unique_id", str(uuid.uuid4()))
        identity.identity_type = IdentityType(data.get("identity_type", "device"))
        identity.manufacturer = data.get("manufacturer", "")
        identity.model = data.get("model", "")
        identity.serial_number = data.get("serial_number", "")
        identity.fabrication_date = data.get("fabrication_date")
        identity.device_category = data.get("device_category", "")
        identity.application_domain = data.get("application_domain", "")
        identity.hardware_version = data.get("hardware_version", "")
        identity.firmware_version = data.get("firmware_version", "")
        identity.driver_version = data.get("driver_version", "")
        identity.created_at = data.get("created_at", "")
        identity.last_modified = data.get("last_modified", "")
        identity.lifecycle_records = data.get("lifecycle_records", [])
        identity.is_authorized_for_service = data.get("is_authorized_for_service", False)
        identity.authorization_records = data.get("authorization_records", [])
        return identity


@dataclass
class ProjectIdentity:
    """
    Identité d'un projet d'ingénierie.
    Contient les métadonnées et le suivi de version du projet.
    """
    
    project_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_name: str = ""
    description: str = ""
    
    # Gestion des versions
    version: str = "0.1.0"
    version_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Classification
    project_type: str = ""  # ex: drone_design, robot_arm, test_bench
    classification: str = "internal"  # internal, confidential, restricted
    
    # Dates
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    modified_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    
    # Exigences et critères d'acceptation
    requirements: List[Dict[str, Any]] = field(default_factory=list)
    acceptance_criteria: List[Dict[str, Any]] = field(default_factory=list)
    
    # Statut du projet
    status: str = "draft"  # draft, in_design, in_simulation, in_testing, 
                            # validated, in_production, archived
    
    def add_requirement(self, req_id: str, description: str, 
                       priority: str = "P1", 
                       verification_method: str = "test",
                       safety_related: bool = False):
        """
        Ajoute une exigence tracée.
        
        Chaque exigence doit être vérifiable par test, analyse ou inspection.
        """
        requirement = {
            "req_id": req_id,
            "description": description,
            "priority": priority,
            "verification_method": verification_method,
            "safety_related": safety_related,
            "status": "proposed",  # proposed, verified, validated, rejected
            "created_at": datetime.now(timezone.utc).isoformat(),
            "satisfied_by": [],  # composants qui satisfont cette exigence
            "verified_by": []    # tests qui démontrent la satisfaction
        }
        self.requirements.append(requirement)
        self.modified_at = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le projet."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "description": self.description,
            "version": self.version,
            "version_history": self.version_history,
            "project_type": self.project_type,
            "classification": self.classification,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "requirements": self.requirements,
            "acceptance_criteria": self.acceptance_criteria,
            "status": self.status
        }