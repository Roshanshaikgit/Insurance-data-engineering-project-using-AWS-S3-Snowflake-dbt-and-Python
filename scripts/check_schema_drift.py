
import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
CONTRACT_DIR = PROJECT_ROOT / "config" / "schema_contracts"


# Known, approved source-column aliases.
# Add aliases here instead of changing contracts for harmless renames.
ALIAS_CONFIG_PATH = PROJECT_ROOT / "config" / "column_aliases.json"


def load_column_aliases():
    """Load and validate approved aliases from central configuration."""
    try:
        with ALIAS_CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Unable to load column alias configuration: {exc}"
        ) from exc

    aliases_by_dataset = {}

    for dataset, fields in config.items():
        aliases_by_dataset[dataset.lower()] = {}

        for canonical_name, aliases in fields.items():
            canonical = canonical_name.strip().lower()

            for alias in aliases:
                source_name = alias.strip().lower()

                existing = aliases_by_dataset[dataset.lower()].get(
                    source_name
                )

                if existing and existing != canonical:
                    raise RuntimeError(
                        f"Alias '{source_name}' maps to multiple "
                        f"canonical columns in dataset '{dataset}'"
                    )

                aliases_by_dataset[dataset.lower()][source_name] = (
                    canonical
                )

    return aliases_by_dataset


COLUMN_ALIASES = load_column_aliases()

def normalize_column_name(column, aliases):
    """Standardize case, whitespace, and approved column aliases."""
    normalized = str(column).strip().lower()
    return aliases.get(normalized, normalized)


def validate_schema(csv_path, contract_path, dataset_name=None):
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

    aliases = COLUMN_ALIASES.get(dataset_name, {})

    # Normalize source headers before validating the contract.
    original_columns = list(df.columns)
    normalized_columns = [
        normalize_column_name(column, aliases)
        for column in original_columns
    ]

    # Never silently choose between two columns that map to the same name.
    seen = set()
    duplicates = set()

    for column in normalized_columns:
        if column in seen:
            duplicates.add(column)
        seen.add(column)

    if duplicates:
        return [
            "Ambiguous columns after normalization: "
            f"{sorted(duplicates)}. Check the source CSV headers."
        ]

    df.columns = normalized_columns
    actual_columns = set(df.columns)

    # Normalize contract column names too, so comparisons are consistent.
    required_columns = {
        normalize_column_name(column, aliases)
        for column in contract.get("required_columns", [])
    }

    expected_types = {
        normalize_column_name(column, aliases): data_type
        for column, data_type in contract.get("columns", {}).items()
    }

    errors = []

    missing = sorted(required_columns - actual_columns)

    # A declared optional column is expected, even if it is not required.
    known_columns = required_columns | set(expected_types)
    unexpected = sorted(actual_columns - known_columns)

    if missing:
        errors.append(f"Missing required columns: {missing}")

    rules = contract.get("rules", {})
    allow_unexpected = rules.get("allow_unexpected_columns", False)

    if unexpected and not allow_unexpected:
        errors.append(f"Unexpected columns: {unexpected}")

    # Validate data types using canonical column names.
    for column, data_type in expected_types.items():
        if column not in actual_columns:
            continue

        values = df[column].astype(str).str.strip()
        non_empty = values[values != ""]

        # Blank values are handled by separate quality checks.
        if non_empty.empty or data_type == "string":
            continue

        if data_type == "number":
            invalid = pd.to_numeric(
                non_empty, errors="coerce"
            ).isna()

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
                f"Unsupported data type '{data_type}' "
                f"for column '{column}'"
            )
            continue

        if invalid.any():
            examples = non_empty[invalid].head(3).tolist()
            errors.append(
                f"Invalid {data_type} values in '{column}': {examples}"
            )

    # Validate business keys using canonical names.
    business_keys = [
        normalize_column_name(key, aliases)
        for key in contract.get("business_key", [])
    ]

    for key in business_keys:
        if key not in actual_columns:
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
            duplicate_mask = values.ne("") & values.duplicated(
                keep=False
            )

            if duplicate_mask.any():
                duplicates_found = sorted(
                    values[duplicate_mask].unique()
                )
                errors.append(
                    f"Duplicate business key values in '{key}': "
                    f"{duplicates_found[:5]}"
                )

    return errors


def check_schema(dataset_name):
    contract_path = CONTRACT_DIR / f"{dataset_name}.json"
    csv_path = DATA_DIR / f"{dataset_name}.csv"

    if not contract_path.exists():
        return [f"{dataset_name}: schema contract not found"]

    if not csv_path.exists():
        return [f"{dataset_name}: source CSV not found"]

    errors = validate_schema(
        csv_path,
        contract_path,
        dataset_name=dataset_name,
    )

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
