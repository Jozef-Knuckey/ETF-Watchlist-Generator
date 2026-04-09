import io
import requests
import pandas as pd
from .base import ETFFetcher

# SPDR (State Street) publishes daily holdings as XLSX
_HOLDINGS_URL = (
    "https://www.ssga.com/us/en/institutional/etfs/library-content/products"
    "/fund-data/etfs/us/holdings-daily-us-en-{ticker_lower}.xlsx"
)


class SPDRFetcher(ETFFetcher):
    """Fetches holdings for SPDR (State Street Global Advisors) ETFs (e.g. SPY, XLK, GLD)."""

    def get_holdings(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        url = _HOLDINGS_URL.format(ticker_lower=ticker.lower())

        resp = requests.get(url, headers=self.HEADERS, timeout=30)
        resp.raise_for_status()

        # SPDR XLSX files have metadata rows; holdings start after a blank line
        xl = pd.ExcelFile(io.BytesIO(resp.content))
        df_raw = xl.parse(xl.sheet_names[0], header=None)

        # Find the row where the actual column headers appear
        header_idx = None
        for i, row in df_raw.iterrows():
            values = [str(v).strip() for v in row.values if pd.notna(v)]
            if any(v in ("Ticker", "Name", "Symbol") for v in values):
                header_idx = i
                break

        if header_idx is None:
            raise ValueError(f"Could not locate header row in SPDR XLSX for {ticker}")

        df = pd.read_excel(
            io.BytesIO(resp.content),
            sheet_name=xl.sheet_names[0],
            header=header_idx,
        )
        df = df.rename(columns=lambda c: str(c).strip())

        col_map = {
            "Ticker": "ticker",
            "Symbol": "ticker",
            "Name": "name",
            "Security Name": "name",
            "Weight": "weight",
            "% Weight": "weight",
            "Weightings": "weight",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        missing = {"ticker", "name", "weight"} - set(df.columns)
        if missing:
            raise ValueError(
                f"Unexpected SPDR XLSX format for {ticker}. "
                f"Missing columns: {missing}. Got: {list(df.columns)}"
            )

        return self._clean(df[["ticker", "name", "weight"]])
