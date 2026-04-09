import json
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import sys
from pathlib import Path

import etf as etf_pkg
import market_data
import filters as flt
import output

OUTPUT_FOLDER = Path.home() / "Desktop" / "ETF Watchlist Generator"
PROVIDERS_FILE = Path(__file__).parent / "providers.json"


class RedirectText:
    """Redirects stdout to the GUI log area."""

    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget

    def write(self, text: str):
        self.widget.configure(state="normal")
        self.widget.insert(tk.END, text)
        self.widget.see(tk.END)
        self.widget.configure(state="disabled")

    def flush(self):
        pass


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ETF Watchlist Generator")
        self.resizable(False, False)
        self._build_ui()
        self._center()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # ── Header ──────────────────────────────────────────────
        header = tk.Frame(self, bg="#1a1a2e")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(
            header,
            text="ETF Watchlist Generator",
            font=("Segoe UI", 14, "bold"),
            bg="#1a1a2e",
            fg="white",
            pady=10,
        ).pack()

        # ── Inputs ──────────────────────────────────────────────
        form = tk.Frame(self, pady=8)
        form.grid(row=1, column=0, columnspan=2, sticky="ew", **pad)

        def row(label, hint, r):
            tk.Label(form, text=label, font=("Segoe UI", 10, "bold"), anchor="w").grid(
                row=r, column=0, sticky="w", padx=(0, 10), pady=4
            )
            tk.Label(form, text=hint, font=("Segoe UI", 8), fg="#666", anchor="w").grid(
                row=r, column=2, sticky="w", padx=(6, 0)
            )
            var = tk.StringVar()
            entry = ttk.Entry(form, textvariable=var, width=16, font=("Segoe UI", 10))
            entry.grid(row=r, column=1, sticky="w")
            return var

        self.ticker_var = row("ETF Ticker(s)", "e.g.  IGV  or  IGV QQQ XLE  (space separated)", 0)
        ttk.Button(
            form, text="Browse Providers", width=16,
            command=self._open_provider_browser,
        ).grid(row=0, column=3, padx=(10, 0))
        self.cap_var    = row("Min Market Cap ($B)", "e.g.  2  =  $2 billion  (optional)", 1)
        self.price_var  = row("Min Price ($)", "e.g.  10  =  $10  (optional)", 2)
        self.volume_var = row("Min Avg Volume", "e.g.  500000  =  500k  (optional)", 3)

        # ── Presets ─────────────────────────────────────────────
        presets_frame = tk.Frame(self)
        presets_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 4))

        tk.Label(
            presets_frame, text="Quick Filters:", font=("Segoe UI", 9, "bold")
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        cap_presets = [
            ("Small  $300M+", "0.3"),
            ("Mid  $2B+",     "2"),
            ("Large  $10B+",  "10"),
            ("Mega  $100B+",  "100"),
        ]
        for col, (label, value) in enumerate(cap_presets, start=1):
            ttk.Button(
                presets_frame,
                text=label,
                width=12,
                command=lambda v=value: self.cap_var.set(v),
            ).grid(row=0, column=col, padx=3)

        ttk.Button(
            presets_frame,
            text="Liquid  500k vol",
            width=14,
            command=lambda: self.volume_var.set("500000"),
        ).grid(row=0, column=len(cap_presets) + 1, padx=(10, 3))

        ttk.Button(
            presets_frame,
            text="Clear",
            width=6,
            command=self._clear_filters,
        ).grid(row=0, column=len(cap_presets) + 2, padx=3)

        # ── Button ──────────────────────────────────────────────
        self.btn = ttk.Button(
            self, text="Generate Watchlist", command=self._on_generate, width=24
        )
        self.btn.grid(row=3, column=0, columnspan=2, pady=(4, 10))

        # ── Log ─────────────────────────────────────────────────
        self.log = scrolledtext.ScrolledText(
            self,
            height=12,
            width=58,
            font=("Consolas", 9),
            state="disabled",
            bg="#f5f5f5",
            relief="flat",
            borderwidth=1,
        )
        self.log.grid(row=4, column=0, columnspan=2, padx=12, pady=(0, 8), sticky="ew")

        # ── Status bar ──────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        tk.Label(
            self,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#555",
            anchor="w",
        ).grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 8))

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _log(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert(tk.END, msg + "\n")
        self.log.see(tk.END)
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.configure(state="disabled")

    def _set_status(self, msg: str):
        self.status_var.set(msg)

    def _clear_filters(self):
        self.cap_var.set("")
        self.price_var.set("")
        self.volume_var.set("")

    def _on_generate(self):
        raw = self.ticker_var.get().strip().upper()
        tickers = [t for t in raw.replace(",", " ").split() if t]
        if not tickers:
            self._set_status("Please enter at least one ETF ticker.")
            return

        def _parse_float(val):
            v = val.strip()
            return float(v) if v else None

        try:
            min_cap    = _parse_float(self.cap_var.get())
            min_price  = _parse_float(self.price_var.get())
            min_volume = _parse_float(self.volume_var.get())
        except ValueError:
            self._set_status("Invalid filter value — enter plain numbers only (e.g. 2, not $2B).")
            return

        self.btn.configure(state="disabled")
        self._clear_log()
        self._set_status("Running...")

        # Redirect stdout into the log widget
        sys.stdout = RedirectText(self.log)

        threading.Thread(
            target=self._run,
            args=(tickers, min_cap, min_price, min_volume),
            daemon=True,
        ).start()

    def _run(self, tickers, min_cap, min_price, min_volume):
        import pandas as pd
        try:
            all_holdings = []

            for i, ticker in enumerate(tickers, 1):
                print(f"── ETF {i}/{len(tickers)}: {ticker} ──────────────────")
                print(f"  Detecting provider...")
                fetcher = etf_pkg.get_fetcher(ticker)
                print(f"  Provider: {type(fetcher).__name__.replace('Fetcher', '')}")

                print(f"  Fetching holdings...")
                holdings = fetcher.get_holdings(ticker)
                print(f"  {len(holdings)} holdings found.")
                all_holdings.append(holdings)

            print(f"\n[3/4] Enriching with market data (may take ~30s)...")
            combined = pd.concat(all_holdings, ignore_index=True)

            # Deduplicate — keep first occurrence of each ticker
            before = len(combined)
            combined = combined.drop_duplicates(subset="ticker").reset_index(drop=True)
            if len(tickers) > 1:
                print(f"      Combined: {before} holdings → {len(combined)} unique tickers.")

            enriched = market_data.enrich(combined)

            print(f"[4/4] Applying filters...")
            filtered = flt.apply_filters(
                enriched,
                min_market_cap=min_cap,
                min_price=min_price,
                min_avg_volume=min_volume,
            )

            if filtered.empty:
                print("No holdings passed the filters. Try relaxing the criteria.")
                self.after(0, self._set_status, "Done — no tickers passed filters.")
                return

            OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
            label = "_".join(tickers)
            out_path = OUTPUT_FOLDER / f"{label}_watchlist.txt"
            output.write_tradingview(filtered, out_path)

            print(f"\nDone. {len(filtered)} tickers saved to:")
            print(f"  {out_path}")
            if min_cap:
                print(f"  Market cap : >= ${min_cap}B")
            if min_price:
                print(f"  Price      : >= ${min_price}")
            if min_volume:
                print(f"  Volume     : >= {min_volume:,.0f}")

            self.after(0, self._set_status, f"Done — {len(filtered)} tickers saved to Desktop folder.")

        except Exception as e:
            print(f"\nError: {e}")
            self.after(0, self._set_status, f"Error: {e}")

        finally:
            sys.stdout = sys.__stdout__
            self.after(0, lambda: self.btn.configure(state="normal"))


    def _open_provider_browser(self):
        ProviderBrowser(self, self.ticker_var)


class ProviderBrowser(tk.Toplevel):
    """Dialog for browsing ETFs by provider and adding them to the ticker field."""

    def __init__(self, parent, ticker_var: tk.StringVar):
        super().__init__(parent)
        self.title("Browse by Provider")
        self.resizable(False, False)
        self.grab_set()  # modal

        self.ticker_var = ticker_var
        self.providers = json.loads(PROVIDERS_FILE.read_text()) if PROVIDERS_FILE.exists() else {}
        self.check_vars: list[tuple[str, tk.BooleanVar]] = []

        self._build_ui()
        self._center(parent)

    def _build_ui(self):
        # ── Search ──────────────────────────────────────────────
        top = tk.Frame(self, pady=8, padx=12)
        top.pack(fill="x")

        tk.Label(top, text="Search provider:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._refresh())
        ttk.Entry(top, textvariable=self.search_var, width=22, font=("Segoe UI", 10)).pack(
            side="left", padx=(8, 0)
        )

        # ── ETF list ────────────────────────────────────────────
        list_frame = tk.Frame(self, padx=12)
        list_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_frame, width=380, height=320, highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        ))

        # ── Buttons ─────────────────────────────────────────────
        btn_frame = tk.Frame(self, pady=8, padx=12)
        btn_frame.pack(fill="x")

        ttk.Button(btn_frame, text="Add Selected to Ticker Field",
                   command=self._add_selected, width=28).pack(side="left")
        ttk.Button(btn_frame, text="Clear Selection",
                   command=self._clear_selection, width=14).pack(side="left", padx=(8, 0))
        ttk.Button(btn_frame, text="Close",
                   command=self.destroy, width=8).pack(side="right")

        self._refresh()

    def _refresh(self):
        for widget in self.inner.winfo_children():
            widget.destroy()
        self.check_vars.clear()

        query = self.search_var.get().strip().lower()

        for provider, data in self.providers.items():
            aliases = data.get("aliases", [])
            if query and query not in provider.lower() and not any(query in a for a in aliases):
                continue

            # Provider header
            tk.Label(
                self.inner, text=provider,
                font=("Segoe UI", 10, "bold"), anchor="w", fg="#1a1a2e"
            ).pack(fill="x", pady=(8, 2))

            for etf in data.get("etfs", []):
                var = tk.BooleanVar()
                self.check_vars.append((etf["ticker"], var))
                tk.Checkbutton(
                    self.inner,
                    text=f"  {etf['ticker']:8}  {etf['name']}",
                    variable=var,
                    font=("Segoe UI", 9),
                    anchor="w",
                ).pack(fill="x")

    def _add_selected(self):
        selected = [t for t, var in self.check_vars if var.get()]
        if not selected:
            return
        existing = self.ticker_var.get().strip()
        existing_tickers = existing.upper().split() if existing else []
        combined = existing_tickers + [t for t in selected if t not in existing_tickers]
        self.ticker_var.set(" ".join(combined))
        self.destroy()

    def _clear_selection(self):
        for _, var in self.check_vars:
            var.set(False)

    def _center(self, parent):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        px = parent.winfo_x() + (parent.winfo_width() - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"+{px}+{py}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
