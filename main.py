"""Run with: python main.py --help"""
import argparse
from dataclasses import fields
import json
import sys
from pathlib import Path
import numpy as np
from simulator.config import Config
from simulator.terrain import load_dem, synthetic_dem
from simulator.simulation import simulate, export

ROOT = Path(__file__).resolve().parent


def main():
    # Windows terminals may otherwise reject the user's Unicode directory name.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Educational Landslide Risk & Terrain Simulation Tool')
    parser.add_argument('--dem', type=Path, help='Headerless CSV elevations in metres; otherwise generate demo')
    parser.add_argument('--config', type=Path, help='JSON object overriding any central Config parameter')
    parser.add_argument('--output', type=Path, default=ROOT/'output', help='Output directory')
    for flag, key, help_text in [('rainfall', 'rainfall_mm_per_hour', 'Rainfall in mm/hour'),
                               ('rainfall-hours', 'rainfall_duration_hours', 'Rainfall exposure in hours'),
                               ('cohesion', 'cohesion', 'Cohesion in kPa'),
                               ('friction-angle', 'friction_angle', 'Friction angle in degrees'),
                               ('soil-depth', 'soil_depth', 'Soil depth in metres'),
                               ('cell-size', 'cell_size', 'Square grid spacing in metres'),
                               ('duration', 'simulation_duration', 'Particle motion duration in seconds'),
                               ('dt', 'simulation_dt', 'Outer integration timestep in seconds')]:
        parser.add_argument('--'+flag, dest=key, type=float, default=None, help=help_text)
    args = parser.parse_args()
    try:
        values = json.loads(args.config.read_text(encoding='utf-8')) if args.config else {}
        if not isinstance(values, dict):
            raise ValueError('config must be a JSON object')
        unknown = set(values) - {f.name for f in fields(Config)}
        if unknown:
            raise ValueError(f'Unknown configuration keys: {sorted(unknown)}')
        for key in {f.name for f in fields(Config)}:
            if getattr(args, key, None) is not None:
                values[key] = getattr(args, key)
        c = Config(**values).validate()
        z = load_dem(args.dem) if args.dem else synthetic_dem(cell_size=c.cell_size)
        result = simulate(z, c)
        export(result, args.output)
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        parser.error(str(exc))
    s = result[1]
    print('Landslide Risk & Terrain Simulation Tool')
    print(f"DEM: {z.shape[0]} x {z.shape[1]} | Elevation: {z.min():.1f}–{z.max():.1f} m")
    print(f"Maximum slope: {s['maximum_slope_degrees']:.1f} deg")
    print(f"Rainfall: {c.rainfall_mm_per_hour:g} mm/h over {c.rainfall_duration_hours:g} h | Motion: {c.simulation_duration:g} s")
    print(f"Saturation: {c.initial_saturation:.3f} → {s['final_saturation']:.3f}")
    print(f"Minimum FoS: {s['minimum_fos']:.3f} | Unstable cells: {s['unstable_cells']} | Area: {s['unstable_area_m2']:.0f} m²")
    print(f"Particles: {s['generated_particles']} | Maximum velocity: {s['maximum_particle_velocity_m_s']:.2f} m/s")
    print(f"Output: {(args.output/'simulation.json').resolve()}")
    print('From the project folder: python -m http.server 8000 --bind 127.0.0.1')
    print('Open http://localhost:8000/web/ (or open web/index.html and select simulation.json).')


if __name__ == '__main__':
    main()
