
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"
QUARANTINE_DIR = PROJECT_ROOT / "data" / "quarantine"


def main():
    policies = pd.read_csv(
        DATA_DIR / "policies.csv",
        dtype=str,
    )

    policyholders = pd.read_csv(
        DATA_DIR / "policyholders.csv",
        dtype=str,
    )

    # Create an invalid test record without modifying the source CSV.
    bad_policy = policies.iloc[[0]].copy()
    bad_policy.loc[:, "policy_id"] = "PL9999"
    bad_policy.loc[:, "policyholder_id"] = "PH9999"

    test_policies = pd.concat(
        [policies, bad_policy],
        ignore_index=True,
    )

    known_policyholders = set(
        policyholders["policyholder_id"].dropna()
    )

    # Identify records that reference nonexistent policyholders.
    invalid_mask = (
        test_policies["policyholder_id"].isna()
        | ~test_policies["policyholder_id"].isin(
            known_policyholders
        )
    )

    valid_records = test_policies.loc[~invalid_mask].copy()
    quarantined_records = test_policies.loc[invalid_mask].copy()

    # Store a reason so the problem can be investigated.
    quarantined_records["rejection_reason"] = (
        "Missing or unknown policyholder_id"
    )

    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

    valid_records.to_csv(
        DATA_DIR / "validated_policies.csv",
        index=False,
    )

    quarantined_records.to_csv(
        QUARANTINE_DIR / "invalid_policies.csv",
        index=False,
    )

    print(f"Input records: {len(test_policies)}")
    print(f"Valid records: {len(valid_records)}")
    print(f"Quarantined records: {len(quarantined_records)}")
    print(
        "Quarantine file:",
        QUARANTINE_DIR / "invalid_policies.csv",
    )


if __name__ == "__main__":
    main()
