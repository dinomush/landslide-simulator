import json
import unittest
from dataclasses import replace
import numpy as np
from simulator.config import Config
from simulator.terrain import synthetic_dem, terrain_fields
from simulator.simulation import simulate
from simulator.dynamics import Particles, sample


class SimulationTests(unittest.TestCase):
    def test_rainfall_chain_reproducible_and_strict_json(self):
        z = synthetic_dem()
        c = Config(simulation_duration=3, simulation_dt=.2, particle_count_limit=20)
        low = simulate(z, replace(c, rainfall_mm_per_hour=0))
        high = simulate(z, c)
        self.assertGreater(high[1]['final_saturation'], low[1]['final_saturation'])
        self.assertLess(high[1]['minimum_fos'], low[1]['minimum_fos'])
        self.assertGreater(high[1]['unstable_cells'], low[1]['unstable_cells'])
        self.assertGreater(high[1]['total_particle_distance_m'], 0)
        self.assertLessEqual(high[1]['generated_particles'], 20)
        self.assertEqual(high[0], simulate(z, c)[0])
        self.assertEqual(high[0]['frames'][-1]['time'], 3)
        json.dumps(high, allow_nan=False)

    def test_particles_downhill_and_boundary_stop(self):
        y, x = np.mgrid[:6, :6]
        t = terrain_fields(100-x.astype(float), 1)
        c = Config(particle_count_limit=1, damping=.2, cell_size=1)
        p = Particles(t, c)
        p.positions = np.array([[4.8, 2.]])
        p.velocities = np.array([[1., 0.]])
        p.active = np.array([True])
        p.advance(np.full((6, 6), .5), 2)
        self.assertGreater(p.positions[0, 0], 4.8)
        self.assertLessEqual(p.positions[0, 0], 5)
        self.assertFalse(p.active[0])
        np.testing.assert_allclose(p.velocities, 0)

    def test_bilinear_sampling(self):
        y,x = np.mgrid[:4,:5]
        np.testing.assert_allclose(sample(2*x+3*y, np.array([[1.5, 2.5]]), 1), [10.5])

    def test_tiny_initial_drive_can_grow_with_rain(self):
        y, x = np.mgrid[:10, :10]
        c = Config(cell_size=1, particle_count_limit=1)
        p = Particles(terrain_fields(100-x.astype(float), 1), c)
        p.positions = np.array([[2., 2.]])
        p.velocities = np.zeros((1, 2))
        p.active = np.array([True])
        p.advance(np.full((10, 10), .99999), .2)
        self.assertTrue(p.active[0])
        p.advance(np.full((10, 10), .8), 1)
        self.assertGreater(p.velocities[0, 0], .1)

    def test_invalid_parameters(self):
        for changes in ({'simulation_dt':0}, {'rainfall_mm_per_hour':-1}, {'cohesion':float('inf')},
                        {'friction_angle':90}, {'soil_depth':0}, {'particle_count_limit':2.5}):
            with self.assertRaises(ValueError): replace(Config(), **changes).validate()
