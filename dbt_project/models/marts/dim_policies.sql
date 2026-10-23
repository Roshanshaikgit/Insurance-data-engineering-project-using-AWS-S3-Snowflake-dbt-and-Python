{{ config(materialized='table') }}

SELECT
    {{ dbt_utils.generate_surrogate_key([
        'POLICY_ID'
    ]) }} AS POLICY_SK,

    POLICY_ID,
    POLICYHOLDER_ID,
    AGENT_ID,
    POLICY_TYPE,
    PREMIUM_AMOUNT,
    POLICY_STATUS,
    EFFECTIVE_DATE,
    UPDATED_AT

FROM {{ ref('silver_policies') }}

WHERE POLICY_ID IS NOT NULL

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY POLICY_ID
    ORDER BY UPDATED_AT DESC NULLS LAST,
             DBT_LOADED_AT DESC NULLS LAST
) = 1