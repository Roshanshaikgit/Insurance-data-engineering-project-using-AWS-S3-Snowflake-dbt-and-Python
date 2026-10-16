
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    ("Schema validation", PROJECT_ROOT / "scripts" / "check_schema_drift.py"),
    ("Business data validation", PROJECT_ROOT / "scripts" / "validate_data.py"),
]


def main():
    print("Starting insurance data quality gate...", flush=True)

    for check_name, script_path in CHECKS:
        print(f"\nRunning {check_name}...", flush=True)

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"\nQUALITY GATE FAILED: {check_name} failed. "
                "Downstream processing must stop.",
                flush=True,
            )
            raise SystemExit(result.returncode)

        print(f"{check_name} PASSED.", flush=True)

    print("\nQUALITY GATE PASSED. All configured checks succeeded.", flush=True)


if __name__ == "__main__":
    main()
