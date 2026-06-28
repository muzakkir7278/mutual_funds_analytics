# Capstone Project 1 - Mutual Fund Analytics

## DAY 1 - Project Setup + Data Ingestion (ETL)

This project folder was created based on the Day 1 task shown in the uploaded screenshot.

### Folder Structure

```text
mutual_fund_analytics_day1/
├── data/
│   ├── raw/           # 10 provided CSV datasets
│   └── processed/     # cleaned/transformed outputs
├── notebooks/         # Jupyter notebooks
├── sql/               # SQL scripts
├── dashboard/         # dashboard files
├── reports/           # reports and data quality summary
├── scripts/           # helper scripts
├── data_ingestion.py
├── live_nav_fetch.py
├── requirements.txt
└── README.md
```

### Uploaded Raw Datasets

| File | Rows | Columns | Nulls | Duplicate Rows |
|---|---:|---:|---:|---:|
| 01_fund_master.csv | 40 | 15 | 0 | 0 |
| 02_nav_history.csv | 46000 | 3 | 0 | 0 |
| 03_aum_by_fund_house.csv | 90 | 5 | 0 | 0 |
| 04_monthly_sip_inflows.csv | 48 | 6 | 12 | 0 |
| 05_category_inflows.csv | 144 | 3 | 0 | 0 |
| 06_industry_folio_count.csv | 21 | 6 | 0 | 0 |
| 07_scheme_performance.csv | 40 | 19 | 0 | 0 |
| 08_investor_transactions.csv | 32778 | 13 | 0 | 0 |
| 09_portfolio_holdings.csv | 322 | 8 | 0 | 0 |
| 10_benchmark_indices.csv | 8050 | 3 | 0 | 0 |

### AMFI Code Validation

Validated fund_master.amfi_code against nav_history.amfi_code. Missing codes count: 0.

### How to Run

```bash
cd mutual_fund_analytics_day1
python -m venv venv
# Windows PowerShell
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python data_ingestion.py
python live_nav_fetch.py
```

### Day 1 Git Commit Message

```bash
git init
git add .
git commit -m "Day 1: Data ingestion complete"
```
