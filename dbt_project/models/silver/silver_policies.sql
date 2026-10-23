
{{
    config(
        materialized='incremental',
        unique_key='POLICY_ID',
        incremental_strategy='merge'
    )
}}

WITH source_policies AS (
    SELECT *
    FROM {{ ref('bronze_policies') }}

    {% if is_incremental() %}
    WHERE DBT_LOADED_AT >= (
        SELECT DATEADD(
            day,
            -3,
            COALESCE(
                MAX(DBT_LOADED_AT),
                '1900-01-01'::TIMESTAMP_NTZ
            )
        )
        FROM {{ this }}
    )
    {% endif %}
),

ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY POLICY_ID
            ORDER BY UPDATED_AT DESC NULLS LAST,
                     DBT_LOADED_AT DESC NULLS LAST
        ) AS ROW_NUM
    FROM source_policies
    WHERE POLICY_ID IS NOT NULL
),

deduplicated AS (
    SELECT
        POLICY_ID,
        POLICYHOLDER_ID,
        AGENT_ID,
        TRIM(POLICY_TYPE) AS POLICY_TYPE,
        PREMIUM_AMOUNT,
        TRIM(POLICY_STATUS) AS POLICY_STATUS,
        EFFECTIVE_DATE,
        UPDATED_AT,
        DBT_LOADED_AT
    FROM ranked
    WHERE ROW_NUM = 1
)

SELECT p.*
FROM deduplicated p
INNER JOIN {{ ref('silver_policyholders') }} h
    ON p.POLICYHOLDER_ID = h.POLICYHOLDER_ID
