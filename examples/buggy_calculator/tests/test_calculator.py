from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from calculator import add


def test_add_returns_sum() -> None:
    assert add(1, 2) == 3
