
{{
    config(
        materialized='incremental',
        unique_key='PAYMENT_ID',
        incremental_strategy='merge'
    )
}}

WITH source_payments AS (
    SELECT *
    FROM {{ ref('bronze_payments') }}

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
            PARTITION BY PAYMENT_ID
            ORDER BY UPDATED_AT DESC NULLS LAST,
                     DBT_LOADED_AT DESC
        ) AS ROW_NUM
    FROM source_payments
    WHERE PAYMENT_ID IS NOT NULL
),

deduplicated AS (
    SELECT
        PAYMENT_ID,
        POLICY_ID,
        PAYMENT_AMOUNT,
        PAYMENT_DATE,
        PAYMENT_STATUS,
        UPDATED_AT,
        DBT_LOADED_AT
    FROM ranked
    WHERE ROW_NUM = 1
)

SELECT pay.*
FROM deduplicated pay
INNER JOIN {{ ref('silver_policies') }} p
    ON pay.POLICY_ID = p.POLICY_ID
