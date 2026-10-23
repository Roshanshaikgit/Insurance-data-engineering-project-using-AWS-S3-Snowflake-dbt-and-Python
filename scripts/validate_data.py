
from pathlib import Path
import argparse
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
GENERATED_DIR = PROJECT_ROOT / "data" / "generated"
DAILY_BATCH_DIR = PROJECT_ROOT / "data" / "daily_batches"

# Expected incoming schema for every insurance dataset.
SCHEMAS = {
    "policyholders": [
        "policyholder_id", "full_name", "city", "email", "updated_at"
    ],
    "agents": [
        "agent_id", "agent_name", "region", "updated_at"
    ],
    "policies": [
        "policy_id", "policyholder_id", "agent_id", "policy_type",
        "premium_amount", "policy_status", "effective_date", "updated_at"
    ],
    "claims": [
        "claim_id", "policy_id", "claim_amount", "claim_status",
        "claim_date", "updated_at"
    ],
    "payments": [
        "payment_id", "policy_id", "payment_amount", "payment_date",
        "payment_status", "updated_at"
    ],
}

PRIMARY_KEYS = {
    "policyholders": "policyholder_id",
    "agents": "agent_id",
    "policies": "policy_id",
    "claims": "claim_id",
    "payments": "payment_id",
}

REQUIRED_FIELDS = {
    "policyholders": [
        "policyholder_id", "full_name", "city", "updated_at"
    ],
    "agents": ["agent_id", "agent_name", "region", "updated_at"],
    "policies": [
        "policy_id", "policyholder_id", "agent_id", "policy_type",
        "premium_amount", "policy_status", "effective_date", "updated_at"
    ],
    "claims": [
        "claim_id", "policy_id", "claim_amount", "claim_status",
        "claim_date", "updated_at"
    ],
    "payments": [
        "payment_id", "policy_id", "payment_amount", "payment_date",
        "payment_status", "updated_at"
    ],
}

DATE_FIELDS = {
    "policyholders": ["updated_at"],
    "agents": ["updated_at"],
    "policies": ["effective_date", "updated_at"],
    "claims": ["claim_date", "updated_at"],
    "payments": ["payment_date", "updated_at"],
}

AMOUNT_FIELDS = {
    "policies": ["premium_amount"],
    "claims": ["claim_amount"],
    "payments": ["payment_amount"],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Validate insurance CSV files before ingestion."
    )
    parser.add_argument(
        "--date",
        help="Daily batch date in YYYY-MM-DD format. "
             "Without this option, validates data/generated."
    )
    return parser.parse_args()


def load_dataset(data_dir, name, errors):
    path = data_dir / f"{name}.csv"

    if not path.is_file():
        errors.append(f"{name}: required file is missing: {path}")
        return None

    try:
        # Read as strings first to preserve IDs and detect invalid values.
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as exc:
        errors.append(f"{name}: could not read CSV: {exc}")
        return None

    expected = SCHEMAS[name]
    actual = list(df.columns)

    missing_columns = [c for c in expected if c not in actual]
    unexpected_columns = [c for c in actual if c not in expected]

    if missing_columns:
        errors.append(
            f"{name}: missing column(s): {', '.join(missing_columns)}"
        )

    if unexpected_columns:
        errors.append(
            f"{name}: unexpected column(s): "
            f"{', '.join(unexpected_columns)}"
        )

    # Avoid later KeyErrors if the incoming schema is incomplete.
    usable_columns = [c for c in expected if c in df.columns]
    return df, usable_columns


