\# Insurance Data Platform — Source Data Contract



\*\*Contract version:\*\* 1.0  

\*\*Status:\*\* Draft — Learning Project  

\*\*Target:\*\* AWS S3 → Snowflake RAW → Bronze → Silver → Gold



\## 1. Source delivery



\- Proposed frequency: Daily.

\- Proposed delivery pattern: Incremental extracts.

\- Delivery location: AWS S3.

\- Datasets: Policyholders, Policies, Claims, Agents, Payments.

\- A batch must be identified by a unique batch ID.



\## 2. Record identification



| Dataset | Candidate business key |

|---|---|

| Policyholders | policyholder\_id |

| Policies | policy\_id |

| Claims | claim\_id |

| Agents | agent\_id |

| Payments | payment\_id |



The source team must confirm key uniqueness and stability.



\## 3. Change handling



\- Updated records must be applied.

\- Record ordering and late-arriving changes require confirmation.

\- Delete representation is not yet defined.

\- Missing records in an incremental file must not be treated as deletions.



\## 4. Completeness and reconciliation



\- Verify all required files have arrived.

\- Validate file format and required columns.

\- Capture parsed and loaded row counts.

\- Compare against authoritative source controls when available.

\- Record batch-level outcomes in the ingestion audit table.

\- Block downstream processing when mandatory controls fail.



\## 5. Schema changes



\- Compare incoming schemas with approved contracts.

\- Detect unexpected or missing columns and type changes.

\- Do not silently accept breaking changes.

\- Require validation and approval before changing the approved contract.



\## 6. Open decisions



\- Confirm actual delivery frequency.

\- Confirm full after-image versus partial-update records.

\- Confirm update ordering and tie-breaking rules.

\- Confirm deletion behavior.

\- Confirm source-side batch metadata and reconciliation controls.

\- Confirm late-arrival, replay, and correction behavior.



\*\*Important:\*\* This document records proposed learning-project decisions. It does not represent a signed contract with an actual source-system owner.

