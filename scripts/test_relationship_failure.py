
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"


def main():
    policies = pd.read_csv(DATA_DIR / "policies.csv")
    claims = pd.read_csv(DATA_DIR / "claims.csv")

    bad_claim = claims.iloc[[0]].copy()
    bad_claim.loc[:, "claim_id"] = "CL9999"
    bad_claim.loc[:, "policy_id"] = "PL9999"

    test_claims = pd.concat([claims, bad_claim], ignore_index=True)

    valid_policy_ids = set(policies["policy_id"].dropna())

    invalid_claims = test_claims[
        test_claims["policy_id"].isna()
        | ~test_claims["policy_id"].isin(valid_policy_ids)
    ]

    print(f"Claims tested: {len(test_claims)}")
    print(f"Invalid claims found: {len(invalid_claims)}")

    if invalid_claims.empty:
        print("TEST FAILED: Invalid claim was not detected.")
        raise SystemExit(1)

    print("TEST PASSED: Invalid claim was detected.")
    print(
        invalid_claims[["claim_id", "policy_id"]].to_string(
            index=False
        )
    )


if __name__ == "__main__":
    main()
