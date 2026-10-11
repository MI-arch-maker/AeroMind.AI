# control/pid_controller.py
"""
Contrôleur PID pour la régulation.
Section 3.E : boucles de régulation adaptées au matériel.
"""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class PIDGains:
    """Gains du contrôleur PID."""
    kp: float = 1.0  # Gain proportionnel
    ki: float = 0.0  # Gain intégral
    kd: float = 0.0  # Gain dérivé


@dataclass
class PIDLimits:
    """Limites du contrôleur PID."""
    output_min: float = -100.0
    output_max: float = 100.0
    integral_min: float = -1000.0
    integral_max: float = 1000.0
    rate_limit: float = 0.0  # Limite de vitesse de variation (0 = pas de limite)


class PIDController:
    """
    Contrôleur PID avec anti-windup et limitation de vitesse.
    
    Utilisé pour les boucles de régulation nécessitant un contrôle
    précis : température, vitesse, position, pression, etc.
    """
    
    def __init__(self, gains: PIDGains = None, limits: PIDLimits = None,
                 name: str = "pid"):
        self.name = name
        self.gains = gains or PIDGains()
        self.limits = limits or PIDLimits()
        
        # État interne
        self._integral: float = 0.0
        self._previous_error: float = 0.0
        self._previous_output: float = 0.0
        self._last_time: Optional[float] = None
        
        # Statistiques
        self._sample_count: int = 0
        self._saturation_count: int = 0
    
    def reset(self):
        """Remet le contrôleur à zéro."""
        self._integral = 0.0
        self._previous_error = 0.0
        self._previous_output = 0.0
        self._last_time = None
        self._sample_count = 0
        self._saturation_count = 0
    
    def compute(self, setpoint: float, measured_value: float, 
                current_time: Optional[float] = None) -> float:
        """
        Calcule la sortie du PID.
        
        Args:
            setpoint: Valeur consigne
            measured_value: Valeur mesurée
            current_time: Temps actuel (utilise time.time() si None)
        
        Returns:
            Sortie du contrôleur (dans les limites)
        """
        if current_time is None:
            current_time = time.time()
        
        # Calcul de dt
        if self._last_time is None:
            dt = 0.001  # Premier échantillon, dt par défaut
        else:
            dt = max(current_time - self._last_time, 1e-6)
        
        # Calcul de l'erreur
        error = setpoint - measured_value
        
        # Terme proportionnel
        p_term = self.gains.kp * error
        
        # Terme intégral avec anti-windup
        self._integral += error * dt
        self._integral = max(self.limits.integral_min, 
                           min(self.limits.integral_max, self._integral))
        i_term = self.gains.ki * self._integral
        
        # Terme dérivé
        if dt > 0:
            derivative = (error - self._previous_error) / dt
        else:
            derivative = 0.0
        d_term = self.gains.kd * derivative
        
        # Sortie brute
        output = p_term + i_term + d_term
        
        # Limitation de vitesse de variation
        if self.limits.rate_limit > 0 and self._last_time is not None:
            max_change = self.limits.rate_limit * dt
            output = max(self._previous_output - max_change,
                        min(self._previous_output + max_change, output))
        
        # Limitation de la sortie
        if output > self.limits.output_max:
            output = self.limits.output_max
            self._saturation_count += 1
            # Anti-windup : geler l'intégrale
            self._integral -= error * dt
        elif output < self.limits.output_min:
            output = self.limits.output_min
            self._saturation_count += 1
            # Anti-windup : geler l'intégrale
            self._integral -= error * dt
        
        # Mise à jour de l'état
        self._previous_error = error
        self._previous_output = output
        self._last_time = current_time
        self._sample_count += 1
        
        return output
    
    def get_status(self) -> Dict:
        """Retourne le statut du contrôleur."""
        return {
            "name": self.name,
            "kp": self.gains.kp,
            "ki": self.gains.ki,
            "kd": self.gains.kd,
            "integral": self._integral,
            "last_output": self._previous_output,
            "sample_count": self._sample_count,
            "saturation_count": self._saturation_count,
            "saturation_rate": (
                self._saturation_count / max(1, self._sample_count)
            )
        }