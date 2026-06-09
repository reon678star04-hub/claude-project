# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Streamlit-based Python web application** — a Japanese stock screener (日本株 ネットキャッシュ比率スクリーナー) that identifies JPX-listed companies where the net cash ratio (net cash / market cap) exceeds a user-defined threshold.

## Running the App

```bash
python -m streamlit run app.py
```

There is no build step, no test suite, and no linter configured. Verify changes by running the app and interacting with it.

## Architecture

`app.py` is a single-file monolithic Streamlit app. The data flow is:

1. **JPX stock list** — fetched from JPX's public Excel file or loaded from local `data_j.xls` cache
2. **Financial data** — fetched per-ticker from Yahoo Finance (yfinance), persisted in `net_cash_cache.pkl` (pickle) to avoid redundant API calls
3. **User annotations** — stored in `memo.json` (ratings + notes per ticker)
4. **Screening** — pandas DataFrame filtering by computed net cash ratio
5. **Display** — Streamlit UI with Plotly charts for per-stock financial history

### Key Financial Calculation

```
Net Cash = Current Assets + (Investment Securities × 0.7) - Total Liabilities
Net Cash Ratio = Net Cash / Market Cap
```

### Core Functions in `app.py`

| Function | Purpose |
|---|---|
| `load_jpx()` | Fetch/cache JPX stock list (Excel → DataFrame) |
| `load_cache()` / `save_cache()` | Read/write `net_cash_cache.pkl` |
| `load_memo()` / `save_memo()` | Read/write `memo.json` |
| `fetch_one(ticker)` | Pull balance sheet + market cap from yfinance |
| `get_value()` | Extract a balance sheet line item, handling multiple possible column name variants from yfinance |
| `get_history()` | Build multi-year financial history for charts |
| `show_results()` | Render the filtered results table |
| `show_detail_section()` | Render per-stock drill-down with Plotly chart and memo UI |
| `fmt_oku()` | Format yen amounts as 億円 (100M yen units) |

## Key Conventions

- **Ticker format:** 4-digit JPX code zero-padded + `.T` suffix (e.g., `1234.T`)
- **UI language:** Japanese for all user-facing labels and strings
- **yfinance column name handling:** `get_value()` accepts a list of candidate column names because yfinance returns inconsistent keys across tickers/versions — always extend this list rather than assuming a single key name
- **Caching:** `@st.cache_data` on pure data-loading functions; pickle for yfinance responses (slow API); JSON for user-editable data
- **Rate limiting:** Configurable sleep between yfinance calls (sidebar setting) to avoid hitting API limits

## Data Files

| File | Description |
|---|---|
| `data_j.xls` | Cached JPX stock list (re-fetched if stale) |
| `net_cash_cache.pkl` | Cached yfinance balance sheet data |
| `memo.json` | User ratings and notes per ticker (generated at runtime) |

The `net_cash_cache.pkl` is committed to the repo as a seed cache. When modifying financial data fetching logic, the cache may need to be cleared or migrated.
