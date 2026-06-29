"""
analysis.py
===========
Runs all SQL queries against data/claims.db and produces
the 4-panel dashboard saved to outputs/cms_dashboard.png.

Run order:
    1. python data/generate_data.py     (creates the database)
    2. python analysis.py               (runs queries + builds dashboard)
    3. python export_powerbi.py         (exports CSVs for Power BI / Tableau)
"""

import sqlite3
import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

os.makedirs('outputs', exist_ok=True)

# ── Connect ───────────────────────────────────────────────────
DB_PATH = 'data/claims.db'
if not os.path.exists(DB_PATH):
    raise FileNotFoundError(
        "Database not found. Run  python data/generate_data.py  first."
    )
conn = sqlite3.connect(DB_PATH)

print("=" * 60)
print("PROJECT 1: CMS Medicare Healthcare Claims Analysis")
print("=" * 60)
print("\n[1] Running SQL queries...\n")

# ── Query 1: Readmission rate by state ───────────────────────
q1 = """
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
ORDER BY readmission_rate_pct DESC
"""
df_q1 = pd.read_sql_query(q1, conn)
print("── QUERY 1: 30-Day Readmission Rates by State ──")
print(df_q1.to_string(index=False))

# ── Query 2: Cost drivers by diagnosis ───────────────────────
q2 = """
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
"""
df_q2 = pd.read_sql_query(q2, conn)
print("\n── QUERY 2: Cost Drivers by Diagnosis Category ──")
print(df_q2.to_string(index=False))

# ── Query 3: Provider type performance ───────────────────────
q3 = """
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
"""
df_q3 = pd.read_sql_query(q3, conn)
print("\n── QUERY 3: Performance by Provider Type ──")
print(df_q3.to_string(index=False))

# ── Query 4: Age group readmission analysis ───────────────────
q4 = """
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
"""
df_q4 = pd.read_sql_query(q4, conn)
print("\n── QUERY 4: Readmissions by Patient Age Group ──")
print(df_q4.to_string(index=False))

# ── Query 5: Year-over-year trends ───────────────────────────
q5 = """
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
"""
df_q5 = pd.read_sql_query(q5, conn)
print("\n── QUERY 5: Year-over-Year Trends ──")
print(df_q5.to_string(index=False))

conn.close()

# ── Dashboard ─────────────────────────────────────────────────
print("\n[2] Generating dashboard...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    'CMS Medicare Claims Analysis Dashboard',
    fontsize=16, fontweight='bold', y=0.98
)

# Chart 1: Readmission rates by state
ax1 = axes[0, 0]
df_q1_sorted = df_q1.sort_values('readmission_rate_pct', ascending=True)
bars = ax1.barh(
    df_q1_sorted['state'],
    df_q1_sorted['readmission_rate_pct'],
    color=sns.color_palette('coolwarm', len(df_q1_sorted))
)
ax1.set_xlabel('30-Day Readmission Rate (%)')
ax1.set_title('Readmission Rates by State', fontweight='bold')
mean_rate = df_q1['readmission_rate_pct'].mean()
ax1.axvline(mean_rate, color='red', linestyle='--', alpha=0.7,
            label=f'Mean: {mean_rate:.1f}%')
ax1.legend(fontsize=8)
for bar, val in zip(bars, df_q1_sorted['readmission_rate_pct']):
    ax1.text(bar.get_width() + 0.1,
             bar.get_y() + bar.get_height() / 2,
             f'{val:.1f}%', va='center', fontsize=8)

# Chart 2: Billed vs Medicare paid by diagnosis
ax2 = axes[0, 1]
df_q2_sorted = df_q2.sort_values('avg_billed', ascending=False)
x     = range(len(df_q2_sorted))
width = 0.35
ax2.bar([i - width/2 for i in x], df_q2_sorted['avg_billed'],
        width, label='Avg Billed', color='steelblue', alpha=0.8)
