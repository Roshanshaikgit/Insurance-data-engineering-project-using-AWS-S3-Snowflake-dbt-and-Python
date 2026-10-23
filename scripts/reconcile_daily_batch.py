
import argparse
import csv
from pathlib import Path

from scripts.load_daily_batch import connect_to_snowflake

ROOT = Path(__file__).resolve().parent.parent

DATASETS = {
    "POLICYHOLDERS": (
        "policyholders.csv",
        "INSURANCE_DB.RAW.RAW_POLICYHOLDERS",
        "POLICYHOLDER_ID",
        "policyholder_id",
    ),
    "AGENTS": (
        "agents.csv",
        "INSURANCE_DB.RAW.RAW_AGENTS",
        '"agent_id"',
        "agent_id",
    ),
    "POLICIES": (
        "policies.csv",
        "INSURANCE_DB.RAW.RAW_POLICIES",
        '"policy_id"',
        "policy_id",
    ),
    "CLAIMS": (
        "claims.csv",
        "INSURANCE_DB.RAW.RAW_CLAIMS",
        '"claim_id"',
        "claim_id",
    ),
    "PAYMENTS": (
        "payments.csv",
        "INSURANCE_DB.RAW.RAW_PAYMENTS",
        '"payment_id"',
        "payment_id",
    ),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    batch_id = args.date.replace("-", "")
    folder = ROOT / "data" / "daily_batches" / batch_id

    if not folder.is_dir():
        raise SystemExit(f"Batch folder not found: {folder}")

    conn = connect_to_snowflake()
    cursor = conn.cursor()
    failures = 0

    try:
        print(f"\nRECONCILIATION: {batch_id}\n")

        for dataset, config in DATASETS.items():
            filename, table, sql_key, csv_key = config
            path = folder / filename

            if not path.is_file():
                print(f"FAIL {dataset}: source file missing")
                failures += 1
                continue

            with path.open(
                newline="", encoding="utf-8-sig"
            ) as file:
                reader = csv.DictReader(file)
                source_keys = [
                    (row.get(csv_key) or "").strip()
                    for row in reader
                ]

            blanks = sum(not key for key in source_keys)
            valid_keys = [key for key in source_keys if key]
            unique_keys = set(valid_keys)
            source_duplicates = len(valid_keys) - len(unique_keys)

            actual_rows = 0
            actual_distinct = 0
            keys = sorted(unique_keys)

            for start in range(0, len(keys), 500):
                chunk = keys[start:start + 500]
                placeholders = ", ".join(["%s"] * len(chunk))
                cursor.execute(
                    f"""
                    SELECT COUNT(*), COUNT(DISTINCT {sql_key})
                    FROM {table}
                    WHERE {sql_key} IN ({placeholders})
                    """,
                    tuple(chunk),
                )
                rows, distinct_rows = cursor.fetchone()
                actual_rows += rows
                actual_distinct += distinct_rows

            missing = len(unique_keys) - actual_distinct
            raw_duplicates = actual_rows - actual_distinct

            passed = (
                len(source_keys) == actual_rows
                and blanks == 0
                and source_duplicates == 0
                and missing == 0
                and raw_duplicates == 0
            )

            print(
                f"{'PASS' if passed else 'FAIL'} {dataset}: "
                f"source={len(source_keys)}, raw={actual_rows}, "
                f"missing={missing}, source_duplicates={source_duplicates}, "
                f"raw_duplicates={raw_duplicates}, blank_keys={blanks}"
            )

            if not passed:
                failures += 1

        print(
            "\nRECONCILIATION PASSED"
            if failures == 0
            else f"\nRECONCILIATION FAILED: {failures} dataset(s)"
        )
    finally:
        cursor.close()
        conn.close()

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
