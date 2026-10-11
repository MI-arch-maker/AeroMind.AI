# hardware/gateway.py
"""
Passerelle de communication avec les appareils.
Section 2.D : couche de communication et d'intégration matérielle.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone
import time
import threading
import queue


class ConnectionStatus(Enum):
    """Statut de connexion d'un appareil."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    TIMEOUT = "timeout"


class GatewayEventType(Enum):
    """Types d'événements de la passerelle."""
    DEVICE_CONNECTED = "device_connected"
    DEVICE_DISCONNECTED = "device_disconnected"
    DATA_RECEIVED = "data_received"
    COMMAND_SENT = "command_sent"
    ERROR_OCCURRED = "error_occurred"
    TIMEOUT_OCCURRED = "timeout_occurred"
    DEVICE_IDENTIFIED = "device_identified"


@dataclass
class GatewayEvent:
    """Événement émis par la passerelle."""
    event_type: GatewayEventType
    device_id: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    data: Any = None
    message: str = ""


class DeviceConnection(ABC):
    """
    Classe abstraite pour une connexion à un appareil.
    Chaque type de connexion implémente ses propres méthodes.
    """
    
    def __init__(self, device_id: str):
        self.device_id = device_id
        self.status = ConnectionStatus.DISCONNECTED
        self.last_activity = 0.0
        self.error_count = 0
        self._lock = threading.Lock()
    
    @abstractmethod
    def connect(self) -> bool:
        """Établit la connexion avec l'appareil."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Ferme la connexion."""
        pass
    
    @abstractmethod
    def send_command(self, command: str, params: Dict[str, Any] = None) -> bool:
        """Envoie une commande à l'appareil."""
        pass
    
    @abstractmethod
    def read_data(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Lit les données de l'appareil."""
        pass
    
    @abstractmethod
    def identify_device(self) -> Optional[Dict[str, Any]]:
        """Identifie l'appareil connecté."""
        pass
    
    def is_alive(self) -> bool:
        """Vérifie si la connexion est encore active."""
        return self.status == ConnectionStatus.CONNECTED


class DeviceGateway:
    """
    Passerelle centrale de communication avec tous les appareils.
    
    Gère la découverte, la connexion, les permissions et la journalisation.
    """
    
    def __init__(self):
        self._connections: Dict[str, DeviceConnection] = {}
        self._event_handlers: Dict[GatewayEventType, List[Callable]] = {}
        self._command_log: List[Dict[str, Any]] = []
        self._data_queue: queue.Queue = queue.Queue()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Permissions
        self._device_permissions: Dict[str, List[str]] = {}
        self._restricted_commands: List[str] = ["emergency_stop", "full_power"]
    
    def register_connection(self, connection: DeviceConnection):
        """Enregistre une connexion d'appareil."""
        self._connections[connection.device_id] = connection
    
    def register_event_handler(self, event_type: GatewayEventType, 
                              handler: Callable[[GatewayEvent], None]):
        """Enregistre un gestionnaire d'événements."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def emit_event(self, event: GatewayEvent):
        """Émet un événement à tous les gestionnaires enregistrés."""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"Erreur gestionnaire d'événement: {e}")
    
    def connect_device(self, device_id: str) -> bool:
        """Connecte un appareil enregistré."""
        if device_id not in self._connections:
            return False
        
        conn = self._connections[device_id]
        if conn.status == ConnectionStatus.CONNECTED:
            return True
        
        conn.status = ConnectionStatus.CONNECTING
        success = conn.connect()
        
        if success:
            conn.status = ConnectionStatus.CONNECTED
            self.emit_event(GatewayEvent(
                GatewayEventType.DEVICE_CONNECTED, device_id,
                message="Appareil connecté"
            ))
            # Identifier l'appareil après connexion
            identity = conn.identify_device()
            if identity:
                self.emit_event(GatewayEvent(
                    GatewayEventType.DEVICE_IDENTIFIED, device_id,
                    data=identity
                ))
        else:
            conn.status = ConnectionStatus.ERROR
            conn.error_count += 1
            self.emit_event(GatewayEvent(
                GatewayEventType.ERROR_OCCURRED, device_id,
                message=f"Échec de connexion (erreur #{conn.error_count})"
            ))
        
        return success
    
    def disconnect_device(self, device_id: str) -> bool:
        """Déconnecte un appareil."""
        if device_id not in self._connections:
            return False
        
        conn = self._connections[device_id]
        success = conn.disconnect()
        conn.status = ConnectionStatus.DISCONNECTED
        
        self.emit_event(GatewayEvent(
            GatewayEventType.DEVICE_DISCONNECTED, device_id,
            message="Appareil déconnecté"
        ))
        
        return success
    
    def send_command(self, device_id: str, command: str, 
                    params: Dict[str, Any] = None) -> bool:
        """
        Envoie une commande à un appareil avec vérification des permissions.
        """
        if device_id not in self._connections:
            return False
        
        conn = self._connections[device_id]
        
        # Vérifier les permissions
        if not self._check_permission(device_id, command):
            self._log_command(device_id, command, params, False, "Permission refusée")
            return False
        
        # Vérifier l'état de la connexion
        if conn.status != ConnectionStatus.CONNECTED:
            self._log_command(device_id, command, params, False, "Appareil non connecté")
            return False
        
        success = conn.send_command(command, params)
        self._log_command(device_id, command, params, success)
        
        if success:
            self.emit_event(GatewayEvent(
                GatewayEventType.COMMAND_SENT, device_id,
                data={"command": command, "params": params}
            ))
        
        return success
    
    def read_data(self, device_id: str, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Lit les données d'un appareil."""
        if device_id not in self._connections:
            return None
        
        conn = self._connections[device_id]
        if conn.status != ConnectionStatus.CONNECTED:
            return None
        
        data = conn.read_data(timeout)
        if data:
            self.emit_event(GatewayEvent(
                GatewayEventType.DATA_RECEIVED, device_id,
                data=data
            ))
            conn.last_activity = time.time()
        
        return data
    
    def _check_permission(self, device_id: str, command: str) -> bool:
        """Vérifie si une commande est autorisée pour un appareil."""
        # Les commandes restreintes nécessitent une autorisation explicite
        if command in self._restricted_commands:
            permissions = self._device_permissions.get(device_id, [])
            if command not in permissions:
                return False
        return True
    
    def grant_permission(self, device_id: str, command: str):
        """Accorde une permission spécifique pour un appareil."""
        if device_id not in self._device_permissions:
            self._device_permissions[device_id] = []
        if command not in self._device_permissions[device_id]:
            self._device_permissions[device_id].append(command)
    
    def revoke_permission(self, device_id: str, command: str):
        """Révoque une permission."""
        if device_id in self._device_permissions:
            if command in self._device_permissions[device_id]:
                self._device_permissions[device_id].remove(command)
    
    def _log_command(self, device_id: str, command: str, 
                    params: Dict, success: bool, error: str = ""):
        """Journalise une commande."""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "device_id": device_id,
            "command": command,
            "params": params or {},
            "success": success,
            "error": error
        }
        self._command_log.append(log_entry)
    
    def get_command_log(self, limit: int = 100) -> List[Dict]:
        """Retourne le journal des commandes."""
        return self._command_log[-limit:]
    
    def get_connected_devices(self) -> List[str]:
        """Retourne la liste des appareils connectés."""
        return [d_id for d_id, conn in self._connections.items()
                if conn.status == ConnectionStatus.CONNECTED]
    
    def start_monitoring(self, interval: float = 1.0):
        """Démarre la surveillance des connexions."""
        self._running = True
        
        def monitor_loop():
            while self._running:
                for device_id, conn in self._connections.items():
                    if conn.status == ConnectionStatus.CONNECTED:
                        # Vérifier le timeout
                        if time.time() - conn.last_activity > 30.0:
                            conn.status = ConnectionStatus.TIMEOUT
                            self.emit_event(GatewayEvent(
                                GatewayEventType.TIMEOUT_OCCURRED, device_id,
                                message="Timeout de communication détecté"
                            ))
                time.sleep(interval)
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Arrête la surveillance."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Retourne un résumé de l'état de la passerelle."""
        return {
            "total_devices": len(self._connections),
            "connected": len(self.get_connected_devices()),
            "devices": {
                d_id: {
                    "status": conn.status.value,
                    "error_count": conn.error_count,
                    "last_activity": conn.last_activity
                } for d_id, conn in self._connections.items()
            },
            "total_commands_sent": len(self._command_log)
        }