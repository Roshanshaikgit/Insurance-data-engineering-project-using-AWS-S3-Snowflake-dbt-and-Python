
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

STAGES = [
    (
        "Source data quality gate",
        [sys.executable, "scripts/run_quality_gate.py"],
    ),
]


def main():
    started_at = datetime.now(timezone.utc)
    print("Starting insurance data pipeline.", flush=True)
    print(f"Started at UTC: {started_at.isoformat()}", flush=True)

    for stage_name, command in STAGES:
        print(f"\n{'=' * 60}", flush=True)
        print(f"Stage: {stage_name}", flush=True)
        print("=" * 60, flush=True)

        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            check=False,
        )

        if result.returncode != 0:
            print(
                f"\nPIPELINE FAILED: {stage_name}; "
                f"exit code {result.returncode}.",
                flush=True,
            )
            raise SystemExit(result.returncode)

        print(f"Stage PASSED: {stage_name}", flush=True)

    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()

    print("\nPIPELINE PASSED.", flush=True)
    print(f"Finished at UTC: {finished_at.isoformat()}", flush=True)
    print(f"Duration: {duration:.2f} seconds", flush=True)


if __name__ == "__main__":
    main()
