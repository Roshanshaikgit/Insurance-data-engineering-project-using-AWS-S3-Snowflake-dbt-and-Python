SELECT
    "agent_id"::VARCHAR AS agent_id,
    TRIM("agent_name") AS agent_name,
    TRIM("region") AS region,
    "updated_at"::TIMESTAMP_NTZ AS updated_at,
    CURRENT_TIMESTAMP()::TIMESTAMP_NTZ AS dbt_loaded_at
FROM INSURANCE_DB.RAW.RAW_AGENTS
WHERE "agent_id" IS NOT NULL