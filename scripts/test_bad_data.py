
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"


def main():
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    policyholders = pd.read_csv(DATA_DIR / "policyholders.csv")

    bad_policy = policies.iloc[[0]].copy()
    bad_policy.loc[:, "policy_id"] = "PL9999"
    bad_policy.loc[:, "policyholder_id"] = "PH9999"

    test_policies = pd.concat([policies, bad_policy], ignore_index=True)

    valid_policyholder_ids = set(
        policyholders["policyholder_id"].dropna()
    )

    invalid_policies = test_policies[
        test_policies["policyholder_id"].isna()
        | ~test_policies["policyholder_id"].isin(
            valid_policyholder_ids
        )
    ]

    print(f"Policies tested: {len(test_policies)}")
    print(f"Invalid policies found: {len(invalid_policies)}")

    if invalid_policies.empty:
        print("TEST FAILED: Invalid policy was not detected.")
        raise SystemExit(1)

    print("TEST PASSED: Invalid policy was detected.")
    print(
        invalid_policies[
            ["policy_id", "policyholder_id"]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
