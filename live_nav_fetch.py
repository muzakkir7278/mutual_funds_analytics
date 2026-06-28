"""Fetch live mutual fund NAV data from mfapi.in and save raw CSV files.
Run from project root: python live_nav_fetch.py
"""
from pathlib import Path
import requests
import pandas as pd

RAW_DIR = Path("data/raw")
RAW_DIR.mkdir(parents=True, exist_ok=True)

SCHEMES = {
    "hdfc_top_100_direct": "125497",
    "sbi_bluechip": "119551",
    "icici_bluechip": "120503",
    "nippon_large_cap": "118632",
    "axis_bluechip": "119092",
    "kotak_bluechip": "120841",
}


def fetch_scheme_nav(name: str, code: str) -> None:
    url = f"https://api.mfapi.in/mf/{code}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    payload = response.json()

    rows = payload.get("data", [])
    meta = payload.get("meta", {})
    df = pd.DataFrame(rows)
    for key, value in meta.items():
        df[f"meta_{key}"] = value

    output_path = RAW_DIR / f"live_nav_{code}_{name}.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} rows: {output_path}")


def main() -> None:
    for name, code in SCHEMES.items():
        fetch_scheme_nav(name, code)


if __name__ == "__main__":
    main()
