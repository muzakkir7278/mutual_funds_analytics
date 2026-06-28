import os
import re
import sqlite3
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
REPORTS_DIR = Path("reports")
SQL_DIR = Path("sql")
DB_PATH = Path("bluestock_mf.db")

PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
SQL_DIR.mkdir(parents=True, exist_ok=True)

RAW_FILES = [
    "01_fund_master.csv",
    "02_nav_history.csv",
    "03_aum_by_fund_house.csv",
    "04_monthly_sip_inflows.csv",
    "05_category_inflows.csv",
    "06_industry_folio_count.csv",
    "07_scheme_performance.csv",
    "08_investor_transactions.csv",
    "09_portfolio_holdings.csv",
    "10_benchmark_indices.csv",
]


def clean_col_name(col: str) -> str:
    col = str(col).strip().lower()
    col = re.sub(r"[%]", "percent", col)
    col = re.sub(r"[^0-9a-zA-Z]+", "_", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [clean_col_name(c) for c in df.columns]
    return df


def convert_dates_and_numbers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        lower_col = col.lower()
        if "date" in lower_col or "month" in lower_col:
            df[col] = pd.to_datetime(df[col], errors="coerce")
        if any(word in lower_col for word in [
            "nav", "aum", "amount", "value", "return", "ratio", "expense", "folio", "count", "inflow", "sip"
        ]):
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


def clean_nav_history(df: pd.DataFrame) -> pd.DataFrame:
    df = convert_dates_and_numbers(df)
    nav_cols = [c for c in df.columns if "nav" in c]
    for col in nav_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[(df[col].isna()) | (df[col] > 0)]
    df = df.drop_duplicates()
    if "amfi_code" in df.columns and "date" in df.columns:
        df = df.sort_values(["amfi_code", "date"])
        for col in nav_cols:
            df[col] = df.groupby("amfi_code")[col].ffill()
    return df


def clean_investor_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df = convert_dates_and_numbers(df)
    if "transaction_type" in df.columns:
        df["transaction_type"] = (
            df["transaction_type"].astype(str).str.strip().str.lower().replace({
                "sip": "SIP",
                "lumpsum": "Lumpsum",
                "lump_sum": "Lumpsum",
                "lump sum": "Lumpsum",
                "redemption": "Redemption",
            })
        )
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df[df["amount"] > 0]
    if "kyc_status" in df.columns:
        df["kyc_status"] = df["kyc_status"].astype(str).str.strip().str.title()
    return df.drop_duplicates()


def clean_scheme_performance(df: pd.DataFrame) -> pd.DataFrame:
    df = convert_dates_and_numbers(df)
    if "expense_ratio" in df.columns:
        df["expense_ratio"] = pd.to_numeric(df["expense_ratio"], errors="coerce")
        df = df[(df["expense_ratio"].isna()) | ((df["expense_ratio"] >= 0.1) & (df["expense_ratio"] <= 2.5))]
    return df.drop_duplicates()


def clean_one_file(file_name: str) -> pd.DataFrame:
    source_path = RAW_DIR / file_name
    if not source_path.exists():
        raise FileNotFoundError(f"Missing raw file: {source_path}")

    df = pd.read_csv(source_path)
    df = clean_column_names(df)

    if file_name == "02_nav_history.csv":
        df = clean_nav_history(df)
    elif file_name == "08_investor_transactions.csv":
        df = clean_investor_transactions(df)
    elif file_name == "07_scheme_performance.csv":
        df = clean_scheme_performance(df)
    else:
        df = convert_dates_and_numbers(df).drop_duplicates()

    output_path = PROCESSED_DIR / f"clean_{file_name}"
    df.to_csv(output_path, index=False)
    return df


def create_schema_sql() -> None:
    schema = """-- Day 2 SQLite Star Schema
-- Mutual Fund Analytics Project

DROP TABLE IF EXISTS dim_fund;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_aum;

CREATE TABLE dim_fund (
    amfi_code INTEGER PRIMARY KEY,
    scheme_name TEXT,
    fund_house TEXT,
    category TEXT,
    sub_category TEXT,
    risk_grade TEXT
);

CREATE TABLE dim_date (
    date_id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT UNIQUE,
    year INTEGER,
    month INTEGER,
    quarter INTEGER
);

CREATE TABLE fact_nav (
    nav_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER,
    date TEXT,
    nav REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE fact_transactions (
    transaction_id TEXT PRIMARY KEY,
    amfi_code INTEGER,
    investor_id TEXT,
    transaction_type TEXT,
    transaction_date TEXT,
    amount REAL,
    state TEXT,
    kyc_status TEXT,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE fact_performance (
    performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    amfi_code INTEGER,
    return_1y REAL,
    return_3y REAL,
    return_5y REAL,
    expense_ratio REAL,
    FOREIGN KEY (amfi_code) REFERENCES dim_fund(amfi_code)
);

CREATE TABLE fact_aum (
    aum_id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_house TEXT,
    date TEXT,
    aum REAL
);
"""
    (SQL_DIR / "schema.sql").write_text(schema, encoding="utf-8")


def create_queries_sql() -> None:
    queries = """-- Day 2 Analytical SQL Queries

-- 1. Top 5 funds/fund houses by AUM
SELECT * FROM clean_03_aum_by_fund_house LIMIT 5;

-- 2. Average NAV per month
SELECT amfi_code, strftime('%Y-%m', date) AS month, AVG(nav) AS avg_nav
FROM clean_02_nav_history
GROUP BY amfi_code, strftime('%Y-%m', date)
ORDER BY month;

-- 3. SIP YoY growth / trend
SELECT * FROM clean_04_monthly_sip_inflows ORDER BY 1;

-- 4. Transactions by state
SELECT state, COUNT(*) AS transaction_count, SUM(amount) AS total_amount
FROM clean_08_investor_transactions
GROUP BY state
ORDER BY total_amount DESC;

-- 5. Funds with expense_ratio less than 1 percent
SELECT * FROM clean_07_scheme_performance WHERE expense_ratio < 1;

-- 6. Transaction summary by type
SELECT transaction_type, COUNT(*) AS transaction_count, SUM(amount) AS total_amount, AVG(amount) AS average_amount
FROM clean_08_investor_transactions
GROUP BY transaction_type;

-- 7. KYC status summary
SELECT kyc_status, COUNT(*) AS investor_count
FROM clean_08_investor_transactions
GROUP BY kyc_status;

-- 8. NAV records by scheme
SELECT amfi_code, COUNT(*) AS nav_records
FROM clean_02_nav_history
GROUP BY amfi_code
ORDER BY nav_records DESC;

-- 9. Top schemes by 1-year return
SELECT * FROM clean_07_scheme_performance ORDER BY return_1y DESC LIMIT 10;

-- 10. Sample portfolio holdings
SELECT * FROM clean_09_portfolio_holdings LIMIT 20;
"""
    (SQL_DIR / "queries.sql").write_text(queries, encoding="utf-8")


def load_cleaned_csvs_to_sqlite() -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{DB_PATH}")
    rows = []
    for csv_path in sorted(PROCESSED_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path)
        table_name = csv_path.stem
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        rows.append({"table_name": table_name, "row_count": len(df), "column_count": len(df.columns)})
    summary = pd.DataFrame(rows)
    summary.to_csv(REPORTS_DIR / "sqlite_row_count_summary.csv", index=False)
    return summary


def create_data_dictionary() -> None:
    rows = []
    for csv_path in sorted(PROCESSED_DIR.glob("*.csv")):
        df = pd.read_csv(csv_path)
        for col in df.columns:
            rows.append({
                "dataset": csv_path.name,
                "column_name": col,
                "data_type": str(df[col].dtype),
                "business_definition": "Column used for mutual fund analytics, reporting, and SQL analysis.",
                "source_reference": csv_path.name.replace("clean_", ""),
            })
    dictionary = pd.DataFrame(rows)
    dictionary.to_csv(REPORTS_DIR / "data_dictionary.csv", index=False)

    with open(REPORTS_DIR / "data_dictionary.md", "w", encoding="utf-8") as f:
        f.write("# Data Dictionary\n\n")
        f.write("| Dataset | Column Name | Data Type | Business Definition | Source Reference |\n")
        f.write("|---|---|---|---|---|\n")
        for row in rows:
            f.write(f"| {row['dataset']} | {row['column_name']} | {row['data_type']} | {row['business_definition']} | {row['source_reference']} |\n")


def verify_sqlite_tables() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [x[0] for x in cur.fetchall()]
    conn.close()
    return tables


def main() -> None:
    print("DAY 2: DATA CLEANING + SQL DATABASE DESIGN")
    print("Checking raw CSV files...")
    for file_name in RAW_FILES:
        print(f"- {file_name}")
        clean_one_file(file_name)

    print("Creating sql/schema.sql...")
    create_schema_sql()
    print("Creating sql/queries.sql...")
    create_queries_sql()
    print("Loading cleaned CSVs to bluestock_mf.db...")
    summary = load_cleaned_csvs_to_sqlite()
    print("Creating reports/data_dictionary.md...")
    create_data_dictionary()

    print("\nSQLite tables:")
    for table in verify_sqlite_tables():
        print("-", table)

    print("\nRow count summary:")
    print(summary.to_string(index=False))

    print("\nDAY 2 COMPLETED SUCCESSFULLY")
    print("Generated deliverables:")
    print("- data/processed/clean_*.csv")
    print("- bluestock_mf.db")
    print("- sql/schema.sql")
    print("- sql/queries.sql")
    print("- reports/data_dictionary.md")
    print("- reports/sqlite_row_count_summary.csv")


if __name__ == "__main__":
    main()
