from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"


def main():
    policies = pd.read_csv(DATA_DIR / "policies.csv", dtype=str)
    policyholders = pd.read_csv(
        DATA_DIR / "policyholders.csv",
        dtype=str,
    )

    # Add a deliberately invalid policy for testing.
    bad_policy = policies.iloc[[0]].copy()
    bad_policy.loc[:, "policy_id"] = "PL9999"
    bad_policy.loc[:, "policyholder_id"] = "PH9999"

    test_policies = pd.concat(
        [policies, bad_policy],
        ignore_index=True,
    )

    known_policyholders = set(policyholders["policyholder_id"])

    invalid_policies = test_policies[
        ~test_policies["policyholder_id"].isin(known_policyholders)
    ]

    print(f"Policies tested: {len(test_policies)}")
    print(f"Invalid policies found: {len(invalid_policies)}")

    if not invalid_policies.empty:
        print("\nInvalid records:")
        print(
            invalid_policies[
                ["policy_id", "policyholder_id"]
            ].to_string(index=False)
        )


if __name__ == "__main__":
    main()
