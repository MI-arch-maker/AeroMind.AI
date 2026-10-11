# simulation/physics_models.py
"""
Modèles physiques pour la simulation.
Section 2.B : calculs fondés sur des modèles validés.
"""

import math
from dataclasses import dataclass
from typing import Dict


class PhysicsModel:
    """Classe de base pour tous les modèles physiques."""
    
    @staticmethod
    def ohms_law(voltage: float = None, current: float = None, 
                resistance: float = None) -> Dict[str, float]:
        """Loi d'Ohm : V = R * I"""
        if voltage is not None and current is not None:
            return {"resistance": voltage / current if current != 0 else float('inf')}
        elif voltage is not None and resistance is not None:
            return {"current": voltage / resistance if resistance != 0 else 0}
        elif current is not None and resistance is not None:
            return {"voltage": current * resistance}
        return {}
    
    @staticmethod
    def power_dc(voltage: float, current: float) -> float:
        """Puissance en courant continu : P = V * I"""
        return voltage * current
    
    @staticmethod
    def thermal_resistance(heat_flow: float, temp_difference: float) -> float:
        """Résistance thermique : Rth = ΔT / Q"""
        if heat_flow == 0:
            return float('inf')
        return temp_difference / heat_flow


class ThermalModel:
    """
    Modèle thermique simple pour composants électroniques.
    
    Modèle RC thermique : température augmente avec la puissance dissipée
    et diminue avec le refroidissement.
    """
    
    def __init__(self, thermal_mass: float = 0.1,  # J/K
                 thermal_resistance: float = 10.0,  # K/W
                 ambient_temperature: float = 25.0):  # °C
        self.thermal_mass = thermal_mass
        self.thermal_resistance = thermal_resistance
        self.ambient_temperature = ambient_temperature
        self.temperature = ambient_temperature
    
    def update(self, dt: float, power_dissipated: float) -> float:
        """
        Met à jour la température.
        
        Args:
            dt: Pas de temps (s)
            power_dissipated: Puissance dissipée (W)
        
        Returns:
            Nouvelle température (°C)
        """
        # dT/dt = (P - (T - T_ambient) / Rth) / C
        heat_generated = power_dissipated
        heat_dissipated = (self.temperature - self.ambient_temperature) / self.thermal_resistance
        
        dTdt = (heat_generated - heat_dissipated) / self.thermal_mass
        self.temperature += dTdt * dt
        
        return self.temperature


class ElectricalModel:
    """
    Modèle électrique pour circuits simples.
    """
    
    def __init__(self, supply_voltage: float = 12.0,
                 internal_resistance: float = 0.1):
        self.supply_voltage = supply_voltage
        self.internal_resistance = internal_resistance
    
    def calculate_motor_current(self, back_emf: float, 
                               winding_resistance: float) -> float:
        """
        Calcule le courant d'un moteur DC.
        I = (V - E) / R
        """
        voltage_across = self.supply_voltage - back_emf
        if winding_resistance == 0:
            return 0.0
        return voltage_across / winding_resistance
    
    def calculate_back_emf(self, speed_rpm: float, 
                          emf_constant: float) -> float:
        """Calcule la force contre-électromotrice."""
        return speed_rpm * emf_constant


class MechanicalModel:
    """
    Modèle mécanique pour systèmes en rotation.
    """
    
    def __init__(self, moment_of_inertia: float = 0.01,  # kg·m²
                 damping_coefficient: float = 0.01):  # N·m·s/rad
        self.moment_of_inertia = moment_of_inertia
        self.damping_coefficient = damping_coefficient
        self.angular_velocity = 0.0  # rad/s
        self.angle = 0.0  # rad
    
    def update(self, dt: float, applied_torque: float,
              load_torque: float = 0.0) -> Dict[str, float]:
        """
        Met à jour l'état mécanique.
        
        J * dω/dt = T_applied - T_load - b * ω
        """
        net_torque = (applied_torque - load_torque - 
                     self.damping_coefficient * self.angular_velocity)
        
        angular_acceleration = net_torque / self.moment_of_inertia
        self.angular_velocity += angular_acceleration * dt
        self.angle += self.angular_velocity * dt
        
        return {
            "angular_velocity": self.angular_velocity,
            "angle": self.angle,
            "angular_acceleration": angular_acceleration
        }