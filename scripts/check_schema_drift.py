
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
CONTRACT_DIR = PROJECT_ROOT / "config" / "schema_contracts"


def validate_schema(csv_path, contract_path):
    """Validate CSV columns and supported data types against a contract."""
    try:
        with contract_path.open("r", encoding="utf-8") as file:
            contract = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"Invalid schema contract: {exc}"]

    try:
        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    except (
        ValueError,
        OSError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as exc:
        return [f"Unable to read CSV: {exc}"]

    actual_columns = set(df.columns)
    required_columns = set(contract.get("required_columns", []))
    expected_types = contract.get("columns", {})
    errors = []

    missing = sorted(required_columns - actual_columns)
    unexpected = sorted(actual_columns - required_columns)

    if missing:
        errors.append(f"Missing required columns: {missing}")

    allow_unexpected = contract.get("rules", {}).get(
        "allow_unexpected_columns", False
    )
    if unexpected and not allow_unexpected:
        errors.append(f"Unexpected columns: {unexpected}")

    for column, data_type in expected_types.items():
        if column not in actual_columns:
            continue

        values = df[column].astype(str).str.strip()
        non_empty = values[values != ""]

        # Empty values are handled separately by future quality checks.
        if non_empty.empty or data_type == "string":
            continue

        if data_type == "number":
            invalid = pd.to_numeric(non_empty, errors="coerce").isna()

        elif data_type == "date":
            invalid = pd.to_datetime(
                non_empty, errors="coerce", format="mixed"
            ).isna()

        elif data_type == "timestamp":
            invalid = pd.to_datetime(
                non_empty, errors="coerce", format="mixed"
            ).isna()

        else:
            errors.append(
                f"Unsupported data type '{data_type}' for column '{column}'"
            )
            continue

        if invalid.any():
            examples = non_empty[invalid].head(3).tolist()
            errors.append(
                f"Invalid {data_type} values in '{column}': {examples}"
            )

    
    # Validate business keys defined in the contract.
    rules = contract.get("rules", {})
    business_keys = contract.get("business_key", [])

    for key in business_keys:
        if key not in df.columns:
            continue

        values = df[key].astype(str).str.strip()

        if rules.get("business_key_not_null", False):
            blank_rows = values.eq("")

            if blank_rows.any():
                errors.append(
                    f"Blank business key values in '{key}': "
                    f"{int(blank_rows.sum())} row(s)"
                )

        if rules.get("business_key_unique_within_batch", False):
            duplicate_mask = (
                values.ne("") & values.duplicated(keep=False)
            )

            if duplicate_mask.any():
                duplicates = sorted(values[duplicate_mask].unique())
                errors.append(
                    f"Duplicate business key values in '{key}': "
                    f"{duplicates[:5]}"
                )

    return errors



def check_schema(dataset_name):
    contract_path = CONTRACT_DIR / f"{dataset_name}.json"
    csv_path = DATA_DIR / f"{dataset_name}.csv"

    if not contract_path.exists():
        return [f"{dataset_name}: schema contract not found"]

    if not csv_path.exists():
        return [f"{dataset_name}: source CSV not found"]

    errors = validate_schema(csv_path, contract_path)

    if errors:
        return [f"{dataset_name}: {error}" for error in errors]

    print(f"{dataset_name}: schema check PASSED")
    return []


def main():
    datasets = [
        "policyholders",
        "policies",
        "claims",
        "agents",
        "payments",
    ]

    errors = []
    for dataset_name in datasets:
        errors.extend(check_schema(dataset_name))

    if errors:
        print("SCHEMA VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("SCHEMA VALIDATION PASSED")


if __name__ == "__main__":
    main()
