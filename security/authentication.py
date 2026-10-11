# security/authentication.py
"""
Gestion de l'authentification et des autorisations.
Section 8 : authentification robuste et contrôle d'accès par rôles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
import hashlib
import secrets


class UserRole(Enum):
    """Rôles utilisateur avec différents niveaux de permission."""
    ADMINISTRATOR = "administrator"
    ENGINEER = "engineer"
    TECHNICIAN = "technician"
    OPERATOR = "operator"
    VIEWER = "viewer"
    MAINTENANCE = "maintenance"


class Permission(Enum):
    """Permissions granulaires."""
    # Lecture
    VIEW_PROJECTS = "view_projects"
    VIEW_DESIGNS = "view_designs"
    VIEW_SIMULATIONS = "view_simulations"
    VIEW_TEST_RESULTS = "view_test_results"
    VIEW_DEVICE_STATUS = "view_device_status"
    VIEW_MAINTENANCE = "view_maintenance"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    
    # Modification
    EDIT_PROJECTS = "edit_projects"
    EDIT_DESIGNS = "edit_designs"
    EDIT_SIMULATIONS = "edit_simulations"
    EDIT_TEST_SCENARIOS = "edit_test_scenarios"
    EDIT_PARAMETERS = "edit_parameters"
    
    # Exécution
    RUN_SIMULATIONS = "run_simulations"
    RUN_TESTS = "run_tests"
    CONTROL_DEVICES = "control_devices"
    EXECUTE_COMMANDS = "execute_commands"
    
    # Administration
    MANAGE_USERS = "manage_users"
    MANAGE_DEVICES = "manage_devices"
    MANAGE_SAFETY = "manage_safety"
    APPROVE_DESIGNS = "approve_designs"
    AUTHORIZE_SERVICE = "authorize_service"
    EMERGENCY_STOP = "emergency_stop"
    BYPASS_INTERLOCKS = "bypass_interlocks"
    
    # Maintenance
    PERFORM_MAINTENANCE = "perform_maintenance"
    UPDATE_FIRMWARE = "update_firmware"
    CALIBRATE_SENSORS = "calibrate_sensors"


# Matrice de permissions par rôle
ROLE_PERMISSIONS: Dict[UserRole, Set[Permission]] = {
    UserRole.ADMINISTRATOR: set(Permission),  # Toutes les permissions
    
    UserRole.ENGINEER: {
        Permission.VIEW_PROJECTS, Permission.VIEW_DESIGNS,
        Permission.VIEW_SIMULATIONS, Permission.VIEW_TEST_RESULTS,
        Permission.VIEW_DEVICE_STATUS, Permission.VIEW_MAINTENANCE,
        Permission.EDIT_PROJECTS, Permission.EDIT_DESIGNS,
        Permission.EDIT_SIMULATIONS, Permission.EDIT_TEST_SCENARIOS,
        Permission.EDIT_PARAMETERS, Permission.RUN_SIMULATIONS,
        Permission.RUN_TESTS, Permission.CONTROL_DEVICES,
        Permission.EXECUTE_COMMANDS, Permission.APPROVE_DESIGNS,
    },
    
    UserRole.TECHNICIAN: {
        Permission.VIEW_PROJECTS, Permission.VIEW_DESIGNS,
        Permission.VIEW_SIMULATIONS, Permission.VIEW_TEST_RESULTS,
        Permission.VIEW_DEVICE_STATUS, Permission.VIEW_MAINTENANCE,
        Permission.RUN_TESTS, Permission.PERFORM_MAINTENANCE,
        Permission.CALIBRATE_SENSORS, Permission.UPDATE_FIRMWARE,
    },
    
    UserRole.OPERATOR: {
        Permission.VIEW_PROJECTS, Permission.VIEW_DEVICE_STATUS,
        Permission.VIEW_TEST_RESULTS, Permission.VIEW_MAINTENANCE,
        Permission.CONTROL_DEVICES, Permission.EXECUTE_COMMANDS,
        Permission.EMERGENCY_STOP,
    },
    
    UserRole.VIEWER: {
        Permission.VIEW_PROJECTS, Permission.VIEW_DESIGNS,
        Permission.VIEW_SIMULATIONS, Permission.VIEW_TEST_RESULTS,
        Permission.VIEW_DEVICE_STATUS,
    },
    
    UserRole.MAINTENANCE: {
        Permission.VIEW_DEVICE_STATUS, Permission.VIEW_MAINTENANCE,
        Permission.PERFORM_MAINTENANCE, Permission.CALIBRATE_SENSORS,
        Permission.UPDATE_FIRMWARE, Permission.EMERGENCY_STOP,
        Permission.BYPASS_INTERLOCKS,
    },
}


@dataclass
class User:
    """Représente un utilisateur du système."""
    user_id: str
    username: str
    full_name: str = ""
    email: str = ""
    role: UserRole = UserRole.VIEWER
    
    # Authentification
    password_hash: str = ""
    salt: str = ""
    
    # Métadonnées
    is_active: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_login: Optional[str] = None
    failed_login_attempts: int = 0
    max_failed_attempts: int = 5
    
    # Restrictions
    allowed_devices: List[str] = field(default_factory=list)  # vide = tous
    restricted_actions: List[str] = field(default_factory=list)
    
    def set_password(self, password: str):
        """Définit le mot de passe hashé avec sel."""
        self.salt = secrets.token_hex(32)
        self.password_hash = self._hash_password(password, self.salt)
    
    def verify_password(self, password: str) -> bool:
        """Vérifie le mot de passe."""
        if not self.password_hash:
            return False
        return self._hash_password(password, self.salt) == self.password_hash
    
    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Hash le mot de passe avec le sel."""
        return hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8') + salt.encode('utf-8'),
            100000  # 100k itérations
        ).hex()
    
    def has_permission(self, permission: Permission) -> bool:
        """Vérifie si l'utilisateur a une permission."""
        if not self.is_active:
            return False
        return permission in ROLE_PERMISSIONS.get(self.role, set())
    
    def can_access_device(self, device_id: str) -> bool:
        """Vérifie si l'utilisateur peut accéder à un appareil."""
        if not self.is_active:
            return False
        if not self.allowed_devices:  # Vide = accès à tous
            return True
        return device_id in self.allowed_devices


