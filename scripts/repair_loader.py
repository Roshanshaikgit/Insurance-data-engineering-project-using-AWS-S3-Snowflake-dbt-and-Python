from pathlib import Path
import re
import csv

p = Path("scripts/load_daily_batch.py")
s = p.read_text(encoding="utf-8-sig")

# Add required imports.
if "import csv" not in s:
    s = s.replace("import argparse", "import argparse\nimport csv", 1)

if "from pathlib import Path" not in s:
    s = s.replace(
        "from datetime import datetime, timezone",
        "from datetime import datetime, timezone\nfrom pathlib import Path",
        1,
    )

# Remove the obsolete one-row manifest function.
s, n = re.subn(
    r"def register_manifest\(cursor, batch_id\):.*?"
    r"(?=def register_manifest\(cursor, batch_id, expected_counts\):)",
    "",
    s,
    count=1,
    flags=re.S,
)
if n != 1:
    raise SystemExit("STOP: Could not identify the obsolete manifest function.")

# Add CSV row-count calculation.
if "def expected_row_counts(batch_id):" not in s:
    marker = "def register_manifest(cursor, batch_id, expected_counts):"
    helper = '''def expected_row_counts(batch_id):
    """Count data rows in each locally generated batch CSV."""
    batch_dir = Path(__file__).resolve().parent.parent / "data" / "daily_batches" / batch_id
    counts = {}

    for name in DATASETS:
        file_path = batch_dir / f"{name}.csv"
        if not file_path.is_file():
            raise FileNotFoundError(
                f"Missing local batch CSV: {file_path}. "
                "Generate the batch before loading it."
            )

        with file_path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            next(reader, None)
            counts[name] = sum(1 for row in reader if row)

        if counts[name] < 1:
            raise ValueError(f"No data rows found in {file_path}")

    return counts


'''
    if marker not in s:
        raise SystemExit("STOP: New manifest function not found.")
    s = s.replace(marker, helper + marker, 1)

# Restore/add manifest validation.
if "def validate_manifest(" not in s:
    marker = "def already_succeeded(cursor, batch_id, dataset):"
    validator = '''def validate_manifest(cursor, batch_id, expected_counts):
    cursor.execute(
        f"""
        SELECT DATASET_NAME, EXPECTED_FILE, EXPECTED_ROWS, IS_REQUIRED
        FROM {DATABASE}.{SCHEMA}.SOURCE_BATCH_MANIFEST
        WHERE BATCH_ID = %s
        """,
        (batch_id,),
    )

    manifest = {
        str(row[0]).lower(): row
        for row in cursor.fetchall()
    }
    errors = []

    for name in DATASETS:
        entry = manifest.get(name)
        if entry is None:
            errors.append(f"Missing manifest entry for {name}")
            continue

        if entry[1] != f"{name}.csv":
            errors.append(f"{name}: incorrect expected filename {entry[1]}")

        if int(entry[2]) != expected_counts[name]:
            errors.append(
                f"{name}: manifest expects {entry[2]} rows; "
                f"local CSV contains {expected_counts[name]}"
            )

        if not entry[3]:
            errors.append(f"{name}: IS_REQUIRED must be TRUE")

    if errors:
        raise RuntimeError("Manifest validation failed: " + "; ".join(errors))

    print(f"Manifest validation passed: {len(DATASETS)} datasets.")


'''
    if marker not in s:
        raise SystemExit("STOP: Cannot find insertion point for manifest validation.")
    s = s.replace(marker, validator + marker, 1)

# Make the loader use the expected count for each dataset.
s = s.replace(
    "def load_one_dataset(cursor, batch_id, name, config, available_files):",
    "def load_one_dataset(cursor, batch_id, name, config, available_files, expected_rows):",
    1,
)

start = s.find("def load_one_dataset(")
end = s.find("\ndef main(", start)
if start < 0 or end < 0:
    raise SystemExit("STOP: Could not isolate load_one_dataset().")

part = s[start:end]
part = part.replace("expected_rows=1", "expected_rows=expected_rows")
part = part.replace(
    "if rows_loaded != 1:",
    "if rows_loaded != expected_rows:",
)
part = part.replace(
    'f"Expected 1 loaded row but Snowflake reported {rows_loaded}"',
    'f"Expected {expected_rows} loaded rows but Snowflake reported {rows_loaded}"',
)
s = s[:start] + part + s[end:]

# Calculate counts and pass them through main().
s = s.replace(
    'print(f"\\nRegistering manifest for {batch_id}...")\n'
    "            register_manifest(cursor, batch_id)\n"
    "            validate_manifest(cursor, batch_id)",
    'expected_counts = expected_row_counts(batch_id)\n'
    '            print(f"\\nRegistering manifest for {batch_id}...")\n'
    "            register_manifest(cursor, batch_id, expected_counts)\n"
    "            validate_manifest(cursor, batch_id, expected_counts)",
    1,
)

s = s.replace(
    "cursor, batch_id, name, config, available_files\n"
    "                )",
    "cursor, batch_id, name, config, available_files, expected_counts[name]\n"
    "                )",
    1,
)

# Confirm the repaired signatures and calls before writing.
required = [
    "def expected_row_counts(batch_id):",
    "def register_manifest(cursor, batch_id, expected_counts):",
    "def validate_manifest(cursor, batch_id, expected_counts):",
    "rows_parsed = sum(int(row[2] or 0) for row in results)",
    "rows_loaded = sum(int(row[3] or 0) for row in results)",
    "if rows_loaded != expected_rows:",
    "register_manifest(cursor, batch_id, expected_counts)",
    "validate_manifest(cursor, batch_id, expected_counts)",
    "expected_counts[name]",
]
missing = [item for item in required if item not in s]
if missing:
    raise SystemExit("STOP: Repair checks failed: " + repr(missing))

if len(re.findall(r"^def register_manifest\(", s, re.M)) != 1:
    raise SystemExit("STOP: Manifest function count is not exactly one.")

backup = p.with_suffix(".py.bak")
if not backup.exists():
    raise SystemExit("STOP: Original backup is missing; refusing to modify the file.")

p.write_text(s, encoding="utf-8")
print("Loader repair applied successfully.")
print("Backup preserved at:", backup)
print("Next: run a syntax check before running any ingestion.")
