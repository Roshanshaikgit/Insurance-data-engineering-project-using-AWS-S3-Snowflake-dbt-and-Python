
import os
import subprocess
import sys
import getpass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT = PROJECT_ROOT / "dbt_project"

STAGES = [
    (
        "Source data quality gate",
        [sys.executable, "scripts/run_quality_gate.py"],
        PROJECT_ROOT,
    ),
    (
        "dbt build: Bronze, Silver, Gold and data tests",
        [str(PROJECT_ROOT / ".venv" / "Scripts" / "dbt.exe"), "build"],
        DBT_PROJECT,
    ),
]


def main():
    started_at = datetime.now(timezone.utc)
    print("Starting insurance data pipeline.", flush=True)
    print(f"Started at UTC: {started_at.isoformat()}", flush=True)

    env = os.environ.copy()

    # Prompt securely if the Snowflake password is not already available.
    if not env.get("SNOWFLAKE_PASSWORD"):
        env["SNOWFLAKE_PASSWORD"] = getpass.getpass(
            "Snowflake password: "
        )

    for stage_name, command, working_directory in STAGES:
        print(f"\n{'=' * 60}", flush=True)
        print(f"Stage: {stage_name}", flush=True)
        print("=" * 60, flush=True)

        result = subprocess.run(
            command,
            cwd=working_directory,
            env=env,
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
