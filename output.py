import pandas as pd
from pathlib import Path


def write_tradingview(df: pd.DataFrame, path: str | Path) -> Path:
    """Write tickers to a TradingView-importable watchlist file.

    Format: one ticker per line.
    TradingView accepts plain tickers (AAPL) or exchange-prefixed (NASDAQ:AAPL).
    This writes plain tickers; TradingView resolves the exchange automatically.

    Returns the Path written to.
    """
    path = Path(path)
    tickers = df["ticker"].dropna().unique().tolist()

    with path.open("w") as f:
        f.write("\n".join(tickers) + "\n")

    return path
