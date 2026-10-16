
import json
import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
CONTRACT_DIR = PROJECT_ROOT / "config" / "schema_contracts"


def check_schema(dataset_name):
    contract_path = CONTRACT_DIR / f"{dataset_name}.json"
    csv_path = DATA_DIR / f"{dataset_name}.csv"

    if not contract_path.exists():
        return [f"{dataset_name}: schema contract not found"]

    if not csv_path.exists():
        return [f"{dataset_name}: source CSV not found"]

    try:
        with contract_path.open("r", encoding="utf-8") as file:
            contract = json.load(file)
    except (json.JSONDecodeError, OSError) as exc:
        return [f"{dataset_name}: invalid contract: {exc}"]

    try:
        actual_columns = set(
            pd.read_csv(csv_path, nrows=0).columns
        )
    except (ValueError, OSError, pd.errors.ParserError) as exc:
        return [f"{dataset_name}: unable to read CSV: {exc}"]

    required_columns = set(contract.get("required_columns", []))
    missing = sorted(required_columns - actual_columns)
    unexpected = sorted(actual_columns - required_columns)

    errors = []

    if missing:
        errors.append(
            f"{dataset_name}: missing required columns: {missing}"
        )

    if unexpected and not contract.get("rules", {}).get(
        "allow_unexpected_columns", False
    ):
        errors.append(
            f"{dataset_name}: unexpected columns: {unexpected}"
        )

    if not errors:
        print(f"{dataset_name}: schema check PASSED")

    return errors


def main():
    datasets = ["policyholders"]
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
