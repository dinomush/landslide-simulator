"""Spatially uniform infiltration; the same equation also accepts arrays."""
import numpy as np


def update_saturation(m, rainfall, dt_hours, config):
    """Explicit Euler in HOURS, internally substepped for stable drainage."""
    if not np.isfinite([rainfall, dt_hours]).all() or rainfall < 0 or dt_hours < 0:
        raise ValueError('rainfall and hydrology time must be finite and nonnegative')
    result = np.asarray(m, dtype=float)
    if not np.isfinite(result).all() or np.any((result < 0) | (result > 1)):
        raise ValueError('saturation must be finite and within [0, 1]')
    n = max(1, int(np.ceil(dt_hours * config.drainage_coefficient / 0.5)))
    if n > 100000:
        raise ValueError('hydrology timestep/drainage requires too many substeps')
    step = dt_hours / n
    for _ in range(n):
        # dm = k_in * (rainfall/1000) * dt_hours/H - k_d * m * dt_hours
        dm = (config.infiltration_coefficient * (rainfall / 1000) / config.soil_depth
              - config.drainage_coefficient * result) * step
        result = np.clip(result + dm, 0, 1)
    return result
