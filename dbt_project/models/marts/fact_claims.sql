
{{
    config(
        materialized='incremental',
        unique_key='CLAIM_ID',
        incremental_strategy='merge'
    )
}}

{% set backfill_start_date = var('backfill_start_date', none) %}

WITH claims AS (
    SELECT
        CLAIM_ID,
        POLICY_ID,
        POLICYHOLDER_ID,
        CLAIM_AMOUNT,
        CLAIM_STATUS,
        CLAIM_DATE,
        UPDATED_AT,
        DBT_LOADED_AT
    FROM {{ ref('silver_claims') }}
    WHERE CLAIM_ID IS NOT NULL

    {% if is_incremental() %}
        {% if backfill_start_date %}
            AND CLAIM_DATE >= TO_DATE('{{ backfill_start_date }}')
        {% else %}
            AND DBT_LOADED_AT >= (
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
    {% endif %}

    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY CLAIM_ID
        ORDER BY UPDATED_AT DESC NULLS LAST,
                 DBT_LOADED_AT DESC NULLS LAST
    ) = 1
),

claim_dimensions AS (
    SELECT
        c.CLAIM_ID,
        p.POLICY_SK,
        ph.POLICYHOLDER_SK,
        c.POLICY_ID,
        COALESCE(
            c.POLICYHOLDER_ID,
            p.POLICYHOLDER_ID
        ) AS POLICYHOLDER_ID,
        c.CLAIM_DATE,
        c.CLAIM_AMOUNT,
        c.CLAIM_STATUS,
        c.UPDATED_AT,
        c.DBT_LOADED_AT
    FROM claims c
    LEFT JOIN {{ ref('dim_policies') }} p
        ON c.POLICY_ID = p.POLICY_ID
    LEFT JOIN {{ ref('dim_policyholders') }} ph
        ON COALESCE(
            c.POLICYHOLDER_ID,
            p.POLICYHOLDER_ID
        ) = ph.POLICYHOLDER_ID
       AND c.CLAIM_DATE >= TO_DATE(ph.VALID_FROM)
       AND (
            c.CLAIM_DATE < TO_DATE(ph.VALID_TO)
            OR ph.VALID_TO IS NULL
       )
)

SELECT
    CLAIM_ID,
    POLICY_SK,
    POLICYHOLDER_SK,
    POLICY_ID,
    POLICYHOLDER_ID,
    CLAIM_DATE,
    CLAIM_AMOUNT,
    CLAIM_STATUS,
    UPDATED_AT,
    DBT_LOADED_AT
FROM claim_dimensions
