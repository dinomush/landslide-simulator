import unittest
from dataclasses import replace
import numpy as np
from simulator.config import Config
from simulator.stability import factor_of_safety, classify_risk


class StabilityTests(unittest.TestCase):
    def test_water_cohesion_and_friction(self):
        c = Config()
        theta = np.deg2rad(35)
        fs = float(factor_of_safety(theta, .5, c))
        self.assertLess(factor_of_safety(theta, 1, c), fs)
        self.assertGreater(factor_of_safety(theta, .5, replace(c, cohesion=20)), fs)
        self.assertGreater(factor_of_safety(theta, .5, replace(c, friction_angle=40)), fs)

    def test_flat_is_stable_finite(self):
        fs = factor_of_safety(np.zeros((3, 3)), 1, Config())
        self.assertTrue(np.isfinite(fs).all())
        self.assertTrue((fs >= 1.5).all())

    def test_threshold_boundaries(self):
        np.testing.assert_array_equal(classify_risk(np.array([.99, 1, 1.2, 1.5])), [0, 1, 2, 3])
