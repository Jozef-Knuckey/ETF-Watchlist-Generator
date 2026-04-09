import yfinance as yf
from .base import ETFFetcher
from .ishares import iSharesFetcher
from .invesco import InvescoFetcher
from .spdr import SPDRFetcher
from .vanguard import VanguardFetcher
from .fallback import FallbackFetcher

_PROVIDER_MAP: dict[str, type[ETFFetcher]] = {
    "ishares": iSharesFetcher,
    "blackrock": iSharesFetcher,
    "invesco": InvescoFetcher,
    "spdr": SPDRFetcher,
    "state street": SPDRFetcher,
    "vanguard": VanguardFetcher,
}


def get_fetcher(ticker: str) -> ETFFetcher:
    """Detect the ETF provider via yfinance and return the matching fetcher.

    Raises ValueError if the provider is not supported or cannot be detected.
    """
    info = yf.Ticker(ticker.upper()).info
    fund_family = (info.get("fundFamily") or "").lower()

    if not fund_family:
        raise ValueError(
            f"Could not determine fund family for '{ticker}'. "
            "Verify it is a valid ETF ticker."
        )

    for key, fetcher_class in _PROVIDER_MAP.items():
        if key in fund_family:
            return fetcher_class()

    # Unknown provider — fall back to stockanalysis.com which covers all ETFs
    print(f"      Note: '{fund_family}' is not a natively supported provider. Using universal fallback.")
    return FallbackFetcher()
