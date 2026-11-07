"""Bilinear field sampling and damped point-particle motion."""
import numpy as np


def sample(field, positions, cell_size):
    """Positions are metres: x follows columns, y follows rows (down the canvas)."""
    rows, cols = field.shape
    x = np.clip(positions[:, 0] / cell_size, 0, cols - 1)
    y = np.clip(positions[:, 1] / cell_size, 0, rows - 1)
    x0, y0 = x.astype(int), y.astype(int)
    x1, y1 = np.minimum(x0 + 1, cols - 1), np.minimum(y0 + 1, rows - 1)
    fx, fy = x - x0, y - y0
    return ((1-fx)*(1-fy)*field[y0, x0] + fx*(1-fy)*field[y0, x1]
            + (1-fx)*fy*field[y1, x0] + fx*fy*field[y1, x1])


class Particles:
    def __init__(self, terrain, config):
        self.terrain, self.config = terrain, config
        self.rng = np.random.default_rng(config.random_seed)
        self.used = np.zeros(terrain['slope'].shape, dtype=bool)
        self.positions = np.empty((0, 2))
        self.velocities = np.empty((0, 2))
        self.active = np.empty(0, dtype=bool)
        self.distance = 0.0
        self.max_speed = 0.0

    def release(self, fs):
        """At most one particle per source cell, weighted by instability, capped globally."""
        cells = np.argwhere((fs < 1.0) & ~self.used)
        count = min(len(cells), self.config.particle_count_limit - len(self.positions))
        if count <= 0:
            return
        weights = 1 - fs[cells[:, 0], cells[:, 1]]
        chosen = cells[self.rng.choice(len(cells), count, replace=False, p=weights/weights.sum())]
        self.used[chosen[:, 0], chosen[:, 1]] = True
        self.positions = np.vstack((self.positions, chosen[:, ::-1] * self.config.cell_size))
        self.velocities = np.vstack((self.velocities, np.zeros((count, 2))))
        self.active = np.r_[self.active, np.ones(count, dtype=bool)]

    def advance(self, fs, dt):
        c, terrain = self.config, self.terrain
        # Small substeps resolve terrain changes and keep explicit damping stable.
        step_limit = min(c.max_motion_substep, 0.5 / max(c.damping, c.epsilon))
        remaining = dt
        while remaining > c.epsilon:
            ids = np.flatnonzero(self.active)
            if not len(ids):
                return
            p, v = self.positions[ids], self.velocities[ids]
            speed = np.linalg.norm(v, axis=1).max(initial=0)
            h = min(remaining, step_limit, 0.25*c.cell_size/max(speed, 1))
            gx = sample(terrain['gradient_x'], p, c.cell_size)
            gy = sample(terrain['gradient_y'], p, c.cell_size)
            gradient = np.column_stack((gx, gy))
            magnitude = np.linalg.norm(gradient, axis=1)
            direction = -gradient / np.maximum(magnitude[:, None], c.epsilon)
            drive = c.gravity * np.sin(np.arctan(magnitude)) * np.maximum(0, 1-sample(fs, p, c.cell_size))
            # A = g sin(theta) max(0,1-FS) D - damping V
            acceleration = drive[:, None] * direction - c.damping * v
            # Semi-implicit Euler: V_new=V+A dt; P_new=P+V_new dt.
            new_v = v + acceleration * h
            candidate = p + new_v * h
            upper = (np.array(terrain['slope'].shape[::-1])-1)*c.cell_size
            outside = np.any((candidate < 0) | (candidate > upper), axis=1)
            candidate = np.clip(candidate, 0, upper)
            # Dissipate momentum at uphill steps; this simple model cannot climb valley walls.
            uphill = sample(terrain['elevation'], candidate, c.cell_size) > sample(terrain['elevation'], p, c.cell_size) + c.epsilon
            candidate[uphill] = p[uphill]
            velocity = np.linalg.norm(new_v, axis=1)
            # Newly unstable cells may have tiny drive that grows with later rain.
            # Keep those particles active; settle only when local drive vanishes.
            stopped = outside | uphill | ((velocity < c.stop_speed) & (drive <= c.epsilon))
            self.max_speed = max(self.max_speed, float(velocity.max(initial=0)))
            self.distance += float(np.linalg.norm(candidate-p, axis=1).sum())
            new_v[stopped] = 0
            self.positions[ids], self.velocities[ids] = candidate, new_v
            self.active[ids[stopped]] = False
            remaining -= h

    def snapshot(self):
        """Compact rows: x, y, vx, vy, active. Row index is the persistent particle ID."""
        return np.column_stack((self.positions, self.velocities, self.active)).round(5).tolist()
