# hardware/profiles.py
"""
Profils matériels normalisés.
Section 2.C : chaque appareil est décrit par un profil standardisé.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import json


class DeviceCategory(Enum):
    """Catégories d'appareils supportés."""
    MICROCONTROLLER = "microcontroller"
    SINGLE_BOARD_COMPUTER = "single_board_computer"
    SENSOR_MODULE = "sensor_module"
    ACTUATOR_MODULE = "actuator_module"
    MOTOR_CONTROLLER = "motor_controller"
    DATA_ACQUISITION = "data_acquisition"
    POWER_SUPPLY = "power_supply"
    TEST_INSTRUMENT = "test_instrument"
    ROBOT_CONTROLLER = "robot_controller"
    PLC = "plc"
    CUSTOM = "custom"


class InterfaceType(Enum):
    """Types d'interfaces physiques et logicielles."""
    USB = "usb"
    ETHERNET = "ethernet"
    SERIAL = "serial"          # UART, RS-232, RS-485
    CAN = "can"
    I2C = "i2c"
    SPI = "spi"
    GPIO = "gpio"
    PWM = "pwm"
    ANALOG_INPUT = "analog_input"
    ANALOG_OUTPUT = "analog_output"
    DIGITAL_INPUT = "digital_input"
    DIGITAL_OUTPUT = "digital_output"
    BLUETOOTH = "bluetooth"
    WIFI = "wifi"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    OPC_UA = "opc_ua"
    SCPI = "scpi"
    ROS2 = "ros2"


class ProtocolType(Enum):
    """Protocoles de communication supportés."""
    JSON_OVER_SERIAL = "json_serial"
    BINARY_SERIAL = "binary_serial"
    MODBUS_TCP = "modbus_tcp"
    MODBUS_RTU = "modbus_rtu"
    CAN_OPEN = "can_open"
    RAW_CAN = "raw_can"
    MQTT = "mqtt"
    WEBSOCKET = "websocket"
    RAW_TCP = "raw_tcp"
    UDP = "udp"
    SCPI = "scpi"
    I2C_RAW = "i2c_raw"
    SPI_RAW = "spi_raw"
    GPIO_DIRECT = "gpio_direct"


@dataclass
class ElectricalSpecs:
    """Spécifications électriques d'un composant."""
    nominal_voltage: float = 0.0  # V
    voltage_tolerance: float = 0.1  # ±10% par défaut
    max_current: float = 0.0  # A
    max_power: float = 0.0  # W
    logic_level: float = 3.3  # V (3.3V ou 5V)
    thermal_limit: float = 70.0  # °C
    
    def is_voltage_compatible(self, supply_voltage: float) -> bool:
        """Vérifie si une tension d'alimentation est compatible."""
        min_v = self.nominal_voltage * (1 - self.voltage_tolerance)
        max_v = self.nominal_voltage * (1 + self.voltage_tolerance)
        return min_v <= supply_voltage <= max_v


@dataclass
class InterfaceProfile:
    """Profil d'une interface de communication."""
    interface_type: InterfaceType
    protocol: ProtocolType
    max_data_rate: float = 0.0  # bauds ou bits/s
    max_latency: float = 0.0  # ms
    
    # Détails spécifiques
    pin_count: int = 0
    connector_type: str = ""
    is_bidirectional: bool = True
    supports_hot_plug: bool = False


@dataclass
class SensorProfile:
    """Profil d'un capteur."""
    sensor_id: str
    sensor_type: str  # temperature, pressure, position, etc.
    measurement_range_min: float = 0.0
    measurement_range_max: float = 0.0
    unit: str = ""
    accuracy: float = 0.0  # ±valeur
    resolution: float = 0.0
    sampling_rate_max: float = 0.0  # Hz
    response_time: float = 0.0  # ms
    
    # Calibration
    calibration_date: Optional[str] = None
    calibration_due: Optional[str] = None
    calibration_offset: float = 0.0
    calibration_scale: float = 1.0
    
    # État de santé
    is_functional: bool = True
    last_reading: Optional[float] = None
    last_reading_time: Optional[str] = None


@dataclass
class ActuatorProfile:
    """Profil d'un actionneur."""
    actuator_id: str
    actuator_type: str  # motor, servo, relay, valve, etc.
    
    # Limites mécaniques
    max_stroke: float = 0.0  # mm ou degrés
    max_speed: float = 0.0
    max_force: float = 0.0  # N
    max_torque: float = 0.0  # N·m
    
    # Limites électriques
    nominal_voltage: float = 0.0
    stall_current: float = 0.0
    nominal_current: float = 0.0
    
    # Caractéristiques dynamiques
    response_time: float = 0.0  # ms
    settling_time: float = 0.0  # ms
    
    # État de repos (position sûr en cas de panne)
    rest_position: float = 0.0
    failsafe_position: float = 0.0
    
    # État
    is_enabled: bool = False
    current_position: float = 0.0


