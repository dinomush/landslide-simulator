"""Infinite-slope Factor of Safety and educational risk classes."""
import numpy as np


def factor_of_safety(slope, saturation, config):
    cos = np.cos(slope)
    # u = m gamma_w H cos²(theta); stresses are kPa throughout.
    normal = (config.soil_unit_weight - saturation * config.water_unit_weight) * config.soil_depth * cos**2
    resistance = config.cohesion + normal * np.tan(np.deg2rad(config.friction_angle))
    driving = config.soil_unit_weight * config.soil_depth * np.sin(slope) * cos
    fs = resistance / np.maximum(driving, config.epsilon)
    return np.where(driving > config.epsilon, fs, config.flat_fos)


def classify_risk(fs, thresholds=(1.0, 1.2, 1.5)):
    """0 unstable, 1 high, 2 moderate, 3 relatively stable; boundaries inclusive above."""
    return np.searchsorted(thresholds, fs, side='right')
