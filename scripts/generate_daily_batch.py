#!/usr/bin/env python3
"""Generate a daily insurance batch from the latest earlier batch template.

Creates five date-scoped CSV files and a CDC sidecar. Existing batches are
never overwritten. Manifest generation remains a separate step.
"""
import argparse
import csv
from datetime import date, datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BATCH_ROOT = PROJECT_ROOT / "data" / "daily_batches"

DATASETS = ("agents", "policyholders", "policies", "claims", "payments")
EXPECTED_ROWS = {
    "agents": 50,
    "policyholders": 500,
    "policies": 1000,
    "claims": 1500,
    "payments": 2000,
}
ID_INFO = {
    "agents": ("agent_id", "AG", 4),
    "policyholders": ("policyholder_id", "PH", 5),
    "policies": ("policy_id", "POL", 5),
    "claims": ("claim_id", "CLM", 5),
    "payments": ("payment_id", "PAY", 5),
}


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path, headers, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def find_template(batch_id):
    if not BATCH_ROOT.is_dir():
        raise SystemExit(f"ERROR: Daily batch directory not found: {BATCH_ROOT}")
    candidates = sorted(
        (p for p in BATCH_ROOT.iterdir()
         if p.is_dir() and p.name.isdigit() and p.name < batch_id),
        key=lambda p: p.name,
        reverse=True,
    )
    for folder in candidates:
        if all((folder / f"{name}.csv").is_file() for name in DATASETS):
            return folder
    raise SystemExit(
        f"ERROR: No earlier batch with all five CSV files found under {BATCH_ROOT}"
    )


def make_id(prefix, batch_id, number, width):
    return f"{prefix}{batch_id}{number:0{width}d}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a daily insurance batch and CDC sidecar."
    )
    parser.add_argument("--date", help="Batch date in YYYY-MM-DD format")
    parser.add_argument("--batch-id", help="Batch ID in YYYYMMDD format")
    args = parser.parse_args()

    if not args.date and not args.batch_id:
        parser.error("provide --date YYYY-MM-DD or --batch-id YYYYMMDD")

    if args.date:
        try:
            batch_date = date.fromisoformat(args.date)
        except ValueError:
            parser.error("--date must use YYYY-MM-DD")
        batch_id = batch_date.strftime("%Y%m%d")
    else:
        batch_id = args.batch_id
        try:
            batch_date = datetime.strptime(batch_id, "%Y%m%d").date()
        except ValueError:
            parser.error("--batch-id must use YYYYMMDD")

    out_dir = BATCH_ROOT / batch_id
    if out_dir.exists():
        raise SystemExit(
            f"ERROR: Batch directory already exists; refusing to overwrite: {out_dir}"
        )

    template_dir = find_template(batch_id)
    data = {}
    for name in DATASETS:
        headers, rows = read_csv(template_dir / f"{name}.csv")
        if len(rows) != EXPECTED_ROWS[name]:
            raise SystemExit(
                f"ERROR: {template_dir / (name + '.csv')} has {len(rows)} rows; "
                f"expected {EXPECTED_ROWS[name]}. No files were written."
            )
        data[name] = (headers, rows)

    # Build maps so every foreign key continues to point at a row in this batch.
    id_maps = {}
    for name in ("agents", "policyholders", "policies", "claims", "payments"):
        id_col, prefix, width = ID_INFO[name]
        headers, rows = data[name]
        if id_col not in headers:
            raise SystemExit(f"ERROR: Expected column '{id_col}' in {name}.csv")
        id_maps[name] = {
            row[id_col]: make_id(prefix, batch_id, i, width)
            for i, row in enumerate(rows, start=1)
        }

    # Determine one timestamp for the new batch.
    batch_timestamp = datetime.combine(
        batch_date, datetime.min.time(), tzinfo=timezone.utc
    ).isoformat(timespec="seconds")

    generated = {}
    for name in DATASETS:
        headers, source_rows = data[name]
        rows = []
        id_col = ID_INFO[name][0]
        for old in source_rows:
            row = dict(old)
            row[id_col] = id_maps[name][old[id_col]]
            if "updated_at" in headers:
                row["updated_at"] = batch_timestamp

            # Remap relationships to the new batch's IDs.
            if name == "policies":
                if "policyholder_id" in row:
                    row["policyholder_id"] = id_maps["policyholders"].get(
                        old.get("policyholder_id"), row["policyholder_id"]
                    )
                if "agent_id" in row:
                    row["agent_id"] = id_maps["agents"].get(
                        old.get("agent_id"), row["agent_id"]
                    )
                if "effective_date" in row and row["effective_date"]:
                    row["effective_date"] = batch_date.isoformat()
            elif name in ("claims", "payments"):
                if "policy_id" in row:
                    row["policy_id"] = id_maps["policies"].get(
                        old.get("policy_id"), row["policy_id"]
                    )
                date_col = "claim_date" if name == "claims" else "payment_date"
                if date_col in row and row[date_col]:
                    row[date_col] = batch_date.isoformat()

            rows.append(row)
        generated[name] = (headers, rows)

    # Write only after all source data and relationships have been validated.
    out_dir.mkdir(parents=True)
    try:
        for name in DATASETS:
            headers, rows = generated[name]
            write_csv(out_dir / f"{name}.csv", headers, rows)

        # CDC is deliberately separate from the five-file daily manifest.
        policy_headers, policy_rows = data["policies"]
        if not policy_rows:
            raise SystemExit("ERROR: Template policies.csv has no rows.")
        prior_policy = policy_rows[0]
        prior_policy_id = prior_policy["policy_id"]
        previous_status = prior_policy.get("policy_status", "")
        statuses = ("Active", "Renewed", "Pending")
        new_status = next(
            (status for status in statuses if status.lower() != previous_status.lower()),
            "Renewed",
        )
        cdc_dir = out_dir / "cdc"
        cdc_dir.mkdir()
        cdc_headers = [
            "event_id", "policy_id", "policy_status", "operation",
            "source_updated_at",
        ]
        cdc_row = {
            "event_id": f"EVT-{batch_id}-{prior_policy_id}",
            "policy_id": prior_policy_id,
            "policy_status": new_status,
            "operation": "UPDATE",
            "source_updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        write_csv(cdc_dir / "policy_cdc_events.csv", cdc_headers, [cdc_row])
    except Exception:
        # Avoid leaving a seemingly complete batch if writing fails part-way.
        import shutil
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

    total = sum(len(generated[name][1]) for name in DATASETS)
    print(f"SUCCESS: Generated batch {batch_id} using template {template_dir.name}")
    print(f"Output: {out_dir}")
    print("Files:")
    for name in DATASETS:
        print(f"  {name}.csv: {len(generated[name][1])} rows")
    print(f"  cdc/policy_cdc_events.csv: 1 CDC event (separate workflow)")
    print(f"Total daily-batch rows: {total}")
    print("Next: run scripts\\create_batch_manifest.py --batch-id " + batch_id)


if __name__ == "__main__":
    main()