@dataclass
class SafetySpecs:
    """Spécifications de sécurité d'un appareil."""
    safe_state_on_power_off: str = "deenergized"
    safe_state_on_fault: str = "deenergized"
    safe_state_on_comm_loss: str = "deenergized"
    
    has_emergency_stop_input: bool = False
    has_interlock_input: bool = False
    has_overcurrent_protection: bool = False
    has_thermal_protection: bool = False
    
    # Normes de sécurité applicables
    applicable_standards: List[str] = field(default_factory=list)
    
    # Niveau de risque
    risk_level: str = "low"  # low, medium, high, critical
    
    # Procédures
    startup_procedure: List[str] = field(default_factory=list)
    shutdown_procedure: List[str] = field(default_factory=list)
    emergency_procedure: List[str] = field(default_factory=list)


class HardwareProfile:
    """
    Profil matériel normalisé complet d'un appareil.
    
    Implémente la section 2.C du cahier des charges :
    tous les champs minimum requis pour décrire un appareil.
    """
    
    def __init__(self):
        # Identification
        self.profile_id: str = ""
        self.manufacturer: str = ""
        self.model: str = ""
        self.serial_number: str = ""
        
        # Classification
        self.category: DeviceCategory = DeviceCategory.CUSTOM
        self.description: str = ""
        
        # Architecture
        self.processor: str = ""
        self.clock_frequency: float = 0.0  # Hz
        self.memory_flash: int = 0  # bytes
        self.memory_ram: int = 0  # bytes
        self.operating_system: str = ""  # ou "bare_metal"
        
        # Version
        self.hardware_version: str = ""
        self.firmware_version: str = ""
        self.driver_version: str = ""
        self.firmware_checksum: str = ""
        
        # Spécifications électriques
        self.electrical: ElectricalSpecs = ElectricalSpecs()
        
        # Interfaces
        self.interfaces: List[InterfaceProfile] = field(default_factory=list)
        
        # Capteurs intégrés
        self.sensors: List[SensorProfile] = field(default_factory=list)
        
        # Actionneurs intégrés
        self.actuators: List[ActuatorProfile] = field(default_factory=list)
        
        # Sécurité
        self.safety: SafetySpecs = SafetySpecs()
        
        # Conditions d'utilisation
        self.operating_temperature_min: float = -40.0
        self.operating_temperature_max: float = 85.0
        self.operating_humidity_max: float = 95.0  # %RH
        self.storage_temperature_min: float = -40.0
        self.storage_temperature_max: float = 85.0
        
        # Restrictions fabricant
        self.manufacturer_restrictions: List[str] = field(default_factory=list)
        
        # Procédures
        self.calibration_procedure: List[str] = field(default_factory=list)
        self.diagnostic_procedure: List[str] = field(default_factory=list)
        self.error_codes: Dict[int, str] = field(default_factory=dict)
        
        # Métadonnées
        self.created_at: str = datetime.now(timezone.utc).isoformat()
        self.last_updated: str = datetime.now(timezone.utc).isoformat()
        self.verification_status: str = "unverified"  # unverified, verified, validated
    
    def add_interface(self, interface_type: InterfaceType, 
                     protocol: ProtocolType, **kwargs):
        """Ajoute une interface au profil."""
        iface = InterfaceProfile(
            interface_type=interface_type,
            protocol=protocol,
            **kwargs
        )
        self.interfaces.append(iface)
    
    def add_sensor(self, sensor: SensorProfile):
        """Ajoute un capteur au profil."""
        self.sensors.append(sensor)
    
    def add_actuator(self, actuator: ActuatorProfile):
        """Ajoute un actionneur au profil."""
        self.actuators.append(actuator)
    
    def get_interfaces_by_type(self, iface_type: InterfaceType) -> List[InterfaceProfile]:
        """Retourne toutes les interfaces d'un type donné."""
        return [i for i in self.interfaces if i.interface_type == iface_type]
    
    def get_sensors_by_type(self, sensor_type: str) -> List[SensorProfile]:
        """Retourne tous les capteurs d'un type donné."""
        return [s for s in self.sensors if s.sensor_type == sensor_type]
    
    def supports_protocol(self, protocol: ProtocolType) -> bool:
        """Vérifie si l'appareil supporte un protocole."""
        return any(i.protocol == protocol for i in self.interfaces)
    
    def to_dict(self) -> Dict[str, Any]:
        """Sérialise le profil complet."""
        return {
            "profile_id": self.profile_id,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "serial_number": self.serial_number,
            "category": self.category.value,
            "description": self.description,
            "processor": self.processor,
            "clock_frequency": self.clock_frequency,
            "memory_flash": self.memory_flash,
            "memory_ram": self.memory_ram,
            "operating_system": self.operating_system,
            "hardware_version": self.hardware_version,
            "firmware_version": self.firmware_version,
            "driver_version": self.driver_version,
            "firmware_checksum": self.firmware_checksum,
            "electrical": {
                "nominal_voltage": self.electrical.nominal_voltage,
                "voltage_tolerance": self.electrical.voltage_tolerance,
                "max_current": self.electrical.max_current,
                "max_power": self.electrical.max_power,
                "logic_level": self.electrical.logic_level,
                "thermal_limit": self.electrical.thermal_limit
            },
            "interfaces": [
                {
                    "type": i.interface_type.value,
                    "protocol": i.protocol.value,
                    "max_data_rate": i.max_data_rate,
                    "max_latency": i.max_latency
                } for i in self.interfaces
            ],
            "sensors": [
                {
                    "id": s.sensor_id,
                    "type": s.sensor_type,
                    "range_min": s.measurement_range_min,
                    "range_max": s.measurement_range_max,
                    "unit": s.unit,
                    "accuracy": s.accuracy,
                    "is_functional": s.is_functional
                } for s in self.sensors
            ],
            "actuators": [
                {
                    "id": a.actuator_id,
                    "type": a.actuator_type,
                    "max_stroke": a.max_stroke,
                    "max_speed": a.max_speed,
                    "nominal_voltage": a.nominal_voltage,
                    "rest_position": a.rest_position,
                    "failsafe_position": a.failsafe_position
                } for a in self.actuators
            ],
            "safety": {
                "safe_state_on_power_off": self.safety.safe_state_on_power_off,
                "safe_state_on_fault": self.safety.safe_state_on_fault,
                "safe_state_on_comm_loss": self.safety.safe_state_on_comm_loss,
                "has_emergency_stop": self.safety.has_emergency_stop_input,
                "has_interlock": self.safety.has_interlock_input,
                "risk_level": self.safety.risk_level
            },
            "operating_conditions": {
                "temp_min": self.operating_temperature_min,
                "temp_max": self.operating_temperature_max,
                "humidity_max": self.operating_humidity_max
            },
            "verification_status": self.verification_status,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HardwareProfile':
        """Reconstruit un profil à partir d'un dictionnaire."""
        profile = cls()
        profile.profile_id = data.get("profile_id", "")
        profile.manufacturer = data.get("manufacturer", "")
        profile.model = data.get("model", "")
        profile.serial_number = data.get("serial_number", "")
        profile.category = DeviceCategory(data.get("category", "custom"))
        profile.description = data.get("description", "")
        profile.processor = data.get("processor", "")
        profile.clock_frequency = data.get("clock_frequency", 0)
        profile.memory_flash = data.get("memory_flash", 0)
        profile.memory_ram = data.get("memory_ram", 0)
        profile.operating_system = data.get("operating_system", "")
        profile.hardware_version = data.get("hardware_version", "")
        profile.firmware_version = data.get("firmware_version", "")
        profile.driver_version = data.get("driver_version", "")
        profile.firmware_checksum = data.get("firmware_checksum", "")
        profile.verification_status = data.get("verification_status", "unverified")
        
        # Reconstruction électrique
        elec = data.get("electrical", {})
        profile.electrical = ElectricalSpecs(
            nominal_voltage=elec.get("nominal_voltage", 0),
            voltage_tolerance=elec.get("voltage_tolerance", 0.1),
            max_current=elec.get("max_current", 0),
            max_power=elec.get("max_power", 0),
            logic_level=elec.get("logic_level", 3.3),
            thermal_limit=elec.get("thermal_limit", 70)
        )
        
        # Reconstruction interfaces
        for iface_data in data.get("interfaces", []):
            profile.add_interface(
                InterfaceType(iface_data.get("type", "usb")),
                ProtocolType(iface_data.get("protocol", "json_serial")),
                max_data_rate=iface_data.get("max_data_rate", 0),
                max_latency=iface_data.get("max_latency", 0)
            )
        
        return profile


# === Profils prédéfinis pour composants courants ===

def create_esp32_profile() -> HardwareProfile:
    """Crée un profil pour ESP32."""
    profile = HardwareProfile()
    profile.profile_id = "esp32_devkit_v1"
    profile.manufacturer = "Espressif"
    profile.model = "ESP32-DevKitC"
    profile.category = DeviceCategory.MICROCONTROLLER
    profile.description = "Microcontrôleur dual-core avec WiFi et Bluetooth"
    profile.processor = "Xtensa LX6 dual-core"
    profile.clock_frequency = 240_000_000  # 240 MHz
    profile.memory_flash = 4_194_304  # 4 MB
    profile.memory_ram = 520_192  # 520 KB
    profile.operating_system = "bare_metal"
    profile.hardware_version = "v1"
    profile.firmware_version = "1.0.0"
    
    # Électrique
    profile.electrical = ElectricalSpecs(
        nominal_voltage=3.3,
        voltage_tolerance=0.05,
        max_current=0.5,
        max_power=1.65,
        logic_level=3.3,
        thermal_limit=85.0
    )
    
    # Interfaces
    profile.add_interface(InterfaceType.USB, ProtocolType.JSON_OVER_SERIAL, 
                         max_data_rate=921600, max_latency=10)
    profile.add_interface(InterfaceType.WIFI, ProtocolType.WEBSOCKET, 
                         max_data_rate=1000000, max_latency=50)
    profile.add_interface(InterfaceType.GPIO, ProtocolType.GPIO_DIRECT, 
                         max_data_rate=0, max_latency=1)
    profile.add_interface(InterfaceType.I2C, ProtocolType.I2C_RAW, 
                         max_data_rate=400000, max_latency=5)
    profile.add_interface(InterfaceType.SPI, ProtocolType.SPI_RAW, 
                         max_data_rate=80000000, max_latency=2)
    
    # Sécurité
    profile.safety = SafetySpecs(
        safe_state_on_power_off="all_outputs_low",
        safe_state_on_fault="all_outputs_low",
        safe_state_on_comm_loss="watchdog_reset",
        has_overcurrent_protection=True,
        has_thermal_protection=True,
        risk_level="low"
    )
    
    return profile


def create_stm32_profile() -> HardwareProfile:
    """Crée un profil pour STM32."""
    profile = HardwareProfile()
    profile.profile_id = "stm32f4_discovery"
    profile.manufacturer = "STMicroelectronics"
    profile.model = "STM32F407G-DISC1"
    profile.category = DeviceCategory.MICROCONTROLLER
    profile.processor = "ARM Cortex-M4"
    profile.clock_frequency = 168_000_000
    profile.memory_flash = 1_048_576  # 1 MB
    profile.memory_ram = 196_608  # 192 KB
    profile.operating_system = "bare_metal"
    
    profile.electrical = ElectricalSpecs(
        nominal_voltage=3.3,
        voltage_tolerance=0.05,
        max_current=0.25,
        max_power=0.825,
        logic_level=3.3,
        thermal_limit=85.0
    )
    
    profile.add_interface(InterfaceType.USB, ProtocolType.JSON_OVER_SERIAL,
                         max_data_rate=2000000, max_latency=5)
    profile.add_interface(InterfaceType.CAN, ProtocolType.CAN_OPEN,
                         max_data_rate=1000000, max_latency=1)
    
    return profile


def create_test_bench_profile() -> HardwareProfile:
    """Crée un profil pour un banc d'essai générique."""
    profile = HardwareProfile()
    profile.profile_id = "test_bench_v1"
    profile.manufacturer = "AeroMind Lab"
    profile.model = "Banc d'essai modulaire"
    profile.category = DeviceCategory.TEST_INSTRUMENT
    
    profile.electrical = ElectricalSpecs(
        nominal_voltage=12.0,
        voltage_tolerance=0.1,
        max_current=10.0,
        max_power=120.0,
        logic_level=3.3,
        thermal_limit=60.0
    )
    
    # Capteurs du banc
    profile.add_sensor(SensorProfile(
        sensor_id="temp_motor",
        sensor_type="temperature",
        measurement_range_min=-40.0,
        measurement_range_max=125.0,
        unit="°C",
        accuracy=0.5,
        resolution=0.1,
        sampling_rate_max=10.0
    ))
    profile.add_sensor(SensorProfile(
        sensor_id="current_motor",
        sensor_type="current",
        measurement_range_min=0.0,
        measurement_range_max=20.0,
        unit="A",
        accuracy=0.1,
        resolution=0.01,
        sampling_rate_max=1000.0
    ))
    
    # Actionneurs du banc
    profile.add_actuator(ActuatorProfile(
        actuator_id="motor_main",
        actuator_type="brushed_dc_motor",
        max_speed=3000.0,
        max_torque=5.0,
        nominal_voltage=12.0,
        stall_current=15.0,
        nominal_current=3.0,
        rest_position=0.0,
        failsafe_position=0.0
    ))
    
    return profile