import os
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DB_PATH = "bluestock_mf.db"
REPORT_DIR = "reports"
CHART_DIR = os.path.join(REPORT_DIR, "charts")
RF_RATE = 0.065
TRADING_DAYS = 252

os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)

def load_table(conn, table_name):
    return pd.read_sql_query("SELECT * FROM " + table_name, conn)

def first_col(df, keywords):
    for col in df.columns:
        lower = col.lower()
        for word in keywords:
            if word in lower:
                return col
    return None

def calc_cagr(series, years):
    series = series.dropna()
    if len(series) < 2:
        return np.nan
    start = series.iloc[0]
    end = series.iloc[-1]
    if start <= 0 or end <= 0 or years <= 0:
        return np.nan
    return (end / start) ** (1 / years) - 1

def max_drawdown(nav_series):
    nav_series = nav_series.dropna()
    if len(nav_series) < 2:
        return np.nan
    running_max = nav_series.cummax()
    drawdown = nav_series / running_max - 1
    return drawdown.min()

def compute_alpha_beta(fund_returns, benchmark_returns):
    aligned = pd.concat([fund_returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 5:
        return np.nan, np.nan
    y = aligned.iloc[:, 0]
    x = aligned.iloc[:, 1]
    if x.var() == 0:
        return np.nan, np.nan
    beta = np.cov(x, y)[0, 1] / np.var(x)
    alpha_daily = y.mean() - beta * x.mean()
    alpha_annual = alpha_daily * TRADING_DAYS
    return alpha_annual, beta

def main():
    print("DAY 4: Fund Performance Analytics started")
    conn = sqlite3.connect(DB_PATH)

    nav = load_table(conn, "clean_02_nav_history")
    benchmark = load_table(conn, "clean_10_benchmark_indices")

    nav_date_col = first_col(nav, ["date"])
    nav_code_col = first_col(nav, ["amfi", "scheme_code", "code"])
    nav_value_col = first_col(nav, ["nav"])

    if not nav_date_col or not nav_code_col or not nav_value_col:
        raise Exception("Required NAV columns not found.")

    nav[nav_date_col] = pd.to_datetime(nav[nav_date_col], errors="coerce")
    nav[nav_value_col] = pd.to_numeric(nav[nav_value_col], errors="coerce")
    nav = nav.dropna(subset=[nav_date_col, nav_code_col, nav_value_col])
    nav = nav.sort_values([nav_code_col, nav_date_col])

    nav["daily_return"] = nav.groupby(nav_code_col)[nav_value_col].pct_change()
    nav.to_csv(os.path.join(REPORT_DIR, "daily_returns.csv"), index=False)
    print("Saved: reports/daily_returns.csv")

    nav_pivot = nav.pivot_table(index=nav_date_col, columns=nav_code_col, values=nav_value_col, aggfunc="last").sort_index()
    returns_pivot = nav_pivot.pct_change()

    bench_date_col = first_col(benchmark, ["date"])
    bench_value_col = None
    for col in benchmark.columns:
        if col != bench_date_col:
            converted = pd.to_numeric(benchmark[col], errors="coerce")
            if converted.notna().sum() > 0:
                bench_value_col = col
                benchmark[col] = converted
                break

    benchmark_returns = None
    benchmark_series = None
    if bench_date_col and bench_value_col:
        benchmark[bench_date_col] = pd.to_datetime(benchmark[bench_date_col], errors="coerce")
        benchmark = benchmark.dropna(subset=[bench_date_col, bench_value_col]).sort_values(bench_date_col)
        benchmark_series = benchmark.set_index(bench_date_col)[bench_value_col]
        benchmark_returns = benchmark_series.pct_change()

    rows = []
    alpha_beta_rows = []

    for code in nav_pivot.columns:
        fund_nav = nav_pivot[code].dropna()
        fund_ret = returns_pivot[code].dropna()
        if len(fund_nav) < 2 or len(fund_ret) < 2:
            continue

        years = max((fund_nav.index.max() - fund_nav.index.min()).days / 365.25, 0.01)
        end_date = fund_nav.index.max()

        cagr_1y = calc_cagr(fund_nav[fund_nav.index >= end_date - pd.DateOffset(years=1)], 1)
        cagr_3y = calc_cagr(fund_nav[fund_nav.index >= end_date - pd.DateOffset(years=3)], 3)
        cagr_5y = calc_cagr(fund_nav[fund_nav.index >= end_date - pd.DateOffset(years=5)], 5)
        cagr_full = calc_cagr(fund_nav, years)

        annual_return = fund_ret.mean() * TRADING_DAYS
        annual_vol = fund_ret.std() * np.sqrt(TRADING_DAYS)
        sharpe = (annual_return - RF_RATE) / annual_vol if annual_vol and annual_vol > 0 else np.nan

        downside = fund_ret[fund_ret < 0]
        downside_vol = downside.std() * np.sqrt(TRADING_DAYS)
        sortino = (annual_return - RF_RATE) / downside_vol if downside_vol and downside_vol > 0 else np.nan

        mdd = max_drawdown(fund_nav)
        alpha = np.nan
        beta = np.nan
        tracking_error = np.nan

        if benchmark_returns is not None:
            alpha, beta = compute_alpha_beta(fund_ret, benchmark_returns)
            aligned = pd.concat([fund_ret, benchmark_returns], axis=1).dropna()
            if aligned.shape[0] > 2:
                tracking_error = (aligned.iloc[:, 0] - aligned.iloc[:, 1]).std() * np.sqrt(TRADING_DAYS)

        rows.append({
            "amfi_code": code,
            "start_date": fund_nav.index.min(),
            "end_date": fund_nav.index.max(),
            "cagr_1y": cagr_1y,
            "cagr_3y": cagr_3y,
            "cagr_5y": cagr_5y,
            "cagr_full_period": cagr_full,
            "annual_return": annual_return,
            "annual_volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": mdd,
            "tracking_error": tracking_error,
            "alpha_annual": alpha,
            "beta": beta
        })

        alpha_beta_rows.append({"amfi_code": code, "alpha_annual": alpha, "beta": beta})

    scorecard = pd.DataFrame(rows)
    alpha_beta = pd.DataFrame(alpha_beta_rows)

    if not scorecard.empty:
        scorecard["rank_3y_return"] = scorecard["cagr_3y"].rank(ascending=False, method="min")
        scorecard["rank_sharpe"] = scorecard["sharpe_ratio"].rank(ascending=False, method="min")
        scorecard["rank_alpha"] = scorecard["alpha_annual"].rank(ascending=False, method="min")
        scorecard["rank_max_drawdown"] = scorecard["max_drawdown"].rank(ascending=False, method="min")

        max_rank = max(len(scorecard), 1)
        scorecard["fund_score"] = (
            0.30 * (1 - scorecard["rank_3y_return"] / max_rank) +
            0.25 * (1 - scorecard["rank_sharpe"] / max_rank) +
            0.20 * (1 - scorecard["rank_alpha"] / max_rank) +
            0.15 * 0.50 +
            0.10 * (1 - scorecard["rank_max_drawdown"] / max_rank)
        ) * 100
        scorecard = scorecard.sort_values("fund_score", ascending=False)

    scorecard.to_csv(os.path.join(REPORT_DIR, "fund_scorecard.csv"), index=False)
    alpha_beta.to_csv(os.path.join(REPORT_DIR, "alpha_beta.csv"), index=False)
    print("Saved: reports/fund_scorecard.csv")
    print("Saved: reports/alpha_beta.csv")

    if not returns_pivot.empty:
        plt.figure(figsize=(10, 6))
        returns_pivot.iloc[:, :10].stack().dropna().plot(kind="hist", bins=50)
        plt.title("Daily Return Distribution for Selected Funds")
        plt.xlabel("Daily Return")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_DIR, "day4_daily_return_distribution.png"), dpi=150)
        plt.close()

    if not scorecard.empty:
        top = scorecard.head(10).set_index("amfi_code")["fund_score"]
        plt.figure(figsize=(12, 6))
        top.sort_values().plot(kind="barh")
        plt.title("Top 10 Funds by Performance Score")
        plt.xlabel("Fund Score")
        plt.ylabel("AMFI Code")
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_DIR, "day4_top_10_fund_score.png"), dpi=150)
        plt.close()

    if benchmark_returns is not None and benchmark_series is not None and not scorecard.empty:
        top_codes = list(scorecard.head(5)["amfi_code"])
        plt.figure(figsize=(12, 6))
        for code in top_codes:
            if code in nav_pivot.columns:
                series = nav_pivot[code].dropna()
                if len(series) > 2:
                    normalized = series / series.iloc[0] * 100
                    plt.plot(normalized.index, normalized.values, label=str(code))

        bench_norm = benchmark_series.dropna()
        if len(bench_norm) > 2:
            bench_norm = bench_norm / bench_norm.iloc[0] * 100
            plt.plot(bench_norm.index, bench_norm.values, label="Benchmark", linewidth=3)

        plt.title("Top Funds vs Benchmark Comparison")
        plt.xlabel("Date")
        plt.ylabel("Normalized Value")
        plt.legend(fontsize=8)
        plt.tight_layout()
        plt.savefig(os.path.join(CHART_DIR, "benchmark_comparison_chart.png"), dpi=150)
        plt.close()

    summary_path = os.path.join(REPORT_DIR, "performance_analytics_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Day 4 Fund Performance Analytics Summary\n\n")
        f.write("Generated outputs:\n\n")
        f.write("- reports/daily_returns.csv\n")
        f.write("- reports/fund_scorecard.csv\n")
        f.write("- reports/alpha_beta.csv\n")
        f.write("- reports/charts/benchmark_comparison_chart.png\n")
        f.write("- reports/charts/day4_daily_return_distribution.png\n")
        f.write("- reports/charts/day4_top_10_fund_score.png\n")

    print("Saved: reports/performance_analytics_summary.md")
    print("DAY 4 completed successfully.")
    conn.close()

if __name__ == "__main__":
    main()
