"""Lets `pytest` import seedance_api from a plain checkout, without `pip install -e .`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
