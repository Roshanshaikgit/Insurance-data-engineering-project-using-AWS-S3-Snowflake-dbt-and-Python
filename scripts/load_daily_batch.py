
import argparse
import csv
import getpass
import os
from datetime import datetime, timezone
from pathlib import Path

import snowflake.connector


DATABASE = "INSURANCE_DB"
SCHEMA = "RAW"
STAGE = f"@{DATABASE}.{SCHEMA}.INSURANCE_S3_STAGE"

DATASETS = {
    "agents": {
        "table": "RAW_AGENTS",
        "dataset": "AGENTS",
        "columns": '"agent_id", "agent_name", "region", "updated_at"',
        "timestamp_format": True,
    },
    "policyholders": {
        "table": "RAW_POLICYHOLDERS",
        "dataset": "POLICYHOLDERS",
        "columns": "POLICYHOLDER_ID, NAME, CITY, EMAIL, UPDATED_AT",
        "timestamp_format": False,
    },
    "policies": {
        "table": "RAW_POLICIES",
        "dataset": "POLICIES",
        "columns": (
            '"policy_id", "policyholder_id", "agent_id", '
            '"policy_type", "premium_amount", "policy_status", '
            '"effective_date", "updated_at"'
        ),
        "timestamp_format": False,
    },
    "claims": {
        "table": "RAW_CLAIMS",
        "dataset": "CLAIMS",
        "columns": (
            '"claim_id", "policy_id", "claim_amount", '
            '"claim_status", "claim_date", "updated_at"'
        ),
        "timestamp_format": False,
    },
    "payments": {
        "table": "RAW_PAYMENTS",
        "dataset": "PAYMENTS",
        "columns": (
            '"payment_id", "policy_id", "payment_amount", '
            '"payment_date", "payment_status", "updated_at"'
        ),
        "timestamp_format": False,
    },
}


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def connect_to_snowflake():
    required = ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER")
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        raise RuntimeError(
            "Missing environment variable(s): " + ", ".join(missing)
        )

    password = os.getenv("SNOWFLAKE_PASSWORD")
    if not password:
        password = getpass.getpass("Snowflake password: ")

    options = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "password": password,
        "warehouse": "COMPUTE_WH",
        "database": DATABASE,
        "schema": SCHEMA,
    }

    role = os.getenv("SNOWFLAKE_ROLE")
    if role:
        options["role"] = role

    return snowflake.connector.connect(**options)


