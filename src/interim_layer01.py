"""TEMPORARY stand-in for Layers 0-1 so Layers 2-3 can run before
clean_data.py / deterministic.py exist. Delete once those write
data/processed/grants_features.csv - Layer 2 reads that file first.

It does only the bare minimum Layer 2 needs:
  * grant_id = opportunity_id, drop duplicate ids
  * hard_filtered = posted grant whose close date is before agency as_of_date,
    or a status other than posted/forecasted
Forecasts are kept (they feed the watchlist track).
"""

import pandas as pd

import config


def build() -> pd.DataFrame:
    df = pd.read_csv(config.RAW_GRANTS)
    df = df.rename(columns={"opportunity_id": "grant_id"}).drop_duplicates("grant_id")
    as_of = pd.Timestamp(config.load_agency()["as_of_date"])
    close = pd.to_datetime(df["close_date"], errors="coerce")
    expired = (~df["is_forecast"].astype(bool)) & close.notna() & (close < as_of)
    bad_status = ~df["opportunity_status"].isin(["posted", "forecasted"])
    df["hard_filtered"] = expired | bad_status
    df["hard_filter_reason"] = ""
    df.loc[expired, "hard_filter_reason"] = f"closed before {as_of.date()}"
    df.loc[bad_status, "hard_filter_reason"] = "status: " + df.loc[bad_status, "opportunity_status"].astype(str)
    return df
