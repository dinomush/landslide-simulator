"""Central parameters. SI units, except rainfall (mm/h) and hydrology (hours)."""
from dataclasses import asdict, dataclass
import math


@dataclass
class Config:
    cell_size: float = 5.0
    rainfall_mm_per_hour: float = 80.0
    infiltration_coefficient: float = 0.9
    drainage_coefficient: float = 0.01  # per hour
    initial_saturation: float = 0.05
    rainfall_duration_hours: float = 24.0
    cohesion: float = 10.0  # kPa = kN/m²
    friction_angle: float = 30.0  # degrees
    soil_depth: float = 2.0  # m
    soil_unit_weight: float = 18.0  # kN/m³
    water_unit_weight: float = 9.81  # kN/m³
    risk_thresholds: tuple = (1.0, 1.2, 1.5)
    simulation_dt: float = 0.2  # seconds
    simulation_duration: float = 60.0  # seconds
    frame_interval: float = 1.0  # seconds; initial/final always included
    particle_count_limit: int = 600
    damping: float = 0.6  # per second
    random_seed: int = 42
    gravity: float = 9.81  # m/s²
    stop_speed: float = 0.02  # m/s
    epsilon: float = 1e-10
    flat_fos: float = 1000.0
    max_motion_substep: float = 0.05

    def validate(self):
        """Reject non-finite, nonphysical, or impractically large inputs."""
        for key, value in asdict(self).items():
            if key == 'risk_thresholds':
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'{key} must be a finite number')
            if value < 0:
                raise ValueError(f'{key} cannot be negative')
        for key in ('cell_size', 'soil_depth', 'soil_unit_weight', 'simulation_dt',
                    'simulation_duration', 'frame_interval', 'gravity', 'epsilon',
                    'flat_fos', 'max_motion_substep'):
            if getattr(self, key) <= 0:
                raise ValueError(f'{key} must be positive')
        if not 0 <= self.friction_angle < 90:
            raise ValueError('friction_angle must be in [0, 90) degrees')
        if not 0 <= self.initial_saturation <= 1 or not 0 <= self.infiltration_coefficient <= 1:
            raise ValueError('saturation and infiltration_coefficient must be in [0, 1]')
        if self.water_unit_weight > self.soil_unit_weight:
            raise ValueError('water_unit_weight must not exceed soil_unit_weight')
        t = self.risk_thresholds
        if len(t) != 3 or not all(math.isfinite(x) for x in t) or not 0 < t[0] < t[1] < t[2]:
            raise ValueError('risk_thresholds must contain three increasing positive numbers')
        if any(type(getattr(self, k)) is not int for k in ('particle_count_limit', 'random_seed')):
            raise ValueError('particle_count_limit and random_seed must be integers')
        if self.particle_count_limit > 2000:
            raise ValueError('particle_count_limit must be <= 2000 for this lightweight MVP')
        effective_dt = min(self.simulation_dt, self.max_motion_substep, 0.5 / max(self.damping, 1e-10))
        if self.simulation_duration / effective_dt > 200000:
            raise ValueError('requested duration/dt requires too many integration steps')
        if self.simulation_duration / max(self.frame_interval, self.simulation_dt) > 5000:
            raise ValueError('too many frames; increase frame_interval')
        return self
