import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from supportops import synth


@pytest.fixture(scope="session")
def data():
    return synth.generate()