def record_audit(
    cursor,
    dataset,
    filename,
    batch_id,
    status,
    rows_parsed=0,
    rows_loaded=0,
    expected_rows=1,
    error=None,
):
    now = utc_now()

    cursor.execute(
        f"""
        INSERT INTO {DATABASE}.{SCHEMA}.INGESTION_AUDIT
        (
            DATASET_NAME, SOURCE_FILE, BATCH_ID, LOAD_STATUS,
            ROWS_PARSED, ROWS_LOADED, EXPECTED_ROWS, REJECTED_ROWS,
            STARTED_AT, COMPLETED_AT, ERROR_MESSAGE, CREATED_AT
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            dataset, filename, batch_id, status,
            rows_parsed, rows_loaded, expected_rows,
            max(rows_parsed - rows_loaded, 0),
            now, now, error, now,
        ),
    )


def expected_row_counts(batch_id):
    """Count data rows in each locally generated batch CSV."""
    batch_dir = Path(__file__).resolve().parent.parent / "data" / "daily_batches" / batch_id
    counts = {}

    for name in DATASETS:
        file_path = batch_dir / f"{name}.csv"
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Missing local batch CSV: {file_path}. "
                "Generate the batch before loading it."
            )

        with file_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            counts[name] = sum(1 for row in reader if row)

        if counts[name] < 1:
            raise ValueError(f"No data rows found in {file_path}")

    return counts


def register_manifest(cursor, batch_id, expected_counts):
    """Register expected CSV row counts for each dataset in a batch."""
    source_rows = []

    for name, config in DATASETS.items():
        expected_rows = expected_counts[name]
        source_rows.append(
            f"SELECT '{batch_id}' AS BATCH_ID, "
            f"'{config['dataset']}' AS DATASET_NAME, "
            f"'{name}.csv' AS EXPECTED_FILE, "
            f"{expected_rows} AS EXPECTED_ROWS"
        )

    source_sql = "\nUNION ALL\n".join(source_rows)

    cursor.execute(
        f"""
        MERGE INTO {DATABASE}.{SCHEMA}.SOURCE_BATCH_MANIFEST target
        USING ({source_sql}) source
        ON target.BATCH_ID = source.BATCH_ID
           AND target.DATASET_NAME = source.DATASET_NAME
        WHEN MATCHED THEN UPDATE SET
            target.EXPECTED_FILE = source.EXPECTED_FILE,
            target.EXPECTED_ROWS = source.EXPECTED_ROWS,
            target.IS_REQUIRED = TRUE
        WHEN NOT MATCHED THEN INSERT (
            BATCH_ID, DATASET_NAME, EXPECTED_FILE,
            EXPECTED_ROWS, IS_REQUIRED
        )
        VALUES (
            source.BATCH_ID, source.DATASET_NAME,
            source.EXPECTED_FILE, source.EXPECTED_ROWS, TRUE
        )
        """
    )

    print(f"Manifest registered for batch {batch_id}.")

def validate_manifest(cursor, batch_id, expected_counts):
    cursor.execute(
        f"""
        SELECT DATASET_NAME, EXPECTED_FILE, EXPECTED_ROWS, IS_REQUIRED
        FROM {DATABASE}.{SCHEMA}.SOURCE_BATCH_MANIFEST
        WHERE BATCH_ID = %s
        """,
        (batch_id,),
    )

    manifest = {
        str(row[0]).lower(): row
        for row in cursor.fetchall()
    }
    errors = []

    for name in DATASETS:
        entry = manifest.get(name)
        if entry is None:
            errors.append(f"Missing manifest entry for {name}")
            continue

        if entry[1] != f"{name}.csv":
            errors.append(f"{name}: incorrect expected filename {entry[1]}")

        if int(entry[2]) != expected_counts[name]:
            errors.append(
                f"{name}: manifest expects {entry[2]} rows; "
                f"local CSV contains {expected_counts[name]}"
            )

        if not entry[3]:
            errors.append(f"{name}: IS_REQUIRED must be TRUE")

    if errors:
        raise RuntimeError("Manifest validation failed: " + "; ".join(errors))

    print(f"Manifest validation passed: {len(DATASETS)} datasets.")


def already_succeeded(cursor, batch_id, dataset):
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {DATABASE}.{SCHEMA}.INGESTION_AUDIT
        WHERE BATCH_ID = %s
          AND DATASET_NAME = %s
          AND LOAD_STATUS = 'SUCCESS'
        """,
        (batch_id, dataset),
    )

    return cursor.fetchone()[0] > 0


def stage_files(cursor, stage_path):
    cursor.execute(f"LIST {stage_path}")

    return {
        row[0].replace("\\", "/").rsplit("/", 1)[-1]
        for row in cursor.fetchall()
    }


