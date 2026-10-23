SELECT
    "policy_id"::VARCHAR AS policy_id,
    "policyholder_id"::VARCHAR AS policyholder_id,
    "agent_id"::VARCHAR AS agent_id,
    TRIM("policy_type") AS policy_type,
    "premium_amount"::NUMBER(12,2) AS premium_amount,
    TRIM("policy_status") AS policy_status,
    "effective_date"::DATE AS effective_date,
    "updated_at"::TIMESTAMP_NTZ AS updated_at,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS dbt_loaded_at
FROM INSURANCE_DB.RAW.RAW_POLICIES
WHERE "policy_id" IS NOT NULL