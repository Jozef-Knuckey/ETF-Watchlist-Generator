import click
import pandas as pd
from pathlib import Path

import etf as etf_pkg
import market_data
import filters as flt
import output


@click.command()
@click.argument("ticker")
@click.option(
    "--min-market-cap", "-m",
    type=float,
    default=None,
    help="Minimum market cap in billions (e.g. 2 = $2B).",
)
@click.option(
    "--min-price", "-p",
    type=float,
    default=None,
    help="Minimum stock price in USD.",
)
@click.option(
    "--min-volume", "-v",
    type=float,
    default=None,
    help="Minimum 3-month average daily volume.",
)
@click.option(
    "--out", "-o",
    type=click.Path(),
    default=None,
    help="Output file path. Defaults to ~/Desktop/ETF Watchlist Generator/<TICKER>_watchlist.txt",
)
def main(ticker, min_market_cap, min_price, min_volume, out):
    """Fetch ETF holdings, apply filters, and export a TradingView watchlist.

    TICKER is the ETF symbol, e.g. IGV, QQQ, SPY.

    Examples:

    \b
        python main.py IGV --min-market-cap 2
        python main.py QQQ --min-market-cap 10 --min-price 5
        python main.py SPY --min-market-cap 50 --out big_caps.txt
    """
    ticker = ticker.upper()

    default_folder = Path.home() / "Desktop" / "ETF Watchlist Generator"
    default_folder.mkdir(parents=True, exist_ok=True)

    out_path = Path(out) if out else default_folder / f"{ticker}_watchlist.txt"

    click.echo(f"[1/4] Detecting provider for {ticker}...")
    fetcher = etf_pkg.get_fetcher(ticker)
    click.echo(f"      Provider: {type(fetcher).__name__.replace('Fetcher', '')}")

    click.echo(f"[2/4] Fetching holdings...")
    holdings = fetcher.get_holdings(ticker)
    click.echo(f"      {len(holdings)} holdings found.")

    click.echo(f"[3/4] Enriching with market data (this may take a moment)...")
    enriched = market_data.enrich(holdings)

    click.echo(f"[4/4] Applying filters...")
    filtered = flt.apply_filters(
        enriched,
        min_market_cap=min_market_cap,
        min_price=min_price,
        min_avg_volume=min_volume,
    )

    if filtered.empty:
        click.echo("No holdings passed the filters. Try relaxing the criteria.")
        return

    written = output.write_tradingview(filtered, out_path)

    click.echo(f"\nDone. {len(filtered)} tickers saved to: {written}")
    if min_market_cap:
        click.echo(f"  Market cap filter : >= ${min_market_cap}B")
    if min_price:
        click.echo(f"  Price filter      : >= ${min_price}")
    if min_volume:
        click.echo(f"  Volume filter     : >= {min_volume:,.0f}")


if __name__ == "__main__":
    main()
