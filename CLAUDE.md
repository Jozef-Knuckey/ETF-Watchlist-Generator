# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ETF Watchlist Generator — Python CLI. Input an ETF ticker, fetch its holdings, filter by market cap / price / volume, export a TradingView-importable `.txt` file.

## Running

```bash
python main.py IGV --min-market-cap 2
python main.py QQQ --min-market-cap 10 --min-price 5
python main.py SPY --min-market-cap 50 --out big_caps.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Architecture

```
main.py          CLI entry point (click)
etf/
  base.py        Abstract ETFFetcher — all fetchers return DataFrame(ticker, name, weight)
  factory.py     get_fetcher(ticker) — detects provider via yfinance fundFamily, returns fetcher
  ishares.py     iShares/BlackRock — queries product screener API, downloads holdings CSV
  invesco.py     Invesco — hits holdings download endpoint
  spdr.py        SPDR/State Street — downloads holdings XLSX
  vanguard.py    Vanguard — scrapes profile page for fund ID, calls holdings API
market_data.py   enrich(df) — adds market_cap (billions), price, avg_volume via yfinance
filters.py       apply_filters(df, min_market_cap, min_price, min_avg_volume)
output.py        write_tradingview(df, path) — one ticker per line .txt
```

## Adding a New Provider

1. Create `etf/<provider>.py` subclassing `ETFFetcher`, implement `get_holdings(ticker) -> pd.DataFrame`
2. Return DataFrame must have columns: `ticker`, `name`, `weight` — call `self._clean(df)` before returning
3. Register in `etf/factory.py` `_PROVIDER_MAP` keyed on the lowercase `fundFamily` string yfinance returns

## Known Fragility

Provider data URLs are unofficial and may break if the provider changes their site. Each fetcher has a comment showing the URL pattern. If a fetch fails with an HTTP error, the URL is the first thing to verify.
