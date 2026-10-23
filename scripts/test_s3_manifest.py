from scripts.load_daily_batch import connect_to_snowflake, load_manifest_from_s3

connection = connect_to_snowflake()
try:
    with connection.cursor() as cursor:
        counts = load_manifest_from_s3(cursor, "20261021")
        print("\nTotal expected rows:", sum(counts.values()))
finally:
    connection.close()
