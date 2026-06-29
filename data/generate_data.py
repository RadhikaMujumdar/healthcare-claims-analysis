"""
generate_data.py
================
Generates synthetic CMS Medicare-style claims data and saves
it to a SQLite database at data/claims.db.

Run this FIRST before anything else:
    python data/generate_data.py

Structure mirrors real CMS Medicare Provider Utilization data:
    https://data.cms.gov/provider-summary-by-type-of-service
"""

import sqlite3
import random
import os
import pandas as pd
import numpy as np

random.seed(42)
np.random.seed(42)

# ── Reference data ────────────────────────────────────────────
STATES = ['MA', 'NY', 'CA', 'TX', 'FL', 'IL', 'PA', 'OH', 'GA', 'NC']

PROVIDER_TYPES = [
    'General Acute Care',
    'Teaching Hospital',
    'Critical Access',
    'Specialty'
]

# (drg_code, description, diagnosis_category, base_charge, base_pay)
DRG_DATA = [
    ('470', 'Major Joint Replacement',  'Musculoskeletal',   15000, 12000),
    ('871', 'Septicemia w MCC',         'Infectious',        45000, 38000),
    ('291', 'Heart Failure w MCC',      'Cardiovascular',    35000, 28000),
    ('392', 'Esophagitis/GI',           'Gastrointestinal',  12000,  9000),
    ('641', 'Nutritional Disorders',    'Metabolic',         18000, 14000),
    ('193', 'COPD w MCC',               'Respiratory',       28000, 22000),
    ('247', 'Coronary Bypass w Cath',   'Cardiovascular',    85000, 68000),
    ('682', 'Renal Failure w MCC',      'Renal',             32000, 25000),
    ('312', 'Syncope & Collapse',       'Neurological',      14000, 11000),
    ('189', 'Pulmonary Edema',          'Respiratory',       22000, 17000),
]

AGE_GROUPS = ['65-74', '75-84', '85+']
YEARS      = [2021, 2022, 2023]

# ── Generate providers ────────────────────────────────────────
providers = []
for i in range(50):
    pid   = f'P{i+1:04d}'
    state = random.choice(STATES)
    ptype = random.choice(PROVIDER_TYPES)
    beds  = random.randint(50, 800)
    providers.append((pid, f'Hospital {i+1} - {state}', state, ptype, beds))

# ── Generate claims ───────────────────────────────────────────
claims = []
for i in range(1000):
    provider   = random.choice(providers)
    pid, _, _, ptype, _ = provider
    drg        = random.choice(DRG_DATA)
    discharges = random.randint(10, 300)

    multiplier = 1.3 if ptype == 'Teaching Hospital' else 1.0
    charges    = round(drg[3] * multiplier * random.uniform(0.8, 1.4), 2)
    payments   = round(drg[4] * multiplier * random.uniform(0.75, 1.2), 2)
    medicare   = round(payments * random.uniform(0.75, 0.90), 2)

    read_rate  = 0.20 if drg[2] in ['Cardiovascular', 'Infectious'] else 0.10
    readmit    = int(discharges * read_rate * random.uniform(0.5, 1.5))

    claims.append((
        f'C{i+1:05d}', pid,
        drg[0], drg[1], drg[2],
        discharges, charges, payments, medicare,
        readmit,
        random.choice(AGE_GROUPS),
        random.choice(YEARS)
    ))

# ── Write to SQLite ───────────────────────────────────────────
os.makedirs('data', exist_ok=True)
db_path = 'data/claims.db'
conn    = sqlite3.connect(db_path)
cur     = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS providers;
DROP TABLE IF EXISTS claims;

CREATE TABLE providers (
    provider_id    TEXT PRIMARY KEY,
    provider_name  TEXT,
    state          TEXT,
    provider_type  TEXT,
    bed_count      INTEGER
);

CREATE TABLE claims (
    claim_id              TEXT PRIMARY KEY,
    provider_id           TEXT,
    drg_code              TEXT,
    drg_description       TEXT,
    diagnosis_category    TEXT,
    total_discharges      INTEGER,
    avg_covered_charges   REAL,
    avg_total_payments    REAL,
    avg_medicare_payment  REAL,
    readmitted_30day      INTEGER,
    patient_age_group     TEXT,
    discharge_year        INTEGER,
    FOREIGN KEY (provider_id) REFERENCES providers(provider_id)
);
""")

cur.executemany("INSERT INTO providers VALUES (?,?,?,?,?)", providers)
cur.executemany("INSERT INTO claims   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", claims)
conn.commit()
conn.close()

print(f"Database created: {db_path}")
print(f"  Providers : 50")
print(f"  Claims    : 1,000")
