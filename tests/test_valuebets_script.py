import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_manual_demo_returns_concrete_value_bet() -> None:
    proc = subprocess.run(
        [sys.executable, "scripts/valuebets_tipsport_betano.py", "--manual-demo", "--target", "tipsport", "--min-edge", "1.0"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0
    assert "Found value bets:" in proc.stdout
    assert "Arsenal vs Chelsea" in proc.stdout
