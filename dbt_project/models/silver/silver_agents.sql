
{{
    config(
        materialized='incremental',
        unique_key='AGENT_ID',
        incremental_strategy='merge'
    )
}}

WITH source_agents AS (
    SELECT *
    FROM {{ ref('bronze_agents') }}

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
            PARTITION BY AGENT_ID
            ORDER BY UPDATED_AT DESC NULLS LAST,
                     DBT_LOADED_AT DESC
        ) AS ROW_NUM
    FROM source_agents
    WHERE AGENT_ID IS NOT NULL
)

SELECT
    AGENT_ID,
    TRIM(AGENT_NAME) AS AGENT_NAME,
    TRIM(REGION) AS REGION,
    UPDATED_AT,
    DBT_LOADED_AT
FROM ranked
WHERE ROW_NUM = 1
