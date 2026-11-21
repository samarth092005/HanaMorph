import unittest
import sys
import os

suite = unittest.TestSuite()
loader = unittest.TestLoader()
tests_dir = os.path.dirname(os.path.abspath(__file__))

suite.addTests(loader.discover(start_dir=tests_dir, pattern="test_*.py"))
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

if not result.wasSuccessful():
    sys.exit(1)
