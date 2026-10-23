
{{ config(materialized='table') }}


WITH historical_versions AS (

    SELECT
        {{ dbt_utils.generate_surrogate_key([
            'POLICYHOLDER_ID',
            'DBT_VALID_FROM'
        ]) }} AS POLICYHOLDER_SK,

        POLICYHOLDER_ID,
        FULL_NAME,
        CITY,
        EMAIL,
        DBT_VALID_FROM AS VALID_FROM,
        DBT_VALID_TO AS VALID_TO,
        DBT_VALID_TO IS NULL AS IS_CURRENT

    FROM {{ ref('policyholders_snapshot') }}
    WHERE POLICYHOLDER_ID IS NOT NULL


),

unknown_member AS (

    SELECT
        {{ dbt_utils.generate_surrogate_key([
            "'UNKNOWN'",
            "'UNKNOWN'"
        ]) }} AS POLICYHOLDER_SK,

        'UNKNOWN' AS POLICYHOLDER_ID,
        'Unknown' AS FULL_NAME,
        'Unknown' AS CITY,
        CAST(NULL AS VARCHAR) AS EMAIL,
        TO_TIMESTAMP_NTZ('1900-01-01 00:00:00') AS VALID_FROM,
        CAST(NULL AS TIMESTAMP_NTZ) AS VALID_TO,
        FALSE AS IS_CURRENT

)

SELECT * FROM historical_versions

UNION ALL

SELECT * FROM unknown_member
