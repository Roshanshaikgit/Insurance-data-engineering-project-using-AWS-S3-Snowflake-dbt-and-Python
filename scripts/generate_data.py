
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "generated"


def generate_policyholders():
    return pd.DataFrame(
        [
            {
                "policyholder_id": "PH0001",
                "full_name": "Aarav Sharma",
                "city": "Hyderabad",
                "email": "aarav@example.com",
                "updated_at": "2026-10-14 09:30:00",
            },
            {
                "policyholder_id": "PH0002",
                "full_name": "Maya Reddy",
                "city": "Bengaluru",
                "email": "maya@example.com",
                "updated_at": "2026-10-14 10:15:00",
            },
            {
                "policyholder_id": "PH0003",
                "full_name": "Daniel Thomas",
                "city": "Chennai",
                "email": "daniel@example.com",
                "updated_at": "2026-10-14 11:45:00",
            },
        ]
    )


def generate_agents():
    return pd.DataFrame(
        [
            {
                "agent_id": "AG0001",
                "agent_name": "Priya Nair",
                "region": "South",
                "updated_at": "2026-10-14 08:00:00",
            },
            {
                "agent_id": "AG0002",
                "agent_name": "Rahul Mehta",
                "region": "West",
                "updated_at": "2026-10-14 08:30:00",
            },
            {
                "agent_id": "AG0003",
                "agent_name": "Sara Khan",
                "region": "North",
                "updated_at": "2026-10-14 09:00:00",
            },
        ]
    )


def generate_policies():
    return pd.DataFrame(
        [
            {
                "policy_id": "PL0001",
                "policyholder_id": "PH0001",
                "agent_id": "AG0001",
                "policy_type": "Health",
                "premium_amount": 12500.00,
                "policy_status": "Active",
                "effective_date": "2026-01-01",
                "updated_at": "2026-10-14 12:00:00",
            },
            {
                "policy_id": "PL0002",
                "policyholder_id": "PH0002",
                "agent_id": "AG0002",
                "policy_type": "Auto",
                "premium_amount": 8400.00,
                "policy_status": "Active",
                "effective_date": "2026-03-15",
                "updated_at": "2026-10-14 12:30:00",
            },
            {
                "policy_id": "PL0003",
                "policyholder_id": "PH0001",
                "agent_id": "AG0003",
                "policy_type": "Life",
                "premium_amount": 18000.00,
                "policy_status": "Pending",
                "effective_date": "2026-06-01",
                "updated_at": "2026-10-14 13:00:00",
            },
        ]
    )


def generate_claims():
    return pd.DataFrame(
        [
            {
                "claim_id": "CL0001",
                "policy_id": "PL0001",
                "claim_amount": 25000.00,
                "claim_status": "Submitted",
                "claim_date": "2026-10-01",
                "updated_at": "2026-10-14 14:00:00",
            },
            {
                "claim_id": "CL0002",
                "policy_id": "PL0001",
                "claim_amount": 7500.00,
                "claim_status": "Approved",
                "claim_date": "2026-09-20",
                "updated_at": "2026-10-14 14:15:00",
            },
            {
                "claim_id": "CL0003",
                "policy_id": "PL0002",
                "claim_amount": 12000.00,
                "claim_status": "Under Review",
                "claim_date": "2026-10-05",
                "updated_at": "2026-10-14 14:30:00",
            },
        ]
    )


def generate_payments():
    return pd.DataFrame(
        [
            {
                "payment_id": "PM0001",
                "policy_id": "PL0001",
                "payment_amount": 12500.00,
                "payment_date": "2026-01-01",
                "payment_status": "Completed",
                "updated_at": "2026-10-14 15:00:00",
            },
            {
                "payment_id": "PM0002",
                "policy_id": "PL0002",
                "payment_amount": 8400.00,
                "payment_date": "2026-03-15",
                "payment_status": "Completed",
                "updated_at": "2026-10-14 15:15:00",
            },
            {
                "payment_id": "PM0003",
                "policy_id": "PL0003",
                "payment_amount": 18000.00,
                "payment_date": "2026-06-01",
                "payment_status": "Pending",
                "updated_at": "2026-10-14 15:30:00",
            },
        ]
    )


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "policyholders": generate_policyholders(),
        "agents": generate_agents(),
        "policies": generate_policies(),
        "claims": generate_claims(),
        "payments": generate_payments(),
    }

    for name, dataframe in datasets.items():
        output_file = OUTPUT_DIR / f"{name}.csv"
        dataframe.to_csv(output_file, index=False)
        print(f"Created {output_file.name}: {len(dataframe)} rows")

    print("All five insurance datasets generated successfully.")


if __name__ == "__main__":
    main()
