import io
import requests
import pandas as pd
from .base import ETFFetcher

# Invesco holdings download endpoint — returns CSV when fileType=holdings
_HOLDINGS_URL = (
    "https://www.invesco.com/us/financial-products/etfs/fund-data/download"
    "/{ticker}?fileType=holdings&audienceType=Investor"
)


class InvescoFetcher(ETFFetcher):
    """Fetches holdings for Invesco ETFs (e.g. IGV, QQQ, QQQM)."""

    def get_holdings(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        url = _HOLDINGS_URL.format(ticker=ticker)

        resp = requests.get(url, headers=self.HEADERS, timeout=30)
        resp.raise_for_status()

        df = pd.read_csv(io.StringIO(resp.text))
        df = df.rename(columns=lambda c: c.strip())

        # Invesco column names vary slightly by fund; map the common ones
        col_map = {
            "HoldingsTicker": "ticker",
            "Ticker": "ticker",
            "Security Identifier": "ticker",
            "Name": "name",
            "SecurityName": "name",
            "Weight": "weight",
            "Weightings": "weight",
            "% Weight": "weight",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        missing = {"ticker", "name", "weight"} - set(df.columns)
        if missing:
            raise ValueError(
                f"Unexpected Invesco CSV format for {ticker}. "
                f"Missing columns: {missing}. Got: {list(df.columns)}"
            )

        return self._clean(df[["ticker", "name", "weight"]])
