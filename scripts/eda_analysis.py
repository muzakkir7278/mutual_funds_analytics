import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

DB_PATH = "bluestock_mf.db"
CHART_DIR = os.path.join("reports", "charts")
REPORT_DIR = "reports"

os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

def read_table(conn, table_name):
    return pd.read_sql_query("SELECT * FROM " + table_name, conn)

def save_fig(filename):
    path = os.path.join(CHART_DIR, filename)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()
    print("Saved:", path)

def first_existing_column(df, keywords):
    for col in df.columns:
        lower = col.lower()
        for word in keywords:
            if word in lower:
                return col
    return None

def numeric_columns(df):
    cols = []
    for col in df.columns:
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().sum() > 0:
            cols.append(col)
    return cols

def make_numeric(df, col):
    df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def main():
    print("DAY 3: Exploratory Data Analysis started")

    conn = sqlite3.connect(DB_PATH)

    tables = [
        "clean_01_fund_master",
        "clean_02_nav_history",
        "clean_03_aum_by_fund_house",
        "clean_04_monthly_sip_inflows",
        "clean_05_category_inflows",
        "clean_06_industry_folio_count",
        "clean_07_scheme_performance",
        "clean_08_investor_transactions",
        "clean_09_portfolio_holdings",
        "clean_10_benchmark_indices",
    ]

    data = {}
    for table in tables:
        try:
            data[table] = read_table(conn, table)
            print("Loaded:", table, data[table].shape)
        except Exception as e:
            print("Could not load", table, ":", e)

    findings = []

    nav = data.get("clean_02_nav_history")
    aum = data.get("clean_03_aum_by_fund_house")
    sip = data.get("clean_04_monthly_sip_inflows")
    category = data.get("clean_05_category_inflows")
    folio = data.get("clean_06_industry_folio_count")
    perf = data.get("clean_07_scheme_performance")
    tx = data.get("clean_08_investor_transactions")
    holdings = data.get("clean_09_portfolio_holdings")
    benchmark = data.get("clean_10_benchmark_indices")

    # 1 NAV trend selected schemes
    if nav is not None:
        date_col = first_existing_column(nav, ["date"])
        code_col = first_existing_column(nav, ["amfi", "scheme_code", "code"])
        nav_col = first_existing_column(nav, ["nav"])
        if date_col and code_col and nav_col:
            nav[date_col] = pd.to_datetime(nav[date_col], errors="coerce")
            nav = make_numeric(nav, nav_col)
            codes = nav[code_col].dropna().unique()[:10]
            plt.figure(figsize=(12, 6))
            for code in codes:
                temp = nav[nav[code_col] == code].sort_values(date_col)
                plt.plot(temp[date_col], temp[nav_col], label=str(code))
            plt.title("NAV Trend for Selected Schemes")
            plt.xlabel("Date")
            plt.ylabel("NAV")
            plt.legend(fontsize=7)
            save_fig("01_nav_trend_selected_schemes.png")
            findings.append("Selected scheme NAVs show visible long-term movement and short-term volatility.")

    # 2 Average NAV per month
    if nav is not None:
        date_col = first_existing_column(nav, ["date"])
        code_col = first_existing_column(nav, ["amfi", "scheme_code", "code"])
        nav_col = first_existing_column(nav, ["nav"])
        if date_col and code_col and nav_col:
            nav["month"] = pd.to_datetime(nav[date_col], errors="coerce").dt.to_period("M").astype(str)
            avg_nav = nav.groupby("month")[nav_col].mean()
            plt.figure(figsize=(12, 6))
            avg_nav.plot()
            plt.title("Average NAV per Month")
            plt.xlabel("Month")
            plt.ylabel("Average NAV")
            save_fig("02_average_nav_per_month.png")
            findings.append("Average monthly NAV helps identify broad trend direction across schemes.")

    # 3 Top fund houses by AUM
    if aum is not None:
        fund_col = first_existing_column(aum, ["fund_house", "fund house", "amc"])
        nums = numeric_columns(aum)
        if fund_col and nums:
            aum_col = nums[-1]
            aum = make_numeric(aum, aum_col)
            top = aum.groupby(fund_col)[aum_col].sum().sort_values(ascending=False).head(10)
            plt.figure(figsize=(12, 6))
            top.plot(kind="bar")
            plt.title("Top 10 Fund Houses by AUM")
            plt.xlabel("Fund House")
            plt.ylabel("AUM")
            save_fig("03_top_10_fund_houses_by_aum.png")
            findings.append("AUM is concentrated among the leading fund houses.")

    # 4 SIP monthly trend
    if sip is not None:
        date_col = first_existing_column(sip, ["month", "date"])
        nums = numeric_columns(sip)
        if date_col and nums:
            val_col = nums[-1]
            sip[date_col] = pd.to_datetime(sip[date_col], errors="coerce")
            sip = make_numeric(sip, val_col)
            sip_sorted = sip.sort_values(date_col)
            plt.figure(figsize=(12, 6))
            plt.plot(sip_sorted[date_col], sip_sorted[val_col])
            plt.title("Monthly SIP Inflow Trend")
            plt.xlabel("Month")
            plt.ylabel("SIP Inflow")
            save_fig("04_monthly_sip_inflow_trend.png")
            findings.append("Monthly SIP inflow trend indicates changing retail investor participation.")

    # 5 Category inflow bar chart
    if category is not None:
        cat_col = first_existing_column(category, ["category"])
        nums = numeric_columns(category)
        if cat_col and nums:
            val_col = nums[-1]
            category = make_numeric(category, val_col)
            top_cat = category.groupby(cat_col)[val_col].sum().sort_values(ascending=False)
            plt.figure(figsize=(12, 6))
            top_cat.plot(kind="bar")
            plt.title("Category-wise Net Inflows")
            plt.xlabel("Category")
            plt.ylabel("Net Inflow")
            save_fig("05_category_wise_net_inflows.png")
            findings.append("Category inflows show which fund categories attracted higher investor money.")

    # 6 Category inflow heatmap using matplotlib imshow
    if category is not None:
        cat_col = first_existing_column(category, ["category"])
        date_col = first_existing_column(category, ["month", "date"])
        nums = numeric_columns(category)
        if cat_col and date_col and nums:
            val_col = nums[-1]
            category[date_col] = pd.to_datetime(category[date_col], errors="coerce")
            category["month_label"] = category[date_col].dt.to_period("M").astype(str)
            category = make_numeric(category, val_col)
            pivot = category.pivot_table(index=cat_col, columns="month_label", values=val_col, aggfunc="sum").fillna(0)
            if pivot.shape[0] > 0 and pivot.shape[1] > 0:
                plt.figure(figsize=(14, 7))
                plt.imshow(pivot.values, aspect="auto")
                plt.colorbar(label="Net Inflow")
                plt.yticks(range(len(pivot.index)), pivot.index)
                plt.xticks(range(len(pivot.columns)), pivot.columns, rotation=90, fontsize=7)
                plt.title("Category Inflow Heatmap")
                save_fig("06_category_inflow_heatmap.png")
                findings.append("Category heatmap highlights strong and weak inflow months.")

    # 7 Transaction count by type
    if tx is not None:
        ttype = first_existing_column(tx, ["transaction_type", "type"])
        if ttype:
            plt.figure(figsize=(8, 5))
            tx[ttype].value_counts().plot(kind="bar")
            plt.title("Transaction Count by Type")
            plt.xlabel("Transaction Type")
            plt.ylabel("Count")
            save_fig("07_transaction_count_by_type.png")
            findings.append("Transaction type chart shows the mix of SIP, lumpsum, and redemption activity.")

    # 8 Transaction amount by type
    if tx is not None:
        ttype = first_existing_column(tx, ["transaction_type", "type"])
        amount = first_existing_column(tx, ["amount"])
        if ttype and amount:
            tx = make_numeric(tx, amount)
            plt.figure(figsize=(8, 5))
            tx.groupby(ttype)[amount].sum().plot(kind="bar")
            plt.title("Transaction Amount by Type")
            plt.xlabel("Transaction Type")
            plt.ylabel("Total Amount")
            save_fig("08_transaction_amount_by_type.png")
            findings.append("Transaction value by type shows which transaction type contributes most money.")

    # 9 State distribution
    if tx is not None:
        state = first_existing_column(tx, ["state"])
        amount = first_existing_column(tx, ["amount"])
        if state and amount:
            tx = make_numeric(tx, amount)
            top_state = tx.groupby(state)[amount].sum().sort_values(ascending=False).head(10)
            plt.figure(figsize=(10, 6))
            top_state.sort_values().plot(kind="barh")
            plt.title("Top 10 States by Transaction Amount")
            plt.xlabel("Total Amount")
            plt.ylabel("State")
            save_fig("09_top_states_by_transaction_amount.png")
            findings.append("Geographic distribution shows the states contributing the highest transaction value.")

    # 10 KYC status split
    if tx is not None:
        kyc = first_existing_column(tx, ["kyc"])
        if kyc:
            plt.figure(figsize=(7, 7))
            tx[kyc].value_counts().plot(kind="pie", autopct="%1.1f%%")
            plt.title("KYC Status Split")
            plt.ylabel("")
            save_fig("10_kyc_status_split.png")
            findings.append("KYC split shows investor compliance status distribution.")

    # 11 Age group distribution
    if tx is not None:
        age = first_existing_column(tx, ["age_group", "age"])
        if age:
            plt.figure(figsize=(8, 5))
            tx[age].value_counts().plot(kind="bar")
            plt.title("Age Group Distribution")
            plt.xlabel("Age Group")
            plt.ylabel("Investor Count")
            save_fig("11_age_group_distribution.png")
            findings.append("Age distribution shows which age segments are more active.")

    # 12 Amount boxplot by age group
    if tx is not None:
        age = first_existing_column(tx, ["age_group", "age"])
        amount = first_existing_column(tx, ["amount"])
        if age and amount:
            tx = make_numeric(tx, amount)
            groups = []
            labels = []
            for label, grp in tx.groupby(age):
                vals = grp[amount].dropna()
                if len(vals) > 0:
                    groups.append(vals)
                    labels.append(str(label))
            if groups:
                plt.figure(figsize=(10, 6))
                plt.boxplot(groups, labels=labels)
                plt.title("Transaction Amount Box Plot by Age Group")
                plt.xlabel("Age Group")
                plt.ylabel("Amount")
                save_fig("12_amount_boxplot_by_age_group.png")
                findings.append("Box plot identifies spread and outliers in transaction amount by age group.")

    # 13 Folio growth
    if folio is not None:
        date_col = first_existing_column(folio, ["month", "date"])
        nums = numeric_columns(folio)
        if date_col and nums:
            val_col = nums[-1]
            folio[date_col] = pd.to_datetime(folio[date_col], errors="coerce")
            folio = make_numeric(folio, val_col)
            folio_sorted = folio.sort_values(date_col)
            plt.figure(figsize=(12, 6))
            plt.plot(folio_sorted[date_col], folio_sorted[val_col])
            plt.title("Folio Count Growth")
            plt.xlabel("Date")
            plt.ylabel("Folio Count")
            save_fig("13_folio_count_growth.png")
            findings.append("Folio growth indicates expansion in investor participation over time.")

    # 14 Expense ratio distribution
    if perf is not None:
        exp = first_existing_column(perf, ["expense"])
        if exp:
            perf = make_numeric(perf, exp)
            plt.figure(figsize=(8, 5))
            perf[exp].dropna().plot(kind="hist", bins=20)
            plt.title("Expense Ratio Distribution")
            plt.xlabel("Expense Ratio")
            save_fig("14_expense_ratio_distribution.png")
            findings.append("Expense ratio distribution shows cost variation across schemes.")

    # 15 Average returns comparison
    if perf is not None:
        return_cols = [c for c in perf.columns if "return" in c.lower()]
        if return_cols:
            for col in return_cols:
                perf = make_numeric(perf, col)
            plt.figure(figsize=(10, 6))
            perf[return_cols].mean().plot(kind="bar")
            plt.title("Average Returns Comparison")
            plt.xlabel("Return Period")
            plt.ylabel("Average Return")
            save_fig("15_average_returns_comparison.png")
            findings.append("Average return comparison shows relative performance across return periods.")

    # 16 NAV return correlation
    if nav is not None:
        date_col = first_existing_column(nav, ["date"])
        code_col = first_existing_column(nav, ["amfi", "scheme_code", "code"])
        nav_col = first_existing_column(nav, ["nav"])
        if date_col and code_col and nav_col:
            pivot = nav.pivot_table(index=date_col, columns=code_col, values=nav_col)
            if pivot.shape[1] >= 2:
                returns = pivot.iloc[:, :10].pct_change()
                corr = returns.corr()
                plt.figure(figsize=(10, 8))
                plt.imshow(corr.values, aspect="auto")
                plt.colorbar(label="Correlation")
                plt.xticks(range(len(corr.columns)), corr.columns, rotation=90, fontsize=7)
                plt.yticks(range(len(corr.index)), corr.index, fontsize=7)
                plt.title("NAV Return Correlation Matrix")
                save_fig("16_nav_return_correlation_matrix.png")
                findings.append("Return correlation matrix shows how similarly selected schemes move.")

    # 17 Sector allocation
    if holdings is not None:
        sector = first_existing_column(holdings, ["sector"])
        weight = first_existing_column(holdings, ["weight", "allocation", "percentage", "percent"])
        if sector and weight:
            holdings = make_numeric(holdings, weight)
            sector_sum = holdings.groupby(sector)[weight].sum().sort_values(ascending=False).head(10)
            plt.figure(figsize=(8, 8))
            sector_sum.plot(kind="pie", autopct="%1.1f%%")
            plt.title("Top Sector Allocation")
            plt.ylabel("")
            save_fig("17_sector_allocation_donut.png")
            findings.append("Sector allocation chart shows equity exposure concentration by sector.")

    # 18 Benchmark trend
    if benchmark is not None:
        date_col = first_existing_column(benchmark, ["date"])
        nums = numeric_columns(benchmark)
        if date_col and nums:
            val_col = nums[-1]
            benchmark[date_col] = pd.to_datetime(benchmark[date_col], errors="coerce")
            benchmark = make_numeric(benchmark, val_col)
            benchmark_sorted = benchmark.sort_values(date_col)
            plt.figure(figsize=(12, 6))
            plt.plot(benchmark_sorted[date_col], benchmark_sorted[val_col])
            plt.title("Benchmark Index Trend")
            plt.xlabel("Date")
            plt.ylabel("Index Value")
            save_fig("18_benchmark_index_trend.png")
            findings.append("Benchmark trend provides market context for mutual fund performance.")

    # Write findings
    findings_path = os.path.join(REPORT_DIR, "eda_findings.md")
    with open(findings_path, "w", encoding="utf-8") as f:
        f.write("# Day 3 EDA Findings\n\n")
        for i, finding in enumerate(findings[:10], start=1):
            f.write(str(i) + ". " + finding + "\n")

    conn.close()

    print("\nDAY 3 EDA completed.")
    print("Charts saved in:", CHART_DIR)
    print("Findings saved in:", findings_path)
    print("Total charts attempted: 18")
    print("Charts generated depend on available columns in your datasets.")

if __name__ == "__main__":
    main()
