SELECT
    "claim_id"::VARCHAR AS claim_id,
    "policy_id"::VARCHAR AS policy_id,
    "claim_amount"::NUMBER(12,2) AS claim_amount,
    TRIM("claim_status") AS claim_status,
    "claim_date"::DATE AS claim_date,
    "updated_at"::TIMESTAMP_NTZ AS updated_at,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS dbt_loaded_at
FROM INSURANCE_DB.RAW.RAW_CLAIMS
WHERE "claim_id" IS NOT NULL