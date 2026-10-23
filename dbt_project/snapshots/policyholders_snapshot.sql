
{% snapshot policyholders_snapshot %}

{{
    config(
        target_schema='SILVER',
        unique_key='POLICYHOLDER_ID',
        strategy='timestamp',
        updated_at='UPDATED_AT',
        invalidate_hard_deletes=True
    )
}}

SELECT
    POLICYHOLDER_ID,
    FULL_NAME,
    CITY,
    EMAIL,
    UPDATED_AT
FROM {{ ref('bronze_policyholders') }}
WHERE POLICYHOLDER_ID IS NOT NULL

UNION ALL

SELECT
    POLICYHOLDER_ID,
    FULL_NAME,
    CITY,
    EMAIL,
    SOURCE_UPDATED_AT AS UPDATED_AT
FROM INSURANCE_DB.BACKFILL_LAB.SYNTHETIC_POLICYHOLDER_HISTORY
WHERE POLICYHOLDER_ID IS NOT NULL
  AND TEST_DATA_FLAG = TRUE
  AND POLICYHOLDER_ID NOT IN (
      SELECT POLICYHOLDER_ID
      FROM {{ ref('bronze_policyholders') }}
  )

{% endsnapshot %}
