import re
import requests
import pandas as pd
from bs4 import BeautifulSoup
from .base import ETFFetcher

# Vanguard ETF profile page — we scrape the fund ID then hit their holdings API
_PROFILE_URL = "https://investor.vanguard.com/etf/profile/overview/{ticker}"
_HOLDINGS_API = "https://api.vanguard.com/rs/ire/01/pe/fund/{fund_id}/portfolio-holding.jsonp"


class VanguardFetcher(ETFFetcher):
    """Fetches holdings for Vanguard ETFs (e.g. VTI, VOO, VGT).

    Flow:
      1. Scrape the Vanguard ETF profile page to extract the internal fund ID.
      2. Call Vanguard's holdings API with that fund ID.
    """

    def get_holdings(self, ticker: str) -> pd.DataFrame:
        ticker = ticker.upper()
        fund_id = self._get_fund_id(ticker)
        return self._fetch_holdings(ticker, fund_id)

    def _get_fund_id(self, ticker: str) -> str:
        url = _PROFILE_URL.format(ticker=ticker)
        resp = requests.get(url, headers=self.HEADERS, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Fund ID appears in meta tags or embedded JSON as "fundId" or "portId"
        for tag in soup.find_all("meta"):
            content = tag.get("content", "")
            match = re.search(r"\b(\d{4})\b", content)
            if match:
                return match.group(1)

        # Fallback: look in inline scripts
        for script in soup.find_all("script"):
            match = re.search(r'"fundId"\s*:\s*"?(\d+)"?', script.string or "")
            if match:
                return match.group(1)

        raise ValueError(
            f"Could not extract Vanguard fund ID for '{ticker}'. "
            "The page structure may have changed."
        )

    def _fetch_holdings(self, ticker: str, fund_id: str) -> pd.DataFrame:
        url = _HOLDINGS_API.format(fund_id=fund_id)
        resp = requests.get(url, headers=self.HEADERS, timeout=30)
        resp.raise_for_status()

        # Response is JSONP; strip the callback wrapper
        text = resp.text.strip()
        json_str = re.sub(r"^[^(]+\(", "", text).rstrip(");")

        import json
        data = json.loads(json_str)

        holdings = data.get("holding", data.get("holdings", []))
        rows = []
        for h in holdings:
            rows.append({
                "ticker": h.get("ticker", h.get("symbol", "")),
                "name": h.get("shortName", h.get("name", "")),
                "weight": float(h.get("percentWeight", h.get("weight", 0))),
            })

        return self._clean(pd.DataFrame(rows))
