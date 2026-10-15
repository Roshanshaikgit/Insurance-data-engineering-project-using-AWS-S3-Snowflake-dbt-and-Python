\# Insurance Data Dictionary



All data in this project is fictional.



\## 1. Policies



| Column | Expected type | Purpose |

|---|---|---|

| policy\_id | String | Unique policy identifier |

| policyholder\_id | String | Policyholder reference |

| agent\_id | String | Agent reference |

| policy\_type | String | Insurance product type |

| premium\_amount | Decimal | Premium amount |

| policy\_status | String | Current policy status |

| effective\_date | Date | Policy effective date |

| updated\_at | Timestamp | Source modification timestamp |



\## 2. Policyholders



| Column | Expected type | Purpose |

|---|---|---|

| policyholder\_id | String | Unique policyholder identifier |

| full\_name | String | Fictional customer name |

| city | String | Customer city |

| email | String | Fictional email |

| updated\_at | Timestamp | Source modification timestamp |



\## 3. Claims



| Column | Expected type | Purpose |

|---|---|---|

| claim\_id | String | Unique claim identifier |

| policy\_id | String | Related policy |

| claim\_amount | Decimal | Claimed amount |

| claim\_status | String | Claim processing status |

| claim\_date | Date | Claim submission date |

| updated\_at | Timestamp | Source modification timestamp |



\## 4. Agents



| Column | Expected type | Purpose |

|---|---|---|

| agent\_id | String | Unique agent identifier |

| agent\_name | String | Fictional agent name |

| region | String | Assigned business region |

| updated\_at | Timestamp | Source modification timestamp |



\## 5. Payments



| Column | Expected type | Purpose |

|---|---|---|

| payment\_id | String | Unique payment identifier |

| policy\_id | String | Related policy |

| payment\_amount | Decimal | Payment amount |

| payment\_date | Date | Payment date |

| payment\_status | String | Payment processing status |

| updated\_at | Timestamp | Source modification timestamp |



\## General Rules



\- Identifiers are treated as strings to preserve leading zeros.

\- Monetary amounts must be numeric and validated against business rules.

\- Dates and timestamps must be parseable.

\- Required identifiers must not be null or blank.

\- Source modification timestamps are useful for incremental processing but are not guaranteed to capture every change.

\- New or changed columns must follow a controlled schema-change process.

\- Referential integrity must be validated before publishing trusted reporting data.

