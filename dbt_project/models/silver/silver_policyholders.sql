
{{
    config(
        materialized='incremental',
        unique_key='POLICYHOLDER_ID',
        incremental_strategy='merge'
    )
}}

WITH source_policyholders AS (
    SELECT *
    FROM {{ ref('bronze_policyholders') }}

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
        POLICYHOLDER_ID,
        FULL_NAME,
        CITY,
        EMAIL,
        UPDATED_AT,
        DBT_LOADED_AT,
        ROW_NUMBER() OVER (
            PARTITION BY POLICYHOLDER_ID
            ORDER BY UPDATED_AT DESC NULLS LAST,
                     DBT_LOADED_AT DESC
        ) AS ROW_NUM
    FROM source_policyholders
    WHERE POLICYHOLDER_ID IS NOT NULL
)

SELECT
    POLICYHOLDER_ID,
    TRIM(FULL_NAME) AS FULL_NAME,
    TRIM(CITY) AS CITY,
    LOWER(TRIM(EMAIL)) AS EMAIL,
    UPDATED_AT,
    DBT_LOADED_AT
FROM ranked
WHERE ROW_NUM = 1
