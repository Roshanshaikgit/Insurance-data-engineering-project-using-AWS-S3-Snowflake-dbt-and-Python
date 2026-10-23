{{ config(materialized='table') }}

SELECT
    p.POLICY_ID,
    p.POLICYHOLDER_ID,
    ph.FULL_NAME AS POLICYHOLDER_NAME,
    ph.CITY AS POLICYHOLDER_CITY,
    p.AGENT_ID,
    a.AGENT_NAME,
    a.REGION AS AGENT_REGION,
    p.POLICY_TYPE,
    p.PREMIUM_AMOUNT,
    p.POLICY_STATUS,
    p.EFFECTIVE_DATE,
    p.UPDATED_AT
FROM {{ ref('silver_policies') }} p
LEFT JOIN {{ ref('silver_policyholders') }} ph
    ON p.POLICYHOLDER_ID = ph.POLICYHOLDER_ID
LEFT JOIN {{ ref('silver_agents') }} a
    ON p.AGENT_ID = a.AGENT_ID