#!/usr/bin/env python

# built-in modules
import unittest
import tempfile
import os, sys
import math

# private modules
sys.path.append(os.path.join(os.path.dirname(__file__), "../tools")) # this is the generic folder for subroutines
from ts_thresholds import *

class Test(unittest.TestCase):
    def setUp(self):
        self._s = """
 minval = 1e-12
  steps =          3          8         20         60
      * =   1.00e-13   1.00e-10   1.00e-06   1.00e-02
      T =   1.00e-11   1.00e-08   1.00e-05   1.00e+00
"""
        self._d = {
            "minval": 1.0e-12,
            "steps": [3, 8, 20, 60],
            "*": [1.0e-13, 1.0e-10, 1.0e-06, 1.0e-02],
            "T": [1.0e-11, 1.0e-08, 1.0e-05, 1.0e-00]
        }
        f = tempfile.NamedTemporaryFile(mode='w+b', delete=False)
        self._filename = f.name
        f.write(self._s.encode('ascii'))
        f.close()

    def tearDown(self):
        pass

    def test_basic_setup(self):
        t1 = Thresholds(self._s)  # from string
        t2 = Thresholds(self._d)  # from dictionary
        self.assertEqual(t1, t2)
        t3 = Thresholds(self._filename)  # from file
        self.assertEqual(t1, t3)

    def test_output(self):
        t1 = Thresholds(self._s)
        t2 = Thresholds(self._s)
        # test string output and input
        t2.from_str(str(t2))
        self.assertEqual(t1, t2)
        # test dictionary output and input
        t2.from_dict(t2.to_dict())
        self.assertEqual(t1, t2)
        # test file output and input
        t2.to_file(self._filename)
        t2.from_file(self._filename)
        self.assertEqual(t1, t2)

    def test_thresholds(self):
        t = Thresholds(self._s)
        self.assertAlmostEqual(t.get_threshold('PP', 8), 1.0e-10)
        self.assertAlmostEqual(t.get_threshold('T', 8), 1.0e-8)
        self.assertAlmostEqual(t.get_threshold('PP', 1), 1.0e-13)
        self.assertAlmostEqual(t.get_threshold('T', 1), 1.0e-11)
        t1 = t.get_threshold('PP', 8)
        t3 = t.get_threshold('PP', 20)
        t.mode = 'const'
        t2 = t.get_threshold('PP', 11)
        self.assertAlmostEqual(t2, t3)
        t.mode = 'linear'
        t2 = t.get_threshold('PP', 11)
        self.assertAlmostEqual(t2, float(11 - 8) / (20 - 8) * (t3 - t1) + t1)
        t.mode = 'log'
        t2 = t.get_threshold('PP', 11)
        self.assertAlmostEqual(t2, math.exp(float(11 - 8) / (20 - 8) * (math.log(t3) - math.log(t1)) + math.log(t1)))

    def test_updating(self):
        t = Thresholds(self._s)
        t.digits = 4
        t.increase_factor = 4.0
        t.update_threshold('PP', 8, 0.5e-7)
        self.assertAlmostEqual(t.get_threshold('PP', 8), 2.0e-7)
        t.update_threshold('T', 8, 0.5e-9)
        self.assertAlmostEqual(t.get_threshold('T', 8), 2.0e-9)
        t.mode = 'linear'
        t.update_threshold('PP', 40, 1.00e-02)
        self.assertAlmostEqual(t.get_threshold('PP', 60), 8.0e-2)

    def test_modifying(self):
        t = Thresholds(self._s)
        t.mode = 'linear'
        t.add_step(1)
        self.assertAlmostEqual(t.get_threshold('PP', 1), t.get_threshold('PP', 3))
        self.assertAlmostEqual(t.get_threshold('PP', 1), t.get_threshold('PP', 2))
        t.add_step(80)
        self.assertAlmostEqual(t.get_threshold('PP', 60), t.get_threshold('PP', 80))
        self.assertAlmostEqual(t.get_threshold('PP', 60), t.get_threshold('PP', 70))
        t.add_step(10)
        self.assertAlmostEqual(t.get_threshold('PP', 10), 1.7e-7)
        t.removeStep(1)
        t.removeStep(10)
        t.removeStep(80)
        self.assertEqual(t, Thresholds(self._s))
        t.add_variable('QV')
        t.increase_factor = 1.0
        t.update_threshold('QV', 3, 1.0e-12)
        t.update_threshold('QV', 8, 1.0e-9)
        t.update_threshold('QV', 20, 5.0e-5)
        t.update_threshold('QV', 60, 1.0e-1)
        self.assertAlmostEqual(t.get_threshold('QV', 15), 2.9167083333333337e-05)
        t.remove_variable('QV')
        self.assertEqual(t, Thresholds(self._s))


if __name__ == "__main__":
    unittest.main()
