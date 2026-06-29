-- ================================================================
-- Healthcare Claims SQL Analysis
-- Radhika Mujumdar | Portfolio Project
-- ================================================================
-- Database : data/claims.db  (SQLite)
-- Tables   : claims, providers
-- Run via  : analysis.py  (queries are embedded there too)
--            or any SQLite client pointed at data/claims.db
-- ================================================================


-- ----------------------------------------------------------------
-- QUERY 1: 30-Day Readmission Rate by State
-- Purpose : Identify geographic hotspots with high readmission rates
-- Insight : Ohio had the highest rate at 14.1% — above the 12.5% mean
-- ----------------------------------------------------------------
SELECT
    p.state,
    COUNT(DISTINCT c.claim_id)                              AS total_claims,
    SUM(c.total_discharges)                                 AS total_patients,
    SUM(c.readmitted_30day)                                 AS total_readmissions,
    ROUND(
        100.0 * SUM(c.readmitted_30day) / SUM(c.total_discharges), 2
    )                                                       AS readmission_rate_pct,
    ROUND(AVG(c.avg_total_payments), 2)                     AS avg_payment
FROM claims c
JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.state
ORDER BY readmission_rate_pct DESC;


-- ----------------------------------------------------------------
-- QUERY 2: Cost Drivers by Diagnosis Category
-- Purpose : Rank diagnosis categories by average billed charge
-- Insight : Cardiovascular highest at ~$68K avg billed;
--           large gap between billed and Medicare paid in all categories
-- ----------------------------------------------------------------
SELECT
    diagnosis_category,
    SUM(total_discharges)                                   AS total_patients,
    ROUND(AVG(avg_covered_charges), 2)                      AS avg_billed,
    ROUND(AVG(avg_medicare_payment), 2)                     AS avg_medicare_paid,
    ROUND(AVG(avg_covered_charges)
          - AVG(avg_medicare_payment), 2)                   AS avg_cost_gap,
    ROUND(
        100.0 * SUM(readmitted_30day) / SUM(total_discharges), 2
    )                                                       AS readmit_rate_pct
FROM claims
GROUP BY diagnosis_category
ORDER BY avg_billed DESC;


-- ----------------------------------------------------------------
-- QUERY 3: Performance by Provider Type
-- Purpose : Compare readmission rates and costs across provider types
-- Insight : Specialty hospitals had highest readmission rate (13.2%);
--           Teaching hospitals billed most on average
-- ----------------------------------------------------------------
SELECT
    p.provider_type,
    COUNT(DISTINCT p.provider_id)                           AS num_providers,
    SUM(c.total_discharges)                                 AS total_patients,
    ROUND(AVG(c.avg_covered_charges), 2)                    AS avg_charges,
    ROUND(AVG(c.avg_medicare_payment), 2)                   AS avg_medicare,
    ROUND(
        100.0 * SUM(c.readmitted_30day) / SUM(c.total_discharges), 2
    )                                                       AS readmit_rate_pct
FROM claims c
JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.provider_type
ORDER BY avg_charges DESC;


-- ----------------------------------------------------------------
-- QUERY 4: Readmission Rate by Patient Age Group
-- Purpose : Identify which age groups are most vulnerable
-- Insight : 85+ patients had highest readmission rate and avg cost
-- ----------------------------------------------------------------
SELECT
    patient_age_group,
    SUM(total_discharges)                                   AS total_patients,
    SUM(readmitted_30day)                                   AS readmissions,
    ROUND(
        100.0 * SUM(readmitted_30day) / SUM(total_discharges), 2
    )                                                       AS readmit_rate_pct,
    ROUND(AVG(avg_total_payments), 2)                       AS avg_payment
FROM claims
GROUP BY patient_age_group
ORDER BY readmit_rate_pct DESC;


-- ----------------------------------------------------------------
-- QUERY 5: Year-over-Year Payment Trends (2021–2023)
-- Purpose : Track Medicare payment trends and readmission rates over time
-- Insight : Payment volumes and readmission rates shifted year over year
-- ----------------------------------------------------------------
SELECT
    discharge_year,
    SUM(total_discharges)                                   AS total_patients,
    ROUND(SUM(avg_total_payments * total_discharges) / 1e6, 2)
                                                            AS total_payments_M,
    ROUND(AVG(avg_medicare_payment), 2)                     AS avg_medicare_payment,
    ROUND(
        100.0 * SUM(readmitted_30day) / SUM(total_discharges), 2
    )                                                       AS readmit_rate_pct
FROM claims
GROUP BY discharge_year
ORDER BY discharge_year;


-- ----------------------------------------------------------------
-- QUERY 6: Top 10 Highest-Cost Providers
-- Purpose : Provider-level benchmarking for cost outlier detection
-- ----------------------------------------------------------------
SELECT
    c.provider_id,
    p.provider_name,
    p.state,
    p.provider_type,
    COUNT(DISTINCT c.claim_id)                              AS total_claims,
    SUM(c.total_discharges)                                 AS total_patients,
    ROUND(AVG(c.avg_covered_charges), 2)                    AS avg_billed,
    ROUND(
        100.0 * SUM(c.readmitted_30day) / SUM(c.total_discharges), 2
    )                                                       AS readmit_rate_pct
FROM claims c
JOIN providers p ON c.provider_id = p.provider_id
GROUP BY c.provider_id
ORDER BY avg_billed DESC
LIMIT 10;