def load_one_dataset(cursor, batch_id, name, config, available_files, expected_rows):
    filename = f"{name}.csv"
    dataset = config["dataset"]

    if already_succeeded(cursor, batch_id, dataset):
        print(f"SKIP {filename}: already recorded as SUCCESS")
        return True

    if filename not in available_files:
        message = f"Required file not found in S3 stage: {filename}"
        record_audit(
            cursor, dataset, filename, batch_id, "FAILED",
            expected_rows=expected_rows, error=message,
        )
        print(f"FAIL {filename}: {message}")
        return False

    stage_path = f"{STAGE}/daily/{batch_id}/"

    try:
        timestamp_option = (
            "TIMESTAMP_FORMAT = 'AUTO'"
            if config["timestamp_format"] else ""
        )

        if name == "policyholders":
            copy_sql = f"""
                COPY INTO {DATABASE}.{SCHEMA}.{config['table']}
                    ({config['columns']})
                FROM (
                    SELECT
                        $1::VARCHAR,
                        $2::VARCHAR,
                        $3::VARCHAR,
                        $4::VARCHAR,
                        $5::TIMESTAMP_NTZ
                    FROM {stage_path}
                )
                FILES = ('{filename}')
                FILE_FORMAT = (
                    TYPE = CSV
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                )
                ON_ERROR = 'ABORT_STATEMENT'
            """
        else:
            copy_sql = f"""
                COPY INTO {DATABASE}.{SCHEMA}.{config['table']}
                    ({config['columns']})
                FROM {stage_path}
                FILES = ('{filename}')
                FILE_FORMAT = (
                    TYPE = CSV
                    SKIP_HEADER = 1
                    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
                    {timestamp_option}
                )
                ON_ERROR = 'ABORT_STATEMENT'
            """

        cursor.execute(copy_sql)
        results = cursor.fetchall()

        if not results:
            raise RuntimeError("Snowflake returned no COPY result rows")

        statuses = [str(row[1]).upper() for row in results]
        rows_parsed = sum(int(row[2] or 0) for row in results)
        rows_loaded = sum(int(row[3] or 0) for row in results)

        if any("LOAD_SKIPPED" in status for status in statuses):
            raise RuntimeError(
                "Snowflake skipped this file based on load history. "
                "Check RAW table contents and audit history."
            )

        if any("LOAD_FAILED" in status for status in statuses):
            raise RuntimeError("Snowflake reported a failed file load")

        if rows_loaded != expected_rows:
            raise RuntimeError(
                f"Expected {expected_rows} loaded rows but Snowflake reported {rows_loaded}"
            )

        record_audit(
            cursor, dataset, filename, batch_id, "SUCCESS",
            rows_parsed=rows_parsed,
            rows_loaded=rows_loaded,
            expected_rows=expected_rows,
        )

        print(f"SUCCESS {filename}: loaded {rows_loaded} row(s)")
        return True

    except Exception as exc:
        message = str(exc)[:2000]

        try:
            record_audit(
                cursor, dataset, filename, batch_id, "FAILED",
                expected_rows=expected_rows, error=message,
            )
        except Exception as audit_exc:
            print(f"WARNING: could not write failure audit: {audit_exc}")

        print(f"FAIL {filename}: {message}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Load a daily CSV batch from S3 into Snowflake RAW."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Batch date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    try:
        batch_date = datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        parser.error("--date must use YYYY-MM-DD format")

    batch_id = batch_date.strftime("%Y%m%d")
    connection = None

    try:
        connection = connect_to_snowflake()
        connection.autocommit(True)

        with connection.cursor() as cursor:
            cursor.execute("SELECT CURRENT_DATABASE(), CURRENT_ROLE()")
            print("Connected to Snowflake:", cursor.fetchone())

            expected_counts = expected_row_counts(batch_id)
            print(f"\nRegistering manifest for {batch_id}...")
            register_manifest(cursor, batch_id, expected_counts)
            validate_manifest(cursor, batch_id, expected_counts)

            stage_path = f"{STAGE}/daily/{batch_id}/"
            print(f"\nChecking S3 stage for batch {batch_id}...")
            available_files = stage_files(cursor, stage_path)

            print(
                "Files found:",
                ", ".join(sorted(available_files)) or "(none)",
            )

            required_files = {
                f"{name}.csv" for name in DATASETS
            }
            missing_files = sorted(required_files - available_files)

            if missing_files:
                print("\nDAILY LOAD BLOCKED: required files are missing:")
                for filename in missing_files:
                    print(f"  - {filename}")
                print("Upload the missing files and retry.")
                raise SystemExit(1)

            print("\nAll required files are present. Starting load...")
            all_success = True

            for name, config in DATASETS.items():
                success = load_one_dataset(
                    cursor, batch_id, name, config, available_files, expected_counts[name]
                )
                all_success = all_success and success

        if not all_success:
            print(f"\nDAILY LOAD INCOMPLETE: {batch_id}")
            print("Review failure messages and INGESTION_AUDIT.")
            raise SystemExit(1)

        print(f"\nDAILY LOAD PASSED: {batch_id}")
        print("Next run the project pipeline:")
        print("python orchestration\\run_pipeline.py")

    except SystemExit:
        raise
    except Exception as exc:
        print(f"\nDAILY LOAD FAILED: {exc}")
        raise SystemExit(1)
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()

