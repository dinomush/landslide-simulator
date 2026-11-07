import unittest
import numpy as np
from simulator.config import Config
from simulator.hydrology import update_saturation


class HydrologyTests(unittest.TestCase):
    def test_more_rain_more_water(self):
        c = Config()
        self.assertGreater(update_saturation(.1, 80, 1, c), update_saturation(.1, 5, 1, c))

    def test_units(self):
        c = Config(infiltration_coefficient=1, drainage_coefficient=0, soil_depth=2)
        self.assertAlmostEqual(float(update_saturation(0, 100, 1, c)), .05)

    def test_clamps_and_drainage(self):
        c = Config()
        self.assertEqual(float(update_saturation(.9, 1e9, 24, c)), 1)
        m = update_saturation(np.array([0, 1]), 0, 1000, c)
        self.assertTrue(np.all((m >= 0) & (m <= 1)))
        self.assertLess(m[1], 1)

    def test_invalid(self):
        for rainfall in (-1, float('nan')):
            with self.assertRaises(ValueError): update_saturation(0, rainfall, 1, Config())
