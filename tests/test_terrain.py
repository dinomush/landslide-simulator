import unittest
import numpy as np
from simulator.terrain import terrain_fields, load_dem, synthetic_dem


class TerrainTests(unittest.TestCase):
    def test_flat(self):
        t = terrain_fields(np.ones((8, 9)), 5)
        for name in ('slope', 'direction_x', 'direction_y'):
            np.testing.assert_allclose(t[name], 0)

    def test_plane_gradient_and_direction(self):
        y, x = np.mgrid[:8, :9] * 2
        t = terrain_fields(0.3*x+0.4*y, 2)
        np.testing.assert_allclose(t['slope'], np.arctan(0.5))
        np.testing.assert_allclose(t['direction_x'], -0.6)
        np.testing.assert_allclose(t['direction_y'], -0.8)
        self.assertTrue(all(np.isfinite(a).all() for a in t.values()))

    def test_invalid_dem(self):
        for z in (np.array([1, 2]), np.full((2, 2), np.nan), np.full((2, 2), np.inf)):
            with self.assertRaises(ValueError): terrain_fields(z, 1)

    def test_demo_is_finite(self):
        self.assertTrue(all(np.isfinite(a).all() for a in terrain_fields(synthetic_dem(), 5).values()))
