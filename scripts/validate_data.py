
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"


def load_csv(filename, id_columns):
    return pd.read_csv(DATA_DIR / filename, dtype=id_columns)


def main():
    policyholders = load_csv(
        "policyholders.csv",
        {"policyholder_id": str},
    )

    agents = load_csv(
        "agents.csv",
        {"agent_id": str},
    )

    policies = load_csv(
        "policies.csv",
        {
            "policy_id": str,
            "policyholder_id": str,
            "agent_id": str,
        },
    )

    claims = load_csv(
        "claims.csv",
        {
            "claim_id": str,
            "policy_id": str,
        },
    )

    payments = load_csv(
        "payments.csv",
        {
            "payment_id": str,
            "policy_id": str,
        },
    )

    errors = []

    # Check primary keys for missing and duplicate values.
    datasets = {
        "policyholders": (policyholders, "policyholder_id"),
        "agents": (agents, "agent_id"),
        "policies": (policies, "policy_id"),
        "claims": (claims, "claim_id"),
        "payments": (payments, "payment_id"),
    }

    for name, (df, key) in datasets.items():
        if df[key].isna().any() or df[key].str.strip().eq("").any():
            errors.append(f"{name}: missing or blank {key}")

        if df[key].duplicated().any():
            errors.append(f"{name}: duplicate {key}")

    # Validate foreign-key relationships.
    checks = [
        (
            "policies",
            policies,
            "policyholder_id",
            set(policyholders["policyholder_id"].dropna()),
        ),
        (
            "policies",
            policies,
            "agent_id",
            set(agents["agent_id"].dropna()),
        ),
        (
            "claims",
            claims,
            "policy_id",
            set(policies["policy_id"].dropna()),
        ),
        (
            "payments",
            payments,
            "policy_id",
            set(policies["policy_id"].dropna()),
        ),
    ]

    for name, df, column, valid_ids in checks:
        invalid = (
            df[column].isna()
            | ~df[column].isin(valid_ids)
        )

        if invalid.any():
            errors.append(
                f"{name}: {int(invalid.sum())} invalid {column} reference(s)"
            )

    # Validate monetary amounts.
    for name, df, column in [
        ("policies", policies, "premium_amount"),
        ("claims", claims, "claim_amount"),
        ("payments", payments, "payment_amount"),
    ]:
        amounts = pd.to_numeric(df[column], errors="coerce")

        if amounts.isna().any():
            errors.append(f"{name}: missing or nonnumeric {column}")

        elif (amounts < 0).any():
            errors.append(f"{name}: negative {column}")

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print("VALIDATION PASSED")
    for name, (df, _) in datasets.items():
        print(f"{name}: {len(df)} records")

    print("Primary keys, monetary amounts, and relationships are valid.")


if __name__ == "__main__":
    main()
