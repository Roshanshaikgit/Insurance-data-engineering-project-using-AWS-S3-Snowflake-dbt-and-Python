SELECT
    "payment_id"::VARCHAR AS payment_id,
    "policy_id"::VARCHAR AS policy_id,
    "payment_amount"::NUMBER(12,2) AS payment_amount,
    "payment_date"::DATE AS payment_date,
    TRIM("payment_status") AS payment_status,
    "updated_at"::TIMESTAMP_NTZ AS updated_at,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS dbt_loaded_at
FROM INSURANCE_DB.RAW.RAW_PAYMENTS
WHERE "payment_id" IS NOT NULL