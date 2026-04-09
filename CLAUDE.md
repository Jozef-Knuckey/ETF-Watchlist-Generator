# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

ETF Watchlist Generator — Python GUI tool for US stock market research. Input one or more ETF tickers, fetch their holdings, filter by market cap / price / volume, and export a TradingView-importable `.txt` file. Output is saved to `~/Desktop/ETF Watchlist Generator/`.

## Running

```bash
# GUI (primary interface)
python gui.py

# CLI (alternative)
python main.py IGV --min-market-cap 2
python main.py QQQ --min-market-cap 10 --min-price 5
python main.py IGV QQQ --min-market-cap 2 --out combined.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Architecture

```
gui.py           Tkinter GUI — main entry point for end users
main.py          CLI entry point (click)
providers.json   Curated provider → ETF list for Browse by Provider dialog

etf/
  base.py        Abstract ETFFetcher — all fetchers return DataFrame(ticker, name, weight)
  factory.py     get_fetcher(ticker) — detects provider via yfinance fundFamily, returns fetcher
                 Falls back to FallbackFetcher for any unknown provider
  ishares.py     iShares/BlackRock — queries product screener API, scrapes product page for CSV URL
  invesco.py     Invesco — hits holdings download endpoint
  spdr.py        SPDR/State Street — downloads holdings XLSX
  vanguard.py    Vanguard — scrapes profile page for fund ID, calls holdings API
  fallback.py    Universal fallback — scrapes stockanalysis.com, works for any ETF provider

market_data.py   enrich(df) — adds market_cap (billions), price, avg_volume via yfinance
filters.py       apply_filters(df, min_market_cap, min_price, min_avg_volume)
output.py        write_tradingview(df, path) — one ticker per line .txt
```

## GUI Features

- Multi-ticker input — space separated e.g. `IGV QQQ XLE`
- Quick filter preset buttons: Small ($300M+), Mid ($2B+), Large ($10B+), Mega ($100B+), Liquid (500k vol)
- Browse by Provider dialog — search ARK, Global X, VanEck, Roundhill etc. and select ETFs via checkboxes
- Progress log shown in-window during generation
- Output auto-saved to `~/Desktop/ETF Watchlist Generator/<TICKER>_watchlist.txt`

## Adding a New Provider (native fetcher)

1. Create `etf/<provider>.py` subclassing `ETFFetcher`, implement `get_holdings(ticker) -> pd.DataFrame`
2. Return DataFrame must have columns: `ticker`, `name`, `weight` — call `self._clean(df)` before returning
3. Register in `etf/factory.py` `_PROVIDER_MAP` keyed on the lowercase `fundFamily` string yfinance returns

## Adding ETFs to the Browse Dialog

Edit `providers.json` — add to an existing provider or create a new entry following the same structure.

## Known Fragility

Provider-specific fetcher URLs are unofficial and may break if providers update their sites. The universal fallback (`etf/fallback.py` via stockanalysis.com) handles any ETF when native fetchers fail or the provider is unknown.
