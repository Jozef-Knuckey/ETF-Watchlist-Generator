from abc import ABC, abstractmethod
import pandas as pd


class ETFFetcher(ABC):
    """Abstract base class for ETF holdings fetchers.

    All subclasses must implement get_holdings() and return a DataFrame
    with at minimum these columns:
        ticker  (str)   - stock ticker symbol
        name    (str)   - company name
        weight  (float) - % weight in ETF
    """

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    @abstractmethod
    def get_holdings(self, ticker: str) -> pd.DataFrame:
        pass

    def _clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate and normalise holdings DataFrame."""
        required = {"ticker", "name", "weight"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Holdings DataFrame missing columns: {missing}")

        df = df.copy()
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(0.0)

        # Drop cash positions, empty rows, and non-stock entries
        df = df[df["ticker"].notna() & (df["ticker"] != "") & (df["ticker"] != "NAN")]
        df = df[~df["ticker"].str.contains(r"[^A-Z0-9.\-]", regex=True)]

        return df.reset_index(drop=True)
