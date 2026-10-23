
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "data" / "daily_batches"
DATASETS = ["agents", "policyholders", "policies", "claims", "payments"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", required=True)
    batch_id = parser.parse_args().batch_id
    folder = ROOT / batch_id

    if not folder.is_dir():
        raise SystemExit(f"Batch directory not found: {folder}")

    expected = {f"{name}.csv" for name in DATASETS}
    actual = {p.name for p in folder.glob("*.csv")}
    if actual != expected:
        raise SystemExit(
            f"CSV mismatch. Missing={sorted(expected-actual)}; "
            f"unexpected={sorted(actual-expected)}"
        )

    entries = []
    for name in DATASETS:
        path = folder / f"{name}.csv"
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = max(sum(1 for _ in csv.reader(f)) - 1, 0)

        if rows < 1:
            raise SystemExit(f"No data rows in {path.name}")

        entries.append({
            "dataset_name": name,
            "source_file": path.name,
            "expected_rows": rows,
            "file_size_bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })

    manifest = {
        "manifest_version": 1,
        "batch_id": batch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(entries),
        "files": entries,
    }

    output = folder / "manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest created: {output}")
    print(f"Files: {len(entries)}")
    print(f"Expected data rows: {sum(e['expected_rows'] for e in entries)}")


if __name__ == "__main__":
    main()


def load_manifest(batch_dir):
    """Read and validate the generated JSON batch manifest."""
    manifest_path = batch_dir / "manifest.json"

    if not manifest_path.is_file():
        raise FileNotFoundError(
            f"Manifest not found: {manifest_path}"
        )

    with manifest_path.open("r", encoding="utf-8-sig") as file:
        manifest = json.load(file)

    if not isinstance(manifest, dict):
        raise ValueError("manifest.json must contain a JSON object")

    return manifest


def get_manifest_datasets(manifest):
    """Support common manifest layouts without guessing file contents."""
    datasets = manifest.get("datasets")

    if not isinstance(datasets, dict):
        raise ValueError(
            "manifest.json must contain a 'datasets' object. "
            "Inspect the existing manifest before changing its format."
        )

    return datasets


def validate_batch_files(batch_dir, manifest):
    """Check that expected CSV files exist and contain readable headers."""
    manifest_datasets = get_manifest_datasets(manifest)
    validated = {}

    for name, config in DATASETS.items():
        csv_path = batch_dir / f"{name}.csv"

        if not csv_path.is_file():
            raise FileNotFoundError(
                f"Required dataset file is missing: {csv_path}"
            )

        with csv_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.reader(file)
            header = next(reader, None)

        if not header or not any(column.strip() for column in header):
            raise ValueError(f"{csv_path.name} has no valid header")

        expected_entry = manifest_datasets.get(name)
        if expected_entry is None:
            raise ValueError(
                f"Manifest has no entry for dataset '{name}'"
            )

        validated[name] = {
            "path": csv_path,
            "header": [column.strip() for column in header],
            "config": config,
            "manifest_entry": expected_entry,
        }

    return validated


def extract_expected_rows(entry):
    """Read an expected row count when the manifest provides one."""
    if isinstance(entry, int):
        return entry

    if isinstance(entry, dict):
        for key in ("expected_rows", "row_count", "rows", "record_count"):
            value = entry.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Invalid expected row count: {value!r}"
                    )

    return None


def count_csv_data_rows(csv_path):
    """Count data records, excluding the header."""
    with csv_path.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.reader(file)
        next(reader, None)
        return sum(1 for _ in reader)


def validate_expected_rows(validated):
    """Compare actual CSV data records with manifest counts if available."""
    for name, item in validated.items():
        expected = extract_expected_rows(item["manifest_entry"])
        actual = count_csv_data_rows(item["path"])

        if expected is not None and actual != expected:
            raise ValueError(
                f"{name}.csv row-count mismatch: "
                f"manifest expects {expected}, file has {actual}"
            )

        print(
            f"Validated {name}.csv: {actual} data rows"
            + (
                f" (expected {expected})"
                if expected is not None
                else ""
            )
        )


def record_audit(
    cursor,
    batch_id,
    dataset,
    status,
    rows_loaded=0,
    error_message=None,
):
    """Write an audit result without deleting existing audit history."""
    cursor.execute(
        f"""
        INSERT INTO {AUDIT_TABLE}
            (BATCH_ID, DATASET_NAME, STATUS, ROWS_LOADED,
             ERROR_MESSAGE, UPDATED_AT)
        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP())
        """,
        (
            batch_id,
            dataset,
            status,
            rows_loaded,
            error_message,
        ),
    )


def already_succeeded(cursor, batch_id, dataset):
    """Return True when the latest audit status for this dataset succeeded."""
    cursor.execute(
        f"""
        SELECT STATUS
        FROM {AUDIT_TABLE}
        WHERE BATCH_ID = %s
          AND DATASET_NAME = %s
        ORDER BY UPDATED_AT DESC
        LIMIT 1
        """,
        (batch_id, dataset),
    )
    row = cursor.fetchone()
    return bool(row and str(row[0]).upper() == "SUCCESS")

def build_copy_expressions(dataset_name, columns):
    """Build safe conversions for staged CSV values."""
    expressions = []

    for position, column in enumerate(columns, start=1):
        field = f"NULLIF(TRIM(${position}::VARCHAR), '')"
        normalized = column.upper()

        if normalized in {
            "EFFECTIVE_DATE",
            "CLAIM_DATE",
            "PAYMENT_DATE",
            "START_DATE",
            "END_DATE",
            "DATE_OF_BIRTH",
        }:
            expression = f"TRY_TO_DATE({field}, 'YYYY-MM-DD')"

        elif normalized in {
            "UPDATED_AT",
            "INGESTED_AT",
            "CREATED_AT",
        }:
            expression = f"TRY_TO_TIMESTAMP_NTZ({field})"

        elif normalized in {
            "PREMIUM_AMOUNT",
            "CLAIM_AMOUNT",
            "PAYMENT_AMOUNT",
        }:
            expression = f"TRY_TO_DECIMAL({field}, 18, 2)"

        else:
            expression = field

        expressions.append(expression)

    return expressions



def load_one_dataset(cursor, batch_id, dataset_name, item, stage_path):
    """Load one CSV using a Snowflake staged-file transformation."""
    config = item["config"]
    columns = config["columns"]
    table = f"{DATABASE}.{SCHEMA}.{config['table']}"
    filename = f"{dataset_name}.csv"

    if already_succeeded(cursor, batch_id, dataset_name):
        print(f"SKIP {dataset_name}: already marked SUCCESS")
        return True

    if filename not in stage_files(cursor, stage_path):
        message = f"{filename} not found under {stage_path}"
        record_audit(
            cursor, batch_id, dataset_name, "FAILED", 0, message
        )
        print(f"FAILED {dataset_name}: {message}")
        return False

    target_columns = ", ".join(columns)
    expressions = ", ".join(
        build_copy_expressions(dataset_name, columns)
    )

    # Use a path relative to the stage root (which ends in /raw/).
    staged_file = f"{STAGE}/daily/{batch_id}/{filename}"

    copy_sql = f"""
        COPY INTO {table} ({target_columns})
        FROM (
            SELECT {expressions}
            FROM {staged_file}
                (FILE_FORMAT => '{FILE_FORMAT}')
        )
        ON_ERROR = 'ABORT_STATEMENT'
    """

    try:
        cursor.execute(copy_sql)
        results = cursor.fetchall()

        rows_loaded = 0
        for result in results:
            if len(result) > 3 and str(result[1]).upper() == "LOADED":
                rows_loaded += int(result[3] or 0)

        record_audit(
            cursor, batch_id, dataset_name, "SUCCESS", rows_loaded
        )
        print(f"SUCCESS {dataset_name}: {rows_loaded} rows loaded")
        return True

    except Exception as exc:
        message = str(exc)[:4000]
        record_audit(
            cursor, batch_id, dataset_name, "FAILED", 0, message
        )
        print(f"FAILED {dataset_name}: {message}")
        return False
