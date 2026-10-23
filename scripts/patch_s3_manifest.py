from pathlib import Path

path = Path("scripts/load_daily_batch.py")
source = path.read_text(encoding="utf-8")

if "def load_manifest_from_s3(" in source:
    raise SystemExit("S3 manifest function already exists; no changes made.")

anchor = "def register_manifest(cursor, batch_id, expected_counts):"
if anchor not in source:
    raise SystemExit("Could not find register_manifest. No changes made.")

function = r'''
def load_manifest_from_s3(cursor, batch_id):
    """Read and validate the batch manifest directly from the S3 stage."""
    manifest_path = f"{STAGE}/daily/{batch_id}/manifest.csv"

    cursor.execute(f"""
        SELECT
            $1::VARCHAR,
            LOWER(TRIM($2::VARCHAR)),
            TRIM($3::VARCHAR),
            TRY_TO_NUMBER(TRIM($4::VARCHAR))
        FROM {manifest_path}
        (FILE_FORMAT => (
            TYPE = 'CSV',
            SKIP_HEADER = 1,
            FIELD_OPTIONALLY_ENCLOSED_BY = '"'
        ))
    """)

    rows = cursor.fetchall()
    if not rows:
        raise RuntimeError(f"S3 manifest is empty: {manifest_path}")

    expected_counts = {}
    errors = []

    for row in rows:
        manifest_batch, name, filename, expected_rows = row

        if str(manifest_batch).strip() != batch_id:
            errors.append(f"Unexpected batch ID: {manifest_batch}")
            continue

        if name not in DATASETS:
            errors.append(f"Unexpected dataset: {name}")
            continue

        if filename != f"{name}.csv":
            errors.append(
                f"Unexpected filename for {name}: {filename}"
            )
            continue

        if expected_rows is None or int(expected_rows) < 0:
            errors.append(f"Invalid expected row count for {name}")
            continue

        if name in expected_counts:
            errors.append(f"Duplicate manifest entry: {name}")
            continue

        expected_counts[name] = int(expected_rows)

    missing = sorted(set(DATASETS) - set(expected_counts))
    if missing:
        errors.append(f"Missing datasets: {', '.join(missing)}")

    if errors:
        raise RuntimeError(
            "S3 manifest validation failed: " + "; ".join(errors)
        )

    print(f"S3 manifest validated for batch {batch_id}:")
    for name, count in expected_counts.items():
        print(f"  {name}: {count} expected rows")

    return expected_counts


'''

source = source.replace(anchor, function + anchor, 1)

old_call = "expected_counts = expected_row_counts(batch_id)"
new_call = "expected_counts = load_manifest_from_s3(cursor, batch_id)"

if source.count(old_call) != 1:
    raise SystemExit(
        "Expected exactly one main() manifest-count call; no changes saved."
    )

source = source.replace(old_call, new_call, 1)

path.write_text(source, encoding="utf-8")
print("Loader patched successfully. Existing loading and audit logic preserved.")
