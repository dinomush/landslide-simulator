"""Elevation matrix, finite differences, slope and downhill vectors."""
import numpy as np


def synthetic_dem(rows=100, cols=100, cell_size=5.0):
    """A hill above a steep escarpment, with a valley running downslope."""
    y, x = np.mgrid[:rows, :cols] * cell_size
    width, height = (cols - 1) * cell_size, (rows - 1) * cell_size
    hill = 45 * np.exp(-((x - 0.25 * width) ** 2 + (y - 0.4 * height) ** 2) / 110**2)
    scarp = 45 * (1 - np.tanh((x - 0.53 * width) / 75))
    valley = -22 * np.exp(-((y - 0.6 * height) / 45) ** 2)
    return 120 + 0.12 * (width - x) + hill + scarp + valley


def load_dem(path):
    """Read a headerless CSV of elevations in metres; reject missing values."""
    return validate_dem(np.loadtxt(path, delimiter=','))


def validate_dem(z):
    z = np.asarray(z, dtype=float)
    if z.ndim != 2 or min(z.shape) < 2:
        raise ValueError('DEM must be a 2D matrix with at least 2 rows and 2 columns')
    if z.size > 250000:
        raise ValueError('DEM exceeds 250,000 cells; downsample before use')
    if not np.isfinite(z).all():
        raise ValueError('DEM contains NaN, Infinity, or missing elevations')
    return z


def terrain_fields(z, cell_size):
    z = validate_dem(z)
    if not np.isfinite(cell_size) or cell_size <= 0:
        raise ValueError('cell_size must be positive and finite')
    # Central differences inside, one-sided differences at boundaries.
    gy, gx = np.gradient(z, cell_size, cell_size, edge_order=1)
    magnitude = np.hypot(gx, gy)
    # theta = atan(|grad Z|), D = -grad Z / |grad Z|; flats have D = 0.
    divisor = np.where(magnitude > 0, magnitude, 1)
    fields = dict(elevation=z, gradient_x=gx, gradient_y=gy,
                  slope=np.arctan(magnitude), direction_x=-gx / divisor,
                  direction_y=-gy / divisor)
    if not all(np.isfinite(a).all() for a in fields.values()):
        raise ValueError('DEM or spacing produces non-finite terrain calculations')
    return fields
