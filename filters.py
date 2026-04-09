import pandas as pd


def apply_filters(
    df: pd.DataFrame,
    min_market_cap: float | None = None,  # in billions
    min_price: float | None = None,
    min_avg_volume: float | None = None,
) -> pd.DataFrame:
    """Filter holdings DataFrame by market cap, price, and/or average volume.

    Args:
        df:              Enriched holdings DataFrame (output of market_data.enrich).
        min_market_cap:  Minimum market cap in billions (e.g. 2.0 = $2B).
        min_price:       Minimum stock price in USD.
        min_avg_volume:  Minimum 3-month average daily volume.

    Returns:
        Filtered DataFrame. Rows where the relevant field is NaN are dropped
        when a filter is active (can't confirm they pass the threshold).
    """
    result = df.copy()

    if min_market_cap is not None:
        result = result[result["market_cap"].notna() & (result["market_cap"] >= min_market_cap)]

    if min_price is not None:
        result = result[result["price"].notna() & (result["price"] >= min_price)]

    if min_avg_volume is not None:
        result = result[result["avg_volume"].notna() & (result["avg_volume"] >= min_avg_volume)]

    return result.reset_index(drop=True)
