import io
import re
import requests
import pandas as pd
from .base import ETFFetcher

_SCREENER_URL = (
    "https://www.ishares.com/us/product-screener/product-screener-v3.jsn"
    "?dcrPath=/templatedata/config/product-screener-v3/data/en/us-ishares/"
    "ishares-product-screener-backend-config&siteEntryPassthrough=true"
)
_BASE = "https://www.ishares.com"

# Column indexes in the screener data array
_COL_TICKER = 22
_COL_PAGE = 48


class iSharesFetcher(ETFFetcher):
    """Fetches holdings for iShares (BlackRock) ETFs.

    Flow:
      1. Query iShares product screener to resolve ticker → product page path.
      2. Scrape the product page to extract the CSV holdings download URL.
      3. Download and parse the CSV.
    """

    def get_holdings(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        product_path = self._find_product_path(ticker)
        csv_url = self._find_csv_url(ticker, product_path)
        return self._download_csv(ticker, csv_url)

    def _find_product_path(self, ticker: str) -> str:
        resp = requests.get(_SCREENER_URL, headers=self.HEADERS, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        rows = data["data"]["tableData"]["data"]
        for row in rows:
            if len(row) > _COL_TICKER and row[_COL_TICKER] == ticker:
                if len(row) > _COL_PAGE:
                    return row[_COL_PAGE]

        raise ValueError(
            f"Ticker '{ticker}' not found in iShares product screener. "
            "It may not be an iShares ETF."
        )

    def _find_csv_url(self, ticker: str, product_path: str) -> str:
        page_url = f"{_BASE}{product_path}"
        resp = requests.get(page_url, headers={**self.HEADERS, "Referer": _BASE}, timeout=20)
        resp.raise_for_status()

        # Extract the CSV download link embedded in the page HTML
        match = re.search(
            r'href="(/us/products/[^"]+\.ajax\?fileType=csv&fileName=' + ticker + r'[^"]*)"',
            resp.text,
        )
        if not match:
            raise ValueError(
                f"Could not find CSV download link on iShares product page for {ticker}. "
                f"Page: {page_url}"
            )
        return _BASE + match.group(1)

    def _download_csv(self, ticker: str, url: str) -> pd.DataFrame:
        resp = requests.get(url, headers={**self.HEADERS, "Referer": _BASE}, timeout=30)
        resp.raise_for_status()

        # iShares CSVs have metadata rows at the top before the actual data
        # Decode with UTF-8-sig to strip the BOM character
        text = resp.content.decode("utf-8-sig")
        lines = text.splitlines()

        # Find the header row — it contains 'Ticker' and 'Name'
        header_idx = next(
            (i for i, line in enumerate(lines) if "Ticker" in line and "Name" in line),
            None,
        )
        if header_idx is None:
            raise ValueError(f"Could not locate header row in iShares CSV for {ticker}")

        csv_body = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(csv_body))
        df = df.rename(columns=lambda c: c.strip())

        col_map = {
            "Ticker": "ticker",
            "Name": "name",
            "Weight (%)": "weight",
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

        missing = {"ticker", "name", "weight"} - set(df.columns)
        if missing:
            raise ValueError(
                f"Unexpected iShares CSV format for {ticker}. "
                f"Missing: {missing}. Got: {list(df.columns)}"
            )

        return self._clean(df[["ticker", "name", "weight"]])