ax2.bar([i + width/2 for i in x], df_q2_sorted['avg_medicare_paid'],
        width, label='Avg Medicare Paid', color='coral', alpha=0.8)
ax2.set_xticks(list(x))
ax2.set_xticklabels(
    df_q2_sorted['diagnosis_category'], rotation=35, ha='right', fontsize=8
)
ax2.set_ylabel('Amount (USD)')
ax2.set_title('Billed vs Medicare Paid by Diagnosis', fontweight='bold')
ax2.legend(fontsize=8)
ax2.yaxis.set_major_formatter(
    plt.FuncFormatter(lambda v, _: f'${v/1000:.0f}K')
)

# Chart 3: Readmission rate by provider type
ax3 = axes[1, 0]
colors = ['#2196F3', '#4CAF50', '#FF9800', '#9C27B0']
bars3 = ax3.bar(
    df_q3['provider_type'], df_q3['readmit_rate_pct'],
    color=colors[:len(df_q3)], alpha=0.85,
    edgecolor='white', linewidth=1.5
)
ax3.set_ylabel('30-Day Readmission Rate (%)')
ax3.set_title('Readmission Rate by Provider Type', fontweight='bold')
ax3.set_xticklabels(df_q3['provider_type'], rotation=20, ha='right', fontsize=9)
for bar, val in zip(bars3, df_q3['readmit_rate_pct']):
    ax3.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.1,
        f'{val:.1f}%', ha='center', fontsize=9, fontweight='bold'
    )

# Chart 4: Age group distribution + readmission (pie)
ax4 = axes[1, 1]
age_colors = ['#1565C0', '#1976D2', '#42A5F5']
wedges, texts, autotexts = ax4.pie(
    df_q4['total_patients'],
    labels=[
        f"{r['patient_age_group']}\n({r['readmit_rate_pct']}% readmit)"
        for _, r in df_q4.iterrows()
    ],
    colors=age_colors,
    autopct='%1.1f%%',
    startangle=90,
    pctdistance=0.75
)
for t in texts:     t.set_fontsize(9)
for a in autotexts: a.set_fontsize(8)
ax4.set_title(
    'Patient Distribution & Readmission\nRates by Age Group',
    fontweight='bold'
)

plt.tight_layout()
out = 'outputs/cms_dashboard.png'
plt.savefig(out, dpi=150, bbox_inches='tight')
plt.close()
print(f"   ✓ Dashboard saved: {out}")

# ── Key findings ──────────────────────────────────────────────
print("\n" + "=" * 60)
print("KEY FINDINGS")
print("=" * 60)

top_state = df_q1.loc[df_q1['readmission_rate_pct'].idxmax()]
top_diag  = df_q2.loc[df_q2['avg_billed'].idxmax()]
best_prov = df_q3.loc[df_q3['readmit_rate_pct'].idxmin()]
top_year  = df_q5.loc[df_q5['total_payments_M'].idxmax()]

print(f"""
1. READMISSION HOTSPOT
   {top_state['state']} — highest 30-day readmission rate at {top_state['readmission_rate_pct']}%
   → Above the {mean_rate:.1f}% mean; signals need for post-discharge care improvement

2. HIGHEST-COST DIAGNOSIS
   {top_diag['diagnosis_category']} — avg billed ${top_diag['avg_billed']:,.0f}
   Medicare paid only ${top_diag['avg_medicare_paid']:,.0f} → gap of ${top_diag['avg_cost_gap']:,.0f}

3. BEST PROVIDER TYPE (lowest readmissions)
   {best_prov['provider_type']} — {best_prov['readmit_rate_pct']}% readmission rate
   → Potential model for care coordination best practices

4. YEAR-OVER-YEAR
   Peak payment year: {int(top_year['discharge_year'])} at ${top_year['total_payments_M']}M total Medicare payments
""")

print("=" * 60)
print("✓ Analysis complete.")
print("  Next: python export_powerbi.py  →  outputs/  (CSV + Excel for Power BI/Tableau)")
print("=" * 60)