class AuthenticationManager:
    """
    Gestionnaire d'authentification et d'autorisation.
    
    Toute action sur le système passe par une vérification
    d'authentification et d'autorisation.
    """
    
    def __init__(self):
        self._users: Dict[str, User] = {}
        self._active_sessions: Dict[str, Dict] = {}  # token -> session info
        self._audit_callback: Optional[callable] = None
    
    def set_audit_callback(self, callback: callable):
        """Définit le callback pour la journalisation d'audit."""
        self._audit_callback = callback
    
    def create_user(self, username: str, password: str, role: UserRole,
                   full_name: str = "", email: str = "") -> Optional[User]:
        """Crée un nouvel utilisateur."""
        if username in self._users:
            return None
        
        import uuid
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            full_name=full_name,
            email=email,
            role=role
        )
        user.set_password(password)
        
        self._users[username] = user
        return user
    
    def authenticate(self, username: str, password: str) -> Optional[str]:
        """
        Authentifie un utilisateur et retourne un token de session.
        
        Retourne None si l'authentification échoue.
        """
        user = self._users.get(username)
        
        if not user or not user.is_active:
            self._log_auth_event(username, "authentication_failed", "User not found or inactive")
            return None
        
        # Vérifier le nombre de tentatives échouées
        if user.failed_login_attempts >= user.max_failed_attempts:
            self._log_auth_event(username, "account_locked", "Too many failed attempts")
            return None
        
        if user.verify_password(password):
            # Réinitialiser les tentatives échouées
            user.failed_login_attempts = 0
            user.last_login = datetime.now(timezone.utc).isoformat()
            
            # Créer un token de session
            token = secrets.token_urlsafe(32)
            self._active_sessions[token] = {
                "user_id": user.user_id,
                "username": username,
                "role": user.role.value,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
            
            self._log_auth_event(username, "authentication_success")
            return token
        else:
            user.failed_login_attempts += 1
            self._log_auth_event(username, "authentication_failed", "Invalid password")
            return None
    
    def logout(self, token: str):
        """Déconnecte une session."""
        if token in self._active_sessions:
            session = self._active_sessions.pop(token)
            self._log_auth_event(session["username"], "logout")
    
    def get_user_from_token(self, token: str) -> Optional[User]:
        """Récupère l'utilisateur associé à un token."""
        session = self._active_sessions.get(token)
        if not session:
            return None
        
        # Mettre à jour l'activité
        session["last_activity"] = datetime.now(timezone.utc).isoformat()
        
        return self._users.get(session["username"])
    
    def check_permission(self, token: str, permission: Permission) -> bool:
        """Vérifie si l'utilisateur d'une session a une permission."""
        user = self.get_user_from_token(token)
        if not user:
            return False
        return user.has_permission(permission)
    
    def check_device_access(self, token: str, device_id: str) -> bool:
        """Vérifie si l'utilisateur peut accéder à un appareil."""
        user = self.get_user_from_token(token)
        if not user:
            return False
        return user.can_access_device(device_id)
    
    def _log_auth_event(self, username: str, event_type: str, details: str = ""):
        """Journalise un événement d'authentification."""
        if self._audit_callback:
            self._audit_callback({
                "type": "authentication",
                "event": event_type,
                "username": username,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })