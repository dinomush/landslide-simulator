"""Couple hydrology, stability, particle release and replay frames."""
from dataclasses import asdict
import numpy as np
from .terrain import terrain_fields
from .hydrology import update_saturation
from .stability import factor_of_safety, classify_risk
from .dynamics import Particles
from .utils import write_json


def simulate(z, config):
    c = config.validate()
    terrain = terrain_fields(z, c.cell_size)
    particles = Particles(terrain, c)
    m, time = c.initial_saturation, 0.0
    fs = factor_of_safety(terrain['slope'], m, c)
    initial_min = float(fs.min())
    initial_unstable = int((fs < 1).sum())
    particles.release(fs)
    frames = []

    def save_frame():
        frames.append(dict(time=round(time, 8), rainfall_time_hours=time/c.simulation_duration*c.rainfall_duration_hours,
                           saturation=float(m), minimum_fos=float(fs.min()), unstable_cells=int((fs < 1).sum()),
                           moving_particles=int(particles.active.sum()), particles=particles.snapshot()))

    save_frame()
    next_frame = c.frame_interval
    while time < c.simulation_duration - c.epsilon:
        dt = min(c.simulation_dt, c.simulation_duration-time)
        hours = dt / c.simulation_duration * c.rainfall_duration_hours
        m = float(update_saturation(m, c.rainfall_mm_per_hour, hours, c))
        fs = factor_of_safety(terrain['slope'], m, c)
        particles.release(fs)
        particles.advance(fs, dt)
        time += dt
        if time + c.epsilon >= next_frame or time + c.epsilon >= c.simulation_duration:
            save_frame()
            next_frame = time + c.frame_interval
    risk = classify_risk(fs, c.risk_thresholds)
    summary = dict(dem_rows=z.shape[0], dem_cols=z.shape[1], minimum_elevation_m=float(z.min()),
                   maximum_elevation_m=float(z.max()), mean_slope_degrees=float(np.rad2deg(terrain['slope']).mean()),
                   maximum_slope_degrees=float(np.rad2deg(terrain['slope']).max()), rainfall_mm_per_hour=c.rainfall_mm_per_hour,
                   rainfall_duration_hours=c.rainfall_duration_hours, simulation_duration_seconds=c.simulation_duration,
                   initial_saturation=c.initial_saturation, final_saturation=m, initial_minimum_fos=initial_min,
                   minimum_fos=float(fs.min()), average_fos=float(fs.mean()), initial_unstable_cells=initial_unstable,
                   unstable_cells=int((fs < 1).sum()), unstable_area_m2=int((fs < 1).sum())*c.cell_size**2,
                   generated_particles=len(particles.positions), maximum_particle_velocity_m_s=particles.max_speed,
                   total_particle_distance_m=particles.distance, frames=len(frames))
    data = dict(metadata=dict(version=1, description='Educational model; not a landslide warning system',
                              coordinates='x: columns, y: rows; metres; origin at top left', slope_units='radians',
                              particle_columns=['x', 'y', 'vx', 'vy', 'active'],
                              hydrology_clock='Rainfall hours mapped linearly onto motion seconds; illustrative time compression'),
                terrain=dict(rows=z.shape[0], cols=z.shape[1], cell_size=c.cell_size,
                             elevation=z.round(6).tolist(), slope=terrain['slope'].tolist(),
                             direction_x=terrain['direction_x'].round(6).tolist(), direction_y=terrain['direction_y'].round(6).tolist(),
                             risk=risk.tolist()), parameters=asdict(c), frames=frames, summary=summary)
    return data, summary, dict(factor_of_safety=fs.tolist(), risk=risk.tolist(), thresholds=list(c.risk_thresholds),
                               labels=['unstable', 'high risk', 'moderate risk', 'relatively stable'], saturation=m)


def export(result, output):
    from pathlib import Path
    for name, data in zip(('simulation', 'summary', 'risk_map'), result):
        write_json(Path(output) / f'{name}.json', data)
