
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def inspect_csv(path: Path) -> dict:
    df = pd.read_csv(path)
    print("\n" + "=" * 90)
    print(f"FILE: {path.name}")
    print(f"SHAPE: {df.shape}")
    print("\nDTYPES:")
    print(df.dtypes)
    print("\nHEAD:")
    print(df.head())

    return {
        "file": path.name,
        "rows": len(df),
        "columns": len(df.columns),
        "null_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "column_names": ", ".join(df.columns.astype(str)),
    }


def validate_scheme_codes() -> None:
    fund_master_path = RAW_DIR / "01_fund_master.csv"
    nav_history_path = RAW_DIR / "02_nav_history.csv"
    if not fund_master_path.exists() or not nav_history_path.exists():
        print("Scheme validation skipped: required files not found.")
        return

    fund_master = pd.read_csv(fund_master_path)
    nav_history = pd.read_csv(nav_history_path)

    fm_code_cols = [c for c in fund_master.columns if "code" in c.lower()]
    nav_code_cols = [c for c in nav_history.columns if "code" in c.lower()]

    if not fm_code_cols or not nav_code_cols:
        print("Scheme validation skipped: scheme code columns could not be detected.")
        return

    fm_col = fm_code_cols[0]
    nav_col = nav_code_cols[0]
    fm_codes = set(fund_master[fm_col].dropna().astype(str))
    nav_codes = set(nav_history[nav_col].dropna().astype(str))
    missing = sorted(fm_codes - nav_codes)

    print("\n" + "=" * 90)
    print("AMFI / Scheme Code Validation")
    print(f"fund_master column: {fm_col}")
    print(f"nav_history column: {nav_col}")
    print(f"Total codes in fund_master: {len(fm_codes)}")
    print(f"Total codes in nav_history: {len(nav_codes)}")
    print(f"Missing from nav_history: {len(missing)}")
    if missing:
        print("Missing codes sample:", missing[:20])


def main() -> None:
    csv_files = sorted(RAW_DIR.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError("No CSV files found in data/raw")

    summary = [inspect_csv(path) for path in csv_files]
    pd.DataFrame(summary).to_csv(REPORT_DIR / "data_quality_summary.csv", index=False)
    validate_scheme_codes()
    print("\nData quality summary saved to reports/data_quality_summary.csv")


if __name__ == "__main__":
    main()
