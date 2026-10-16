
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

CHECKS = [
    (
        "Schema unit tests",
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests/unit",
            "-p",
            "test_schema_drift.py",
            "-v",
        ],
    ),
    (
        "Invalid policy test",
        [sys.executable, "scripts/test_bad_data.py"],
    ),
    (
        "Invalid claim relationship test",
        [sys.executable, "scripts/test_relationship_failure.py"],
    ),
    (
        "Integrated quality gate",
        [sys.executable, "scripts/run_quality_gate.py"],
    ),
]


def main():
    print("Starting complete insurance pipeline checks.", flush=True)

    for check_name, command in CHECKS:
        print(f"\n{'=' * 60}", flush=True)
        print(f"Running: {check_name}", flush=True)
        print("=" * 60, flush=True)

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"\nALL CHECKS FAILED: {check_name} returned "
                f"exit code {result.returncode}.",
                flush=True,
            )
            raise SystemExit(result.returncode)

        print(f"{check_name}: PASSED", flush=True)

    print("\nALL CHECKS PASSED.", flush=True)


if __name__ == "__main__":
    main()