def main():
    args = parse_args()

    if args.date:
        try:
            batch_date = pd.to_datetime(
                args.date, format="%Y-%m-%d", errors="raise"
            )
        except ValueError:
            print("ERROR: --date must use YYYY-MM-DD format.")
            raise SystemExit(2)

        batch_id = batch_date.strftime("%Y%m%d")
        data_dir = DAILY_BATCH_DIR / batch_id
        source_name = f"daily batch {batch_id}"
    else:
        data_dir = GENERATED_DIR
        source_name = "original generated data"

    print("=" * 65)
    print("INSURANCE DATA VALIDATION")
    print(f"Source: {source_name}")
    print(f"Folder: {data_dir}")
    print("=" * 65)

    if not data_dir.is_dir():
        print(f"VALIDATION FAILED: folder does not exist: {data_dir}")
        raise SystemExit(1)

    errors = []
    datasets = {}

    # 1. Load files and verify their incoming schemas.
    for name in SCHEMAS:
        result = load_dataset(data_dir, name, errors)
        if result is not None:
            df, usable_columns = result
            datasets[name] = df

            # 2. Required fields must not be null or blank.
            for column in REQUIRED_FIELDS[name]:
                if column not in usable_columns:
                    continue

                blank = df[column].isna() | df[column].str.strip().eq("")
                if blank.any():
                    errors.append(
                        f"{name}: {int(blank.sum())} missing/blank "
                        f"value(s) in {column}"
                    )

            # 3. Primary keys must be populated and unique.
            key = PRIMARY_KEYS[name]
            if key in usable_columns:
                values = df[key].str.strip()
                nonblank = values[values.ne("")]

                if nonblank.duplicated().any():
                    duplicate_count = int(nonblank.duplicated().sum())
                    errors.append(
                        f"{name}: {duplicate_count} duplicate "
                        f"{key} value(s)"
                    )

            # 4. Monetary amounts must be numeric and non-negative.
            for column in AMOUNT_FIELDS.get(name, []):
                if column not in usable_columns:
                    continue

                raw = df[column].str.strip()
                amounts = pd.to_numeric(
                    raw.replace("", pd.NA), errors="coerce"
                )

                invalid = amounts.isna()
                if invalid.any():
                    errors.append(
                        f"{name}: {int(invalid.sum())} missing or "
                        f"nonnumeric {column} value(s)"
                    )

                negative = amounts.lt(0).fillna(False)
                if negative.any():
                    errors.append(
                        f"{name}: {int(negative.sum())} negative "
                        f"{column} value(s)"
                    )

            # 5. Date and timestamp values must be parseable.
            for column in DATE_FIELDS[name]:
                if column not in usable_columns:
                    continue

                raw = df[column].str.strip()
                parsed = pd.to_datetime(
                    raw.replace("", pd.NA), errors="coerce", utc=True
                )
                invalid = parsed.isna()

                if invalid.any():
                    errors.append(
                        f"{name}: {int(invalid.sum())} missing or "
                        f"invalid date/timestamp value(s) in {column}"
                    )

    # 6. Validate foreign-key relationships when required columns exist.
    relationships = [
        ("policies", "policyholder_id", "policyholders",
         "policyholder_id"),
        ("policies", "agent_id", "agents", "agent_id"),
        ("claims", "policy_id", "policies", "policy_id"),
        ("payments", "policy_id", "policies", "policy_id"),
    ]

    for child_name, child_key, parent_name, parent_key in relationships:
        child = datasets.get(child_name)
        parent = datasets.get(parent_name)

        if child is None or parent is None:
            continue
        if child_key not in child.columns or parent_key not in parent.columns:
            continue

        valid_ids = set(
            parent[parent_key].astype(str).str.strip()
        )
        valid_ids.discard("")

        references = child[child_key].astype(str).str.strip()
        invalid = references.eq("") | ~references.isin(valid_ids)

        if invalid.any():
            errors.append(
                f"{child_name}: {int(invalid.sum())} invalid "
                f"{child_key} reference(s) to {parent_name}"
            )

    # 7. Report the result and return a failure code if any check failed.
    print("\nRecord counts:")
    for name in SCHEMAS:
        if name in datasets:
            print(f"  {name}: {len(datasets[name]):,} rows")

    if errors:
        print(f"\nVALIDATION FAILED: {len(errors)} issue(s)")
        for error in errors:
            print(f"  FAIL - {error}")
        raise SystemExit(1)

    total_rows = sum(len(df) for df in datasets.values())

    print(f"\nVALIDATION PASSED: {total_rows:,} total records")
    print("Schema, required fields, primary keys, amounts, dates,")
    print("and foreign-key relationships passed.")
    print("Safe to proceed to the next ingestion step.")


if __name__ == "__main__":
    main()
