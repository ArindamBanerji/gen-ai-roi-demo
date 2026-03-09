"""
Root conftest for the backend test suite.

Static-analysis tests (test_h7_fix3, test_h7_fix4) read router files via
relative paths such as ``pathlib.Path("app/routers/soc.py")``.  Those paths
are only valid when CWD == backend/.  This module-level chdir ensures the
tests work regardless of the directory from which pytest is invoked.
"""
import os
import pathlib

os.chdir(pathlib.Path(__file__).parent)
