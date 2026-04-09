import requests
import pandas as pd
from bs4 import BeautifulSoup
from .base import ETFFetcher

_HOLDINGS_URL = "https://stockanalysis.com/etf/{ticker}/holdings/"


class FallbackFetcher(ETFFetcher):
    """Universal fallback fetcher using stockanalysis.com.

    Used automatically for any ETF provider not explicitly supported.
    Covers all US-listed ETFs regardless of provider.
    """

    def get_holdings(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        url = _HOLDINGS_URL.format(ticker=ticker.lower())

        resp = requests.get(url, headers=self.HEADERS, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")
        table = soup.find("table")
        if table is None:
            raise ValueError(
                f"Could not find holdings table on stockanalysis.com for '{ticker}'. "
                "The ETF may not be listed or the page structure may have changed."
            )

        rows = []
        for tr in table.find("tbody").find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 4:
                continue

            # Ticker is in an <a> tag in the second cell (index 1)
            a_tag = cells[1].find("a")
            symbol = a_tag.get_text(strip=True) if a_tag else cells[1].get_text(strip=True)

            name   = cells[2].get_text(strip=True)
            weight = cells[3].get_text(strip=True).replace("%", "").strip()

            rows.append({"ticker": symbol, "name": name, "weight": weight})

        if not rows:
            raise ValueError(f"No holdings rows parsed from stockanalysis.com for '{ticker}'.")

        return self._clean(pd.DataFrame(rows))
