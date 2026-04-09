import logging
import warnings
import yfinance as yf
import pandas as pd

# Suppress yfinance warnings about delisted/missing tickers
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore")


def enrich(df: pd.DataFrame, batch_size: int = 100) -> pd.DataFrame:
    """Add market_cap (billions), price, and avg_volume columns to a holdings DataFrame.

    Fetches data in batches to avoid yfinance request limits.
    Tickers where data cannot be fetched are kept with NaN values.
    """
    tickers = df["ticker"].tolist()
    records: dict[str, dict] = {}

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        data = yf.download(
            batch,
            period="5d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
        )

        for t in batch:
            try:
                info = yf.Ticker(t).fast_info
                records[t] = {
                    "market_cap": _to_billions(getattr(info, "market_cap", None)),
                    "price": getattr(info, "last_price", None),
                    "avg_volume": getattr(info, "three_month_average_volume", None),
                }
            except Exception:
                records[t] = {"market_cap": None, "price": None, "avg_volume": None}

    enriched = df.copy()
    enriched["market_cap"] = enriched["ticker"].map(lambda t: records.get(t, {}).get("market_cap"))
    enriched["price"] = enriched["ticker"].map(lambda t: records.get(t, {}).get("price"))
    enriched["avg_volume"] = enriched["ticker"].map(lambda t: records.get(t, {}).get("avg_volume"))

    return enriched


def _to_billions(value) -> float | None:
    if value is None:
        return None
    return round(value / 1e9, 4)
