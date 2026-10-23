
{{
    config(
        materialized='incremental',
        unique_key='CLAIM_ID',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}

{% set lookback_days = var('claims_lookback_days', 3) | int %}

WITH source_claims AS (

    SELECT
        CLAIM_ID,
        POLICY_ID,
        CAST(NULL AS VARCHAR) AS POLICYHOLDER_ID,
        CLAIM_AMOUNT,
        CLAIM_STATUS,
        CLAIM_DATE,
        UPDATED_AT,
        DBT_LOADED_AT
    FROM {{ ref('bronze_claims') }}

    {% if is_incremental() %}
    WHERE DBT_LOADED_AT >= (
        SELECT DATEADD(
            day,
            -{{ lookback_days }},
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
            PARTITION BY CLAIM_ID
            ORDER BY
                UPDATED_AT DESC NULLS LAST,
                DBT_LOADED_AT DESC NULLS LAST
        ) AS ROW_NUM
    FROM source_claims
    WHERE CLAIM_ID IS NOT NULL
),

deduplicated AS (

    SELECT
        CLAIM_ID,
        POLICY_ID,
        POLICYHOLDER_ID,
        CLAIM_AMOUNT,
        CLAIM_STATUS,
        CLAIM_DATE,
        UPDATED_AT,
        DBT_LOADED_AT
    FROM ranked
    WHERE ROW_NUM = 1
)

SELECT c.*
FROM deduplicated c
INNER JOIN {{ ref('silver_policies') }} p
    ON c.POLICY_ID = p.POLICY_ID
