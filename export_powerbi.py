"""
export_powerbi.py
=================
Exports analysis results as CSV and Excel files ready to load
directly into Power BI Desktop or Tableau Public.

Run after analysis.py:
    python export_powerbi.py

Output files (all in outputs/):
    claims_flat.csv           ← Full denormalized dataset (Power BI main source)
    summary_by_state.csv      ← Query 1 results
    summary_by_diagnosis.csv  ← Query 2 results
    summary_by_provider.csv   ← Query 3 results
    summary_by_age.csv        ← Query 4 results
    summary_by_year.csv       ← Query 5 results
    claims_powerbi.xlsx       ← All tables in one Excel workbook (one sheet each)

HOW TO LOAD IN POWER BI DESKTOP:
    1. Open Power BI Desktop (free download from microsoft.com/en-us/power-bi)
    2. Home → Get Data → Text/CSV  → select claims_flat.csv
       OR: Home → Get Data → Excel → select claims_powerbi.xlsx
    3. Load all sheets as separate tables
    4. Build visuals using the fields panel on the right

HOW TO LOAD IN TABLEAU PUBLIC:
    1. Open Tableau Public (free from public.tableau.com)
    2. Connect → Text File → select claims_flat.csv
    3. Drag fields onto rows/columns to build views
"""

import sqlite3
import os
import pandas as pd

os.makedirs('outputs', exist_ok=True)

DB_PATH = 'data/claims.db'
if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        "Database not found. Run  python data/generate_data.py  first."
    )

conn = sqlite3.connect(DB_PATH)
print("Exporting data for Power BI and Tableau...\n")

# ── 1. Full flat table (best for Power BI data model) ─────────
flat = pd.read_sql_query("""
SELECT
    c.claim_id,
    c.drg_code,
    c.drg_description,
    c.diagnosis_category,
    c.total_discharges,
    c.avg_covered_charges,
    c.avg_total_payments,
    c.avg_medicare_payment,
    ROUND(c.avg_covered_charges - c.avg_medicare_payment, 2) AS cost_gap,
    ROUND(
        100.0 * c.readmitted_30day / c.total_discharges, 2
    )                                                        AS readmission_rate_pct,
    c.readmitted_30day,
    c.patient_age_group,
    c.discharge_year,
    p.provider_id,
    p.provider_name,
    p.state,
    p.provider_type,
    p.bed_count
FROM claims c
JOIN providers p ON c.provider_id = p.provider_id
ORDER BY c.claim_id
""", conn)

# ── 2. Summary tables (pre-aggregated for quick visuals) ──────
by_state = pd.read_sql_query("""
SELECT
    p.state,
    COUNT(DISTINCT c.claim_id)                              AS total_claims,
    SUM(c.total_discharges)                                 AS total_patients,
    SUM(c.readmitted_30day)                                 AS total_readmissions,
    ROUND(
        100.0 * SUM(c.readmitted_30day) / SUM(c.total_discharges), 2
    )                                                       AS readmission_rate_pct,
    ROUND(AVG(c.avg_covered_charges), 2)                    AS avg_billed,
    ROUND(AVG(c.avg_medicare_payment), 2)                   AS avg_medicare_paid,
    ROUND(AVG(c.avg_total_payments), 2)                     AS avg_total_payment
FROM claims c
JOIN providers p ON c.provider_id = p.provider_id
GROUP BY p.state
ORDER BY readmission_rate_pct DESC
""", conn)

by_diagnosis = pd.read_sql_query("""
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
ORDER BY avg_billed DESC
""", conn)

by_provider = pd.read_sql_query("""
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
ORDER BY avg_charges DESC
""", conn)

by_age = pd.read_sql_query("""
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
ORDER BY readmit_rate_pct DESC
""", conn)

by_year = pd.read_sql_query("""
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
ORDER BY discharge_year
""", conn)

conn.close()

# ── Save CSVs ─────────────────────────────────────────────────
exports = {
    'outputs/claims_flat.csv':          flat,
    'outputs/summary_by_state.csv':     by_state,
    'outputs/summary_by_diagnosis.csv': by_diagnosis,
    'outputs/summary_by_provider.csv':  by_provider,
    'outputs/summary_by_age.csv':       by_age,
    'outputs/summary_by_year.csv':      by_year,
}
for path, df in exports.items():
    df.to_csv(path, index=False)
    print(f"  ✓ {path}  ({len(df):,} rows)")

# ── Save Excel workbook (all sheets in one file) ──────────────
xlsx_path = 'outputs/claims_powerbi.xlsx'
with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
    flat.to_excel(         writer, sheet_name='Claims_Flat',       index=False)
    by_state.to_excel(     writer, sheet_name='By_State',          index=False)
    by_diagnosis.to_excel( writer, sheet_name='By_Diagnosis',      index=False)
    by_provider.to_excel(  writer, sheet_name='By_Provider_Type',  index=False)
    by_age.to_excel(       writer, sheet_name='By_Age_Group',      index=False)
    by_year.to_excel(      writer, sheet_name='By_Year',           index=False)

print(f"\n  ✓ {xlsx_path}  (6 sheets — load directly into Power BI or Tableau)\n")
print("=" * 60)
print("Power BI quick-start:")
print("  1. Open Power BI Desktop")
print("  2. Home → Get Data → Excel → claims_powerbi.xlsx")
print("  3. Select all 6 sheets → Load")
print("  4. Use Claims_Flat as your main table for custom visuals")
print("\nTableau quick-start:")
print("  1. Open Tableau Public")
print("  2. Connect → Text File → claims_flat.csv")
print("  3. Drag 'State' to columns, 'Readmission Rate Pct' to rows")
print("=" * 60)
