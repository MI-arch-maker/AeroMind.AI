# security/__init__.py
"""
AeroMind AI — Couche sécurité informatique
Authentification, rôles et journal d'audit.
"""

from .authentication import AuthenticationManager, User, UserRole, Permission
from .audit import AuditLogger, AuditEvent, AuditEventType