
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_CHECKER = PROJECT_ROOT / "scripts" / "check_schema_drift.py"


def main():
    print("Starting insurance data quality gate...")

    result = subprocess.run(
        [sys.executable, str(SCHEMA_CHECKER)],
        cwd=PROJECT_ROOT,
        check=False,
    )

    if result.returncode != 0:
        print("QUALITY GATE FAILED. Downstream processing must stop.")
        raise SystemExit(result.returncode)

    print("QUALITY GATE PASSED. Schema validation succeeded.")


if __name__ == "__main__":
    main()
