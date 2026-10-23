
import csv
import argparse
from pathlib import Path
from datetime import datetime, timezone


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BATCH_DIR = PROJECT_ROOT / "data" / "daily_batches"

DATASETS = [
    "policyholders",
    "agents",
    "policies",
    "claims",
    "payments",
]


def count_csv_rows(file_path):
    with file_path.open(
        "r", newline="", encoding="utf-8-sig"
    ) as file:
        reader = csv.reader(file)
        next(reader, None)  # Skip header
        return sum(1 for row in reader if row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        required=True,
        help="Batch date in YYYY-MM-DD format",
    )
    args = parser.parse_args()

    try:
        batch_date = datetime.strptime(
            args.date, "%Y-%m-%d"
        ).strftime("%Y%m%d")
    except ValueError:
        raise SystemExit("Date must use YYYY-MM-DD format.")

    batch_dir = BATCH_DIR / batch_date

    if not batch_dir.is_dir():
        raise SystemExit(f"Batch folder not found: {batch_dir}")

    manifest_path = batch_dir / "manifest.csv"

    if manifest_path.exists():
        raise SystemExit(
            f"Manifest already exists: {manifest_path}"
        )

    manifest_rows = []

    for dataset in DATASETS:
        filename = f"{dataset}.csv"
        file_path = batch_dir / filename

        if not file_path.is_file():
            raise SystemExit(f"Required file missing: {file_path}")

        expected_rows = count_csv_rows(file_path)

        manifest_rows.append({
            "batch_id": batch_date,
            "dataset_name": dataset,
            "file_name": filename,
            "expected_rows": expected_rows,
        })

    with manifest_path.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "batch_id",
                "dataset_name",
                "file_name",
                "expected_rows",
            ],
        )
        writer.writeheader()
        writer.writerows(manifest_rows)

    total_rows = sum(
        row["expected_rows"] for row in manifest_rows
    )

    print(f"Manifest created: {manifest_path}")
    print(f"Batch ID: {batch_date}")
    print(f"Datasets: {len(manifest_rows)}")
    print(f"Total expected records: {total_rows}")

    for row in manifest_rows:
        print(
            f"{row['file_name']}: "
            f"{row['expected_rows']} expected rows"
        )


if __name__ == "__main__":
    main()
