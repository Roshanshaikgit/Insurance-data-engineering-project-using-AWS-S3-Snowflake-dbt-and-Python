
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_PATH = REPORT_DIR / "quality_gate_report.json"

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


def save_report(report):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()

    with REPORT_PATH.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)

    print(f"\nQuality report saved to: {REPORT_PATH}")


def main():
    report = {
        "pipeline": "insurance_data_quality_checks",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "overall_status": "PASSED",
        "checks": [],
    }

    print("Starting complete insurance pipeline checks.", flush=True)

    for check_name, command in CHECKS:
        print(f"\n{'=' * 60}", flush=True)
        print(f"Running: {check_name}", flush=True)
        print("=" * 60, flush=True)

        start_time = time.perf_counter()

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        duration_seconds = round(time.perf_counter() - start_time, 3)

        if result.stdout:
            print(result.stdout, end="", flush=True)

        if result.stderr:
            print(result.stderr, end="", file=sys.stderr, flush=True)

        check_result = {
            "check_name": check_name,
            "status": "PASSED" if result.returncode == 0 else "FAILED",
            "command": command,
            "exit_code": result.returncode,
            "duration_seconds": duration_seconds,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        report["checks"].append(check_result)

        if result.returncode != 0:
            report["overall_status"] = "FAILED"
            save_report(report)
            print(
                f"\nALL CHECKS FAILED: {check_name} returned "
                f"exit code {result.returncode}.",
                flush=True,
            )
            raise SystemExit(result.returncode)

        print(f"{check_name}: PASSED", flush=True)

    save_report(report)
    print("\nALL CHECKS PASSED.", flush=True)


if __name__ == "__main__":
    main()
